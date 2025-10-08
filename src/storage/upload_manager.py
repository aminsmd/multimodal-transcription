#!/usr/bin/env python3
"""
Upload management for the transcription pipeline.

This module handles file uploads to external services and upload caching.
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Any

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils import get_file_hash


class UploadManager:
    """
    Manages file uploads and upload caching.
    """
    
    def __init__(self, cache_dir: Path):
        """
        Initialize the upload manager.
        
        Args:
            cache_dir: Directory for storing upload cache
        """
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(exist_ok=True)
        self.upload_cache_path = self.cache_dir / "upload_cache.json"
        self.uploaded_files_cache = self._load_upload_cache()
    
    def _load_upload_cache(self) -> Dict[str, Dict]:
        """
        Load file upload cache.
        
        Returns:
            Upload cache dictionary
        """
        if self.upload_cache_path.exists():
            try:
                with open(self.upload_cache_path, 'r') as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}
    
    def _save_upload_cache(self):
        """Save file upload cache."""
        with open(self.upload_cache_path, 'w') as f:
            json.dump(self.uploaded_files_cache, f, indent=2)
    
    def get_uploaded_file(self, file_path: str) -> Optional[Dict]:
        """
        Get information about an uploaded file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Upload information if file was uploaded, None otherwise
        """
        file_hash = get_file_hash(file_path)
        return self.uploaded_files_cache.get(file_hash)
    
    def cache_uploaded_file(self, file_path: str, file_id: str, state: str = "ACTIVE"):
        """
        Cache information about an uploaded file.
        
        Args:
            file_path: Path to the file
            file_id: ID of the uploaded file
            state: State of the uploaded file
        """
        file_hash = get_file_hash(file_path)
        self.uploaded_files_cache[file_hash] = {
            'file_id': file_id,
            'state': state,
            'file_path': file_path
        }
        self._save_upload_cache()
    
    def is_file_uploaded(self, file_path: str) -> bool:
        """
        Check if a file has been uploaded.
        
        Args:
            file_path: Path to the file
            
        Returns:
            True if file has been uploaded, False otherwise
        """
        file_info = self.get_uploaded_file(file_path)
        return file_info is not None and file_info.get('state') == 'ACTIVE'
    
    def get_upload_stats(self) -> Dict[str, Any]:
        """
        Get upload statistics.
        
        Returns:
            Dictionary containing upload statistics
        """
        total_uploads = len(self.uploaded_files_cache)
        active_uploads = sum(1 for info in self.uploaded_files_cache.values() 
                           if info.get('state') == 'ACTIVE')
        
        stats = {
            "total_uploads": total_uploads,
            "active_uploads": active_uploads,
            "inactive_uploads": total_uploads - active_uploads,
            "cache_file": str(self.upload_cache_path),
            "cache_size_mb": os.path.getsize(self.upload_cache_path) / (1024 * 1024) if self.upload_cache_path.exists() else 0
        }
        
        return stats
    
    def cleanup_upload_cache(self, remove_inactive: bool = True) -> int:
        """
        Clean up upload cache.
        
        Args:
            remove_inactive: Whether to remove inactive uploads
            
        Returns:
            Number of entries cleaned up
        """
        cleaned_count = 0
        original_count = len(self.uploaded_files_cache)
        
        if remove_inactive:
            # Remove inactive uploads
            active_uploads = {}
            for file_hash, info in self.uploaded_files_cache.items():
                if info.get('state') == 'ACTIVE':
                    active_uploads[file_hash] = info
                else:
                    cleaned_count += 1
            
            self.uploaded_files_cache = active_uploads
        else:
            # Remove all uploads
            cleaned_count = len(self.uploaded_files_cache)
            self.uploaded_files_cache = {}
        
        if cleaned_count > 0:
            self._save_upload_cache()
            print(f"Cleaned up {cleaned_count} upload cache entries")
        
        return cleaned_count
    
    def list_uploaded_files(self, state_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List uploaded files.
        
        Args:
            state_filter: Filter by upload state (optional)
            
        Returns:
            List of uploaded file information
        """
        uploaded_files = []
        
        for file_hash, info in self.uploaded_files_cache.items():
            if state_filter is None or info.get('state') == state_filter:
                file_info = {
                    "file_hash": file_hash,
                    "file_id": info.get('file_id'),
                    "state": info.get('state'),
                    "file_path": info.get('file_path'),
                    "cached": True
                }
                uploaded_files.append(file_info)
        
        return uploaded_files
    
    def remove_uploaded_file(self, file_path: str) -> bool:
        """
        Remove a file from upload cache.
        
        Args:
            file_path: Path to the file
            
        Returns:
            True if file was removed, False if not found
        """
        file_hash = get_file_hash(file_path)
        
        if file_hash in self.uploaded_files_cache:
            del self.uploaded_files_cache[file_hash]
            self._save_upload_cache()
            return True
        
        return False
    
    def update_upload_state(self, file_path: str, new_state: str) -> bool:
        """
        Update the state of an uploaded file.
        
        Args:
            file_path: Path to the file
            new_state: New state for the file
            
        Returns:
            True if state was updated, False if file not found
        """
        file_hash = get_file_hash(file_path)
        
        if file_hash in self.uploaded_files_cache:
            self.uploaded_files_cache[file_hash]['state'] = new_state
            self._save_upload_cache()
            return True
        
        return False
    
    def get_upload_cache_info(self) -> Dict[str, Any]:
        """
        Get information about the upload cache.
        
        Returns:
            Dictionary containing cache information
        """
        return {
            "cache_file": str(self.upload_cache_path),
            "cache_exists": self.upload_cache_path.exists(),
            "cache_size_mb": os.path.getsize(self.upload_cache_path) / (1024 * 1024) if self.upload_cache_path.exists() else 0,
            "total_entries": len(self.uploaded_files_cache),
            "active_entries": sum(1 for info in self.uploaded_files_cache.values() if info.get('state') == 'ACTIVE')
        }
