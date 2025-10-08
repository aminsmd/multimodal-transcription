#!/usr/bin/env python3
"""
Transcript combination functionality for the transcription pipeline.

This module handles combining transcript entries from multiple chunks into a unified transcript.
"""

import json
import datetime
from pathlib import Path
from typing import Dict, List

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from models import FullTranscript, TranscriptEntry, TranscriptMetadata, TranscriptType
from utils import format_timestamp, parse_timestamp


class TranscriptCombiner:
    """
    Handles combining transcript entries from multiple chunks.
    """
    
    def __init__(self, run_dir: Path):
        """
        Initialize the transcript combiner.
        
        Args:
            run_dir: Directory for storing combined transcripts
        """
        self.run_dir = run_dir
        self.transcripts_dir = run_dir / "transcripts"
        self.transcripts_dir.mkdir(exist_ok=True)
    
    def create_full_transcript(self, transcript_analysis: Dict, video_id: str, config: Dict) -> Dict:
        """
        Create a full transcript without segmentation by combining all transcript entries.
        
        Args:
            transcript_analysis: Analysis results from all chunks
            video_id: Unique identifier for the video
            config: Pipeline configuration
            
        Returns:
            Dictionary containing the full transcript
        """
        print(f"\n=== Creating Full Transcript ===")
        
        # Collect all transcript entries from all chunks
        all_entries = []
        
        for chunk_data in transcript_analysis.get('chunks', []):
            chunk_transcript = chunk_data.get('transcript', {}).get('transcript', [])
            chunk_start_time = chunk_data.get('chunk_info', {}).get('start_time', 0)
            
            for entry in chunk_transcript:
                # Handle new format with start_time and end_time
                if "absolute_start_time" in entry and "absolute_end_time" in entry:
                    # Use the already calculated absolute timestamps
                    absolute_start_time = entry["absolute_start_time"]
                    absolute_end_time = entry["absolute_end_time"]
                    absolute_start_timestamp = entry.get("absolute_start_timestamp", format_timestamp(absolute_start_time))
                    absolute_end_timestamp = entry.get("absolute_end_timestamp", format_timestamp(absolute_end_time))
                else:
                    # Fallback to legacy format
                    entry_time = parse_timestamp(entry.get('time', '00:00'))
                    absolute_start_time = chunk_start_time + entry_time
                    absolute_end_time = absolute_start_time  # Same as start for legacy format
                    absolute_start_timestamp = format_timestamp(absolute_start_time)
                    absolute_end_timestamp = absolute_start_timestamp
                
                # Create full transcript entry
                full_entry = {
                    "time": absolute_start_timestamp,  # Main time field for backward compatibility
                    "type": entry.get('type', 'utterance'),  # Preserve entry type
                    "speaker": entry.get('speaker', ''),
                    "spoken_text": entry.get('spoken_text', ''),
                    "event_description": entry.get('event_description', ''),  # Preserve event description
                    "visual_description": entry.get('visual_description', ''),
                    "absolute_time": absolute_start_time,  # Used for sorting
                    "absolute_start_timestamp": absolute_start_timestamp,  # Used in text output
                    "absolute_end_timestamp": absolute_end_timestamp  # Used in text output
                }
                all_entries.append(full_entry)
        
        # Sort by absolute time to ensure chronological order
        all_entries.sort(key=lambda x: x['absolute_time'])
        
        # Create full transcript structure
        full_transcript = {
            "video_id": video_id,
            "transcript_type": "full",
            "metadata": {
                "total_entries": len(all_entries),
                "total_duration_seconds": max(entry['absolute_time'] for entry in all_entries) if all_entries else 0,
                "generation_date": datetime.datetime.now().isoformat(),
                "pipeline_configuration": config,
                "run_id": config.get('run_id', '')
            },
            "transcript": all_entries
        }
        
        # Save full transcript
        full_transcript_path = self.transcripts_dir / f'{video_id}_full_transcript.json'
        with open(full_transcript_path, 'w') as f:
            json.dump(full_transcript, f, indent=2)
        print(f"Full transcript saved to {full_transcript_path}")
        
        return full_transcript
