#!/usr/bin/env python3
"""
Basic usage example for the standalone transcription pipeline.

This script demonstrates how to use the TranscriptionPipeline class
to process videos and generate transcripts.
"""

import os
import sys
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from transcription_pipeline import TranscriptionPipeline
from models import TranscriptionConfig

def main():
    """Example usage of the transcription pipeline."""
    
    # Check if GOOGLE_API_KEY is set
    if not os.getenv('GOOGLE_API_KEY'):
        print("Error: GOOGLE_API_KEY environment variable is not set.")
        print("Please set your Google API key:")
        print("export GOOGLE_API_KEY='your_api_key_here'")
        return 1
    
    # Example 1: Process a local video file
    print("=== Example 1: Processing Local Video ===")
    try:
        # Initialize pipeline
        pipeline = TranscriptionPipeline("example_outputs")
        
        # Process a video (replace with your video path)
        video_path = "path/to/your/video.mp4"
        
        if os.path.exists(video_path):
            # Create configuration
            config = TranscriptionConfig(
                video_input=video_path,
                chunk_duration=300,  # 5-minute chunks
                max_workers=4,
                cleanup_uploaded_files=True,  # Clean up uploaded files from Google (default: True)
                force_reprocess=False  # Use cache if available (default: False)
            )
            
            results = pipeline.process_video(config)
            
            print(f"Processing completed!")
            print(f"Video ID: {results.video_id}")
            print(f"Total transcript entries: {len(results.full_transcript.transcript)}")
            print(f"Output directory: {pipeline.run_dir}")
            print(f"Cached: {results.cached}")
        else:
            print(f"Video file not found: {video_path}")
            print("Please update the video_path variable with a valid video file.")
    
    except Exception as e:
        print(f"Error processing local video: {str(e)}")
    
    # Example 2: Process with different chunk size
    print("\n=== Example 2: Different Chunk Size ===")
    try:
        # Initialize pipeline
        pipeline = TranscriptionPipeline("example_outputs")
        
        # Process with larger chunks for longer videos
        results = pipeline.process_video(
            video_input="path/to/your/video.mp4",
            chunk_duration=600,  # 10-minute chunks
            max_workers=4
        )
        
        print(f"Large chunk processing completed!")
        print(f"Video ID: {results['video_id']}")
        print(f"Total transcript entries: {len(results['full_transcript']['transcript'])}")
        print(f"Output directory: {pipeline.run_dir}")
    
    except Exception as e:
        print(f"Error processing with large chunks: {str(e)}")
    
    # Example 3: Custom configuration
    print("\n=== Example 3: Custom Configuration ===")
    try:
        # Initialize pipeline with custom output directory
        pipeline = TranscriptionPipeline("custom_outputs")
        
        # Process with custom settings
        results = pipeline.process_video(
            video_input="path/to/your/video.mp4",
            chunk_duration=600,  # 10-minute chunks for longer videos
            max_workers=8,      # More workers for faster processing
            is_youtube=False
        )
        
        print(f"Custom processing completed!")
        print(f"Chunk duration: {results['chunk_duration']} seconds")
        print(f"Max workers: {results['max_workers']}")
        print(f"Output directory: {pipeline.run_dir}")
    
    except Exception as e:
        print(f"Error with custom configuration: {str(e)}")
    
    print("\n=== Examples completed! ===")
    print("Check the output directories for generated transcripts.")
    
    return 0

if __name__ == "__main__":
    exit(main())
