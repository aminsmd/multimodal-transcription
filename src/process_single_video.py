#!/usr/bin/env python3
"""
Process a single video: download from S3, transcribe, upload to S3, and send notification.

This script is designed to be run in an ECS task for processing individual videos.
It expects environment variables:
- VIDEO_ID: The video ID
- VIDEO_PATH: The S3 path to the video (relative to source bucket)
- S3_SOURCE_BUCKET: Source bucket for reading videos
- S3_DEST_BUCKET: Destination bucket for writing outputs
- S3_OUTPUT_PREFIX: Prefix for output files in destination bucket
"""

import os
import sys
from pathlib import Path
from typing import Optional
import logging

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from api.notification_client import NotificationClient, TranscriptionStatus
from utils.s3_utils import construct_s3_url, download_video_from_s3
from core.pipeline import TranscriptionPipeline
from models import TranscriptionConfig

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Main function to process a single video."""
    # Get required environment variables
    video_id = os.getenv('VIDEO_ID')
    video_path = os.getenv('VIDEO_PATH')
    s3_source_bucket = os.getenv('S3_SOURCE_BUCKET')
    s3_dest_bucket = os.getenv('S3_DEST_BUCKET')
    s3_output_prefix = os.getenv('S3_OUTPUT_PREFIX', 'outputs')
    
    # Validate required variables
    if not video_id:
        logger.error("VIDEO_ID environment variable is required")
        print("❌ ERROR: VIDEO_ID environment variable is required")
        return 1
    
    if not video_path:
        logger.error("VIDEO_PATH environment variable is required")
        print("❌ ERROR: VIDEO_PATH environment variable is required")
        return 1
    
    if not s3_source_bucket:
        logger.error("S3_SOURCE_BUCKET environment variable is required")
        print("❌ ERROR: S3_SOURCE_BUCKET environment variable is required")
        return 1
    
    if not s3_dest_bucket:
        logger.error("S3_DEST_BUCKET environment variable is required")
        print("❌ ERROR: S3_DEST_BUCKET environment variable is required")
        return 1
    
    print("=" * 70)
    print(f"PROCESSING VIDEO: {video_id}")
    print("=" * 70)
    print(f"Video Path: {video_path}")
    print(f"Source Bucket: {s3_source_bucket}")
    print(f"Destination Bucket: {s3_dest_bucket}")
    print(f"Output Prefix: {s3_output_prefix}")
    
    # Initialize notification client
    notification_client = NotificationClient()
    
    # Initialize pipeline (disable repository and MongoDB)
    output_dir = "/tmp/outputs"
    pipeline = TranscriptionPipeline(
        base_dir=output_dir,
        data_dir="/tmp/data",
        enable_file_management=False,
        enable_video_repository=False,
        enable_validation=True,
        enable_mongodb=False
    )
    
    try:
        # Construct S3 URL
        s3_url = construct_s3_url(s3_source_bucket, video_path)
        logger.info(f"S3 URL: {s3_url}")
        print(f"\n⬇️  Downloading from S3: {s3_url}")
        
        # Download video from S3
        aws_region = os.getenv('AWS_DEFAULT_REGION', 'us-east-1')
        local_video_path, download_success = download_video_from_s3(
            s3_url,
            local_path=f"/tmp/video_{video_id}.mp4",
            region_name=aws_region
        )
        
        if not download_success:
            error_msg = f"Failed to download video from S3: {s3_url}"
            logger.error(error_msg)
            print(f"❌ {error_msg}")
            
            # Send error notification
            notification_result = notification_client.notify_error(
                video_id,
                error_msg,
                output_directory=str(pipeline.run_dir)
            )
            print(f"📤 Error notification sent: {'✅' if notification_result['success'] else '❌'}")
            return 1
        
        # Get file size
        try:
            import os as os_module
            file_size = os_module.path.getsize(local_video_path)
            file_size_mb = file_size / (1024 * 1024)
            print(f"✅ Downloaded: {file_size_mb:.2f} MB")
        except Exception:
            print(f"✅ Downloaded successfully")
        
        # Process video through transcription pipeline
        print(f"\n🎬 Starting transcription...")
        logger.info(f"Starting transcription for {video_id}...")
        
        config = TranscriptionConfig(
            video_input=local_video_path,
            chunk_duration=int(os.getenv('CHUNK_SIZE', '600')),
            max_workers=int(os.getenv('MAX_WORKERS', '2')),
            cleanup_uploaded_files=True,
            force_reprocess=False
        )
        
        results = pipeline.process_video(config)
        
        logger.info(f"✅ Successfully transcribed {video_id}")
        logger.info(f"Transcript entries: {len(results.full_transcript.transcript)}")
        print(f"✅ Transcription complete: {len(results.full_transcript.transcript)} entries")
        print(f"📁 Output directory: {pipeline.run_dir}")
        
        # Upload outputs to S3
        print(f"\n⬆️  Uploading outputs to S3...")
        logger.info(f"Uploading outputs to s3://{s3_dest_bucket}/{s3_output_prefix}/")
        
        import subprocess
        upload_result = subprocess.run([
            'aws', 's3', 'sync',
            str(pipeline.run_dir),
            f's3://{s3_dest_bucket}/{s3_output_prefix}/',
            '--exclude', '*.mp4',
            '--exclude', '*.mov',
            '--exclude', '*.avi',
            '--exclude', '*.mkv',
            '--exclude', '*.webm',
            '--exclude', '*.m4v',
            '--exclude', 'videos/*',
            '--exclude', 'chunks/*'
        ], capture_output=True, text=True)
        
        if upload_result.returncode == 0:
            print(f"✅ Uploaded to s3://{s3_dest_bucket}/{s3_output_prefix}/")
            logger.info("S3 upload successful")
        else:
            logger.warning(f"S3 upload had issues: {upload_result.stderr}")
            print(f"⚠️  S3 upload warning: {upload_result.stderr[:200]}")
        
        # Send success notification
        output_directory = f"s3://{s3_dest_bucket}/{s3_output_prefix}/"
        notification_result = notification_client.notify_success(
            video_id,
            output_directory=output_directory
        )
        logger.info(f"Notification sent: {notification_result}")
        print(f"📤 Success notification sent: {'✅' if notification_result['success'] else '❌'}")
        
        # Clean up downloaded video file
        try:
            if os.path.exists(local_video_path):
                os.remove(local_video_path)
                logger.info(f"Cleaned up local video file")
        except Exception as e:
            logger.warning(f"Failed to clean up local video file: {e}")
        
        print(f"\n✅ Video {video_id} processed successfully!")
        return 0
        
    except Exception as e:
        error_msg = f"Error processing video {video_id}: {str(e)}"
        logger.error(error_msg, exc_info=True)
        print(f"\n❌ ERROR: {error_msg}")
        
        # Send error notification
        output_directory = f"s3://{s3_dest_bucket}/{s3_output_prefix}/" if s3_dest_bucket else str(pipeline.run_dir)
        notification_result = notification_client.notify_error(
            video_id,
            error_msg,
            output_directory=output_directory
        )
        print(f"📤 Error notification sent: {'✅' if notification_result['success'] else '❌'}")
        
        # Clean up downloaded video file
        try:
            if 'local_video_path' in locals() and os.path.exists(local_video_path):
                os.remove(local_video_path)
        except Exception:
            pass
        
        return 1


if __name__ == "__main__":
    exit(main())

