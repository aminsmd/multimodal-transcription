#!/usr/bin/env python3
"""
Processing modules for the transcription pipeline.

This package handles parallel processing and result processing.
"""

from .parallel_processor import ParallelProcessor
from .result_processor import ResultProcessor

__all__ = [
    'ParallelProcessor',
    'ResultProcessor'
]
