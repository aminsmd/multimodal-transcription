#!/usr/bin/env python3
"""
Example script for batch processing videos from API.

This script demonstrates how to use the BatchTranscriptionProcessor
to fetch videos from the API, download them from S3, transcribe them,
and send notifications.
"""

import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from batch_transcription_processor import BatchTranscriptionProcessor


def main():
    """Example usage of batch transcription processor."""
    
    # Check for required environment variables
    if not os.getenv('GOOGLE_API_KEY'):
        print("❌ Error: GOOGLE_API_KEY environment variable is not set")
        return 1
    
    # S3_BUCKET_PATH should be set as an environment variable
    # It can be:
    # - A console URL: https://us-east-1.console.aws.amazon.com/s3/buckets/bci-prod-upload?region=us-east-1
    # - An S3 URI: s3://bci-prod-upload
    # - Just the bucket name: bci-prod-upload
    
    # Initialize processor
    processor = BatchTranscriptionProcessor(
        s3_bucket_path=None,  # Will read from S3_BUCKET_PATH env var
        output_dir="outputs",
        data_dir="data",
        chunk_duration=300,  # 5-minute chunks
        max_workers=4,
        enable_file_management=True,
        enable_validation=True
    )
    
    # Process all videos
    summary = processor.process_all_videos()
    
    # Print summary
    print("\n" + "=" * 70)
    print("BATCH PROCESSING SUMMARY")
    print("=" * 70)
    print(f"Total videos: {summary['total_videos']}")
    print(f"Succeeded: {summary['succeeded']}")
    print(f"Failed: {summary['failed']}")
    print(f"Output directory: {summary['output_directory']}")
    
    return 0 if summary['failed'] == 0 else 1


if __name__ == "__main__":
    exit(main())

