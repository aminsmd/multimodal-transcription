#!/usr/bin/env python3
"""
Chunk processing utilities for the transcription pipeline.

This module provides utilities for processing individual video chunks.
"""

import os
from pathlib import Path
from typing import Dict, Any


class ChunkProcessor:
    """
    Handles processing of individual video chunks.
    """
    
    def __init__(self, run_dir: Path):
        """
        Initialize the chunk processor.
        
        Args:
            run_dir: Directory for storing processed chunks
        """
        self.run_dir = run_dir
    
    def get_chunk_info(self, chunk_path: str) -> Dict[str, Any]:
        """
        Get information about a video chunk.
        
        Args:
            chunk_path: Path to the chunk file
            
        Returns:
            Dictionary containing chunk information
        """
        chunk_size_mb = os.path.getsize(chunk_path) / (1024 * 1024)
        
        return {
            "path": chunk_path,
            "size_mb": chunk_size_mb,
            "exists": os.path.exists(chunk_path)
        }
    
    def validate_chunk(self, chunk_path: str) -> bool:
        """
        Validate that a chunk file exists and is readable.
        
        Args:
            chunk_path: Path to the chunk file
            
        Returns:
            True if chunk is valid, False otherwise
        """
        if not os.path.exists(chunk_path):
            return False
        
        try:
            # Try to get file size to ensure it's readable
            os.path.getsize(chunk_path)
            return True
        except OSError:
            return False
    
    def get_chunk_size_mb(self, chunk_path: str) -> float:
        """
        Get the size of a chunk file in MB.
        
        Args:
            chunk_path: Path to the chunk file
            
        Returns:
            Size in MB
        """
        try:
            size_bytes = os.path.getsize(chunk_path)
            return size_bytes / (1024 * 1024)
        except OSError:
            return 0.0
