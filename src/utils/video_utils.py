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
            minutes_int = int(minutes)
            seconds_float = float(seconds)
            
            # Validate seconds (should be 0-59.999)
            if seconds_float >= 60:
                print(f"Warning: Invalid seconds {seconds_float} in timestamp '{timestamp}', capping at 59.999")
                seconds_float = 59.999
            
            return minutes_int * 60 + seconds_float
        elif len(parts) == 3:  # HH:MM:SS
            hours, minutes, seconds = parts
            hours_int = int(hours)
            minutes_int = int(minutes)
            seconds_float = float(seconds)
            
            # Validate minutes (should be 0-59)
            if minutes_int >= 60:
                print(f"Warning: Invalid minutes {minutes_int} in timestamp '{timestamp}', capping at 59")
                minutes_int = 59
            
            # Validate seconds (should be 0-59.999)
            if seconds_float >= 60:
                print(f"Warning: Invalid seconds {seconds_float} in timestamp '{timestamp}', capping at 59.999")
                seconds_float = 59.999
            
            return hours_int * 3600 + minutes_int * 60 + seconds_float
        else:
            return float(timestamp)
    except Exception as e:
        print(f"Warning: Could not parse timestamp '{timestamp}': {e}, using 0.0")
        return 0.0
