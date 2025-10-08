#!/usr/bin/env python3
"""
File storage operations for the transcription pipeline.

This module handles file storage, organization, and management.
"""

import os
import shutil
import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils import get_file_hash, create_safe_filename, ensure_directory


class FileStorage:
    """
    Handles file storage operations for the transcription pipeline.
    """
    
    def __init__(self, base_dir: Path):
        """
        Initialize the file storage manager.
        
        Args:
            base_dir: Base directory for file storage
        """
        self.base_dir = base_dir
        self.videos_dir = base_dir / "videos"
        self.transcripts_dir = base_dir / "transcripts"
        self.chunks_dir = base_dir / "chunks"
        self.cache_dir = base_dir / "cache"
        self.logs_dir = base_dir / "logs"
        
        # Ensure all directories exist
        for directory in [self.videos_dir, self.transcripts_dir, self.chunks_dir, self.cache_dir, self.logs_dir]:
            ensure_directory(directory)
    
    def copy_video(self, video_path: str, video_id: str) -> str:
        """
        Copy local video to pipeline directory.
        
        Args:
            video_path: Source video path
            video_id: Unique identifier for the video
            
        Returns:
            Path to the copied video
        """
        dest_path = self.videos_dir / f"{video_id}.mp4"
        
        if dest_path.exists():
            print(f"Video already exists at {dest_path}")
            return str(dest_path)
        
        print(f"Copying video: {video_path}")
        shutil.copy2(video_path, dest_path)
        
        return str(dest_path)
    
    def save_transcript(self, transcript_data: Dict, video_id: str, transcript_type: str = "full") -> Path:
        """
        Save transcript data to file.
        
        Args:
            transcript_data: Transcript data dictionary
            video_id: Unique identifier for the video
            transcript_type: Type of transcript (full, clean, etc.)
            
        Returns:
            Path to the saved transcript file
        """
        filename = f"{video_id}_{transcript_type}_transcript.json"
        transcript_path = self.transcripts_dir / filename
        
        import json
        with open(transcript_path, 'w') as f:
            json.dump(transcript_data, f, indent=2)
        
        print(f"Transcript saved to {transcript_path}")
        return transcript_path
    
    def save_transcript_text(self, transcript_text: str, video_id: str) -> Path:
        """
        Save transcript as text file.
        
        Args:
            transcript_text: Transcript text content
            video_id: Unique identifier for the video
            
        Returns:
            Path to the saved text file
        """
        filename = f"{video_id}_full_transcript.txt"
        text_path = self.transcripts_dir / filename
        
        with open(text_path, 'w', encoding='utf-8') as f:
            f.write(transcript_text)
        
        print(f"Transcript text saved to {text_path}")
        return text_path
    
    def get_video_path(self, video_id: str) -> Optional[Path]:
        """
        Get the path to a video file.
        
        Args:
            video_id: Unique identifier for the video
            
        Returns:
            Path to the video file if it exists, None otherwise
        """
        video_path = self.videos_dir / f"{video_id}.mp4"
        return video_path if video_path.exists() else None
    
    def get_transcript_path(self, video_id: str, transcript_type: str = "full") -> Optional[Path]:
        """
        Get the path to a transcript file.
        
        Args:
            video_id: Unique identifier for the video
            transcript_type: Type of transcript
            
        Returns:
            Path to the transcript file if it exists, None otherwise
        """
        filename = f"{video_id}_{transcript_type}_transcript.json"
        transcript_path = self.transcripts_dir / filename
        return transcript_path if transcript_path.exists() else None
    
    def list_videos(self) -> List[Dict[str, Any]]:
        """
        List all videos in storage.
        
        Returns:
            List of video information dictionaries
        """
        videos = []
        
        for video_file in self.videos_dir.glob("*.mp4"):
            video_info = {
                "video_id": video_file.stem,
                "filename": video_file.name,
                "path": str(video_file),
                "size_mb": os.path.getsize(video_file) / (1024 * 1024),
                "created": datetime.datetime.fromtimestamp(video_file.stat().st_ctime).isoformat(),
                "modified": datetime.datetime.fromtimestamp(video_file.stat().st_mtime).isoformat()
            }
            videos.append(video_info)
        
        return videos
    
    def list_transcripts(self, video_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List all transcripts in storage.
        
        Args:
            video_id: Filter by video ID (optional)
            
        Returns:
            List of transcript information dictionaries
        """
        transcripts = []
        
        pattern = f"{video_id}_*_transcript.json" if video_id else "*_transcript.json"
        
        for transcript_file in self.transcripts_dir.glob(pattern):
            transcript_info = {
                "filename": transcript_file.name,
                "path": str(transcript_file),
                "size_mb": os.path.getsize(transcript_file) / (1024 * 1024),
                "created": datetime.datetime.fromtimestamp(transcript_file.stat().st_ctime).isoformat(),
                "modified": datetime.datetime.fromtimestamp(transcript_file.stat().st_mtime).isoformat()
            }
            
            # Extract video_id and transcript_type from filename
            parts = transcript_file.stem.split('_')
            if len(parts) >= 3:
                transcript_info["video_id"] = parts[0]
                transcript_info["transcript_type"] = parts[1]
            
            transcripts.append(transcript_info)
        
        return transcripts
    
    def get_storage_stats(self) -> Dict[str, Any]:
        """
        Get storage statistics.
        
        Returns:
            Dictionary containing storage statistics
        """
        videos = self.list_videos()
        transcripts = self.list_transcripts()
        
        total_video_size = sum(v.get('size_mb', 0) for v in videos)
        total_transcript_size = sum(t.get('size_mb', 0) for t in transcripts)
        
        stats = {
            "total_videos": len(videos),
            "total_transcripts": len(transcripts),
            "total_video_size_mb": total_video_size,
            "total_transcript_size_mb": total_transcript_size,
            "total_size_mb": total_video_size + total_transcript_size,
            "storage_directories": {
                "videos": str(self.videos_dir),
                "transcripts": str(self.transcripts_dir),
                "chunks": str(self.chunks_dir),
                "cache": str(self.cache_dir),
                "logs": str(self.logs_dir)
            }
        }
        
        return stats
    
    def cleanup_old_files(self, days_old: int = 30, file_types: List[str] = None) -> int:
        """
        Clean up old files.
        
        Args:
            days_old: Age threshold in days
            file_types: List of file types to clean up (e.g., ['*.mp4', '*.json'])
            
        Returns:
            Number of files cleaned up
        """
        if file_types is None:
            file_types = ['*.mp4', '*.json', '*.txt']
        
        cutoff_date = datetime.datetime.now() - datetime.timedelta(days=days_old)
        cleaned_count = 0
        
        for file_type in file_types:
            for file_path in self.base_dir.rglob(file_type):
                try:
                    file_time = datetime.datetime.fromtimestamp(file_path.stat().st_mtime)
                    if file_time < cutoff_date:
                        file_path.unlink()
                        cleaned_count += 1
                        print(f"Cleaned up old file: {file_path}")
                except Exception as e:
                    print(f"Error cleaning up file {file_path}: {e}")
        
        print(f"Cleaned up {cleaned_count} old files")
        return cleaned_count
    
    def organize_files(self, organization_rules: Dict[str, List[str]]):
        """
        Organize files according to custom rules.
        
        Args:
            organization_rules: Dictionary mapping categories to file patterns
        """
        for category, patterns in organization_rules.items():
            category_dir = self.base_dir / category
            ensure_directory(category_dir)
            
            for pattern in patterns:
                for file_path in self.base_dir.rglob(pattern):
                    if file_path.is_file():
                        dest_path = category_dir / file_path.name
                        if not dest_path.exists():
                            shutil.move(str(file_path), str(dest_path))
                            print(f"Moved {file_path} to {dest_path}")
    
    def backup_files(self, backup_dir: Path, file_patterns: List[str] = None) -> int:
        """
        Create backup of files.
        
        Args:
            backup_dir: Directory to store backups
            file_patterns: List of file patterns to backup
            
        Returns:
            Number of files backed up
        """
        if file_patterns is None:
            file_patterns = ['*.mp4', '*.json', '*.txt']
        
        ensure_directory(backup_dir)
        backed_up_count = 0
        
        for pattern in file_patterns:
            for file_path in self.base_dir.rglob(pattern):
                if file_path.is_file():
                    dest_path = backup_dir / file_path.relative_to(self.base_dir)
                    ensure_directory(dest_path.parent)
                    shutil.copy2(str(file_path), str(dest_path))
                    backed_up_count += 1
                    print(f"Backed up {file_path} to {dest_path}")
        
        print(f"Backed up {backed_up_count} files to {backup_dir}")
        return backed_up_count
