#!/usr/bin/env python3
"""
Standalone Video Transcription Pipeline

A clean and simple pipeline that:
1. Processes video into smaller chunks
2. Generates multimodal transcriptions for chunks (parallel processing)
3. Outputs full transcript without segmentation

Usage:
    python transcription_pipeline.py --input video.mp4 --chunk-size 300
"""

import os
import json
import datetime
import argparse
import tempfile
import hashlib
import subprocess
from typing import Dict, List, Optional, Tuple, Union
from pathlib import Path
from moviepy import VideoFileClip
from google import genai
from google.genai import types
from dotenv import load_dotenv
import time
import concurrent.futures

# Import our data models
from models import (
    TranscriptionConfig, ModelType, TranscriptType,
    FullTranscript, CleanTranscript, PipelineResults,
    CacheEntry, ChunkMetadata, UploadedFileInfo
)

# Import file management
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from core.file_manager import PipelineFileManager, create_file_manager
from utils import get_video_duration, validate_video_file, format_timestamp, parse_timestamp

class TranscriptionPipeline:
    """
    A standalone video transcription pipeline that focuses only on transcription.
    """
    
    def __init__(self, base_dir: str = "outputs", data_dir: str = "data", enable_file_management: bool = True):
        """
        Initialize the transcription pipeline.
        
        Args:
            base_dir: Base directory for storing all outputs
            data_dir: Base directory for data management
            enable_file_management: Whether to enable automatic file management
        """
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(exist_ok=True)
        
        # Create pipeline_runs directory to organize all runs
        self.pipeline_runs_dir = self.base_dir / "pipeline_runs"
        self.pipeline_runs_dir.mkdir(exist_ok=True)
        
        # Create timestamped run directory within pipeline_runs
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        self.run_id = f"transcription_run_{timestamp}"
        self.run_dir = self.pipeline_runs_dir / self.run_id
        self.run_dir.mkdir(exist_ok=True)
        
        # Create structured directories within the run
        (self.run_dir / "videos").mkdir(exist_ok=True)
        (self.run_dir / "chunks").mkdir(exist_ok=True)
        (self.run_dir / "transcripts").mkdir(exist_ok=True)
        (self.run_dir / "cache").mkdir(exist_ok=True)
        (self.run_dir / "logs").mkdir(exist_ok=True)
        
        # Initialize Gemini client
        self.client = self._setup_gemini()
        
        # File upload cache
        self.upload_cache_path = self.run_dir / "cache" / "upload_cache.json"
        self.uploaded_files_cache = self._load_upload_cache()
        
        # Global transcript cache for checking existing transcripts
        self.global_cache_dir = self.base_dir / "transcript_cache"
        self.global_cache_dir.mkdir(exist_ok=True)
        
        # Initialize file manager if enabled
        self.file_manager = None
        if enable_file_management:
            self.file_manager = create_file_manager(data_dir, auto_organize=True)
            print(f"File management enabled: {data_dir}")
        
        # Create run metadata
        self.run_metadata = {
            "run_id": self.run_id,
            "start_time": datetime.datetime.now().isoformat(),
            "base_dir": str(self.base_dir),
            "pipeline_runs_dir": str(self.pipeline_runs_dir),
            "run_dir": str(self.run_dir),
            "file_management_enabled": enable_file_management
        }
        
        print(f"Transcription pipeline run initialized: {self.run_id}")
        print(f"Pipeline runs directory: {self.pipeline_runs_dir}")
        print(f"Run directory: {self.run_dir}")
    
    def _setup_gemini(self):
        """Initialize the Gemini API client."""
        load_dotenv()
        api_key = os.getenv('GOOGLE_API_KEY')
        
        if not api_key:
            raise ValueError("GOOGLE_API_KEY not found in environment variables")
        
        return genai.Client(api_key=api_key)
    
    def _load_upload_cache(self):
        """Load file upload cache."""
        if self.upload_cache_path.exists():
            try:
                with open(self.upload_cache_path, 'r') as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}
    
    def _save_upload_cache(self):
        """Save file upload cache."""
        self.upload_cache_path.parent.mkdir(exist_ok=True)
        with open(self.upload_cache_path, 'w') as f:
            json.dump(self.uploaded_files_cache, f, indent=2)
    
    def _cleanup_uploaded_files(self):
        """Delete all uploaded files from Google at the end of pipeline."""
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
        self._save_upload_cache()
    
    def _get_config_hash(self, config: TranscriptionConfig) -> str:
        """Generate a hash for the current configuration."""
        return config.get_config_hash()
    
    def _get_video_hash(self, video_path: str) -> str:
        """Get hash of video file for cache key."""
        return self._get_file_hash(video_path)
    
    def _check_existing_transcript(self, video_id: str, config: TranscriptionConfig) -> Optional[Dict]:
        """Check if a transcript already exists for this video with the same configuration."""
        config_hash = config.get_config_hash()
        cache_file = self.global_cache_dir / f"{video_id}_{config_hash}.json"
        
        if cache_file.exists():
            try:
                with open(cache_file, 'r') as f:
                    cached_data = json.load(f)
                
                # Verify the transcript file still exists
                transcript_path = Path(cached_data.get('transcript_path', ''))
                if transcript_path.exists():
                    print(f"Found existing transcript for {video_id} with matching configuration")
                    print(f"Transcript path: {transcript_path}")
                    print(f"Generated: {cached_data.get('generation_date', 'Unknown')}")
                    return cached_data
                else:
                    print(f"Cached transcript file not found: {transcript_path}")
                    # Remove stale cache entry
                    cache_file.unlink()
            except Exception as e:
                print(f"Error reading cached transcript: {e}")
                # Remove corrupted cache entry
                cache_file.unlink()
        
        return None
    
    def _save_transcript_cache(self, video_id: str, config_hash: str, transcript_path: str, config: Dict):
        """Save transcript to global cache."""
        cache_data = {
            "video_id": video_id,
            "config_hash": config_hash,
            "transcript_path": str(transcript_path),
            "generation_date": datetime.datetime.now().isoformat(),
            "configuration": config
        }
        
        cache_file = self.global_cache_dir / f"{video_id}_{config_hash}.json"
        with open(cache_file, 'w') as f:
            json.dump(cache_data, f, indent=2)
        
        print(f"Transcript cached: {cache_file}")
    
    def _get_pipeline_config(self, video_input: str, chunk_duration: int, max_workers: int) -> Dict:
        """Get current pipeline configuration."""
        return {
            "video_input": video_input,
            "chunk_duration": chunk_duration,
            "max_workers": max_workers,
            "pipeline_version": "1.0",  # Version for future compatibility
            "model": "gemini-2.5-pro"
        }
    
    def list_cached_transcripts(self) -> List[Dict]:
        """List all cached transcripts."""
        cached_transcripts = []
        
        for cache_file in self.global_cache_dir.glob("*.json"):
            try:
                with open(cache_file, 'r') as f:
                    cache_data = json.load(f)
                
                # Check if transcript file still exists
                transcript_path = Path(cache_data.get('transcript_path', ''))
                if transcript_path.exists():
                    cached_transcripts.append({
                        "video_id": cache_data.get('video_id'),
                        "config_hash": cache_data.get('config_hash'),
                        "transcript_path": str(transcript_path),
                        "generation_date": cache_data.get('generation_date'),
                        "configuration": cache_data.get('configuration', {}),
                        "cache_file": str(cache_file)
                    })
                else:
                    # Remove stale cache entry
                    cache_file.unlink()
            except Exception as e:
                print(f"Error reading cache file {cache_file}: {e}")
                # Remove corrupted cache entry
                cache_file.unlink()
        
        return cached_transcripts
    
    def clear_transcript_cache(self, video_id: Optional[str] = None) -> int:
        """Clear transcript cache. If video_id is provided, clear only that video's cache."""
        cleared_count = 0
        
        if video_id:
            # Clear specific video's cache
            for cache_file in self.global_cache_dir.glob(f"{video_id}_*.json"):
                cache_file.unlink()
                cleared_count += 1
        else:
            # Clear all cache
            for cache_file in self.global_cache_dir.glob("*.json"):
                cache_file.unlink()
                cleared_count += 1
        
        print(f"Cleared {cleared_count} cached transcripts")
        return cleared_count
    
    def _get_file_hash(self, file_path: str) -> str:
        """Calculate file hash for caching."""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    
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
        self._save_upload_cache()
        return uploaded_file
    
    def get_video_id(self, video_input: str) -> str:
        """Generate unique video ID from local video file path."""
        return Path(video_input).stem
    
    def copy_video(self, video_path: str, video_id: str) -> str:
        """Copy local video to pipeline directory."""
        dest_path = self.run_dir / "videos" / f"{video_id}.mp4"
        
        if dest_path.exists():
            print(f"Video already exists at {dest_path}")
            return str(dest_path)
        
        print(f"Copying video: {video_path}")
        import shutil
        shutil.copy2(video_path, dest_path)
        
        return str(dest_path)
    
    def _calculate_size_based_chunks(self, video_path: str, duration: float, target_size_mb: int) -> Tuple[List[Tuple[float, float]], float]:
        """
        Calculate chunk boundaries based on target file size.
        
        This method estimates chunk boundaries by sampling the video at different
        time points and measuring file sizes to approximate the target chunk size.
        """
        print(f"Calculating size-based chunk boundaries for target size: {target_size_mb}MB")
        
        # Get the original video file size
        original_size_mb = os.path.getsize(video_path) / (1024 * 1024)
        print(f"Original video size: {original_size_mb:.1f}MB")
        
        # Estimate total number of chunks needed
        estimated_chunks = max(1, int(original_size_mb / target_size_mb))
        chunk_duration_estimate = duration / estimated_chunks
        
        print(f"Estimated {estimated_chunks} chunks with ~{chunk_duration_estimate:.1f}s duration each")
        
        # Sample a few chunks to get better size estimates
        sample_chunks = []
        sample_size = min(3, estimated_chunks)  # Sample up to 3 chunks
        
        for i in range(sample_size):
            start_time = i * chunk_duration_estimate
            end_time = min((i + 1) * chunk_duration_estimate, duration)
            
            # Create a temporary chunk to measure size
            temp_chunk_path = self.run_dir / "chunks" / f"temp_sample_{i}.mp4"
            try:
                cmd = [
                    'ffmpeg', '-i', video_path,
                    '-ss', str(start_time),
                    '-t', str(end_time - start_time),
                    '-c', 'copy',
                    '-avoid_negative_ts', 'make_zero',
                    str(temp_chunk_path),
                    '-y'
                ]
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode == 0 and temp_chunk_path.exists():
                    chunk_size_mb = os.path.getsize(temp_chunk_path) / (1024 * 1024)
                    sample_chunks.append((start_time, end_time, chunk_size_mb))
                    print(f"Sample chunk {i}: {start_time:.1f}s-{end_time:.1f}s = {chunk_size_mb:.1f}MB")
                # Clean up temp file
                if temp_chunk_path.exists():
                    temp_chunk_path.unlink()
            except Exception as e:
                print(f"Error creating sample chunk {i}: {e}")
        
        # Calculate average size per second from samples
        if sample_chunks:
            total_duration = sum(end - start_time for start_time, end, _ in sample_chunks)
            total_size = sum(size for _, _, size in sample_chunks)
            size_per_second = total_size / total_duration if total_duration > 0 else target_size_mb / 60
        else:
            # Fallback: assume uniform bitrate
            size_per_second = original_size_mb / duration
        
        print(f"Estimated size per second: {size_per_second:.2f}MB/s")
        
        # Calculate chunk boundaries
        chunk_boundaries = []
        current_time = 0.0
        
        while current_time < duration:
            # Calculate target duration for this chunk
            remaining_duration = duration - current_time
            target_duration = target_size_mb / size_per_second
            
            # Don't exceed remaining duration
            chunk_duration = min(target_duration, remaining_duration)
            end_time = current_time + chunk_duration
            
            chunk_boundaries.append((current_time, end_time))
            current_time = end_time
        
        print(f"Calculated {len(chunk_boundaries)} chunk boundaries")
        
        # Calculate average chunk duration from the actual boundaries
        if chunk_boundaries:
            total_duration = sum(end - start for start, end in chunk_boundaries)
            average_chunk_duration = total_duration / len(chunk_boundaries)
        else:
            average_chunk_duration = 0.0
        
        print(f"Average chunk duration: {average_chunk_duration:.1f}s")
        return chunk_boundaries, average_chunk_duration
    
    def create_chunks(self, video_path: str, video_id: str, chunk_duration: int, chunk_size_mb: Optional[int] = None) -> Dict:
        """Create video chunks."""
        chunks_dir = self.run_dir / "chunks" / video_id
        chunks_dir.mkdir(exist_ok=True)
        
        # Check if chunks already exist
        metadata_path = self.run_dir / "chunks" / f"{video_id}_metadata.json"
        if metadata_path.exists():
            with open(metadata_path, 'r') as f:
                metadata = json.load(f)
            
            # Check if all chunk files exist
            all_chunks_exist = True
            for chunk_info in metadata["chunks"]:
                chunk_path = chunks_dir / f"chunk_{chunk_info['start_time']}_{chunk_info['end_time']}.mp4"
                if not chunk_path.exists():
                    all_chunks_exist = False
                    break
            
            if all_chunks_exist:
                print(f"Chunks already exist for video {video_id}")
                return metadata
        
        print(f"Creating chunks from video: {video_path}")
        
        with VideoFileClip(video_path) as video:
            duration = video.duration
            chunks = []
            
            if chunk_size_mb is not None:
                # Size-based chunking
                print(f"Using size-based chunking with target size: {chunk_size_mb}MB")
                chunk_boundaries, calculated_chunk_duration = self._calculate_size_based_chunks(video_path, duration, chunk_size_mb)
                # Use the calculated average chunk duration instead of the config value
                effective_chunk_duration = int(calculated_chunk_duration)
            else:
                # Time-based chunking (original logic)
                print(f"Using time-based chunking with duration: {chunk_duration}s")
                chunk_boundaries = []
                for i in range(0, int(duration), chunk_duration):
                    start_time = i
                    end_time = min(i + chunk_duration, duration)
                    chunk_boundaries.append((start_time, end_time))
                effective_chunk_duration = chunk_duration
            
            for start_time, end_time in chunk_boundaries:
                
                chunk_path = chunks_dir / f"chunk_{start_time}_{end_time}.mp4"
                
                # Extract chunk using ffmpeg for better audio handling
                try:
                    # Use ffmpeg directly for more reliable audio processing
                    cmd = [
                        'ffmpeg', '-i', video_path,
                        '-ss', str(start_time),
                        '-t', str(end_time - start_time),
                        '-c', 'copy',  # Copy streams without re-encoding
                        '-avoid_negative_ts', 'make_zero',
                        str(chunk_path),
                        '-y'  # Overwrite output file
                    ]
                    result = subprocess.run(cmd, capture_output=True, text=True)
                    if result.returncode != 0:
                        print(f"ffmpeg failed for chunk {start_time}-{end_time}: {result.stderr}")
                        # Fallback to MoviePy without audio
                        chunk_video = video.subclipped(start_time, end_time)
                        chunk_video.write_videofile(str(chunk_path), audio=False, logger=None)
                        chunk_video.close()
                    else:
                        print(f"Successfully created chunk {start_time}-{end_time} with audio")
                except Exception as e:
                    print(f"Error creating chunk {start_time}-{end_time}: {str(e)}")
                    # Fallback to MoviePy without audio
                    chunk_video = video.subclipped(start_time, end_time)
                    chunk_video.write_videofile(str(chunk_path), audio=False, logger=None)
                    chunk_video.close()
                
                chunks.append({
                    "start_time": start_time,
                    "end_time": end_time,
                    "duration": end_time - start_time,
                    "path": str(chunk_path)
                })
        
        # Create metadata
        metadata = {
            "video_id": video_id,
            "original_path": video_path,
            "total_duration": duration,
            "chunk_duration": effective_chunk_duration,
            "chunk_size_mb": chunk_size_mb,
            "chunking_method": "size_based" if chunk_size_mb is not None else "time_based",
            "num_chunks": len(chunks),
            "processing_date": datetime.datetime.now().isoformat(),
            "chunks": chunks
        }
        
        # Save metadata
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        print(f"Created {len(chunks)} chunks")
        return metadata
    
    def get_transcript_prompt(self, video_duration: float = 0, chunk_start: int = 0, chunk_end: int = 0) -> str:
        """Get transcript generation prompt."""
        # Calculate chunk duration
        chunk_duration = chunk_end - chunk_start
        chunk_duration_minutes = int(chunk_duration // 60)
        chunk_duration_seconds = int(chunk_duration % 60)
        chunk_duration_str = f"{chunk_duration_minutes:02d}:{chunk_duration_seconds:02d}"
        
        # Calculate chunk start time in MM:SS format
        chunk_start_minutes = int(chunk_start // 60)
        chunk_start_seconds = int(chunk_start % 60)
        chunk_start_str = f"{chunk_start_minutes:02d}:{chunk_start_seconds:02d}"
        
        # Calculate chunk end time in MM:SS format
        chunk_end_minutes = int(chunk_end // 60)
        chunk_end_seconds = int(chunk_end % 60)
        chunk_end_str = f"{chunk_end_minutes:02d}:{chunk_end_seconds:02d}"
        
        # Load the base prompt from the prompt.txt file
        prompt_file_path = Path(__file__).parent / "prompt.txt"
        try:
            with open(prompt_file_path, 'r', encoding='utf-8') as f:
                base_prompt = f.read()
        except FileNotFoundError:
            # Fallback to hardcoded prompt if file not found
            base_prompt = """Role
You are an advanced transcription system tasked with analyzing classroom recordings to produce accurate and detailed transcripts. Your goal is to capture all spoken dialogue and key contextual events while maintaining strict formatting and complete time coverage.

Task Breakdown
1. Transcription of Spoken Text
   * Transcribe every spoken word verbatim, including filler words and grammatical errors.
   * Use placeholders for unclear or missing audio:
      * [Unintelligible] → Sound is present, but words are unclear.
      * [Inaudible] → Sound is completely missing or inaudible.
   * For non-English speech:
      * Transcribe phonetically.
      * Include English translation in parentheses.
Example: "Necesitas ayuda? (Do you need help?)"
   2. Speaker Identification
   * Use diarization techniques (tone, pitch, volume, visual cues).
   * Teacher: Use "teacher".
   * Students: Use "student_A", "student_B", etc., incrementing letters as new speakers appear.
   * Unclear identity: Use "speaker".
   * Group speech: Use "multiple_students".
   3. Event Annotation
   * Add "event" entries only for notable changes, such as but not limited to:
   * Instructional content change:
e.g., "Teacher shows a slide of 9 hearts on the screen".
   * Participant & Activity Structure Changes:
e.g., "Teacher transitions from lecture to facilitating small group work".
   * Interactions with Learning Materials:
e.g., "Students are given calculators".
      * What to AVOID in Context:
      * Irrelevant physical descriptions: Do NOT describe clothing, hairstyles, or general room appearance.
      4. Complete Time Coverage
      * The entire video must be covered from 00:00 to {chunk_duration_str}.
      * No gaps allowed—all time periods must be accounted for.
      * Each entry must have both "start_time" and "end_time" fields.

Output Format
The transcript must be returned as valid JSON with no additional text before or after.
{
    "transcript": [
        {
            "type": "utterance",
            "start_time": "MM:SS",
            "end_time": "MM:SS",
            "speaker": "Speaker identification",
            "spoken_text": "Exact transcription of what is said"
        },
        {
            "type": "event",
            "start_time": "MM:SS",
            "end_time": "MM:SS",
            "event_description": "Description of a specific, non-verbal change in activity, pedagogy, or materials"
        }
    ]
}

Requirements
      * Every entry must include start_time and end_time.
      * No unaccounted time gaps:
      * All speech must be covered by either words, [Unintelligible], or [Inaudible].
      * Maintain consistent speaker identifiers throughout the entire video.
      * Only include "event" entries when a new, meaningful change occurs.
      * JSON must be properly formatted and valid.
      * Final response must not include any explanation or extra text, just the JSON object."""
        
        # Replace the duration placeholder with the actual chunk duration
        base_prompt = base_prompt.replace("{duration_str}", chunk_duration_str)
        
        # Add segment-specific information
        base_prompt += f"\n\nSEGMENT INFORMATION:\n- This is a {chunk_duration_str} segment from a longer video (segment {chunk_start_str} to {chunk_end_str})\n- Your transcription MUST cover the ENTIRE duration of this segment from 00:00 to {chunk_duration_str}\n- Include entries for ALL time periods, even when nothing is being said or audio is not recognizable"
        
        return base_prompt

    def format_timestamp(self, seconds: float) -> str:
        """Format seconds into HH:MM:SS.mmm timestamp."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        seconds_float = seconds % 60
        seconds_int = int(seconds_float)
        milliseconds = int((seconds_float - seconds_int) * 1000)
        
        return f"{hours:02d}:{minutes:02d}:{seconds_int:02d}.{milliseconds:03d}"
    
    def _process_transcript_entry(self, entry: dict, i: int, start_time: int, end_time: int) -> dict:
        """Process a single transcript entry to handle different formats and add required fields."""
        if isinstance(entry, dict):
            # Handle new format with type field (utterance/event) and start_time/end_time
            if "type" in entry and "start_time" in entry and "end_time" in entry:
                try:
                    chunk_start_time = self.parse_timestamp(entry["start_time"])
                    chunk_end_time = self.parse_timestamp(entry["end_time"])
                    absolute_start_time = start_time + chunk_start_time
                    absolute_end_time = start_time + chunk_end_time
                    entry["absolute_start_time"] = absolute_start_time
                    entry["absolute_end_time"] = absolute_end_time
                    entry["absolute_start_timestamp"] = self.format_timestamp(absolute_start_time)
                    entry["absolute_end_timestamp"] = self.format_timestamp(absolute_end_time)
                    # Keep the original time field for backward compatibility (use start_time)
                    entry["time"] = entry["start_time"]
                    entry["absolute_time"] = absolute_start_time
                    entry["absolute_timestamp"] = self.format_timestamp(absolute_start_time)
                    
                    # Handle different entry types
                    if entry["type"] == "utterance":
                        # Ensure required fields for utterance
                        if "speaker" not in entry:
                            entry["speaker"] = "speaker"
                        if "spoken_text" not in entry:
                            entry["spoken_text"] = ""
                        # Add visual_description for backward compatibility
                        if "visual_description" not in entry:
                            entry["visual_description"] = ""
                    elif entry["type"] == "event":
                        # Ensure required fields for event
                        if "event_description" not in entry:
                            entry["event_description"] = ""
                        # Add speaker and spoken_text for backward compatibility
                        if "speaker" not in entry:
                            entry["speaker"] = ""
                        if "spoken_text" not in entry:
                            entry["spoken_text"] = ""
                        # Map event_description to visual_description for backward compatibility
                        if "visual_description" not in entry:
                            entry["visual_description"] = entry.get("event_description", "")
                            
                except Exception as e:
                    print(f"Warning: Failed to parse timestamps '{entry['start_time']}' or '{entry['end_time']}' for entry {i} in chunk {start_time}-{end_time}: {str(e)}")
                    # Fallback: use chunk start time
                    entry["absolute_start_time"] = start_time
                    entry["absolute_end_time"] = start_time
                    entry["absolute_start_timestamp"] = self.format_timestamp(start_time)
                    entry["absolute_end_timestamp"] = self.format_timestamp(start_time)
                    entry["time"] = "00:00"
                    entry["absolute_time"] = start_time
                    entry["absolute_timestamp"] = self.format_timestamp(start_time)
            # Handle legacy format with start_time and end_time (no type field)
            elif "start_time" in entry and "end_time" in entry:
                try:
                    chunk_start_time = self.parse_timestamp(entry["start_time"])
                    chunk_end_time = self.parse_timestamp(entry["end_time"])
                    absolute_start_time = start_time + chunk_start_time
                    absolute_end_time = start_time + chunk_end_time
                    entry["absolute_start_time"] = absolute_start_time
                    entry["absolute_end_time"] = absolute_end_time
                    entry["absolute_start_timestamp"] = self.format_timestamp(absolute_start_time)
                    entry["absolute_end_timestamp"] = self.format_timestamp(absolute_end_time)
                    # Keep the original time field for backward compatibility (use start_time)
                    entry["time"] = entry["start_time"]
                    entry["absolute_time"] = absolute_start_time
                    entry["absolute_timestamp"] = self.format_timestamp(absolute_start_time)
                    # Add type field for new format compatibility
                    if "type" not in entry:
                        entry["type"] = "utterance"
                except Exception as e:
                    print(f"Warning: Failed to parse timestamps '{entry['start_time']}' or '{entry['end_time']}' for entry {i} in chunk {start_time}-{end_time}: {str(e)}")
                    # Fallback: use chunk start time
                    entry["absolute_start_time"] = start_time
                    entry["absolute_end_time"] = start_time
                    entry["absolute_start_timestamp"] = self.format_timestamp(start_time)
                    entry["absolute_end_timestamp"] = self.format_timestamp(start_time)
                    entry["time"] = "00:00"
                    entry["absolute_time"] = start_time
                    entry["absolute_timestamp"] = self.format_timestamp(start_time)
            # Handle legacy format with just "time"
            elif "time" in entry:
                try:
                    chunk_time = self.parse_timestamp(entry["time"])
                    absolute_time = start_time + chunk_time
                    entry["absolute_time"] = absolute_time
                    entry["absolute_timestamp"] = self.format_timestamp(absolute_time)
                    # Add start_time and end_time for consistency
                    entry["start_time"] = entry["time"]
                    entry["end_time"] = entry["time"]
                    entry["absolute_start_time"] = absolute_time
                    entry["absolute_end_time"] = absolute_time
                    entry["absolute_start_timestamp"] = self.format_timestamp(absolute_time)
                    entry["absolute_end_timestamp"] = self.format_timestamp(absolute_time)
                    # Add type field for new format compatibility
                    if "type" not in entry:
                        entry["type"] = "utterance"
                except Exception as e:
                    print(f"Warning: Failed to parse timestamp '{entry['time']}' for entry {i} in chunk {start_time}-{end_time}: {str(e)}")
                    # Fallback: use chunk start time
                    entry["absolute_time"] = start_time
                    entry["absolute_timestamp"] = self.format_timestamp(start_time)
                    entry["start_time"] = "00:00"
                    entry["end_time"] = "00:00"
                    entry["absolute_start_time"] = start_time
                    entry["absolute_end_time"] = start_time
                    entry["absolute_start_timestamp"] = self.format_timestamp(start_time)
                    entry["absolute_end_timestamp"] = self.format_timestamp(start_time)
            else:
                print(f"Warning: Entry {i} in chunk {start_time}-{end_time} missing timestamp fields")
                # Add default timestamps for entries without time fields
                entry["time"] = "00:00"
                entry["start_time"] = "00:00"
                entry["end_time"] = "00:00"
                entry["absolute_time"] = start_time
                entry["absolute_timestamp"] = self.format_timestamp(start_time)
                entry["absolute_start_time"] = start_time
                entry["absolute_end_time"] = start_time
                entry["absolute_start_timestamp"] = self.format_timestamp(start_time)
                entry["absolute_end_timestamp"] = self.format_timestamp(start_time)
                # Add type field for new format compatibility
                if "type" not in entry:
                    entry["type"] = "utterance"
        
        return entry
    
    def _save_raw_response(self, response_text: str, chunk_path: str, start_time: int, end_time: int):
        """
        Save raw API response to file for debugging.
        
        Args:
            response_text: Raw response text from API
            chunk_path: Path to the video chunk
            start_time: Start time of the chunk
            end_time: End time of the chunk
        """
        try:
            import datetime
            from pathlib import Path
            
            # Create raw responses directory
            raw_responses_dir = self.run_dir / "raw_responses"
            raw_responses_dir.mkdir(exist_ok=True)
            
            # Generate filename
            chunk_name = Path(chunk_path).stem
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]  # Include milliseconds
            filename = f"{chunk_name}_{start_time}_{end_time}_raw_response_{timestamp}.json"
            
            # Save the raw response
            raw_response_path = raw_responses_dir / filename
            
            # Create a structured response object
            raw_response_data = {
                "timestamp": datetime.datetime.now().isoformat(),
                "chunk_path": str(chunk_path),
                "chunk_name": chunk_name,
                "start_time": start_time,
                "end_time": end_time,
                "raw_response": response_text,
                "response_length": len(response_text),
                "model": "gemini-2.5-pro"
            }
            
            with open(raw_response_path, 'w', encoding='utf-8') as f:
                json.dump(raw_response_data, f, indent=2, ensure_ascii=False)
            
            print(f"Raw API response saved to: {raw_response_path}")
            
        except Exception as e:
            print(f"Warning: Failed to save raw response: {str(e)}")

    def parse_timestamp(self, timestamp: str) -> float:
        """Parse timestamp string to seconds."""
        try:
            if ':' in timestamp:
                parts = timestamp.split(':')
                if len(parts) == 2:
                    # Format: MM:SS.mmm or MM:SSS
                    minutes = int(parts[0])
                    seconds_part = parts[1]
                    if '.' in seconds_part:
                        seconds = float(seconds_part)
                    else:
                        # Convert "SSS" to "SS.mmm" format
                        if len(seconds_part) == 3:
                            seconds = float(seconds_part) / 1000.0
                        else:
                            seconds = float(seconds_part)
                    
                    # Validate seconds (should be 0-59.999)
                    if seconds >= 60:
                        print(f"Warning: Invalid seconds {seconds} in timestamp '{timestamp}', capping at 59.999")
                        seconds = 59.999
                    
                    return minutes * 60 + seconds
                elif len(parts) == 3:
                    # Handle transcript timestamps like "00:01:23.000" (HH:MM:SS.mmm format)
                    # This is always HH:MM:SS format for transcripts
                    hours = int(parts[0])
                    minutes = int(parts[1])
                    seconds_part = parts[2]
                    if '.' in seconds_part:
                        seconds = float(seconds_part)
                    else:
                        # Convert "SSS" to "SS.mmm" format
                        if len(seconds_part) == 3:
                            seconds = float(seconds_part) / 1000.0
                        else:
                            seconds = float(seconds_part)
                    
                    # Validate minutes (should be 0-59)
                    if minutes >= 60:
                        print(f"Warning: Invalid minutes {minutes} in timestamp '{timestamp}', capping at 59")
                        minutes = 59
                    
                    # Validate seconds (should be 0-59.999)
                    if seconds >= 60:
                        print(f"Warning: Invalid seconds {seconds} in timestamp '{timestamp}', capping at 59.999")
                        seconds = 59.999
                    
                    return hours * 3600 + minutes * 60 + seconds
            return float(timestamp)
        except (ValueError, TypeError) as e:
            print(f"Warning: Could not parse timestamp '{timestamp}': {e}, using 0.0")
            return 0.0
    
    def analyze_chunk_transcript(self, chunk_path: str, start_time: int, end_time: int, video_duration: float = 0) -> Dict:
        """Analyze a single chunk for transcript."""
        chunk_size_mb = os.path.getsize(chunk_path) / (1024 * 1024)
        
        print(f"Analyzing transcript for chunk {start_time}-{end_time} ({chunk_size_mb:.1f}MB)")
        
        # Use basic prompt for parallel processing
        prompt = self.get_transcript_prompt(video_duration=video_duration, chunk_start=start_time, chunk_end=end_time)
        
        if chunk_size_mb < 20:
            print(f"Using direct bytes analysis for chunk {start_time}-{end_time} ({chunk_size_mb:.1f}MB)")
            with open(chunk_path, 'rb') as f:
                chunk_data = f.read()
            response = self.client.models.generate_content(
                model='models/gemini-2.5-pro',
                contents=types.Content(
                    parts=[
                        types.Part(
                            inline_data=types.Blob(data=chunk_data, mime_type='video/mp4')
                        ),
                        types.Part(text=prompt)
                    ]
                )
            )
        else:
            print(f"Using file upload for chunk {start_time}-{end_time} ({chunk_size_mb:.1f}MB)")
            uploaded_file = self._get_or_upload_file(chunk_path)
            response = self.client.models.generate_content(
                model='models/gemini-2.5-pro',
                contents=[
                    uploaded_file,
                    prompt
                ]
            )
        
        # Save raw response for debugging
        self._save_raw_response(response.text, chunk_path, start_time, end_time)
        
        # Parse response
        try:
            text = response.text.strip()
            print(f"Raw response for chunk {start_time}-{end_time}: {text[:200]}...")
            
            if text.startswith("```json"):
                text = text[7:]
            if text.endswith("```"):
                text = text[:-3]
            
            result = json.loads(text.strip())
            
            # Handle case where result is a list (API might return array directly)
            if isinstance(result, list):
                print(f"Result is a list for chunk {start_time}-{end_time}, converting to dict")
                result = {"transcript": result}
            
            # Ensure result has the expected structure
            if not isinstance(result, dict):
                print(f"Unexpected result type for chunk {start_time}-{end_time}: {type(result)}")
                return {"transcript": [], "error": f"Unexpected result type: {type(result)}"}
            
            if "transcript" not in result:
                print(f"No transcript field in result for chunk {start_time}-{end_time}")
                return {"transcript": [], "error": "No transcript field in response"}
            
            # Adjust timestamps to be absolute with better error handling
            for i, entry in enumerate(result.get("transcript", [])):
                result["transcript"][i] = self._process_transcript_entry(entry, i, start_time, end_time)
            
            return result
            
        except json.JSONDecodeError as e:
            print(f"Failed to parse JSON response for chunk {start_time}-{end_time}: {str(e)}")
            print(f"Response text: {text}")
            return {"transcript": [], "error": str(e)}
        except Exception as e:
            print(f"Unexpected error processing chunk {start_time}-{end_time}: {str(e)}")
            return {"transcript": [], "error": str(e)}

    def analyze_all_chunks_parallel(self, chunks_metadata: Dict, video_id: str, max_workers: int = 4) -> Dict:
        """Analyze all chunks for transcripts using parallel processing."""
        print(f"Analyzing {len(chunks_metadata['chunks'])} chunks for transcripts using parallel processing...")
        
        all_transcripts = []
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = []
            
            for chunk_info in chunks_metadata['chunks']:
                future = executor.submit(
                    self.analyze_chunk_transcript,
                    chunk_info['path'],
                    chunk_info['start_time'],
                    chunk_info['end_time'],
                    chunks_metadata.get('total_duration', 0)
                )
                futures.append((chunk_info, future))
            
            for chunk_info, future in futures:
                try:
                    result = future.result()
                    all_transcripts.append({
                        "chunk_info": chunk_info,
                        "transcript": result
                    })
                except Exception as e:
                    print(f"Error analyzing chunk {chunk_info['start_time']}-{chunk_info['end_time']}: {str(e)}")
                    all_transcripts.append({
                        "chunk_info": chunk_info,
                        "transcript": {"transcript": [], "error": str(e)}
                    })
        
        # Combine all transcripts
        combined_transcript = {
            "video_id": video_id,
            "processing_date": datetime.datetime.now().isoformat(),
            "chunks": all_transcripts,
            "all_transcript_entries": []
        }
        
        # Flatten all transcript entries
        for chunk_data in all_transcripts:
            for entry in chunk_data['transcript'].get('transcript', []):
                combined_transcript['all_transcript_entries'].append(entry)
        
        # Save combined transcript
        output_path = self.run_dir / "transcripts" / f"{video_id}_transcript.json"
        with open(output_path, 'w') as f:
            json.dump(combined_transcript, f, indent=2)
        
        print(f"Transcript analysis saved to {output_path}")
        return combined_transcript
    
    def create_full_transcript(self, transcript_analysis: Dict, video_id: str) -> Dict:
        """Create a full transcript without segmentation by combining all transcript entries."""
        print(f"\n=== Creating Full Transcript ===")
        
        # Collect all transcript entries from all chunks
        all_entries = []
        
        for chunk_data in transcript_analysis.get('chunks', []):
            chunk_transcript = chunk_data.get('transcript', {}).get('transcript', [])
            chunk_start_time = chunk_data.get('chunk_info', {}).get('start_time', 0)
            
            for entry in chunk_transcript:
                # Handle new format with start_time and end_time
                if "absolute_start_time" in entry and "absolute_end_time" in entry:
                    # Use the already calculated absolute timestamps
                    absolute_start_time = entry["absolute_start_time"]
                    absolute_end_time = entry["absolute_end_time"]
                    absolute_start_timestamp = entry.get("absolute_start_timestamp", self.format_timestamp(absolute_start_time))
                    absolute_end_timestamp = entry.get("absolute_end_timestamp", self.format_timestamp(absolute_end_time))
                else:
                    # Fallback to legacy format
                    entry_time = self.parse_timestamp(entry.get('time', '00:00'))
                    absolute_start_time = chunk_start_time + entry_time
                    absolute_end_time = absolute_start_time  # Same as start for legacy format
                    absolute_start_timestamp = self.format_timestamp(absolute_start_time)
                    absolute_end_timestamp = absolute_start_timestamp
                
                # Create full transcript entry
                full_entry = {
                    "time": absolute_start_timestamp,  # Main time field for backward compatibility
                    "type": entry.get('type', 'utterance'),  # Preserve entry type
                    "speaker": entry.get('speaker', ''),
                    "spoken_text": entry.get('spoken_text', ''),
                    "event_description": entry.get('event_description', ''),  # Preserve event description
                    "visual_description": entry.get('visual_description', ''),
                    "absolute_time": absolute_start_time,  # Used for sorting
                    "absolute_start_timestamp": absolute_start_timestamp,  # Used in text output
                    "absolute_end_timestamp": absolute_end_timestamp  # Used in text output
                }
                all_entries.append(full_entry)
        
        # Sort by absolute time to ensure chronological order
        all_entries.sort(key=lambda x: x['absolute_time'])
        
        # Create full transcript structure
        full_transcript = {
            "video_id": video_id,
            "transcript_type": "full",
            "metadata": {
                "total_entries": len(all_entries),
                "total_duration_seconds": max(entry['absolute_time'] for entry in all_entries) if all_entries else 0,
                "generation_date": datetime.datetime.now().isoformat(),
                "pipeline_configuration": getattr(self, '_current_config', {}),
                "run_id": self.run_id
            },
            "transcript": all_entries
        }
        
        # Save full transcript
        full_transcript_path = self.run_dir / 'transcripts' / f'{video_id}_full_transcript.json'
        with open(full_transcript_path, 'w') as f:
            json.dump(full_transcript, f, indent=2)
        print(f"Full transcript saved to {full_transcript_path}")
        
        # Also create a human-readable text version
        self.create_full_transcript_text(full_transcript, video_id)
        
        # Create clean version
        self.create_clean_transcript(full_transcript, video_id)
        
        return full_transcript
    
    def create_full_transcript_text(self, full_transcript: Dict, video_id: str):
        """Create a human-readable text version of the full transcript."""
        output_lines = []
        
        # Header
        output_lines.append("=" * 80)
        output_lines.append("FULL VIDEO TRANSCRIPT")
        output_lines.append("=" * 80)
        output_lines.append(f"Video ID: {video_id}")
        output_lines.append(f"Generated: {full_transcript['metadata']['generation_date']}")
        output_lines.append(f"Total Entries: {full_transcript['metadata']['total_entries']}")
        output_lines.append(f"Total Duration: {full_transcript['metadata']['total_duration_seconds']:.1f} seconds")
        output_lines.append("")
        
        # Transcript entries
        for i, entry in enumerate(full_transcript['transcript'], 1):
            # Get start and end timestamps
            start_timestamp = entry.get('absolute_start_timestamp', entry.get('time', '00:00:00.000'))
            end_timestamp = entry.get('absolute_end_timestamp', entry.get('time', '00:00:00.000'))
            
            # Extract just the MM:SS part for display from "HH:MM:SS.fff" format
            start_display = start_timestamp[3:8] if len(start_timestamp) > 8 else start_timestamp  # Get MM:SS from "HH:MM:SS.fff"
            end_display = end_timestamp[3:8] if len(end_timestamp) > 8 else end_timestamp  # Get MM:SS from "HH:MM:SS.fff"
            
            # Format time range
            if start_display == end_display:
                time_display = f"[{start_display}]"
            else:
                time_display = f"[{start_display} - {end_display}]"
            
            speaker = entry.get('speaker', '')
            spoken_text = entry.get('spoken_text', '')
            visual_desc = entry.get('visual_description', '')
            
            # Check if this is primarily a visual event (no spoken text or empty spoken text)
            is_visual_event = (not spoken_text or spoken_text.strip() == '') and visual_desc and visual_desc.strip()
            
            # Format based on content type
            if is_visual_event:
                # Visual event: [time] (Visual: description)
                output_lines.append(f"{time_display} (Visual: {visual_desc})")
            elif speaker and spoken_text:
                # Spoken content with speaker
                if visual_desc and visual_desc.strip():
                    output_lines.append(f"{time_display} {speaker}: {spoken_text} (Visual: {visual_desc})")
                else:
                    output_lines.append(f"{time_display} {speaker}: {spoken_text}")
            elif spoken_text:
                # Spoken content without clear speaker
                if visual_desc and visual_desc.strip():
                    output_lines.append(f"{time_display} {spoken_text} (Visual: {visual_desc})")
                else:
                    output_lines.append(f"{time_display} {spoken_text}")
            else:
                # No content
                if visual_desc and visual_desc.strip():
                    output_lines.append(f"{time_display} (Visual: {visual_desc})")
                else:
                    output_lines.append(f"{time_display} [No audio/visual content]")
            output_lines.append("")
        
        # Footer
        output_lines.append("=" * 80)
        output_lines.append("END OF FULL TRANSCRIPT")
        output_lines.append("=" * 80)
        
        # Save text file
        text_path = self.run_dir / 'transcripts' / f'{video_id}_full_transcript.txt'
        with open(text_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(output_lines))
        
        print(f"Full transcript text saved to {text_path}")
    
    def create_clean_transcript(self, full_transcript: Dict, video_id: str):
        """Create a clean, minimal JSON version of the transcript with only essential fields."""
        print(f"\n=== Creating Clean Transcript ===")
        
        # Create clean entries with only essential fields
        clean_entries = []
        
        for entry in full_transcript.get('transcript', []):
            # Extract just the MM:SS part from the timestamp for cleaner display
            timestamp = entry.get('time', '00:00:00.000')
            if len(timestamp) > 8:  # If it's in HH:MM:SS.fff format
                clean_timestamp = timestamp[3:8]  # Get MM:SS part
            else:
                clean_timestamp = timestamp
            
            # Extract end timestamp as well
            end_timestamp = entry.get('absolute_end_timestamp', entry.get('time', '00:00:00.000'))
            if len(end_timestamp) > 8:  # If it's in HH:MM:SS.fff format
                clean_end_timestamp = end_timestamp[3:8]  # Get MM:SS part
            else:
                clean_end_timestamp = end_timestamp
            
            # Get entry type
            entry_type = entry.get('type', 'utterance')
            
            # Create clean entry with type-specific fields
            clean_entry = {
                "type": entry_type,
                "start_time": clean_timestamp,
                "end_time": clean_end_timestamp
            }
            
            # Handle different entry types
            if entry_type == "utterance":
                # For utterances, include speaker and text
                clean_entry["speaker"] = entry.get('speaker', '')
                clean_entry["text"] = entry.get('spoken_text', '')
                
                # Add visual description if present
                visual_desc = entry.get('visual_description', '')
                if visual_desc and visual_desc.strip():
                    clean_entry["visual"] = visual_desc
                    
            elif entry_type == "event":
                # For events, include event description as text
                clean_entry["text"] = entry.get('event_description', '')
                
                # Events typically don't have speakers, but include if present
                speaker = entry.get('speaker', '')
                if speaker and speaker.strip():
                    clean_entry["speaker"] = speaker
                    
                # Add visual description if present (events might have both)
                visual_desc = entry.get('visual_description', '')
                if visual_desc and visual_desc.strip():
                    clean_entry["visual"] = visual_desc
            
            # Remove empty fields to keep the output clean
            if clean_entry.get("speaker") == "":
                del clean_entry["speaker"]
            if clean_entry.get("text") == "":
                del clean_entry["text"]
            if clean_entry.get("visual") == "" or clean_entry.get("visual") is None:
                if "visual" in clean_entry:
                    del clean_entry["visual"]
            
            clean_entries.append(clean_entry)
        
        # Create clean transcript structure
        clean_transcript = {
            "video_id": video_id,
            "duration_seconds": full_transcript.get('metadata', {}).get('total_duration_seconds', 0),
            "total_entries": len(clean_entries),
            "generated": full_transcript.get('metadata', {}).get('generation_date', ''),
            "pipeline_configuration": full_transcript.get('metadata', {}).get('pipeline_configuration', {}),
            "run_id": full_transcript.get('metadata', {}).get('run_id', ''),
            "transcript": clean_entries
        }
        
        # Save clean transcript
        clean_transcript_path = self.run_dir / 'transcripts' / f'{video_id}_clean_transcript.json'
        with open(clean_transcript_path, 'w') as f:
            json.dump(clean_transcript, f, indent=2)
        
        print(f"Clean transcript saved to {clean_transcript_path}")
        return clean_transcript
    
    def process_video(self, config: TranscriptionConfig) -> PipelineResults:
        """
        Process a video through the transcription pipeline.
        
        Args:
            config: TranscriptionConfig object containing all pipeline settings
            
        Returns:
            PipelineResults: Pipeline results with transcript and metadata
        """
        print(f"Starting transcription pipeline for: {config.video_input}")
        print(f"Run ID: {self.run_id}")
        print(f"Pipeline runs directory: {self.pipeline_runs_dir}")
        print(f"Run directory: {self.run_dir}")
        print(f"Configuration: {config}")
        
        # Handle file management if enabled
        if self.file_manager:
            print(f"\n=== File Management ===")
            # Resolve video path through file manager
            resolved_path, is_new = self.file_manager.resolve_video_path(config.video_input)
            print(f"Resolved video path: {resolved_path}")
            print(f"New file: {is_new}")
            
            # Update config with resolved path
            config.video_input = resolved_path
            
            # Validate video file
            is_valid, error_msg = validate_video_file(resolved_path)
            if not is_valid:
                raise ValueError(f"Invalid video file: {error_msg}")
        
        # Store current configuration
        self._current_config = config.to_dict()
        config_hash = config.get_config_hash()
        
        # Step 1: Get video ID and prepare video
        video_id = self.get_video_id(config.video_input)
        print(f"Video ID: {video_id}")
        
        # Check for existing transcript with same configuration
        if not config.force_reprocess:
            existing_transcript = self._check_existing_transcript(video_id, config)
            if existing_transcript:
                print(f"\n=== Using Existing Transcript ===")
                print(f"Found cached transcript with matching configuration")
                print(f"Configuration: {config}")
                
                # Load the existing transcript
                transcript_path = Path(existing_transcript['transcript_path'])
                with open(transcript_path, 'r') as f:
                    full_transcript_data = json.load(f)
                
                # Create results structure
                # For cached results, we need to get the chunk duration from the cached transcript metadata
                cached_chunk_duration = full_transcript_data.get('metadata', {}).get('pipeline_configuration', {}).get('chunk_duration', config.chunk_duration)
                
                pipeline_results = PipelineResults(
                    video_id=video_id,
                    original_input=config.video_input,
                    processing_date=datetime.datetime.now().isoformat(),
                    chunk_duration=cached_chunk_duration,
                    max_workers=config.max_workers,
                    transcript_analysis={},  # Empty for cached results
                    full_transcript=FullTranscript.from_dict(full_transcript_data),
                    cached=True,
                    cache_info=CacheEntry.from_dict(existing_transcript)
                )
                
                print(f"Using cached transcript: {transcript_path}")
                return pipeline_results
        
        print(f"\n=== Processing New Transcript ===")
        print(f"Configuration: {config}")
        
        video_path = self.copy_video(config.video_input, video_id)
        
        # Step 2: Create chunks
        chunks_metadata = self.create_chunks(video_path, video_id, config.chunk_duration, config.chunk_size_mb)
        
        # Step 3: Generate transcripts for chunks using parallel processing
        print("\n=== Starting Parallel Transcript Generation ===")
        transcript_analysis = self.analyze_all_chunks_parallel(chunks_metadata, video_id, config.max_workers)
        
        # Step 4: Create full transcript
        full_transcript = self.create_full_transcript(transcript_analysis, video_id)
        
        # Create final results
        # Use the effective chunk duration from the metadata (calculated for size-based chunking)
        effective_chunk_duration = chunks_metadata.get('chunk_duration', config.chunk_duration)
        
        pipeline_results = PipelineResults(
            video_id=video_id,
            original_input=config.video_input,
            processing_date=datetime.datetime.now().isoformat(),
            chunk_duration=effective_chunk_duration,
            max_workers=config.max_workers,
            transcript_analysis=transcript_analysis,
            full_transcript=FullTranscript.from_dict(full_transcript),
            cached=False
        )
        
        # Save pipeline results
        output_path = self.run_dir / f"{video_id}_pipeline_results.json"
        with open(output_path, 'w') as f:
            json.dump(pipeline_results.to_dict(), f, indent=2)
        
        # Save transcript to global cache
        full_transcript_path = self.run_dir / 'transcripts' / f'{video_id}_full_transcript.json'
        self._save_transcript_cache(video_id, config_hash, str(full_transcript_path), config.to_dict())
        
        print(f"\nTranscription pipeline completed successfully!")
        print(f"Run ID: {self.run_id}")
        print(f"Pipeline runs directory: {self.pipeline_runs_dir}")
        print(f"Run directory: {self.run_dir}")
        print(f"Results saved to: {output_path}")
        print(f"Structured outputs:")
        print(f"  - Video: {self.run_dir / 'videos' / f'{video_id}.mp4'}")
        print(f"  - Chunks: {self.run_dir / 'chunks' / video_id}")
        print(f"  - Transcripts: {self.run_dir / 'transcripts' / f'{video_id}_transcript.json'}")
        print(f"  - Full Transcript (JSON): {self.run_dir / 'transcripts' / f'{video_id}_full_transcript.json'}")
        print(f"  - Full Transcript (Text): {self.run_dir / 'transcripts' / f'{video_id}_full_transcript.txt'}")
        print(f"  - Clean Transcript: {self.run_dir / 'transcripts' / f'{video_id}_clean_transcript.json'}")
        
        # Clean up uploaded files from Google if requested
        if config.cleanup_uploaded_files:
            self._cleanup_uploaded_files()
        
        # Update file management if enabled
        if self.file_manager:
            self.file_manager.update_video_status(
                config.video_input, 
                "transcribed",
                transcript_path=str(full_transcript_path),
                processing_date=pipeline_results.processing_date,
                run_id=self.run_id
            )
            print(f"Updated file management status for: {video_id}")
        
        return pipeline_results

def main():
    """Main function to run the transcription pipeline."""
    parser = argparse.ArgumentParser(description='Standalone Video Transcription Pipeline')
    parser.add_argument('--input', type=str, required=True,
                       help='Video file path')
    parser.add_argument('--chunk-size', type=int, default=300,
                       help='Duration of each chunk in seconds (default: 300)')
    parser.add_argument('--chunk-size-mb', type=int, default=None,
                       help='Target size of each chunk in MB (alternative to --chunk-size)')
    parser.add_argument('--max-workers', type=int, default=4,
                       help='Maximum number of parallel workers for transcription (default: 4)')
    parser.add_argument('--output-dir', type=str, default='outputs',
                       help='Output directory (default: outputs)')
    parser.add_argument('--no-cleanup', action='store_true',
                       help='Skip cleanup of uploaded files from Google (default: cleanup enabled)')
    parser.add_argument('--force-reprocess', action='store_true',
                       help='Force reprocessing even if transcript exists (default: use cache)')
    parser.add_argument('--data-dir', type=str, default='data',
                       help='Data directory for file management (default: data)')
    parser.add_argument('--no-file-management', action='store_true',
                       help='Disable automatic file management (default: enabled)')
    
    args = parser.parse_args()
    
    try:
        # Create configuration
        config = TranscriptionConfig(
            video_input=args.input,
            chunk_duration=args.chunk_size,
            chunk_size_mb=args.chunk_size_mb,
            max_workers=args.max_workers,
            cleanup_uploaded_files=not args.no_cleanup,
            force_reprocess=args.force_reprocess,
            output_dir=args.output_dir
        )
        
        # Initialize pipeline with file management
        pipeline = TranscriptionPipeline(
            base_dir=args.output_dir,
            data_dir=args.data_dir,
            enable_file_management=not args.no_file_management
        )
        
        # Process video
        results = pipeline.process_video(config)
        
        print(f"\nTranscription pipeline completed successfully!")
        print(f"Run ID: {pipeline.run_id}")
        print(f"Video ID: {results.video_id}")
        print(f"Pipeline runs directory: {pipeline.pipeline_runs_dir}")
        print(f"Run directory: {pipeline.run_dir}")
        print(f"Cached: {results.cached}")
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
