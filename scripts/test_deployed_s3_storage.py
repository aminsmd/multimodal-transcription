#!/usr/bin/env python3
"""
Test script for deployed code with S3 video and S3 storage.
This script processes a single video from S3 and writes all outputs to S3.
"""

import os
import sys
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from transcription_pipeline import TranscriptionPipeline
from models import TranscriptionConfig

def main():
    """Test deployed transcription with S3 video and S3 storage."""
    
    # Check if GOOGLE_API_KEY is set
    if not os.getenv('GOOGLE_API_KEY'):
        print("❌ Error: GOOGLE_API_KEY environment variable is not set.")
        print("Please set your Google API key:")
        print("export GOOGLE_API_KEY='your_api_key_here'")
        return 1
    
    # S3 configuration
    s3_bucket = "multimodal-transcription-videos-1761690600"
    s3_video_url = f"s3://{s3_bucket}/test-videos/Adam_2024-03-03_6_32_PM.mp4"
    s3_output_prefix = "deployed-test-outputs"
    
    print(f"🎥 Testing deployed code with S3 video: {s3_video_url}")
    print(f"📁 Writing all outputs to S3: s3://{s3_bucket}/{s3_output_prefix}/")
    print("=" * 70)
    
    try:
        # Initialize pipeline with S3 output directory
        pipeline = TranscriptionPipeline(f"s3://{s3_bucket}/{s3_output_prefix}")
        
        # Create configuration for testing deployed code with S3 storage
        config = TranscriptionConfig(
            video_input=s3_video_url,
            chunk_duration=120,  # 2-minute chunks for faster testing
            max_workers=2,       # Fewer workers for testing
            cleanup_uploaded_files=True,
            force_reprocess=False
        )
        
        print("🚀 Starting deployed transcription with S3 storage...")
        results = pipeline.process_video(config)
        
        print("\n✅ Deployed processing completed!")
        print(f"📹 Video ID: {results.video_id}")
        print(f"📝 Total transcript entries: {len(results.full_transcript.transcript)}")
        print(f"📁 S3 Output directory: s3://{s3_bucket}/{s3_output_prefix}/")
        print(f"💾 Cached: {results.cached}")
        
        # Show first few transcript entries
        if results.full_transcript.transcript:
            print(f"\n📄 First transcript entry:")
            first_entry = results.full_transcript.transcript[0]
            print(f"   Time: {first_entry.get('start_time', 'N/A')}s")
            print(f"   Text: {first_entry.get('text', 'N/A')[:100]}...")
        
        # List S3 output files
        print(f"\n📋 S3 Output files:")
        import boto3
        s3_client = boto3.client('s3')
        try:
            response = s3_client.list_objects_v2(
                Bucket=s3_bucket,
                Prefix=f"{s3_output_prefix}/"
            )
            if 'Contents' in response:
                for obj in response['Contents']:
                    print(f"   📄 {obj['Key']} ({obj['Size']} bytes)")
            else:
                print("   No files found in S3 output directory")
        except Exception as e:
            print(f"   Error listing S3 files: {e}")
        
        return 0
        
    except Exception as e:
        print(f"❌ Error processing S3 video: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit(main())
