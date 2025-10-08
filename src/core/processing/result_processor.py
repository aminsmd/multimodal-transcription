#!/usr/bin/env python3
"""
Result processing functionality for the transcription pipeline.

This module handles processing and combining results from various pipeline stages.
"""

import json
import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from models import PipelineResults, FullTranscript, CacheEntry


class ResultProcessor:
    """
    Handles processing and combining results from pipeline stages.
    """
    
    def __init__(self, run_dir: Path):
        """
        Initialize the result processor.
        
        Args:
            run_dir: Directory for storing results
        """
        self.run_dir = run_dir
        self.results_dir = run_dir
        self.results_dir.mkdir(exist_ok=True)
    
    def create_pipeline_results(self, video_id: str, original_input: str, 
                               chunk_duration: int, max_workers: int,
                               transcript_analysis: Dict, full_transcript: Dict,
                               cached: bool = False, cache_info: Optional[CacheEntry] = None) -> PipelineResults:
        """
        Create pipeline results from processing data.
        
        Args:
            video_id: Unique identifier for the video
            original_input: Original input path
            chunk_duration: Duration of chunks used
            max_workers: Number of workers used
            transcript_analysis: Analysis results from chunks
            full_transcript: Full transcript data
            cached: Whether results were from cache
            cache_info: Cache information if applicable
            
        Returns:
            PipelineResults object
        """
        # Convert full_transcript dict to FullTranscript object
        full_transcript_obj = FullTranscript.from_dict(full_transcript)
        
        # Create pipeline results
        pipeline_results = PipelineResults(
            video_id=video_id,
            original_input=original_input,
            processing_date=datetime.datetime.now().isoformat(),
            chunk_duration=chunk_duration,
            max_workers=max_workers,
            transcript_analysis=transcript_analysis,
            full_transcript=full_transcript_obj,
            cached=cached,
            cache_info=cache_info
        )
        
        return pipeline_results
    
    def save_pipeline_results(self, pipeline_results: PipelineResults, video_id: str) -> Path:
        """
        Save pipeline results to file.
        
        Args:
            pipeline_results: PipelineResults object to save
            video_id: Unique identifier for the video
            
        Returns:
            Path to saved results file
        """
        output_path = self.results_dir / f"{video_id}_pipeline_results.json"
        with open(output_path, 'w') as f:
            json.dump(pipeline_results.to_dict(), f, indent=2)
        
        print(f"Pipeline results saved to {output_path}")
        return output_path
    
    def combine_transcript_entries(self, transcript_analysis: Dict) -> List[Dict]:
        """
        Combine transcript entries from all chunks into a single list.
        
        Args:
            transcript_analysis: Analysis results from all chunks
            
        Returns:
            List of combined transcript entries
        """
        all_entries = []
        
        for chunk_data in transcript_analysis.get('chunks', []):
            chunk_transcript = chunk_data.get('transcript', {}).get('transcript', [])
            for entry in chunk_transcript:
                all_entries.append(entry)
        
        return all_entries
    
    def sort_transcript_entries(self, entries: List[Dict]) -> List[Dict]:
        """
        Sort transcript entries by absolute time.
        
        Args:
            entries: List of transcript entries
            
        Returns:
            Sorted list of transcript entries
        """
        return sorted(entries, key=lambda x: x.get('absolute_time', 0))
    
    def validate_transcript_entries(self, entries: List[Dict]) -> Dict[str, Any]:
        """
        Validate transcript entries and return validation results.
        
        Args:
            entries: List of transcript entries to validate
            
        Returns:
            Dictionary containing validation results
        """
        validation_results = {
            "total_entries": len(entries),
            "valid_entries": 0,
            "invalid_entries": 0,
            "missing_timestamps": 0,
            "missing_speakers": 0,
            "empty_text": 0,
            "errors": []
        }
        
        for i, entry in enumerate(entries):
            is_valid = True
            
            # Check for required fields
            if not entry.get('time') and not entry.get('absolute_time'):
                validation_results["missing_timestamps"] += 1
                validation_results["errors"].append(f"Entry {i}: Missing timestamp")
                is_valid = False
            
            if entry.get('type') == 'utterance' and not entry.get('speaker'):
                validation_results["missing_speakers"] += 1
                validation_results["errors"].append(f"Entry {i}: Missing speaker for utterance")
                is_valid = False
            
            if not entry.get('spoken_text') and not entry.get('event_description'):
                validation_results["empty_text"] += 1
                validation_results["errors"].append(f"Entry {i}: No text content")
                is_valid = False
            
            if is_valid:
                validation_results["valid_entries"] += 1
            else:
                validation_results["invalid_entries"] += 1
        
        return validation_results
    
    def get_processing_statistics(self, transcript_analysis: Dict) -> Dict[str, Any]:
        """
        Get processing statistics from transcript analysis.
        
        Args:
            transcript_analysis: Analysis results from all chunks
            
        Returns:
            Dictionary containing processing statistics
        """
        stats = {
            "total_chunks": len(transcript_analysis.get('chunks', [])),
            "successful_chunks": 0,
            "failed_chunks": 0,
            "total_entries": 0,
            "processing_errors": []
        }
        
        for chunk_data in transcript_analysis.get('chunks', []):
            chunk_result = chunk_data.get('transcript', {})
            
            if chunk_result.get('error'):
                stats["failed_chunks"] += 1
                stats["processing_errors"].append({
                    "chunk": chunk_data.get('chunk_info', {}),
                    "error": chunk_result.get('error')
                })
            else:
                stats["successful_chunks"] += 1
                stats["total_entries"] += len(chunk_result.get('transcript', []))
        
        return stats
