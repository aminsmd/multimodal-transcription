#!/usr/bin/env python3
"""
File utility functions for the transcription pipeline.
"""

import hashlib
import os
from pathlib import Path
from typing import Optional


def get_file_hash(file_path: str) -> str:
    """
    Calculate SHA256 hash of a file.
    
    Args:
        file_path: Path to the file
        
    Returns:
        SHA256 hash as hex string
    """
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def create_safe_filename(filename: str) -> str:
    """
    Create a safe filename by removing/replacing invalid characters.
    
    Args:
        filename: Original filename
        
    Returns:
        Safe filename
    """
    # Replace invalid characters
    invalid_chars = '<>:"/\\|?*'
    safe_filename = filename
    for char in invalid_chars:
        safe_filename = safe_filename.replace(char, '_')
    
    # Remove leading/trailing spaces and dots
    safe_filename = safe_filename.strip(' .')
    
    # Ensure it's not empty
    if not safe_filename:
        safe_filename = "unnamed_file"
    
    return safe_filename


def ensure_directory(path: str) -> Path:
    """
    Ensure a directory exists, creating it if necessary.
    
    Args:
        path: Directory path
        
    Returns:
        Path object
    """
    dir_path = Path(path)
    dir_path.mkdir(parents=True, exist_ok=True)
    return dir_path


def get_file_size_mb(file_path: str) -> float:
    """
    Get file size in megabytes.
    
    Args:
        file_path: Path to the file
        
    Returns:
        Size in megabytes
    """
    try:
        size_bytes = os.path.getsize(file_path)
        return size_bytes / (1024 * 1024)
    except OSError:
        return 0.0


def find_files_by_extension(directory: str, extensions: list) -> list:
    """
    Find files with specific extensions in a directory.
    
    Args:
        directory: Directory to search
        extensions: List of file extensions (with dots)
        
    Returns:
        List of file paths
    """
    directory = Path(directory)
    if not directory.exists():
        return []
    
    files = []
    for ext in extensions:
        files.extend(directory.glob(f"*{ext}"))
        files.extend(directory.glob(f"*{ext.upper()}"))
    
    return [str(f) for f in files]


def copy_file_safe(src: str, dst: str) -> bool:
    """
    Safely copy a file, creating directories if needed.
    
    Args:
        src: Source file path
        dst: Destination file path
        
    Returns:
        True if successful, False otherwise
    """
    try:
        src_path = Path(src)
        dst_path = Path(dst)
        
        # Create destination directory
        dst_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Copy file
        import shutil
        shutil.copy2(src_path, dst_path)
        return True
    except Exception:
        return False
