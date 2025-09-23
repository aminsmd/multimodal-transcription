#!/usr/bin/env python3
"""
Configuration utility functions for the transcription pipeline.
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from models import TranscriptionConfig


def load_config(config_path: str) -> Optional[TranscriptionConfig]:
    """
    Load configuration from a JSON file.
    
    Args:
        config_path: Path to configuration file
        
    Returns:
        TranscriptionConfig object or None
    """
    try:
        with open(config_path, 'r') as f:
            config_dict = json.load(f)
        return TranscriptionConfig.from_dict(config_dict)
    except Exception as e:
        print(f"Error loading config: {e}")
        return None


def save_config(config: TranscriptionConfig, config_path: str) -> bool:
    """
    Save configuration to a JSON file.
    
    Args:
        config: TranscriptionConfig object
        config_path: Path to save configuration
        
    Returns:
        True if successful, False otherwise
    """
    try:
        config_dict = config.to_dict()
        with open(config_path, 'w') as f:
            json.dump(config_dict, f, indent=2)
        return True
    except Exception as e:
        print(f"Error saving config: {e}")
        return False


def validate_config(config: TranscriptionConfig) -> tuple[bool, str]:
    """
    Validate a configuration object.
    
    Args:
        config: TranscriptionConfig object
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        # The config validation is done in __post_init__
        # This function provides additional validation if needed
        return True, ""
    except Exception as e:
        return False, str(e)


def create_config_from_dict(config_dict: Dict[str, Any]) -> Optional[TranscriptionConfig]:
    """
    Create a TranscriptionConfig from a dictionary.
    
    Args:
        config_dict: Configuration dictionary
        
    Returns:
        TranscriptionConfig object or None
    """
    try:
        return TranscriptionConfig.from_dict(config_dict)
    except Exception as e:
        print(f"Error creating config from dict: {e}")
        return None


def merge_configs(base_config: TranscriptionConfig, override_dict: Dict[str, Any]) -> TranscriptionConfig:
    """
    Merge a base configuration with override values.
    
    Args:
        base_config: Base configuration
        override_dict: Override values
        
    Returns:
        New TranscriptionConfig with merged values
    """
    base_dict = base_config.to_dict()
    base_dict.update(override_dict)
    return TranscriptionConfig.from_dict(base_dict)
