#!/usr/bin/env python3
"""
S3 utility functions for downloading videos from S3 buckets.

This module handles downloading videos from S3 buckets using boto3.
"""

import boto3
import os
from pathlib import Path
from typing import Optional, Tuple
from urllib.parse import urlparse


def extract_bucket_name_from_url(s3_url: str) -> str:
    """
    Extract bucket name from various S3 URL formats.
    
    Args:
        s3_url: S3 URL in various formats:
            - Console URL: https://us-east-1.console.aws.amazon.com/s3/buckets/bucket-name?region=us-east-1
            - S3 URI: s3://bucket-name/path
            - HTTPS URL: https://bucket-name.s3.region.amazonaws.com/path
            - Just bucket name: bucket-name
    
    Returns:
        Bucket name extracted from URL
    """
    # If it's just a bucket name, return it
    if not s3_url.startswith(('http://', 'https://', 's3://')):
        return s3_url
    
    # Handle console URL
    if 'console.aws.amazon.com/s3/buckets/' in s3_url:
        # Extract bucket name from console URL
        # Format: https://region.console.aws.amazon.com/s3/buckets/bucket-name?region=region
        parts = s3_url.split('/buckets/')
        if len(parts) > 1:
            bucket_name = parts[1].split('?')[0].split('/')[0]
            return bucket_name
    
    # Handle S3 URI (s3://bucket-name/path)
    if s3_url.startswith('s3://'):
        parsed = urlparse(s3_url)
        return parsed.netloc
    
    # Handle HTTPS URL (https://bucket-name.s3.region.amazonaws.com/path)
    if s3_url.startswith('http://') or s3_url.startswith('https://'):
        parsed = urlparse(s3_url)
        hostname = parsed.netloc
        # Check if it's an S3 endpoint
        if '.s3.' in hostname or 's3.' in hostname:
            # Extract bucket name (usually the first part before .s3.)
            bucket_name = hostname.split('.')[0]
            return bucket_name
    
    # If we can't parse it, return as-is (might be just a bucket name)
    return s3_url


def construct_s3_url(bucket_name: str, video_path: str) -> str:
    """
    Construct a full S3 URL from bucket name and video path.
    
    Args:
        bucket_name: S3 bucket name
        video_path: Path to video within the bucket (may or may not start with /)
    
    Returns:
        S3 URI in format s3://bucket-name/path/to/video.mp4
    """
    # Remove leading slash from video_path if present
    video_path = video_path.lstrip('/')
    
    # Construct S3 URI
    return f"s3://{bucket_name}/{video_path}"


def download_video_from_s3(
    s3_url: str,
    local_path: Optional[str] = None,
    region_name: str = "us-east-1"
) -> Tuple[str, bool]:
    """
    Download a video file from S3.
    
    Args:
        s3_url: S3 URL in format s3://bucket-name/path/to/video.mp4
        local_path: Local path to save the video. If None, uses video filename in /tmp
        region_name: AWS region name (default: us-east-1)
    
    Returns:
        Tuple of (local_file_path, success)
    """
    try:
        # Parse S3 URL
        if not s3_url.startswith('s3://'):
            raise ValueError(f"Invalid S3 URL format: {s3_url}. Expected format: s3://bucket-name/path")
        
        parsed = urlparse(s3_url)
        bucket_name = parsed.netloc
        s3_key = parsed.path.lstrip('/')
        
        if not bucket_name or not s3_key:
            raise ValueError(f"Invalid S3 URL: {s3_url}")
        
        # Determine local path
        if local_path is None:
            # Use /tmp directory with video filename
            video_filename = Path(s3_key).name
            local_path = f"/tmp/{video_filename}"
        else:
            # Ensure directory exists
            local_dir = Path(local_path).parent
            local_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize S3 client
        s3_client = boto3.client('s3', region_name=region_name)
        
        # Download file
        print(f"Downloading {s3_url} to {local_path}...")
        s3_client.download_file(bucket_name, s3_key, local_path)
        
        print(f"✅ Successfully downloaded video to {local_path}")
        return local_path, True
        
    except Exception as e:
        error_msg = f"Failed to download video from S3: {str(e)}"
        print(f"❌ {error_msg}")
        return "", False


def get_s3_bucket_path() -> str:
    """
    Get S3 bucket path from environment variable S3_BUCKET_PATH.
    
    Returns:
        S3 bucket name or path
    """
    s3_bucket_path = os.getenv('S3_BUCKET_PATH', '')
    
    if not s3_bucket_path:
        raise ValueError("S3_BUCKET_PATH environment variable is not set")
    
    # Extract bucket name from URL if it's a console URL
    bucket_name = extract_bucket_name_from_url(s3_bucket_path)
    
    return bucket_name

