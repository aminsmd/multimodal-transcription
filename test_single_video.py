#!/usr/bin/env python3
"""
Quick test script for processing a single video.
This is the fastest way to test the transcription pipeline.
"""

import os
import sys
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from transcription_pipeline import TranscriptionPipeline
from models import TranscriptionConfig

def main():
    """Test transcription on a single video."""
    
    # Check if GOOGLE_API_KEY is set
    if not os.getenv('GOOGLE_API_KEY'):
        print("❌ Error: GOOGLE_API_KEY environment variable is not set.")
        print("Please set your Google API key:")
        print("export GOOGLE_API_KEY='your_api_key_here'")
        return 1
    
    # Available videos
    available_videos = [
        "data/videos/Adam_2024-03-03_6_32_PM.mp4",
        "data/videos/Angela_2025-03-10_2_11_PM.mp4",
        "data/videos/Audrey_2025-04-06_6_20_PM-2.mp4",
        "data/videos/Briann_2025-02-04_2_52_PM_new.mp4",
        "data/videos/Jennifer_2025-05-01_9_48_PM-2.mp4",
        "data/videos/Maddelyn_2025-04-10_7_04_PM-2.mp4"
    ]
    
    # Find the first available video
    video_path = None
    for video in available_videos:
        if os.path.exists(video):
            video_path = video
            break
    
    if not video_path:
        print("❌ No video files found in data/videos/")
        return 1
    
    print(f"🎥 Testing with video: {video_path}")
    print("=" * 50)
    
    try:
        # Initialize pipeline
        pipeline = TranscriptionPipeline("test_outputs")
        
        # Create configuration for quick testing
        config = TranscriptionConfig(
            video_input=video_path,
            chunk_duration=60,  # 1-minute chunks for faster testing
            max_workers=2,      # Fewer workers for testing
            cleanup_uploaded_files=True,
            force_reprocess=False
        )
        
        print("🚀 Starting transcription...")
        results = pipeline.process_video(config)
        
        print("\n✅ Processing completed!")
        print(f"📹 Video ID: {results.video_id}")
        print(f"📝 Total transcript entries: {len(results.full_transcript.transcript)}")
        print(f"📁 Output directory: {pipeline.run_dir}")
        print(f"💾 Cached: {results.cached}")
        
        # Show first few transcript entries
        if results.full_transcript.transcript:
            print(f"\n📄 First transcript entry:")
            first_entry = results.full_transcript.transcript[0]
            print(f"   Time: {first_entry.get('start_time', 'N/A')}s")
            print(f"   Text: {first_entry.get('text', 'N/A')[:100]}...")
        
        return 0
        
    except Exception as e:
        print(f"❌ Error processing video: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit(main())
