#!/usr/bin/env python3
"""
Enhanced file manager for the transcription pipeline.

This module provides automatic file management, including:
- Video file detection and organization
- Automatic path resolution
- File deduplication
- Integration with the transcription pipeline
"""

import os
import shutil
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
from datetime import datetime

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from data.data_setup import DataManager
from models import TranscriptionConfig


class PipelineFileManager:
    """
    Enhanced file manager that integrates with the transcription pipeline.
    
    This class automatically manages video files, handles deduplication,
    and provides seamless integration with the transcription pipeline.
    """
    
    def __init__(self, base_dir: str = "data", auto_organize: bool = True):
        """
        Initialize the pipeline file manager.
        
        Args:
            base_dir: Base directory for all data
            auto_organize: Whether to automatically organize files
        """
        self.base_dir = Path(base_dir)
        self.auto_organize = auto_organize
        
        # Initialize data manager
        self.data_manager = DataManager(str(self.base_dir))
        
        # File registry for quick lookups
        self.file_registry = self._build_file_registry()
        
        print(f"Pipeline file manager initialized: {self.base_dir}")
        print(f"Auto-organize: {auto_organize}")
    
    def _build_file_registry(self) -> Dict[str, Dict]:
        """Build a registry of all managed files for quick lookup."""
        registry = {}
        
        # Scan all video files
        for video_info in self.data_manager.list_videos():
            video_id = video_info['video_id']
            file_hash = video_info.get('file_hash', '')
            
            registry[video_id] = video_info
            if file_hash:
                registry[file_hash] = video_info
        
        return registry
    
    def resolve_video_path(self, video_input: str) -> Tuple[str, bool]:
        """
        Resolve video input to actual file path.
        
        Args:
            video_input: Video path, video ID, or video filename
            
        Returns:
            Tuple of (resolved_path, is_new_file)
        """
        video_input = Path(video_input)
        
        # Case 1: Direct file path that exists
        if video_input.exists():
            return self._handle_existing_file(video_input)
        
        # Case 2: Video ID lookup
        if video_input.name in self.file_registry:
            video_info = self.file_registry[video_input.name]
            video_path = self.data_manager.get_video_path(video_info['video_id'])
            if video_path and video_path.exists():
                return str(video_path), False
        
        # Case 3: Filename lookup
        for video_info in self.data_manager.list_videos():
            if video_info['filename'] == video_input.name:
                video_path = self.data_manager.get_video_path(video_info['video_id'])
                if video_path and video_path.exists():
                    return str(video_path), False
        
        # Case 4: File not found - return original input
        return str(video_input), True
    
    def _handle_existing_file(self, file_path: Path) -> Tuple[str, bool]:
        """Handle an existing file - check if it's already managed."""
        # Calculate file hash
        file_hash = self._get_file_hash(file_path)
        
        # Check if file is already managed
        if file_hash in self.file_registry:
            video_info = self.file_registry[file_hash]
            managed_path = self.data_manager.get_video_path(video_info['video_id'])
            if managed_path and managed_path.exists():
                return str(managed_path), False
        
        # File exists but not managed - add it
        if self.auto_organize:
            try:
                video_info = self.data_manager.add_video(str(file_path), copy=True)
                self.file_registry[video_info['video_id']] = video_info
                self.file_registry[file_hash] = video_info
                
                managed_path = self.data_manager.get_video_path(video_info['video_id'])
                return str(managed_path), False
            except Exception as e:
                print(f"Warning: Could not add file to management system: {e}")
                return str(file_path), True
        else:
            return str(file_path), True
    
    def _get_file_hash(self, file_path: Path) -> str:
        """Calculate SHA256 hash of file."""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    
    def add_video(self, video_path: str, organize_by_date: bool = True) -> Dict:
        """
        Add a video to the management system.
        
        Args:
            video_path: Path to the video file
            organize_by_date: Whether to organize by date
            
        Returns:
            Video information dictionary
        """
        video_info = self.data_manager.add_video(video_path, copy=True, organize_by_date=organize_by_date)
        
        # Update registry
        self.file_registry[video_info['video_id']] = video_info
        self.file_registry[video_info['file_hash']] = video_info
        
        return video_info
    
    def get_video_info(self, video_input: str) -> Optional[Dict]:
        """
        Get video information by path, ID, or filename.
        
        Args:
            video_input: Video path, ID, or filename
            
        Returns:
            Video information dictionary or None
        """
        video_path, _ = self.resolve_video_path(video_input)
        
        # Find video info by path
        for video_info in self.data_manager.list_videos():
            managed_path = self.data_manager.get_video_path(video_info['video_id'])
            if managed_path and str(managed_path) == video_path:
                return video_info
        
        return None
    
    def update_video_status(self, video_input: str, status: str, **kwargs):
        """Update video status and metadata."""
        video_info = self.get_video_info(video_input)
        if video_info:
            self.data_manager.update_video_status(video_info['video_id'], status, **kwargs)
        else:
            print(f"Warning: Video not found in management system: {video_input}")
    
    def list_videos(self, status: Optional[str] = None) -> List[Dict]:
        """List all managed videos."""
        return self.data_manager.list_videos(status)
    
    def create_config_with_file_management(self, video_input: str, **config_kwargs) -> TranscriptionConfig:
        """
        Create a TranscriptionConfig with automatic file management.
        
        Args:
            video_input: Video path, ID, or filename
            **config_kwargs: Additional configuration parameters
            
        Returns:
            TranscriptionConfig with resolved video path
        """
        # Resolve video path
        resolved_path, is_new = self.resolve_video_path(video_input)
        
        # Create configuration
        config = TranscriptionConfig(
            video_input=resolved_path,
            **config_kwargs
        )
        
        # Add file management metadata
        config.file_managed = not is_new
        config.original_input = video_input
        
        return config
    
    def get_managed_video_path(self, video_input: str) -> Optional[str]:
        """
        Get the managed path for a video.
        
        Args:
            video_input: Video path, ID, or filename
            
        Returns:
            Managed video path or None
        """
        video_path, is_managed = self.resolve_video_path(video_input)
        return video_path if not is_managed else None
    
    def organize_videos(self, organization_rules: Dict[str, List[str]]):
        """
        Organize videos according to custom rules.
        
        Args:
            organization_rules: Dictionary mapping categories to video IDs
        """
        self.data_manager.organize_by_type(organization_rules)
        print(f"Organized videos according to {len(organization_rules)} rules")
    
    def cleanup_old_files(self, days_old: int = 30):
        """Clean up old files and cache."""
        self.data_manager.cleanup_old_files(days_old)
        print(f"Cleaned up files older than {days_old} days")
    
    def export_video_list(self, output_file: Optional[str] = None) -> str:
        """Export video list to CSV."""
        return self.data_manager.export_video_list(output_file)
    
    def get_directory_structure(self) -> Dict:
        """Get current directory structure."""
        return self.data_manager.get_directory_structure()
    
    def refresh_registry(self):
        """Refresh the file registry."""
        self.file_registry = self._build_file_registry()
        print("File registry refreshed")
    
    def get_file_stats(self) -> Dict:
        """Get statistics about managed files."""
        videos = self.data_manager.list_videos()
        
        stats = {
            "total_videos": len(videos),
            "total_size_mb": sum(v.get('file_size_mb', 0) for v in videos),
            "status_counts": {},
            "file_types": {}
        }
        
        for video in videos:
            # Status counts
            status = video.get('status', 'unknown')
            stats["status_counts"][status] = stats["status_counts"].get(status, 0) + 1
            
            # File type counts
            ext = Path(video.get('filename', '')).suffix.lower()
            stats["file_types"][ext] = stats["file_types"].get(ext, 0) + 1
        
        return stats


def create_file_manager(base_dir: str = "data", auto_organize: bool = True) -> PipelineFileManager:
    """
    Factory function to create a file manager.
    
    Args:
        base_dir: Base directory for data
        auto_organize: Whether to auto-organize files
        
    Returns:
        PipelineFileManager instance
    """
    return PipelineFileManager(base_dir, auto_organize)
