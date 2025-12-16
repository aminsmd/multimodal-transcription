#!/usr/bin/env python3
"""
Test script for deployed code with S3 video.
This script processes a single video from S3 using the deployed pipeline.
"""

import os
import sys
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from transcription_pipeline import TranscriptionPipeline
from models import TranscriptionConfig

def main():
    """Test deployed transcription on a single S3 video."""
    
    # Check if GOOGLE_API_KEY is set
    if not os.getenv('GOOGLE_API_KEY'):
        print("❌ Error: GOOGLE_API_KEY environment variable is not set.")
        print("Please set your Google API key:")
        print("export GOOGLE_API_KEY='your_api_key_here'")
        return 1
    
    # S3 video URL
    s3_video_url = "s3://multimodal-transcription-videos-1761690600/test-videos/Adam_2024-03-03_6_32_PM.mp4"
    
    print(f"🎥 Testing deployed code with S3 video: {s3_video_url}")
    print("=" * 60)
    
    try:
        # Initialize pipeline
        pipeline = TranscriptionPipeline("deployed_test_outputs")
        
        # Create configuration for testing deployed code
        config = TranscriptionConfig(
            video_input=s3_video_url,
            chunk_duration=120,  # 2-minute chunks for faster testing
            max_workers=2,       # Fewer workers for testing
            cleanup_uploaded_files=True,
            force_reprocess=False
        )
        
        print("🚀 Starting deployed transcription...")
        results = pipeline.process_video(config)
        
        print("\n✅ Deployed processing completed!")
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
        print(f"❌ Error processing S3 video: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit(main())
