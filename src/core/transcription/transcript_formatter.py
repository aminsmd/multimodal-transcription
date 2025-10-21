#!/usr/bin/env python3
"""
Transcript formatting functionality for the transcription pipeline.

This module handles formatting transcripts into different output formats.
"""

import json
from pathlib import Path
from typing import Dict, List

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from models import CleanTranscript, CleanTranscriptEntry
from utils import format_timestamp


class TranscriptFormatter:
    """
    Handles formatting transcripts into different output formats.
    """
    
    def __init__(self, run_dir: Path):
        """
        Initialize the transcript formatter.
        
        Args:
            run_dir: Directory for storing formatted transcripts
        """
        self.run_dir = run_dir
        self.transcripts_dir = run_dir / "transcripts"
        self.transcripts_dir.mkdir(exist_ok=True)
    
    def create_full_transcript_text(self, full_transcript: Dict, video_id: str):
        """
        Create a human-readable text version of the full transcript.
        
        Args:
            full_transcript: Full transcript dictionary
            video_id: Unique identifier for the video
        """
        output_lines = []
        
        # Header
        output_lines.append("=" * 80)
        output_lines.append("FULL VIDEO TRANSCRIPT")
        output_lines.append("=" * 80)
        output_lines.append(f"Video ID: {video_id}")
        output_lines.append(f"Generated: {full_transcript['metadata']['generation_date']}")
        output_lines.append(f"Total Entries: {full_transcript['metadata']['total_entries']}")
        output_lines.append(f"Total Duration: {full_transcript['metadata']['total_duration_seconds']:.1f} seconds")
        output_lines.append("")
        
        # Transcript entries
        for i, entry in enumerate(full_transcript['transcript'], 1):
            # Get start and end timestamps - use exact strings from JSON without parsing
            start_timestamp = entry.get('start_time', entry.get('absolute_start_timestamp', entry.get('time', '00:00')))
            end_timestamp = entry.get('end_time', entry.get('absolute_end_timestamp', entry.get('time', '00:00')))
            
            # Use the exact timestamp strings as they appear in the JSON
            # Format time range
            if start_timestamp == end_timestamp:
                time_display = f"[{start_timestamp}]"
            else:
                time_display = f"[{start_timestamp} - {end_timestamp}]"
            
            speaker = entry.get('speaker', '')
            spoken_text = entry.get('spoken_text', '')
            visual_desc = entry.get('visual_description', '')
            
            # Check if this is primarily a visual event (no spoken text or empty spoken text)
            is_visual_event = (not spoken_text or spoken_text.strip() == '') and visual_desc and visual_desc.strip()
            
            # Format based on content type
            if is_visual_event:
                # Visual event: [time] (Visual: description)
                output_lines.append(f"{time_display} (Visual: {visual_desc})")
            elif speaker and spoken_text:
                # Spoken content with speaker
                if visual_desc and visual_desc.strip():
                    output_lines.append(f"{time_display} {speaker}: {spoken_text} (Visual: {visual_desc})")
                else:
                    output_lines.append(f"{time_display} {speaker}: {spoken_text}")
            elif spoken_text:
                # Spoken content without clear speaker
                if visual_desc and visual_desc.strip():
                    output_lines.append(f"{time_display} {spoken_text} (Visual: {visual_desc})")
                else:
                    output_lines.append(f"{time_display} {spoken_text}")
            else:
                # No content
                if visual_desc and visual_desc.strip():
                    output_lines.append(f"{time_display} (Visual: {visual_desc})")
                else:
                    output_lines.append(f"{time_display} [No audio/visual content]")
            output_lines.append("")
        
        # Footer
        output_lines.append("=" * 80)
        output_lines.append("END OF FULL TRANSCRIPT")
        output_lines.append("=" * 80)
        
        # Save text file
        text_path = self.transcripts_dir / f'{video_id}_full_transcript.txt'
        with open(text_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(output_lines))
        
        print(f"Full transcript text saved to {text_path}")
    
    def create_clean_transcript(self, full_transcript: Dict, video_id: str) -> Dict:
        """
        Create a clean, minimal JSON version of the transcript with only essential fields.
        
        Args:
            full_transcript: Full transcript dictionary
            video_id: Unique identifier for the video
            
        Returns:
            Clean transcript dictionary
        """
        print(f"\n=== Creating Clean Transcript ===")
        
        # Create clean entries with only essential fields
        clean_entries = []
        
        for entry in full_transcript.get('transcript', []):
            # Extract just the MM:SS part from the timestamp for cleaner display
            timestamp = entry.get('time', '00:00:00.000')
            if len(timestamp) > 10:  # If it's in HH:MM:SS.fff format
                clean_timestamp = timestamp[3:8]  # Get MM:SS part
            elif len(timestamp) >= 5 and ':' in timestamp:  # If it's in MM:SS.fff format
                clean_timestamp = timestamp[:5]  # Get MM:SS part (first 5 chars: MM:SS)
            else:
                clean_timestamp = timestamp
            
            # Extract end timestamp as well
            end_timestamp = entry.get('absolute_end_timestamp', '')
            if not end_timestamp:
                # Fallback: if no absolute_end_timestamp, try to calculate from start_time + duration
                # or use the start_time as a last resort
                end_timestamp = entry.get('time', '00:00:00.000')
            
            if len(end_timestamp) > 10:  # If it's in HH:MM:SS.fff format
                clean_end_timestamp = end_timestamp[3:8]  # Get MM:SS part
            elif len(end_timestamp) >= 5 and ':' in end_timestamp:  # If it's in MM:SS.fff format
                clean_end_timestamp = end_timestamp[:5]  # Get MM:SS part (first 5 chars: MM:SS)
            else:
                clean_end_timestamp = end_timestamp
            
            # Get entry type
            entry_type = entry.get('type', 'utterance')
            
            # Create clean entry with type-specific fields
            clean_entry = {
                "type": entry_type,
                "start_time": clean_timestamp,
                "end_time": clean_end_timestamp
            }
            
            # Handle different entry types
            if entry_type == "utterance":
                # For utterances, include speaker and text
                clean_entry["speaker"] = entry.get('speaker', '')
                clean_entry["text"] = entry.get('spoken_text', '')
                
                # Add visual description if present
                visual_desc = entry.get('visual_description', '')
                if visual_desc and visual_desc.strip():
                    clean_entry["visual"] = visual_desc
                    
            elif entry_type == "event":
                # For events, include event description as text
                clean_entry["text"] = entry.get('event_description', '')
                
                # Events typically don't have speakers, but include if present
                speaker = entry.get('speaker', '')
                if speaker and speaker.strip():
                    clean_entry["speaker"] = speaker
                    
                # Add visual description if present (events might have both)
                visual_desc = entry.get('visual_description', '')
                if visual_desc and visual_desc.strip():
                    clean_entry["visual"] = visual_desc
            
            # Remove empty fields to keep the output clean
            if clean_entry.get("speaker") == "":
                del clean_entry["speaker"]
            if clean_entry.get("text") == "":
                del clean_entry["text"]
            if clean_entry.get("visual") == "" or clean_entry.get("visual") is None:
                if "visual" in clean_entry:
                    del clean_entry["visual"]
            
            clean_entries.append(clean_entry)
        
        # Create clean transcript structure
        clean_transcript = {
            "video_id": video_id,
            "duration_seconds": full_transcript.get('metadata', {}).get('total_duration_seconds', 0),
            "total_entries": len(clean_entries),
            "generated": full_transcript.get('metadata', {}).get('generation_date', ''),
            "pipeline_configuration": full_transcript.get('metadata', {}).get('pipeline_configuration', {}),
            "run_id": full_transcript.get('metadata', {}).get('run_id', ''),
            "transcript": clean_entries
        }
        
        # Save clean transcript
        clean_transcript_path = self.transcripts_dir / f'{video_id}_clean_transcript.json'
        with open(clean_transcript_path, 'w') as f:
            json.dump(clean_transcript, f, indent=2)
        
        print(f"Clean transcript saved to {clean_transcript_path}")
        return clean_transcript
