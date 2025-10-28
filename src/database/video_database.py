#!/usr/bin/env python3
"""
Video database interface for batch processing.

This module provides a simple database interface to manage video processing jobs.
In production, this would connect to MongoDB or another database.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from models import TranscriptionConfig


class VideoStatus(Enum):
    """Video processing status."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class VideoMetadata:
    """Video metadata structure."""
    video_id: str
    filename: str
    file_path: str
    status: VideoStatus
    priority: int
    created_at: str
    metadata: Dict[str, Any]
    processing_config: Dict[str, Any]
    processing_started_at: Optional[str] = None
    processing_completed_at: Optional[str] = None
    error_message: Optional[str] = None
    transcript_path: Optional[str] = None
    run_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        data['status'] = self.status.value
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'VideoMetadata':
        """Create from dictionary."""
        data['status'] = VideoStatus(data['status'])
        return cls(**data)


class VideoDatabase:
    """
    Simple video database interface.
    
    In production, this would connect to MongoDB or another database.
    For now, we use a JSON file for simplicity.
    """
    
    def __init__(self, database_path: str = "data/video_database.json"):
        """
        Initialize the video database.
        
        Args:
            database_path: Path to the JSON database file
        """
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._load_database()
    
    def _load_database(self):
        """Load database from JSON file."""
        if self.database_path.exists():
            with open(self.database_path, 'r') as f:
                self.data = json.load(f)
        else:
            self.data = {
                "videos": [],
                "database_info": {
                    "version": "1.0",
                    "last_updated": datetime.now().isoformat(),
                    "total_videos": 0,
                    "pending_videos": 0,
                    "processed_videos": 0,
                    "failed_videos": 0
                }
            }
        
        # Ensure all status fields are strings (not enums)
        for video in self.data["videos"]:
            if isinstance(video.get("status"), VideoStatus):
                video["status"] = video["status"].value
    
    def _save_database(self):
        """Save database to JSON file."""
        self.data["database_info"]["last_updated"] = datetime.now().isoformat()
        
        # Ensure all status fields are strings before saving
        for video in self.data["videos"]:
            if isinstance(video.get("status"), VideoStatus):
                video["status"] = video["status"].value
        
        with open(self.database_path, 'w') as f:
            json.dump(self.data, f, indent=2)
    
    def get_pending_videos(self, limit: Optional[int] = None) -> List[VideoMetadata]:
        """
        Get videos that need to be processed.
        
        Args:
            limit: Maximum number of videos to return
            
        Returns:
            List of VideoMetadata objects
        """
        pending_videos = []
        for video_data in self.data["videos"]:
            if video_data["status"] == "pending":
                pending_videos.append(VideoMetadata.from_dict(video_data))
        
        # Sort by priority (lower number = higher priority)
        pending_videos.sort(key=lambda x: x.priority)
        
        if limit:
            pending_videos = pending_videos[:limit]
        
        return pending_videos
    
    def get_video_by_id(self, video_id: str) -> Optional[VideoMetadata]:
        """
        Get video by ID.
        
        Args:
            video_id: Video ID to search for
            
        Returns:
            VideoMetadata object or None if not found
        """
        for video_data in self.data["videos"]:
            if video_data["video_id"] == video_id:
                return VideoMetadata.from_dict(video_data)
        return None
    
    def update_video_status(self, video_id: str, status: VideoStatus, 
                          error_message: Optional[str] = None,
                          transcript_path: Optional[str] = None,
                          run_id: Optional[str] = None):
        """
        Update video processing status.
        
        Args:
            video_id: Video ID to update
            status: New status
            error_message: Error message if failed
            transcript_path: Path to transcript file if completed
            run_id: Run ID for tracking
        """
        for i, video_data in enumerate(self.data["videos"]):
            if video_data["video_id"] == video_id:
                video_data["status"] = status.value
                
                if status == VideoStatus.PROCESSING:
                    video_data["processing_started_at"] = datetime.now().isoformat()
                elif status in [VideoStatus.COMPLETED, VideoStatus.FAILED, VideoStatus.SKIPPED]:
                    video_data["processing_completed_at"] = datetime.now().isoformat()
                
                if error_message:
                    video_data["error_message"] = error_message
                
                if transcript_path:
                    video_data["transcript_path"] = transcript_path
                
                if run_id:
                    video_data["run_id"] = run_id
                
                break
        
        self._update_database_stats()
        self._save_database()
    
    def add_video(self, video_metadata: VideoMetadata):
        """
        Add a new video to the database.
        
        Args:
            video_metadata: VideoMetadata object to add
        """
        self.data["videos"].append(video_metadata.to_dict())
        self._update_database_stats()
        self._save_database()
    
    def _update_database_stats(self):
        """Update database statistics."""
        total_videos = len(self.data["videos"])
        pending_videos = sum(1 for v in self.data["videos"] if v["status"] == "pending")
        processed_videos = sum(1 for v in self.data["videos"] if v["status"] == "completed")
        failed_videos = sum(1 for v in self.data["videos"] if v["status"] == "failed")
        
        self.data["database_info"].update({
            "total_videos": total_videos,
            "pending_videos": pending_videos,
            "processed_videos": processed_videos,
            "failed_videos": failed_videos
        })
    
    def get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics."""
        return self.data["database_info"].copy()
    
    def create_transcription_config(self, video_metadata: VideoMetadata) -> TranscriptionConfig:
        """
        Create TranscriptionConfig from VideoMetadata.
        
        Args:
            video_metadata: VideoMetadata object
            
        Returns:
            TranscriptionConfig object
        """
        config_data = video_metadata.processing_config
        return TranscriptionConfig(
            video_input=video_metadata.file_path,
            chunk_duration=config_data.get("chunk_duration", 300),
            max_workers=config_data.get("max_workers", 4),
            force_reprocess=config_data.get("force_reprocess", False),
            cleanup_uploaded_files=True
        )
    
    def mark_video_processing(self, video_id: str, run_id: str):
        """Mark video as currently being processed."""
        self.update_video_status(video_id, VideoStatus.PROCESSING, run_id=run_id)
    
    def mark_video_completed(self, video_id: str, transcript_path: str, run_id: str):
        """Mark video as completed."""
        self.update_video_status(
            video_id, 
            VideoStatus.COMPLETED, 
            transcript_path=transcript_path, 
            run_id=run_id
        )
    
    def mark_video_failed(self, video_id: str, error_message: str, run_id: str):
        """Mark video as failed."""
        self.update_video_status(
            video_id, 
            VideoStatus.FAILED, 
            error_message=error_message, 
            run_id=run_id
        )
