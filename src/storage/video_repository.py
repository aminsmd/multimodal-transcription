#!/usr/bin/env python3
"""
Video Repository - Database-like interface for video management.

This module provides a repository pattern for video management that abstracts
file system operations behind a database-like interface. This makes the system
more compatible with future database deployments on AWS.
"""

import os
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from dataclasses import dataclass, asdict

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from models import TranscriptionConfig
from utils import validate_video_file, get_video_duration


@dataclass
class VideoEntity:
    """
    Video entity representing a video record in the system.
    
    This class provides a database-like structure for video records,
    making it easier to transition to a real database later.
    """
    # Primary key
    video_id: str
    
    # File information
    filename: str
    file_path: str
    file_size_bytes: int
    file_hash: str
    file_extension: str
    
    # Metadata
    duration_seconds: float
    created_at: str
    updated_at: str
    
    # Status and processing
    status: str = "pending"  # pending, processing, transcribed, error
    processing_date: Optional[str] = None
    transcript_path: Optional[str] = None
    run_id: Optional[str] = None
    
    # Additional metadata
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        """Initialize metadata if not provided."""
        if self.metadata is None:
            self.metadata = {}
    
    @classmethod
    def from_file_path(cls, file_path: str, video_id: Optional[str] = None) -> 'VideoEntity':
        """
        Create VideoEntity from file path.
        
        Args:
            file_path: Path to the video file
            video_id: Optional video ID (will be generated from filename if not provided)
            
        Returns:
            VideoEntity instance
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"Video file not found: {file_path}")
        
        # Generate video_id if not provided
        if video_id is None:
            video_id = file_path.stem
        
        # Get file stats
        stat = file_path.stat()
        file_size = stat.st_size
        
        # Calculate file hash
        file_hash = cls._calculate_file_hash(file_path)
        
        # Get video duration
        duration = get_video_duration(str(file_path))
        
        # Get timestamps
        created_at = datetime.fromtimestamp(stat.st_ctime).isoformat()
        updated_at = datetime.fromtimestamp(stat.st_mtime).isoformat()
        
        return cls(
            video_id=video_id,
            filename=file_path.name,
            file_path=str(file_path),
            file_size_bytes=file_size,
            file_hash=file_hash,
            file_extension=file_path.suffix.lower(),
            duration_seconds=duration,
            created_at=created_at,
            updated_at=updated_at,
            status="pending"
        )
    
    @staticmethod
    def _calculate_file_hash(file_path: Path) -> str:
        """Calculate SHA256 hash of file."""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'VideoEntity':
        """Create VideoEntity from dictionary."""
        # Handle legacy metadata format
        if 'original_path' in data:
            data = data.copy()
            data['file_path'] = data.pop('original_path')  # Map original_path to file_path
        
        # Map legacy field names to new field names
        field_mapping = {
            'modified_time': 'updated_at',
            'added_time': 'created_at',
            'updated_time': 'updated_at',
        }
        
        for old_field, new_field in field_mapping.items():
            if old_field in data and new_field:
                data[new_field] = data.pop(old_field)
        
        # Remove legacy fields that are not needed
        legacy_fields_to_remove = ['file_size_mb']
        for field in legacy_fields_to_remove:
            data.pop(field, None)
        
        # Ensure required fields have defaults
        defaults = {
            'metadata': {},
            'status': 'pending',
            'processing_date': None,
            'transcript_path': None,
            'run_id': None,
            'file_extension': '.mp4',
            'duration_seconds': 0.0,
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }
        
        for key, value in defaults.items():
            if key not in data:
                data[key] = value
        
        return cls(**data)
    
    def update_status(self, status: str, **kwargs):
        """Update video status and metadata."""
        self.status = status
        self.updated_at = datetime.now().isoformat()
        
        # Update additional fields
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
    
    def is_processed(self) -> bool:
        """Check if video has been processed."""
        return self.status in ["transcribed", "processed"]
    
    def get_file_size_mb(self) -> float:
        """Get file size in MB."""
        return self.file_size_bytes / (1024 * 1024)


class VideoRepository:
    """
    Repository pattern for video management.
    
    This class provides a database-like interface for video operations,
    abstracting file system operations and making it easier to transition
    to a real database in the future.
    """
    
    def __init__(self, base_dir: str = "data"):
        """
        Initialize the video repository.
        
        Args:
            base_dir: Base directory for video storage
        """
        self.base_dir = Path(base_dir)
        self.videos_dir = self.base_dir / "videos"
        self.metadata_dir = self.base_dir / "metadata"
        
        # Ensure directories exist
        self.videos_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_dir.mkdir(parents=True, exist_ok=True)
        
        # In-memory cache for quick lookups
        self._video_cache: Dict[str, VideoEntity] = {}
        self._load_video_cache()
    
    def _load_video_cache(self):
        """Load video cache from metadata files."""
        self._video_cache.clear()
        
        for metadata_file in self.metadata_dir.glob("*.json"):
            try:
                import json
                with open(metadata_file, 'r') as f:
                    data = json.load(f)
                
                video_entity = VideoEntity.from_dict(data)
                self._video_cache[video_entity.video_id] = video_entity
            except Exception as e:
                print(f"Warning: Could not load metadata from {metadata_file}: {e}")
    
    def _save_video_metadata(self, video_entity: VideoEntity):
        """Save video metadata to file."""
        metadata_file = self.metadata_dir / f"{video_entity.video_id}.json"
        
        import json
        with open(metadata_file, 'w') as f:
            json.dump(video_entity.to_dict(), f, indent=2)
    
    def find_by_id(self, video_id: str) -> Optional[VideoEntity]:
        """
        Find video by ID.
        
        Args:
            video_id: Video identifier
            
        Returns:
            VideoEntity if found, None otherwise
        """
        return self._video_cache.get(video_id)
    
    def find_by_hash(self, file_hash: str) -> Optional[VideoEntity]:
        """
        Find video by file hash.
        
        Args:
            file_hash: SHA256 hash of the file
            
        Returns:
            VideoEntity if found, None otherwise
        """
        for video in self._video_cache.values():
            if video.file_hash == file_hash:
                return video
        return None
    
    def find_by_filename(self, filename: str) -> Optional[VideoEntity]:
        """
        Find video by filename.
        
        Args:
            filename: Name of the video file
            
        Returns:
            VideoEntity if found, None otherwise
        """
        for video in self._video_cache.values():
            if video.filename == filename:
                return video
        return None
    
    def find_by_path(self, file_path: str) -> Optional[VideoEntity]:
        """
        Find video by file path.
        
        Args:
            file_path: Path to the video file
            
        Returns:
            VideoEntity if found, None otherwise
        """
        for video in self._video_cache.values():
            if video.file_path == file_path:
                return video
        return None
    
    def save(self, video_entity: VideoEntity) -> VideoEntity:
        """
        Save video entity to repository.
        
        Args:
            video_entity: Video entity to save
            
        Returns:
            Saved video entity
        """
        # Update timestamps
        video_entity.updated_at = datetime.now().isoformat()
        
        # Add to cache
        self._video_cache[video_entity.video_id] = video_entity
        
        # Save metadata
        self._save_video_metadata(video_entity)
        
        return video_entity
    
    def create_from_file(self, file_path: str, video_id: Optional[str] = None) -> VideoEntity:
        """
        Create video entity from file path.
        
        Args:
            file_path: Path to the video file
            video_id: Optional video ID
            
        Returns:
            Created VideoEntity
        """
        # Check if file already exists in repository
        existing = self.find_by_path(file_path)
        if existing:
            return existing
        
        # Create new entity
        video_entity = VideoEntity.from_file_path(file_path, video_id)
        
        # Save to repository
        return self.save(video_entity)
    
    def update(self, video_id: str, **kwargs) -> Optional[VideoEntity]:
        """
        Update video entity.
        
        Args:
            video_id: Video identifier
            **kwargs: Fields to update
            
        Returns:
            Updated VideoEntity if found, None otherwise
        """
        video_entity = self.find_by_id(video_id)
        if not video_entity:
            return None
        
        # Update fields
        for key, value in kwargs.items():
            if hasattr(video_entity, key):
                setattr(video_entity, key, value)
        
        # Update timestamp
        video_entity.updated_at = datetime.now().isoformat()
        
        # Save changes
        return self.save(video_entity)
    
    def delete(self, video_id: str) -> bool:
        """
        Delete video from repository.
        
        Args:
            video_id: Video identifier
            
        Returns:
            True if deleted, False if not found
        """
        video_entity = self.find_by_id(video_id)
        if not video_entity:
            return False
        
        # Remove from cache
        del self._video_cache[video_id]
        
        # Remove metadata file
        metadata_file = self.metadata_dir / f"{video_id}.json"
        if metadata_file.exists():
            metadata_file.unlink()
        
        return True
    
    def list_all(self, status: Optional[str] = None) -> List[VideoEntity]:
        """
        List all videos in repository.
        
        Args:
            status: Filter by status (optional)
            
        Returns:
            List of VideoEntity objects
        """
        videos = list(self._video_cache.values())
        
        if status:
            videos = [v for v in videos if v.status == status]
        
        return videos
    
    def count(self, status: Optional[str] = None) -> int:
        """
        Count videos in repository.
        
        Args:
            status: Filter by status (optional)
            
        Returns:
            Number of videos
        """
        return len(self.list_all(status))
    
    def get_video_path(self, video_id: str) -> Optional[str]:
        """
        Get video file path by ID.
        
        Args:
            video_id: Video identifier
            
        Returns:
            Path to video file if found, None otherwise
        """
        video_entity = self.find_by_id(video_id)
        if video_entity and Path(video_entity.file_path).exists():
            return video_entity.file_path
        return None
    
    def validate_video(self, video_id: str) -> bool:
        """
        Validate that video file exists and is accessible.
        
        Args:
            video_id: Video identifier
            
        Returns:
            True if video is valid, False otherwise
        """
        video_entity = self.find_by_id(video_id)
        if not video_entity:
            return False
        
        file_path = Path(video_entity.file_path)
        if not file_path.exists():
            return False
        
        # Validate video file
        is_valid, _ = validate_video_file(str(file_path))
        return is_valid
    
    def get_repository_stats(self) -> Dict[str, Any]:
        """
        Get repository statistics.
        
        Returns:
            Dictionary containing repository statistics
        """
        videos = self.list_all()
        
        total_size = sum(v.file_size_bytes for v in videos)
        status_counts = {}
        
        for video in videos:
            status_counts[video.status] = status_counts.get(video.status, 0) + 1
        
        return {
            "total_videos": len(videos),
            "total_size_bytes": total_size,
            "total_size_mb": total_size / (1024 * 1024),
            "status_counts": status_counts,
            "repository_path": str(self.base_dir)
        }
    
    def search(self, query: str, field: str = "filename") -> List[VideoEntity]:
        """
        Search videos by query.
        
        Args:
            query: Search query
            field: Field to search in (filename, video_id, status)
            
        Returns:
            List of matching VideoEntity objects
        """
        results = []
        query_lower = query.lower()
        
        for video in self._video_cache.values():
            if field == "filename" and query_lower in video.filename.lower():
                results.append(video)
            elif field == "video_id" and query_lower in video.video_id.lower():
                results.append(video)
            elif field == "status" and query_lower in video.status.lower():
                results.append(video)
        
        return results
    
    def refresh_cache(self):
        """Refresh the video cache from metadata files."""
        self._load_video_cache()
    
    def cleanup_orphaned_metadata(self):
        """Clean up metadata files for videos that no longer exist."""
        orphaned_count = 0
        
        for video_id, video_entity in list(self._video_cache.items()):
            if not Path(video_entity.file_path).exists():
                del self._video_cache[video_id]
                
                metadata_file = self.metadata_dir / f"{video_id}.json"
                if metadata_file.exists():
                    metadata_file.unlink()
                    orphaned_count += 1
        
        if orphaned_count > 0:
            print(f"Cleaned up {orphaned_count} orphaned metadata files")
        
        return orphaned_count
