#!/usr/bin/env python3
"""
Advanced usage example for the standalone transcription pipeline.

This script demonstrates advanced features like batch processing,
custom output handling, and error recovery.
"""

import os
import sys
import json
from pathlib import Path
from typing import List, Dict

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from transcription_pipeline import TranscriptionPipeline

class BatchTranscriptionProcessor:
    """Advanced batch processing for multiple videos."""
    
    def __init__(self, output_dir: str = "batch_outputs"):
        self.output_dir = output_dir
        self.pipeline = None
        self.results = []
    
    def process_video_list(self, video_list: List[Dict]) -> List[Dict]:
        """
        Process a list of videos with different configurations.
        
        Args:
            video_list: List of dictionaries with video info:
                {
                    "path": "path/to/video.mp4",
                    "is_youtube": False,
                    "chunk_duration": 300,
                    "max_workers": 4
                }
        """
        results = []
        
        for i, video_info in enumerate(video_list):
            print(f"\n=== Processing Video {i+1}/{len(video_list)} ===")
            print(f"Video: {video_info['path']}")
            
            try:
                # Initialize pipeline for each video
                self.pipeline = TranscriptionPipeline(self.output_dir)
                
                # Process video
                result = self.pipeline.process_video(
                    video_input=video_info['path'],
                    chunk_duration=video_info.get('chunk_duration', 300),
                    max_workers=video_info.get('max_workers', 4),
                    is_youtube=video_info.get('is_youtube', False)
                )
                
                # Add metadata
                result['batch_index'] = i
                result['batch_total'] = len(video_list)
                result['success'] = True
                
                results.append(result)
                print(f"✓ Successfully processed: {result['video_id']}")
                
            except Exception as e:
                print(f"✗ Failed to process video: {str(e)}")
                error_result = {
                    'video_path': video_info['path'],
                    'error': str(e),
                    'batch_index': i,
                    'batch_total': len(video_list),
                    'success': False
                }
                results.append(error_result)
        
        self.results = results
        return results
    
    def save_batch_summary(self, output_path: str = None):
        """Save a summary of batch processing results."""
        if not output_path:
            output_path = Path(self.output_dir) / "batch_summary.json"
        
        summary = {
            "total_videos": len(self.results),
            "successful": len([r for r in self.results if r.get('success', False)]),
            "failed": len([r for r in self.results if not r.get('success', False)]),
            "results": self.results
        }
        
        with open(output_path, 'w') as f:
            json.dump(summary, f, indent=2)
        
        print(f"Batch summary saved to: {output_path}")
        return summary

def process_with_custom_output_handling():
    """Example of custom output handling and post-processing."""
    
    print("=== Custom Output Handling Example ===")
    
    try:
        # Initialize pipeline
        pipeline = TranscriptionPipeline("custom_outputs")
        
        # Process video
        results = pipeline.process_video(
            video_input="path/to/your/video.mp4",
            chunk_duration=300,
            max_workers=4,
            is_youtube=False
        )
        
        # Custom post-processing
        full_transcript = results['full_transcript']
        
        # Extract only teacher speech
        teacher_speech = [
            entry for entry in full_transcript['transcript']
            if entry.get('speaker') == 'teacher'
        ]
        
        # Save teacher-only transcript
        teacher_output_path = pipeline.run_dir / "teacher_only_transcript.json"
        with open(teacher_output_path, 'w') as f:
            json.dump({
                "video_id": results['video_id'],
                "speaker": "teacher",
                "total_entries": len(teacher_speech),
                "transcript": teacher_speech
            }, f, indent=2)
        
        print(f"Teacher-only transcript saved to: {teacher_output_path}")
        
        # Extract visual events
        visual_events = [
            entry for entry in full_transcript['transcript']
            if entry.get('type') == 'event' or entry.get('visual_description')
        ]
        
        # Save visual events
        visual_output_path = pipeline.run_dir / "visual_events.json"
        with open(visual_output_path, 'w') as f:
            json.dump({
                "video_id": results['video_id'],
                "total_events": len(visual_events),
                "events": visual_events
            }, f, indent=2)
        
        print(f"Visual events saved to: {visual_output_path}")
        
    except Exception as e:
        print(f"Error in custom output handling: {str(e)}")

def process_with_error_recovery():
    """Example of error recovery and retry logic."""
    
    print("=== Error Recovery Example ===")
    
    video_path = "path/to/your/video.mp4"
    max_retries = 3
    
    for attempt in range(max_retries):
        try:
            print(f"Attempt {attempt + 1}/{max_retries}")
            
            # Initialize pipeline
            pipeline = TranscriptionPipeline("retry_outputs")
            
            # Process video
            results = pipeline.process_video(
                video_input=video_path,
                chunk_duration=300,
                max_workers=4,
                is_youtube=False
            )
            
            print(f"✓ Success on attempt {attempt + 1}")
            return results
            
        except Exception as e:
            print(f"✗ Attempt {attempt + 1} failed: {str(e)}")
            if attempt == max_retries - 1:
                print("All retry attempts failed")
                raise e
            else:
                print("Retrying...")
                continue

def main():
    """Run advanced usage examples."""
    
    # Check if GOOGLE_API_KEY is set
    if not os.getenv('GOOGLE_API_KEY'):
        print("Error: GOOGLE_API_KEY environment variable is not set.")
        print("Please set your Google API key:")
        print("export GOOGLE_API_KEY='your_api_key_here'")
        return 1
    
    # Example 1: Batch processing
    print("=== Batch Processing Example ===")
    try:
        batch_processor = BatchTranscriptionProcessor("batch_outputs")
        
        # Define video list (update with your video paths)
        video_list = [
            {
                "path": "path/to/video1.mp4",
                "is_youtube": False,
                "chunk_duration": 300,
                "max_workers": 4
            },
            {
                "path": "https://www.youtube.com/watch?v=VIDEO_ID",
                "is_youtube": True,
                "chunk_duration": 600,
                "max_workers": 6
            }
        ]
        
        # Process batch
        results = batch_processor.process_video_list(video_list)
        
        # Save summary
        summary = batch_processor.save_batch_summary()
        print(f"Batch processing completed: {summary['successful']}/{summary['total_videos']} successful")
        
    except Exception as e:
        print(f"Error in batch processing: {str(e)}")
    
    # Example 2: Custom output handling
    print("\n=== Custom Output Handling ===")
    try:
        process_with_custom_output_handling()
    except Exception as e:
        print(f"Error in custom output handling: {str(e)}")
    
    # Example 3: Error recovery
    print("\n=== Error Recovery ===")
    try:
        process_with_error_recovery()
    except Exception as e:
        print(f"Error in error recovery: {str(e)}")
    
    print("\n=== Advanced examples completed! ===")
    return 0

if __name__ == "__main__":
    exit(main())
