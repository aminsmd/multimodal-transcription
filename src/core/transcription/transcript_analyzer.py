#!/usr/bin/env python3
"""
Transcript analysis functionality for the transcription pipeline.

This module handles the core logic for analyzing video chunks and generating transcripts.
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional
from concurrent.futures import ThreadPoolExecutor

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from models import TranscriptionConfig, FullTranscript
from utils import format_timestamp, parse_timestamp


class TranscriptAnalyzer:
    """
    Handles transcript analysis for video chunks.
    """
    
    def __init__(self, ai_client, prompt_manager, run_dir: Path):
        """
        Initialize the transcript analyzer.
        
        Args:
            ai_client: AI client for generating transcripts
            prompt_manager: Prompt manager for handling prompts
            run_dir: Directory for storing results
        """
        self.ai_client = ai_client
        self.prompt_manager = prompt_manager
        self.run_dir = run_dir
        self.transcripts_dir = run_dir / "transcripts"
        self.transcripts_dir.mkdir(exist_ok=True)
    
    def analyze_chunk_transcript(self, chunk_path: str, start_time: int, end_time: int, video_duration: float = 0) -> Dict:
        """
        Analyze a single chunk for transcript.
        
        Args:
            chunk_path: Path to the video chunk
            start_time: Start time of the chunk
            end_time: End time of the chunk
            video_duration: Total video duration
            
        Returns:
            Dictionary containing transcript analysis results
        """
        chunk_size_mb = os.path.getsize(chunk_path) / (1024 * 1024)
        
        print(f"Analyzing transcript for chunk {start_time}-{end_time} ({chunk_size_mb:.1f}MB)")
        
        # Get prompt for this chunk
        prompt = self.prompt_manager.get_transcript_prompt(
            video_duration=video_duration, 
            chunk_start=start_time, 
            chunk_end=end_time
        )
        
        # Generate transcript using AI client
        raw_response_dir = str(self.run_dir / "raw_responses")
        if chunk_size_mb < 20:
            print(f"Using direct bytes analysis for chunk {start_time}-{end_time} ({chunk_size_mb:.1f}MB)")
            result = self.ai_client.analyze_chunk_direct(chunk_path, prompt, raw_response_dir)
        else:
            print(f"Using file upload for chunk {start_time}-{end_time} ({chunk_size_mb:.1f}MB)")
            result = self.ai_client.analyze_chunk_upload(chunk_path, prompt, raw_response_dir)
        
        # Process the result
        if result.get('error'):
            print(f"Error analyzing chunk {start_time}-{end_time}: {result['error']}")
            return result
        
        # Adjust timestamps to be absolute
        transcript_entries = result.get('transcript', [])
        for i, entry in enumerate(transcript_entries):
            transcript_entries[i] = self._process_transcript_entry(entry, i, start_time, end_time)
        
        result['transcript'] = transcript_entries
        return result
    
    def analyze_all_chunks_parallel(self, chunks_metadata: Dict, video_id: str, max_workers: int = 4) -> Dict:
        """
        Analyze all chunks for transcripts using parallel processing.
        
        Args:
            chunks_metadata: Metadata about video chunks
            video_id: Unique identifier for the video
            max_workers: Maximum number of parallel workers
            
        Returns:
            Dictionary containing combined transcript analysis
        """
        print(f"Analyzing {len(chunks_metadata['chunks'])} chunks for transcripts using parallel processing...")
        
        all_transcripts = []
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = []
            
            for chunk_info in chunks_metadata['chunks']:
                future = executor.submit(
                    self.analyze_chunk_transcript,
                    chunk_info['path'],
                    chunk_info['start_time'],
                    chunk_info['end_time'],
                    chunks_metadata.get('total_duration', 0)
                )
                futures.append((chunk_info, future))
            
            for chunk_info, future in futures:
                try:
                    result = future.result()
                    all_transcripts.append({
                        "chunk_info": chunk_info,
                        "transcript": result
                    })
                except Exception as e:
                    print(f"Error analyzing chunk {chunk_info['start_time']}-{chunk_info['end_time']}: {str(e)}")
                    all_transcripts.append({
                        "chunk_info": chunk_info,
                        "transcript": {"transcript": [], "error": str(e)}
                    })
        
        # Combine all transcripts
        combined_transcript = {
            "video_id": video_id,
            "processing_date": self._get_current_timestamp(),
            "chunks": all_transcripts,
            "all_transcript_entries": []
        }
        
        # Flatten all transcript entries
        for chunk_data in all_transcripts:
            for entry in chunk_data['transcript'].get('transcript', []):
                combined_transcript['all_transcript_entries'].append(entry)
        
        # Save combined transcript
        output_path = self.transcripts_dir / f"{video_id}_transcript.json"
        with open(output_path, 'w') as f:
            json.dump(combined_transcript, f, indent=2)
        
        print(f"Transcript analysis saved to {output_path}")
        return combined_transcript
    
    def _process_transcript_entry(self, entry: dict, i: int, start_time: int, end_time: int) -> dict:
        """
        Process a single transcript entry to handle different formats and add required fields.
        
        Args:
            entry: Transcript entry dictionary
            i: Entry index
            start_time: Chunk start time
            end_time: Chunk end time
            
        Returns:
            Processed entry dictionary
        """
        if isinstance(entry, dict):
            # Handle new format with type field (utterance/event) and start_time/end_time
            if "type" in entry and "start_time" in entry and "end_time" in entry:
                try:
                    chunk_start_time = parse_timestamp(entry["start_time"])
                    chunk_end_time = parse_timestamp(entry["end_time"])
                    absolute_start_time = start_time + chunk_start_time
                    absolute_end_time = start_time + chunk_end_time
                    entry["absolute_start_time"] = absolute_start_time
                    entry["absolute_end_time"] = absolute_end_time
                    entry["absolute_start_timestamp"] = format_timestamp(absolute_start_time)
                    entry["absolute_end_timestamp"] = format_timestamp(absolute_end_time)
                    # Keep the original time field for backward compatibility (use start_time)
                    entry["time"] = entry["start_time"]
                    entry["absolute_time"] = absolute_start_time
                    entry["absolute_timestamp"] = format_timestamp(absolute_start_time)
                    
                    # Handle different entry types
                    if entry["type"] == "utterance":
                        # Ensure required fields for utterance
                        if "speaker" not in entry:
                            entry["speaker"] = "speaker"
                        if "spoken_text" not in entry:
                            entry["spoken_text"] = ""
                        # Add visual_description for backward compatibility
                        if "visual_description" not in entry:
                            entry["visual_description"] = ""
                    elif entry["type"] == "event":
                        # Ensure required fields for event
                        if "event_description" not in entry:
                            entry["event_description"] = ""
                        # Add speaker and spoken_text for backward compatibility
                        if "speaker" not in entry:
                            entry["speaker"] = ""
                        if "spoken_text" not in entry:
                            entry["spoken_text"] = ""
                        # Map event_description to visual_description for backward compatibility
                        if "visual_description" not in entry:
                            entry["visual_description"] = entry.get("event_description", "")
                            
                except Exception as e:
                    print(f"Warning: Failed to parse timestamps '{entry['start_time']}' or '{entry['end_time']}' for entry {i} in chunk {start_time}-{end_time}: {str(e)}")
                    # Fallback: use chunk start time
                    entry["absolute_start_time"] = start_time
                    entry["absolute_end_time"] = start_time
                    entry["absolute_start_timestamp"] = format_timestamp(start_time)
                    entry["absolute_end_timestamp"] = format_timestamp(start_time)
                    entry["time"] = "00:00"
                    entry["absolute_time"] = start_time
                    entry["absolute_timestamp"] = format_timestamp(start_time)
            # Handle legacy format with start_time and end_time (no type field)
            elif "start_time" in entry and "end_time" in entry:
                try:
                    chunk_start_time = parse_timestamp(entry["start_time"])
                    chunk_end_time = parse_timestamp(entry["end_time"])
                    absolute_start_time = start_time + chunk_start_time
                    absolute_end_time = start_time + chunk_end_time
                    entry["absolute_start_time"] = absolute_start_time
                    entry["absolute_end_time"] = absolute_end_time
                    entry["absolute_start_timestamp"] = format_timestamp(absolute_start_time)
                    entry["absolute_end_timestamp"] = format_timestamp(absolute_end_time)
                    # Keep the original time field for backward compatibility (use start_time)
                    entry["time"] = entry["start_time"]
                    entry["absolute_time"] = absolute_start_time
                    entry["absolute_timestamp"] = format_timestamp(absolute_start_time)
                    # Add type field for new format compatibility
                    if "type" not in entry:
                        entry["type"] = "utterance"
                except Exception as e:
                    print(f"Warning: Failed to parse timestamps '{entry['start_time']}' or '{entry['end_time']}' for entry {i} in chunk {start_time}-{end_time}: {str(e)}")
                    # Fallback: use chunk start time
                    entry["absolute_start_time"] = start_time
                    entry["absolute_end_time"] = start_time
                    entry["absolute_start_timestamp"] = format_timestamp(start_time)
                    entry["absolute_end_timestamp"] = format_timestamp(start_time)
                    entry["time"] = "00:00"
                    entry["absolute_time"] = start_time
                    entry["absolute_timestamp"] = format_timestamp(start_time)
            # Handle legacy format with just "time"
            elif "time" in entry:
                try:
                    chunk_time = parse_timestamp(entry["time"])
                    absolute_time = start_time + chunk_time
                    entry["absolute_time"] = absolute_time
                    entry["absolute_timestamp"] = format_timestamp(absolute_time)
                    # Add start_time and end_time for consistency
                    entry["start_time"] = entry["time"]
                    entry["end_time"] = entry["time"]
                    entry["absolute_start_time"] = absolute_time
                    entry["absolute_end_time"] = absolute_time
                    entry["absolute_start_timestamp"] = format_timestamp(absolute_time)
                    entry["absolute_end_timestamp"] = format_timestamp(absolute_time)
                    # Add type field for new format compatibility
                    if "type" not in entry:
                        entry["type"] = "utterance"
                except Exception as e:
                    print(f"Warning: Failed to parse timestamp '{entry['time']}' for entry {i} in chunk {start_time}-{end_time}: {str(e)}")
                    # Fallback: use chunk start time
                    entry["absolute_time"] = start_time
                    entry["absolute_timestamp"] = format_timestamp(start_time)
                    entry["start_time"] = "00:00"
                    entry["end_time"] = "00:00"
                    entry["absolute_start_time"] = start_time
                    entry["absolute_end_time"] = start_time
                    entry["absolute_start_timestamp"] = format_timestamp(start_time)
                    entry["absolute_end_timestamp"] = format_timestamp(start_time)
            else:
                print(f"Warning: Entry {i} in chunk {start_time}-{end_time} missing timestamp fields")
                # Add default timestamps for entries without time fields
                entry["time"] = "00:00"
                entry["start_time"] = "00:00"
                entry["end_time"] = "00:00"
                entry["absolute_time"] = start_time
                entry["absolute_timestamp"] = format_timestamp(start_time)
                entry["absolute_start_time"] = start_time
                entry["absolute_end_time"] = start_time
                entry["absolute_start_timestamp"] = format_timestamp(start_time)
                entry["absolute_end_timestamp"] = format_timestamp(start_time)
                # Add type field for new format compatibility
                if "type" not in entry:
                    entry["type"] = "utterance"
        
        return entry
    
    def _get_current_timestamp(self) -> str:
        """Get current timestamp in ISO format."""
        import datetime
        return datetime.datetime.now().isoformat()
