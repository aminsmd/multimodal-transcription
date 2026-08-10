#!/usr/bin/env python3
"""
Video utility functions for the transcription pipeline.
"""

import os
import json
import subprocess
from pathlib import Path
from typing import Dict, Optional, Tuple


def get_video_probe(video_path: str) -> Dict:
    """
    Get video container metadata using ffprobe.

    ffprobe is more tolerant than MoviePy for files with extra unsupported
    streams, such as iPhone videos that include Apple spatial/audio metadata.
    """
    cmd = [
        "ffprobe",
        "-v", "error",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        video_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise ValueError(result.stderr.strip() or "ffprobe failed")

    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid ffprobe output: {e}")


def get_primary_video_stream(video_path: str) -> Optional[Dict]:
    """Return the first video stream from a media file."""
    probe = get_video_probe(video_path)
    for stream in probe.get("streams", []):
        if stream.get("codec_type") == "video":
            return stream
    return None


def get_primary_audio_stream(video_path: str) -> Optional[Dict]:
    """Return the first audio stream with a codec FFmpeg can identify."""
    probe = get_video_probe(video_path)
    unsupported_codecs = {"none", "unknown", ""}
    for stream in probe.get("streams", []):
        if stream.get("codec_type") != "audio":
            continue
        codec_name = (stream.get("codec_name") or "").lower()
        if codec_name not in unsupported_codecs:
            return stream
    return None


def get_ffmpeg_primary_stream_map_args(video_path: str) -> list:
    """
    Build ffmpeg -map arguments for the primary video and first supported audio.

    This intentionally excludes data, subtitles, metadata-only streams, and
    unsupported audio streams that can make MoviePy/FFmpeg fail on otherwise
    valid videos.
    """
    probe = get_video_probe(video_path)
    video_stream = None
    audio_stream = None
    unsupported_audio_codecs = {"none", "unknown", ""}

    for stream in probe.get("streams", []):
        codec_type = stream.get("codec_type")
        if codec_type == "video" and video_stream is None:
            video_stream = stream
        elif codec_type == "audio" and audio_stream is None:
            codec_name = (stream.get("codec_name") or "").lower()
            if codec_name not in unsupported_audio_codecs:
                audio_stream = stream

    if video_stream is None:
        raise ValueError("No video stream found")

    map_args = ["-map", f"0:{video_stream['index']}"]
    if audio_stream is not None:
        map_args.extend(["-map", f"0:{audio_stream['index']}"])
    return map_args


def get_video_duration(video_path: str) -> float:
    """
    Get the duration of a video file in seconds.
    
    Args:
        video_path: Path to the video file
        
    Returns:
        Duration in seconds
    """
    try:
        probe = get_video_probe(video_path)
        duration = probe.get("format", {}).get("duration")
        if duration:
            return float(duration)

        for stream in probe.get("streams", []):
            if stream.get("codec_type") == "video" and stream.get("duration"):
                return float(stream["duration"])
    except Exception as e:
        print(f"Error getting video duration with ffprobe: {e}")

    try:
        from moviepy import VideoFileClip

        with VideoFileClip(video_path) as clip:
            return clip.duration
    except Exception as e:
        print(f"Error getting video duration with MoviePy: {e}")
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
    
    # Try to inspect the video file with ffprobe. This validates the usable
    # video stream without failing on unrelated unsupported side streams.
    try:
        probe = get_video_probe(video_path)
        video_stream = None
        for stream in probe.get("streams", []):
            if stream.get("codec_type") == "video":
                video_stream = stream
                break

        if video_stream is None:
            return False, "No video stream found"

        duration = probe.get("format", {}).get("duration") or video_stream.get("duration")
        if duration is None or float(duration) <= 0:
            return False, "Video duration is missing or zero"

        width = int(video_stream.get("width") or 0)
        height = int(video_stream.get("height") or 0)
        if width <= 0 or height <= 0:
            return False, "Video dimensions are missing or invalid"

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