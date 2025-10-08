#!/usr/bin/env python3
"""
Gemini API client for the transcription pipeline.

This module handles all interactions with the Gemini API.
"""

import os
import json
import time
from typing import Dict, Any, Optional
from google import genai
from google.genai import types
from dotenv import load_dotenv

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from models import ModelType


class GeminiClient:
    """
    Client for interacting with the Gemini API.
    """
    
    def __init__(self, model: ModelType = ModelType.GEMINI_2_5_PRO):
        """
        Initialize the Gemini client.
        
        Args:
            model: Model type to use for transcription
        """
        self.model = model
        self.client = self._setup_gemini()
        self.uploaded_files_cache = {}
    
    def _setup_gemini(self):
        """Initialize the Gemini API client."""
        load_dotenv()
        api_key = os.getenv('GOOGLE_API_KEY')
        
        if not api_key:
            raise ValueError("GOOGLE_API_KEY not found in environment variables")
        
        return genai.Client(api_key=api_key)
    
    def analyze_chunk_direct(self, chunk_path: str, prompt: str, raw_response_dir: str = None) -> Dict[str, Any]:
        """
        Analyze a chunk using direct bytes (for smaller files).
        
        Args:
            chunk_path: Path to the video chunk
            prompt: Prompt for transcription
            raw_response_dir: Directory to save raw API responses for debugging
            
        Returns:
            Dictionary containing analysis results
        """
        try:
            with open(chunk_path, 'rb') as f:
                chunk_data = f.read()
            
            response = self.client.models.generate_content(
                model=f'models/{self.model.value}',
                contents=types.Content(
                    parts=[
                        types.Part(
                            inline_data=types.Blob(data=chunk_data, mime_type='video/mp4')
                        ),
                        types.Part(text=prompt)
                    ]
                )
            )
            
            # Save raw response if directory is provided
            if raw_response_dir:
                self._save_raw_response(response.text, chunk_path, raw_response_dir)
            
            return self._parse_response(response.text)
            
        except Exception as e:
            return {"transcript": [], "error": str(e)}
    
    def analyze_chunk_upload(self, chunk_path: str, prompt: str, raw_response_dir: str = None) -> Dict[str, Any]:
        """
        Analyze a chunk using file upload (for larger files).
        
        Args:
            chunk_path: Path to the video chunk
            prompt: Prompt for transcription
            raw_response_dir: Directory to save raw API responses for debugging
            
        Returns:
            Dictionary containing analysis results
        """
        try:
            uploaded_file = self._get_or_upload_file(chunk_path)
            response = self.client.models.generate_content(
                model=f'models/{self.model.value}',
                contents=[
                    uploaded_file,
                    prompt
                ]
            )
            
            # Save raw response if directory is provided
            if raw_response_dir:
                self._save_raw_response(response.text, chunk_path, raw_response_dir)
            
            return self._parse_response(response.text)
            
        except Exception as e:
            return {"transcript": [], "error": str(e)}
    
    def _get_or_upload_file(self, file_path: str):
        """Get or upload file to Gemini."""
        file_hash = self._get_file_hash(file_path)
        cache_entry = self.uploaded_files_cache.get(file_hash)
        
        if cache_entry:
            # Check state
            if cache_entry.get('state') == 'ACTIVE' and 'file_id' in cache_entry:
                print(f"Using cached uploaded file: {cache_entry['file_id']}")
                # Reconstruct a file object for Gemini API
                uploaded_file = self.client.files.get(name=cache_entry['file_id'])
                if uploaded_file.state == 'ACTIVE':
                    return uploaded_file
                else:
                    print(f"Cached file {cache_entry['file_id']} not ACTIVE, re-uploading...")
        
        # Check file size before uploading
        file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
        print(f"File size: {file_size_mb:.1f}MB")
        
        print("Uploading new file...")
        try:
            uploaded_file = self.client.files.upload(file=file_path)
        except Exception as e:
            print(f"Upload failed: {str(e)}")
            raise Exception(f"Failed to upload file {file_path}: {str(e)}")
        
        # Wait for file processing
        print("Waiting for file processing...")
        max_wait_time = 300  # 5 minutes
        start_time = time.time()
        
        while uploaded_file.state == "PROCESSING":
            if time.time() - start_time > max_wait_time:
                raise Exception(f"File processing timeout after {max_wait_time} seconds")
            print("File is still processing...")
            time.sleep(5)
            uploaded_file = self.client.files.get(name=uploaded_file.name)
        
        if uploaded_file.state != "ACTIVE":
            error_msg = f"File processing failed. State: {uploaded_file.state}"
            if hasattr(uploaded_file, 'error') and uploaded_file.error:
                error_msg += f", Error: {uploaded_file.error}"
            print(error_msg)
            raise Exception(error_msg)
        
        # Save to cache
        self.uploaded_files_cache[file_hash] = {
            'file_id': uploaded_file.name,
            'state': uploaded_file.state
        }
        
        return uploaded_file
    
    def _get_file_hash(self, file_path: str) -> str:
        """Calculate file hash for caching."""
        import hashlib
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    
    def _save_raw_response(self, response_text: str, chunk_path: str, raw_response_dir: str):
        """
        Save raw API response to file for debugging.
        
        Args:
            response_text: Raw response text from API
            chunk_path: Path to the video chunk (used for naming)
            raw_response_dir: Directory to save the raw response
        """
        try:
            import os
            from pathlib import Path
            import datetime
            
            # Create raw responses directory if it doesn't exist
            raw_dir = Path(raw_response_dir)
            raw_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate filename based on chunk path and timestamp
            chunk_name = Path(chunk_path).stem
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]  # Include milliseconds
            filename = f"{chunk_name}_raw_response_{timestamp}.json"
            
            # Save the raw response
            raw_response_path = raw_dir / filename
            
            # Create a structured response object
            raw_response_data = {
                "timestamp": datetime.datetime.now().isoformat(),
                "chunk_path": str(chunk_path),
                "chunk_name": chunk_name,
                "raw_response": response_text,
                "response_length": len(response_text),
                "model": self.model.value
            }
            
            with open(raw_response_path, 'w', encoding='utf-8') as f:
                json.dump(raw_response_data, f, indent=2, ensure_ascii=False)
            
            print(f"Raw API response saved to: {raw_response_path}")
            
        except Exception as e:
            print(f"Warning: Failed to save raw response: {str(e)}")

    def _parse_response(self, response_text: str) -> Dict[str, Any]:
        """
        Parse Gemini API response text.
        
        Args:
            response_text: Raw response text from Gemini
            
        Returns:
            Parsed response dictionary
        """
        try:
            text = response_text.strip()
            print(f"Raw response: {text[:200]}...")
            
            if text.startswith("```json"):
                text = text[7:]
            if text.endswith("```"):
                text = text[:-3]
            
            result = json.loads(text.strip())
            
            # Handle case where result is a list (API might return array directly)
            if isinstance(result, list):
                print("Result is a list, converting to dict")
                result = {"transcript": result}
            
            # Ensure result has the expected structure
            if not isinstance(result, dict):
                print(f"Unexpected result type: {type(result)}")
                return {"transcript": [], "error": f"Unexpected result type: {type(result)}"}
            
            if "transcript" not in result:
                print("No transcript field in result")
                return {"transcript": [], "error": "No transcript field in response"}
            
            return result
            
        except json.JSONDecodeError as e:
            print(f"Failed to parse JSON response: {str(e)}")
            print(f"Response text: {response_text}")
            return {"transcript": [], "error": str(e)}
        except Exception as e:
            print(f"Unexpected error processing response: {str(e)}")
            return {"transcript": [], "error": str(e)}
    
    def cleanup_uploaded_files(self):
        """Delete all uploaded files from Google."""
        if not self.uploaded_files_cache:
            print("No uploaded files to clean up.")
            return
        
        print(f"\nCleaning up {len(self.uploaded_files_cache)} uploaded files from Google...")
        deleted_count = 0
        failed_count = 0
        
        for file_hash, cache_entry in self.uploaded_files_cache.items():
            file_id = cache_entry.get('file_id')
            if file_id:
                try:
                    print(f"Deleting file: {file_id}")
                    self.client.files.delete(name=file_id)
                    deleted_count += 1
                except Exception as e:
                    print(f"Failed to delete file {file_id}: {str(e)}")
                    failed_count += 1
        
        print(f"Cleanup completed: {deleted_count} files deleted, {failed_count} failed")
        
        # Clear the cache after cleanup
        self.uploaded_files_cache.clear()
