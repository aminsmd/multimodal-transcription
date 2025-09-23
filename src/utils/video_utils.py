#!/usr/bin/env python3
"""
Video utility functions for the transcription pipeline.
"""

import os
from pathlib import Path
from typing import Optional, Tuple
from moviepy import VideoFileClip


def get_video_duration(video_path: str) -> float:
    """
    Get the duration of a video file in seconds.
    
    Args:
        video_path: Path to the video file
        
    Returns:
        Duration in seconds
    """
    try:
        with VideoFileClip(video_path) as clip:
            return clip.duration
    except Exception as e:
        print(f"Error getting video duration: {e}")
        return 0.0


def validate_video_file(video_path: str) -> Tuple[bool, str]:
    """
    Validate that a video file is readable and supported.
    
    Args:
        video_path: Path to the video file
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not os.path.exists(video_path):
        return False, f"File not found: {video_path}"
    
    if not os.path.isfile(video_path):
        return False, f"Path is not a file: {video_path}"
    
    # Check file extension
    supported_extensions = {'.mp4', '.mov', '.avi', '.mkv', '.webm', '.m4v'}
    file_ext = Path(video_path).suffix.lower()
    if file_ext not in supported_extensions:
        return False, f"Unsupported file format: {file_ext}"
    
    # Try to open the video file
    try:
        with VideoFileClip(video_path) as clip:
            # Just check if we can get basic info
            _ = clip.duration
            _ = clip.size
        return True, ""
    except Exception as e:
        return False, f"Error reading video file: {e}"


def format_timestamp(seconds: float) -> str:
    """
    Format seconds as MM:SS or HH:MM:SS.
    
    Args:
        seconds: Time in seconds
        
    Returns:
        Formatted timestamp string
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    milliseconds = int((seconds % 1) * 1000)
    
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}.{milliseconds:03d}"
    else:
        return f"{minutes:02d}:{secs:02d}.{milliseconds:03d}"


def parse_timestamp(timestamp: str) -> float:
    """
    Parse a timestamp string to seconds.
    
    Args:
        timestamp: Timestamp in MM:SS or HH:MM:SS format
        
    Returns:
        Time in seconds
    """
    try:
        parts = timestamp.split(':')
        if len(parts) == 2:  # MM:SS
            minutes, seconds = parts
            return int(minutes) * 60 + float(seconds)
        elif len(parts) == 3:  # HH:MM:SS
            hours, minutes, seconds = parts
            return int(hours) * 3600 + int(minutes) * 60 + float(seconds)
        else:
            return float(timestamp)
    except Exception:
        return 0.0
