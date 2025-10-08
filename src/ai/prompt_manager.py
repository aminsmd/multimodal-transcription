#!/usr/bin/env python3
"""
Prompt management for the transcription pipeline.

This module handles prompt generation and management for different transcription scenarios.
"""

from pathlib import Path
from typing import Optional


class PromptManager:
    """
    Manages prompts for the transcription pipeline.
    """
    
    def __init__(self, prompt_file_path: Optional[str] = None):
        """
        Initialize the prompt manager.
        
        Args:
            prompt_file_path: Path to the prompt file (optional)
        """
        if prompt_file_path:
            self.prompt_file_path = Path(prompt_file_path)
        else:
            # Default to prompt.txt in the src directory
            self.prompt_file_path = Path(__file__).parent.parent / "prompt.txt"
        
        self._base_prompt = None
    
    def get_transcript_prompt(self, video_duration: float = 0, chunk_start: int = 0, chunk_end: int = 0) -> str:
        """
        Get transcript generation prompt for a specific chunk.
        
        Args:
            video_duration: Total video duration
            chunk_start: Start time of the chunk
            chunk_end: End time of the chunk
            
        Returns:
            Formatted prompt string
        """
        # Calculate chunk duration
        chunk_duration = chunk_end - chunk_start
        chunk_duration_minutes = int(chunk_duration // 60)
        chunk_duration_seconds = int(chunk_duration % 60)
        chunk_duration_str = f"{chunk_duration_minutes:02d}:{chunk_duration_seconds:02d}"
        
        # Calculate chunk start time in MM:SS format
        chunk_start_minutes = int(chunk_start // 60)
        chunk_start_seconds = int(chunk_start % 60)
        chunk_start_str = f"{chunk_start_minutes:02d}:{chunk_start_seconds:02d}"
        
        # Calculate chunk end time in MM:SS format
        chunk_end_minutes = int(chunk_end // 60)
        chunk_end_seconds = int(chunk_end % 60)
        chunk_end_str = f"{chunk_end_minutes:02d}:{chunk_end_seconds:02d}"
        
        # Load the base prompt
        base_prompt = self._load_base_prompt()
        
        # Replace the duration placeholder with the actual chunk duration
        base_prompt = base_prompt.replace("{duration_str}", chunk_duration_str)
        
        # Add segment-specific information
        base_prompt += f"\n\nSEGMENT INFORMATION:\n- This is a {chunk_duration_str} segment from a longer video (segment {chunk_start_str} to {chunk_end_str})\n- Your transcription MUST cover the ENTIRE duration of this segment from 00:00 to {chunk_duration_str}\n- Include entries for ALL time periods, even when nothing is being said or audio is not recognizable"
        
        return base_prompt
    
    def _load_base_prompt(self) -> str:
        """
        Load the base prompt from file.
        
        Returns:
            Base prompt string
        """
        if self._base_prompt is None:
            try:
                with open(self.prompt_file_path, 'r', encoding='utf-8') as f:
                    self._base_prompt = f.read()
            except FileNotFoundError:
                # Fallback to hardcoded prompt if file not found
                self._base_prompt = self._get_default_prompt()
        
        return self._base_prompt
    
    def _get_default_prompt(self) -> str:
        """
        Get the default prompt if no file is found.
        
        Returns:
            Default prompt string
        """
        return """Role
You are an advanced transcription system tasked with analyzing classroom recordings to produce accurate and detailed transcripts. Your goal is to capture all spoken dialogue and key contextual events while maintaining strict formatting and complete time coverage.

Task Breakdown
1. Transcription of Spoken Text
   * Transcribe every spoken word verbatim, including filler words and grammatical errors.
   * Use placeholders for unclear or missing audio:
      * [Unintelligible] → Sound is present, but words are unclear.
      * [Inaudible] → Sound is completely missing or inaudible.
   * For non-English speech:
      * Transcribe phonetically.
      * Include English translation in parentheses.
Example: "Necesitas ayuda? (Do you need help?)"
   2. Speaker Identification
   * Use diarization techniques (tone, pitch, volume, visual cues).
   * Teacher: Use "teacher".
   * Students: Use "student_A", "student_B", etc., incrementing letters as new speakers appear.
   * Unclear identity: Use "speaker".
   * Group speech: Use "multiple_students".
   3. Event Annotation
   * Add "event" entries only for notable changes, such as but not limited to:
   * Instructional content change:
e.g., "Teacher shows a slide of 9 hearts on the screen".
   * Participant & Activity Structure Changes:
e.g., "Teacher transitions from lecture to facilitating small group work".
   * Interactions with Learning Materials:
e.g., "Students are given calculators".
      * What to AVOID in Context:
      * Irrelevant physical descriptions: Do NOT describe clothing, hairstyles, or general room appearance.
      4. Complete Time Coverage
      * The entire video must be covered from 00:00 to {duration_str}.
      * No gaps allowed—all time periods must be accounted for.
      * Each entry must have both "start_time" and "end_time" fields.

Output Format
The transcript must be returned as valid JSON with no additional text before or after.
{
    "transcript": [
        {
            "type": "utterance",
            "start_time": "MM:SS",
            "end_time": "MM:SS",
            "speaker": "Speaker identification",
            "spoken_text": "Exact transcription of what is said"
        },
        {
            "type": "event",
            "start_time": "MM:SS",
            "end_time": "MM:SS",
            "event_description": "Description of a specific, non-verbal change in activity, pedagogy, or materials"
        }
    ]
}

IMPORTANT: All timestamps must be in MM:SS format (e.g., "05:30", "12:45"). Do NOT use HH:MM:SS format. Seconds must be between 00-59. If you need to represent times over 60 minutes, use MM:SS format where MM can be 60 or higher.

Requirements
      * Every entry must include start_time and end_time.
      * No unaccounted time gaps:
      * All speech must be covered by either words, [Unintelligible], or [Inaudible].
      * Maintain consistent speaker identifiers throughout the entire video.
      * Only include "event" entries when a new, meaningful change occurs.
      * JSON must be properly formatted and valid.
      * Final response must not include any explanation or extra text, just the JSON object."""
    
    def set_prompt_file(self, prompt_file_path: str):
        """
        Set a new prompt file path.
        
        Args:
            prompt_file_path: Path to the new prompt file
        """
        self.prompt_file_path = Path(prompt_file_path)
        self._base_prompt = None  # Reset to force reload
    
    def get_prompt_info(self) -> dict:
        """
        Get information about the current prompt configuration.
        
        Returns:
            Dictionary containing prompt information
        """
        return {
            "prompt_file_path": str(self.prompt_file_path),
            "prompt_file_exists": self.prompt_file_path.exists(),
            "prompt_loaded": self._base_prompt is not None
        }
