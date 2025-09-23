#!/usr/bin/env python3
"""
Data directory setup and management utilities for the transcription pipeline.

This script helps you organize your video data and set up proper directory structures
for efficient video processing and transcript management.
"""

import os
import shutil
import json
import hashlib
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import argparse


class DataManager:
    """
    Manages data directory structure and video organization for the transcription pipeline.
    """
    
    def __init__(self, base_dir: str = "data"):
        """
        Initialize the data manager.
        
        Args:
            base_dir: Base directory for all data
        """
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(exist_ok=True)
        
        # Create directory structure
        self.videos_dir = self.base_dir / "videos"
        self.transcripts_dir = self.base_dir / "transcripts"
        self.cache_dir = self.base_dir / "cache"
        self.metadata_dir = self.base_dir / "metadata"
        self.processed_dir = self.base_dir / "processed"
        
        # Create all directories
        for dir_path in [self.videos_dir, self.transcripts_dir, self.cache_dir, 
                        self.metadata_dir, self.processed_dir]:
            dir_path.mkdir(exist_ok=True)
        
        # Create subdirectories for organization
        (self.videos_dir / "raw").mkdir(exist_ok=True)
        (self.videos_dir / "processed").mkdir(exist_ok=True)
        (self.transcripts_dir / "full").mkdir(exist_ok=True)
        (self.transcripts_dir / "clean").mkdir(exist_ok=True)
        (self.transcripts_dir / "text").mkdir(exist_ok=True)
        
        print(f"Data manager initialized with base directory: {self.base_dir}")
        print(f"Directory structure created:")
        print(f"  - Videos: {self.videos_dir}")
        print(f"  - Transcripts: {self.transcripts_dir}")
        print(f"  - Cache: {self.cache_dir}")
        print(f"  - Metadata: {self.metadata_dir}")
        print(f"  - Processed: {self.processed_dir}")
    
    def add_video(self, video_path: str, copy: bool = True, organize_by_date: bool = True) -> Dict:
        """
        Add a video to the data directory.
        
        Args:
            video_path: Path to the video file
            copy: Whether to copy the file (True) or move it (False)
            organize_by_date: Whether to organize videos by date
            
        Returns:
            Dict: Information about the added video
        """
        video_path = Path(video_path)
        
        if not video_path.exists():
            raise FileNotFoundError(f"Video file not found: {video_path}")
        
        # Generate video metadata
        video_info = self._get_video_info(video_path)
        
        # Determine destination directory
        if organize_by_date:
            date_str = datetime.now().strftime("%Y-%m-%d")
            dest_dir = self.videos_dir / "raw" / date_str
            dest_dir.mkdir(exist_ok=True)
        else:
            dest_dir = self.videos_dir / "raw"
        
        # Copy or move the file
        dest_path = dest_dir / video_path.name
        
        if copy:
            shutil.copy2(video_path, dest_path)
            print(f"Copied video to: {dest_path}")
        else:
            shutil.move(str(video_path), str(dest_path))
            print(f"Moved video to: {dest_path}")
        
        # Save metadata
        metadata_path = self.metadata_dir / f"{video_info['video_id']}.json"
        with open(metadata_path, 'w') as f:
            json.dump(video_info, f, indent=2)
        
        print(f"Video metadata saved to: {metadata_path}")
        return video_info
    
    def _get_video_info(self, video_path: Path) -> Dict:
        """Extract video information and metadata."""
        # Generate unique video ID
        video_id = self._generate_video_id(video_path)
        
        # Get file hash for deduplication
        file_hash = self._get_file_hash(video_path)
        
        # Get file size and modification time
        stat = video_path.stat()
        
        return {
            "video_id": video_id,
            "original_path": str(video_path),
            "filename": video_path.name,
            "file_hash": file_hash,
            "file_size_bytes": stat.st_size,
            "file_size_mb": round(stat.st_size / (1024 * 1024), 2),
            "modified_time": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "added_time": datetime.now().isoformat(),
            "status": "raw"
        }
    
    def _generate_video_id(self, video_path: Path) -> str:
        """Generate a unique video ID based on filename and content."""
        # Use filename and first part of hash for ID
        name_hash = hashlib.md5(video_path.name.encode()).hexdigest()[:8]
        return f"{video_path.stem}_{name_hash}"
    
    def _get_file_hash(self, file_path: Path) -> str:
        """Calculate SHA256 hash of file."""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    
    def list_videos(self, status: Optional[str] = None) -> List[Dict]:
        """
        List all videos in the data directory.
        
        Args:
            status: Filter by status ('raw', 'processed', 'transcribed')
            
        Returns:
            List of video information dictionaries
        """
        videos = []
        
        # Scan metadata directory
        for metadata_file in self.metadata_dir.glob("*.json"):
            try:
                with open(metadata_file, 'r') as f:
                    video_info = json.load(f)
                
                if status is None or video_info.get('status') == status:
                    videos.append(video_info)
            except Exception as e:
                print(f"Error reading metadata file {metadata_file}: {e}")
        
        return sorted(videos, key=lambda x: x.get('added_time', ''), reverse=True)
    
    def get_video_path(self, video_id: str) -> Optional[Path]:
        """Get the current path of a video by ID."""
        metadata_file = self.metadata_dir / f"{video_id}.json"
        
        if not metadata_file.exists():
            return None
        
        try:
            with open(metadata_file, 'r') as f:
                video_info = json.load(f)
            
            # Try to find the video file
            possible_paths = [
                Path(video_info.get('original_path', '')),
                self.videos_dir / "raw" / video_info.get('filename', ''),
                self.videos_dir / "processed" / video_info.get('filename', '')
            ]
            
            for path in possible_paths:
                if path.exists():
                    return path
            
            return None
        except Exception:
            return None
    
    def update_video_status(self, video_id: str, status: str, **kwargs):
        """Update video status and additional metadata."""
        metadata_file = self.metadata_dir / f"{video_id}.json"
        
        if not metadata_file.exists():
            raise FileNotFoundError(f"Video metadata not found: {video_id}")
        
        with open(metadata_file, 'r') as f:
            video_info = json.load(f)
        
        video_info['status'] = status
        video_info['updated_time'] = datetime.now().isoformat()
        
        # Add any additional metadata
        for key, value in kwargs.items():
            video_info[key] = value
        
        with open(metadata_file, 'w') as f:
            json.dump(video_info, f, indent=2)
        
        print(f"Updated video {video_id} status to: {status}")
    
    def organize_by_type(self, video_types: Dict[str, List[str]]):
        """
        Organize videos by type/category.
        
        Args:
            video_types: Dictionary mapping type names to lists of video IDs
        """
        for video_type, video_ids in video_types.items():
            type_dir = self.videos_dir / video_type
            type_dir.mkdir(exist_ok=True)
            
            for video_id in video_ids:
                video_path = self.get_video_path(video_id)
                if video_path and video_path.exists():
                    dest_path = type_dir / video_path.name
                    shutil.copy2(video_path, dest_path)
                    print(f"Organized {video_id} into {video_type} category")
    
    def create_batch_config(self, video_ids: List[str], config_template: Dict) -> Dict:
        """
        Create a batch processing configuration for multiple videos.
        
        Args:
            video_ids: List of video IDs to process
            config_template: Template configuration
            
        Returns:
            Batch configuration dictionary
        """
        batch_config = {
            "batch_id": f"batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "created_time": datetime.now().isoformat(),
            "videos": [],
            "default_config": config_template
        }
        
        for video_id in video_ids:
            video_path = self.get_video_path(video_id)
            if video_path:
                batch_config["videos"].append({
                    "video_id": video_id,
                    "video_path": str(video_path),
                    "config": config_template.copy()
                })
        
        # Save batch configuration
        batch_file = self.metadata_dir / f"{batch_config['batch_id']}.json"
        with open(batch_file, 'w') as f:
            json.dump(batch_config, f, indent=2)
        
        print(f"Created batch configuration: {batch_file}")
        return batch_config
    
    def get_directory_structure(self) -> Dict:
        """Get the current directory structure."""
        structure = {
            "base_dir": str(self.base_dir),
            "directories": {
                "videos": {
                    "path": str(self.videos_dir),
                    "subdirs": ["raw", "processed"]
                },
                "transcripts": {
                    "path": str(self.transcripts_dir),
                    "subdirs": ["full", "clean", "text"]
                },
                "cache": {
                    "path": str(self.cache_dir)
                },
                "metadata": {
                    "path": str(self.metadata_dir)
                },
                "processed": {
                    "path": str(self.processed_dir)
                }
            }
        }
        
        return structure
    
    def cleanup_old_files(self, days_old: int = 30):
        """Clean up old temporary files and cache."""
        cutoff_time = datetime.now().timestamp() - (days_old * 24 * 60 * 60)
        cleaned_count = 0
        
        # Clean cache directory
        for file_path in self.cache_dir.rglob("*"):
            if file_path.is_file() and file_path.stat().st_mtime < cutoff_time:
                file_path.unlink()
                cleaned_count += 1
        
        print(f"Cleaned up {cleaned_count} old files")
    
    def export_video_list(self, output_file: str = None) -> str:
        """Export list of all videos to a CSV file."""
        if output_file is None:
            output_file = self.base_dir / f"video_list_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        videos = self.list_videos()
        
        import csv
        with open(output_file, 'w', newline='') as f:
            if videos:
                writer = csv.DictWriter(f, fieldnames=videos[0].keys())
                writer.writeheader()
                writer.writerows(videos)
        
        print(f"Exported video list to: {output_file}")
        return str(output_file)


def main():
    """Main function for data setup and management."""
    parser = argparse.ArgumentParser(description='Data directory setup and management')
    parser.add_argument('--base-dir', type=str, default='data',
                       help='Base directory for data (default: data)')
    parser.add_argument('--add-video', type=str,
                       help='Add a video file to the data directory')
    parser.add_argument('--list-videos', action='store_true',
                       help='List all videos in the data directory')
    parser.add_argument('--organize', action='store_true',
                       help='Set up directory structure')
    parser.add_argument('--export', action='store_true',
                       help='Export video list to CSV')
    
    args = parser.parse_args()
    
    # Initialize data manager
    dm = DataManager(args.base_dir)
    
    if args.organize:
        print("Directory structure set up successfully!")
        print("\nRecommended organization:")
        print("📁 data/")
        print("├── 📁 videos/")
        print("│   ├── 📁 raw/          # Original video files")
        print("│   └── 📁 processed/    # Processed videos")
        print("├── 📁 transcripts/")
        print("│   ├── 📁 full/         # Full transcript JSON files")
        print("│   ├── 📁 clean/        # Clean transcript JSON files")
        print("│   └── 📁 text/         # Human-readable text files")
        print("├── 📁 cache/            # Processing cache")
        print("├── 📁 metadata/         # Video metadata")
        print("└── 📁 processed/        # Final outputs")
    
    if args.add_video:
        try:
            video_info = dm.add_video(args.add_video)
            print(f"Added video: {video_info['video_id']}")
            print(f"File size: {video_info['file_size_mb']} MB")
        except Exception as e:
            print(f"Error adding video: {e}")
    
    if args.list_videos:
        videos = dm.list_videos()
        print(f"\nFound {len(videos)} videos:")
        for video in videos:
            print(f"  - {video['video_id']}: {video['filename']} ({video['file_size_mb']} MB)")
    
    if args.export:
        csv_file = dm.export_video_list()
        print(f"Video list exported to: {csv_file}")


if __name__ == "__main__":
    main()
