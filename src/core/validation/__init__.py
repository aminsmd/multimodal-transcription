#!/usr/bin/env python3
"""
Transcript validation module.

This module provides validation functionality for transcript outputs,
including chronological order checking, gap detection, and failed chunk identification.
"""

from .transcript_validator import TranscriptValidator

__all__ = ['TranscriptValidator']


