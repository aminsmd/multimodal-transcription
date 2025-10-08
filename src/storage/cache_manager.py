#!/usr/bin/env python3
"""
Cache management for the transcription pipeline.

This module handles caching of transcripts and other pipeline results.
"""

import json
import datetime
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Any

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from models import TranscriptionConfig, CacheEntry


class CacheManager:
    """
    Manages caching for the transcription pipeline.
    """
    
    def __init__(self, base_dir: Path, global_cache_dir: Optional[Path] = None):
        """
        Initialize the cache manager.
        
        Args:
            base_dir: Base directory for the pipeline
            global_cache_dir: Global cache directory (optional)
        """
        self.base_dir = base_dir
        self.global_cache_dir = global_cache_dir or base_dir / "transcript_cache"
        self.global_cache_dir.mkdir(exist_ok=True)
    
    def get_config_hash(self, config: TranscriptionConfig) -> str:
        """
        Generate a hash for the current configuration.
        
        Args:
            config: Transcription configuration
            
        Returns:
            Configuration hash string
        """
        return config.get_config_hash()
    
    def get_video_hash(self, video_path: str) -> str:
        """
        Get hash of video file for cache key.
        
        Args:
            video_path: Path to the video file
            
        Returns:
            Video file hash
        """
        return self._get_file_hash(video_path)
    
    def check_existing_transcript(self, video_id: str, config: TranscriptionConfig) -> Optional[Dict]:
        """
        Check if a transcript already exists for this video with the same configuration.
        
        Args:
            video_id: Unique identifier for the video
            config: Transcription configuration
            
        Returns:
            Cached transcript data if found, None otherwise
        """
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
    
    def save_transcript_cache(self, video_id: str, config_hash: str, transcript_path: str, config: Dict):
        """
        Save transcript to global cache.
        
        Args:
            video_id: Unique identifier for the video
            config_hash: Configuration hash
            transcript_path: Path to the transcript file
            config: Configuration dictionary
        """
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
    
    def list_cached_transcripts(self) -> List[Dict]:
        """
        List all cached transcripts.
        
        Returns:
            List of cached transcript information
        """
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
        """
        Clear transcript cache.
        
        Args:
            video_id: Video ID to clear (clears all if None)
            
        Returns:
            Number of cache entries cleared
        """
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
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary containing cache statistics
        """
        cached_transcripts = self.list_cached_transcripts()
        
        stats = {
            "total_cached_transcripts": len(cached_transcripts),
            "cache_directory": str(self.global_cache_dir),
            "cache_files": len(list(self.global_cache_dir.glob("*.json"))),
            "videos": list(set(t.get('video_id') for t in cached_transcripts)),
            "oldest_cache": None,
            "newest_cache": None
        }
        
        if cached_transcripts:
            dates = [t.get('generation_date') for t in cached_transcripts if t.get('generation_date')]
            if dates:
                stats["oldest_cache"] = min(dates)
                stats["newest_cache"] = max(dates)
        
        return stats
    
    def cleanup_old_cache(self, days_old: int = 30) -> int:
        """
        Clean up old cache entries.
        
        Args:
            days_old: Age threshold in days
            
        Returns:
            Number of entries cleaned up
        """
        cutoff_date = datetime.datetime.now() - datetime.timedelta(days=days_old)
        cleaned_count = 0
        
        for cache_file in self.global_cache_dir.glob("*.json"):
            try:
                with open(cache_file, 'r') as f:
                    cache_data = json.load(f)
                
                generation_date = cache_data.get('generation_date')
                if generation_date:
                    cache_date = datetime.datetime.fromisoformat(generation_date)
                    if cache_date < cutoff_date:
                        cache_file.unlink()
                        cleaned_count += 1
            except Exception as e:
                print(f"Error processing cache file {cache_file}: {e}")
                # Remove corrupted cache entry
                cache_file.unlink()
                cleaned_count += 1
        
        print(f"Cleaned up {cleaned_count} old cache entries")
        return cleaned_count
    
    def _get_file_hash(self, file_path: str) -> str:
        """
        Calculate file hash for caching.
        
        Args:
            file_path: Path to the file
            
        Returns:
            SHA256 hash of the file
        """
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
