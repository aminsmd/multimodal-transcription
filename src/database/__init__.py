#!/usr/bin/env python3
"""
Database module for video processing.

This module provides database interfaces for managing video processing jobs.
"""

from .video_database import VideoDatabase, VideoMetadata, VideoStatus

__all__ = ['VideoDatabase', 'VideoMetadata', 'VideoStatus']
