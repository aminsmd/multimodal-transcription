#!/usr/bin/env python3
"""
Batch transcription processor that:
1. Fetches videos from the API that need transcription
2. Downloads videos from S3
3. Processes each video through the transcription pipeline
4. Sends notifications with success/error status and output directory
"""

import os
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
import logging

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from api.video_fetcher import VideoFetcher
from api.notification_client import NotificationClient, TranscriptionStatus
from utils.s3_utils import get_s3_bucket_path, construct_s3_url, download_video_from_s3
from core.pipeline import TranscriptionPipeline
from models import TranscriptionConfig

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class BatchTranscriptionProcessor:
    """
    Processes multiple videos in batch by fetching from API, downloading from S3,
    transcribing, and sending notifications.
    """
    
    def __init__(
        self,
        s3_bucket_path: Optional[str] = None,
        output_dir: str = "outputs",
        data_dir: str = "data",
        chunk_duration: int = 300,
        max_workers: int = 4,
        enable_file_management: bool = True,
        enable_validation: bool = True
    ):
        """
        Initialize the batch transcription processor.
        
        Args:
            s3_bucket_path: S3 source bucket path for reading videos (if None, reads from S3_BUCKET_PATH env var)
                          This is the bucket where input videos are stored (e.g., bci-prod-upload)
            output_dir: Output directory for transcripts (local filesystem, will be synced to S3 separately)
            data_dir: Data directory for file management
            chunk_duration: Duration of each chunk in seconds
            max_workers: Number of parallel workers for transcription
            enable_file_management: Whether to enable file management
            enable_validation: Whether to enable transcript validation
        """
        # Initialize API clients
        self.video_fetcher = VideoFetcher()
        self.notification_client = NotificationClient()
        
        # Get S3 source bucket path (for reading/downloading videos)
        # This is separate from the output S3 bucket used for writing results
        if s3_bucket_path:
            self.s3_source_bucket_name = s3_bucket_path
        else:
            self.s3_source_bucket_name = get_s3_bucket_path()
        
        logger.info(f"S3 source bucket (for reading videos): {self.s3_source_bucket_name}")
        
        # Initialize pipeline
        # Disable video repository and MongoDB - we don't need database/file tracking for batch processing
        # Results are uploaded to S3 and notifications are sent via API
        self.pipeline = TranscriptionPipeline(
            base_dir=output_dir,
            data_dir=data_dir,
            enable_file_management=enable_file_management,
            enable_video_repository=False,  # Disable - not needed for batch processing
            enable_validation=enable_validation,
            enable_mongodb=False  # Disable - not needed for batch processing
        )
        
        self.output_dir = output_dir
        self.chunk_duration = chunk_duration
        self.max_workers = max_workers
        
        # Track processing results
        self.processed_videos: List[Dict[str, Any]] = []
    
    def fetch_videos_to_transcribe(self) -> List[Dict[str, Any]]:
        """
        Fetch the list of videos that need transcription from the API.
        
        Returns:
            List of video dictionaries from the API
        """
        logger.info("=" * 70)
        logger.info("FETCHING VIDEOS FROM API")
        logger.info("=" * 70)
        logger.info(f"API Endpoint: {self.video_fetcher.endpoint_url}")
        
        try:
            result = self.video_fetcher.fetch_videos()
            
            logger.info(f"API Response Status: {result.get('status_code', 'N/A')}")
            logger.info(f"API Call Success: {result['success']}")
            
            if not result['success']:
                logger.error(f"❌ Failed to fetch videos: {result['error']}")
                logger.error(f"Response details: {result.get('response')}")
                logger.error(f"Status code: {result.get('status_code')}")
                print(f"\n❌ API FETCH FAILED: {result['error']}")
                print(f"Status Code: {result.get('status_code', 'N/A')}")
                # Don't fail the entire process if API fetch fails - just return empty list
                return []
            
            videos = result['videos']
            logger.info(f"✅ Successfully fetched {len(videos)} videos from API")
            print(f"\n✅ API FETCH SUCCESS: Found {len(videos)} videos")
            
            if videos:
                logger.info("📋 Video List:")
                print("\n📋 Videos to Process:")
                for i, video in enumerate(videos[:10], 1):  # Show first 10
                    if isinstance(video, dict):
                        video_id = video.get('id', 'N/A')
                        video_path = video.get('path', 'N/A')
                        logger.info(f"  {i}. ID: {video_id}, Path: {video_path}")
                        print(f"  {i}. ID: {video_id}")
                        print(f"     Path: {video_path}")
                    else:
                        logger.info(f"  {i}. {video}")
                        print(f"  {i}. {video}")
                
                if len(videos) > 10:
                    logger.info(f"  ... and {len(videos) - 10} more videos")
                    print(f"  ... and {len(videos) - 10} more videos")
            
            logger.info("=" * 70)
            return videos
        except Exception as e:
            logger.error(f"Exception while fetching videos: {str(e)}", exc_info=True)
            print(f"\n❌ EXCEPTION DURING API FETCH: {str(e)}")
            # Don't fail the entire process - return empty list
            return []
    
    def process_video(self, video_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a single video: download from S3, transcribe, and send notification.
        
        Args:
            video_info: Video information dictionary from API (should contain path or similar)
        
        Returns:
            Dictionary with processing results
        """
        # Extract video path and ID from video_info
        # Expected format: {"id": "69189bf37fcd33a6edc1e9ee", "path": "68dc488aac9091f3e8574f6f/video.mp4"}
        video_path = None
        video_id = None
        
        # Try to extract video path and ID from various possible formats
        if isinstance(video_info, str):
            # If it's just a string, assume it's the path
            video_path = video_info
            video_id = Path(video_path).stem
        elif isinstance(video_info, dict):
            # First, try to get video ID (prefer API-provided ID - 'id' is the expected key)
            video_id = (video_info.get('id') or video_info.get('videoId') or 
                       video_info.get('video_id') or video_info.get('_id'))
            
            # Then, try to get video path ('path' is the expected key)
            video_path = (video_info.get('path') or video_info.get('filePath') or 
                         video_info.get('videoPath') or video_info.get('file_path') or 
                         video_info.get('video_path') or video_info.get('key') or
                         video_info.get('s3Key') or video_info.get('s3_key'))
            
            # If we have a path but no ID, derive ID from path
            if video_path and not video_id:
                video_id = Path(video_path).stem
        
        if not video_path:
            error_msg = f"Could not extract video path from video_info: {video_info}"
            logger.error(error_msg)
            return {
                'success': False,
                'video_id': video_id or 'unknown',
                'error': error_msg
            }
        
        # Ensure we have a video_id (fallback to path-based ID)
        if not video_id:
            video_id = Path(video_path).stem
        
        logger.info(f"Processing video: {video_id} (path: {video_path})")
        print(f"\n🎬 Processing Video {video_id}")
        print(f"   Path: {video_path}")
        
        # Construct full S3 URL using source bucket (for reading videos)
        s3_url = construct_s3_url(self.s3_source_bucket_name, video_path)
        logger.info(f"S3 source URL (for downloading): {s3_url}")
        print(f"   S3 URL: {s3_url}")
        
        # Download video from S3
        print(f"   ⬇️  Downloading from S3...")
        logger.info(f"Starting S3 download for {video_id}...")
        local_video_path, download_success = download_video_from_s3(s3_url)
        
        if not download_success:
            error_msg = f"Failed to download video from S3: {s3_url}"
            logger.error(error_msg)
            print(f"   ❌ DOWNLOAD FAILED: {error_msg}")
            
            # Send error notification
            notification_result = self.notification_client.notify_error(
                video_id,
                error_msg,
                output_directory=str(self.pipeline.run_dir)
            )
            logger.info(f"Notification sent: {notification_result}")
            print(f"   📤 Notification sent: {'✅' if notification_result['success'] else '❌'}")
            
            return {
                'success': False,
                'video_id': video_id,
                'error': error_msg,
                'download_status': 'failed',
                'notification_sent': notification_result['success']
            }
        
        # Log download success with file size
        try:
            import os
            file_size = os.path.getsize(local_video_path)
            file_size_mb = file_size / (1024 * 1024)
            logger.info(f"✅ Successfully downloaded {video_id}: {file_size_mb:.2f} MB")
            print(f"   ✅ DOWNLOAD SUCCESS: {file_size_mb:.2f} MB")
        except Exception:
            logger.info(f"✅ Successfully downloaded {video_id}")
            print(f"   ✅ DOWNLOAD SUCCESS")
        
        # Process video through transcription pipeline
        try:
            logger.info(f"Starting transcription for {video_id}...")
            
            config = TranscriptionConfig(
                video_input=local_video_path,
                chunk_duration=self.chunk_duration,
                max_workers=self.max_workers,
                cleanup_uploaded_files=True,
                force_reprocess=False
            )
            
            results = self.pipeline.process_video(config)
            
            logger.info(f"✅ Successfully transcribed {video_id}")
            logger.info(f"Transcript entries: {len(results.full_transcript.transcript)}")
            logger.info(f"Output directory: {self.pipeline.run_dir}")
            print(f"   ✅ TRANSCRIPTION SUCCESS: {len(results.full_transcript.transcript)} entries")
            print(f"   📁 Output: {self.pipeline.run_dir}")
            
            # Send success notification
            notification_result = self.notification_client.notify_success(
                video_id,
                output_directory=str(self.pipeline.run_dir)
            )
            logger.info(f"Notification sent: {notification_result}")
            print(f"   📤 Notification sent: {'✅' if notification_result['success'] else '❌'}")
            
            # Clean up downloaded video file
            try:
                if os.path.exists(local_video_path):
                    os.remove(local_video_path)
                    logger.info(f"Cleaned up local video file: {local_video_path}")
            except Exception as e:
                logger.warning(f"Failed to clean up local video file: {e}")
            
            return {
                'success': True,
                'video_id': video_id,
                'transcript_entries': len(results.full_transcript.transcript),
                'output_directory': str(self.pipeline.run_dir),
                'download_status': 'success',
                'notification_sent': notification_result['success'],
                'notification_response': notification_result.get('response')
            }
            
        except Exception as e:
            error_msg = f"Error processing video {video_id}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            
            # Send error notification
            notification_result = self.notification_client.notify_error(
                video_id,
                error_msg,
                output_directory=str(self.pipeline.run_dir)
            )
            logger.info(f"Notification sent: {notification_result}")
            
            # Clean up downloaded video file
            try:
                if os.path.exists(local_video_path):
                    os.remove(local_video_path)
            except Exception:
                pass
            
            return {
                'success': False,
                'video_id': video_id,
                'error': error_msg,
                'download_status': 'success' if 'local_video_path' in locals() else 'failed',
                'notification_sent': notification_result['success']
            }
    
    def process_all_videos(self) -> Dict[str, Any]:
        """
        Fetch all videos from API and process them.
        
        Returns:
            Dictionary with summary of processing results
        """
        logger.info("=" * 70)
        logger.info("Starting batch transcription processing")
        logger.info("=" * 70)
        
        # Fetch videos
        print("\n" + "=" * 70)
        print("STEP 1: FETCHING VIDEOS FROM API")
        print("=" * 70)
        try:
            logger.info("Attempting to fetch videos from API...")
            videos = self.fetch_videos_to_transcribe()
            logger.info(f"Video fetch completed. Found {len(videos)} videos.")
            print(f"\n📊 API FETCH SUMMARY: {len(videos)} videos found")
        except Exception as e:
            logger.error(f"Exception occurred while fetching videos: {str(e)}", exc_info=True)
            logger.error(f"Exception type: {type(e).__name__}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            videos = []
        
        if not videos:
            logger.warning("No videos found to transcribe")
            logger.info("This could mean:")
            logger.info("  1. The API returned no videos")
            logger.info("  2. The API call failed")
            logger.info("  3. There was an error parsing the API response")
            logger.info("Exiting gracefully with success status (no videos is not an error)")
            
            # Create a summary file even when no videos found
            import json
            from datetime import datetime
            summary_data = {
                'total_videos': 0,
                'processed': 0,
                'succeeded': 0,
                'failed': 0,
                'output_directory': str(self.pipeline.run_dir),
                'timestamp': datetime.now().isoformat(),
                'status': 'no_videos_found',
                'results': []
            }
            summary_file = self.pipeline.run_dir / 'batch_summary.json'
            with open(summary_file, 'w') as f:
                json.dump(summary_data, f, indent=2)
            logger.info(f"Created summary file: {summary_file}")
            
            # Return success even if no videos found - this is not necessarily an error
            return summary_data
        
        # Process each video
        total_videos = len(videos)
        succeeded = 0
        failed = 0
        
        print("\n" + "=" * 70)
        print(f"STEP 2: PROCESSING {total_videos} VIDEOS")
        print("=" * 70)
        logger.info(f"Processing {total_videos} videos...")
        
        for i, video_info in enumerate(videos, 1):
            logger.info(f"\n{'=' * 70}")
            logger.info(f"Processing video {i}/{total_videos}")
            logger.info(f"{'=' * 70}")
            print(f"\n[{i}/{total_videos}] Processing video...")
            
            result = self.process_video(video_info)
            self.processed_videos.append(result)
            
            # Print summary for this video
            if result['success']:
                succeeded += 1
                print(f"   ✅ Video {i} completed successfully")
            else:
                failed += 1
                print(f"   ❌ Video {i} failed: {result.get('error', 'Unknown error')}")
            
            # Print download status if available
            if 'download_status' in result:
                status_emoji = '✅' if result['download_status'] == 'success' else '❌'
                print(f"   Download: {status_emoji} {result['download_status']}")
        
        # Summary
        print("\n" + "=" * 70)
        print("STEP 3: BATCH PROCESSING SUMMARY")
        print("=" * 70)
        logger.info("\n" + "=" * 70)
        logger.info("Batch processing completed")
        logger.info("=" * 70)
        logger.info(f"Total videos: {total_videos}")
        logger.info(f"Succeeded: {succeeded}")
        logger.info(f"Failed: {failed}")
        logger.info(f"Output directory: {self.pipeline.run_dir}")
        
        print(f"\n📊 FINAL RESULTS:")
        print(f"   Total videos: {total_videos}")
        print(f"   ✅ Succeeded: {succeeded}")
        print(f"   ❌ Failed: {failed}")
        print(f"   📁 Output directory: {self.pipeline.run_dir}")
        
        # Show download status summary
        download_successes = sum(1 for r in self.processed_videos if r.get('download_status') == 'success')
        download_failures = sum(1 for r in self.processed_videos if r.get('download_status') == 'failed')
        if download_successes + download_failures > 0:
            print(f"\n📥 DOWNLOAD STATUS:")
            print(f"   ✅ Successful downloads: {download_successes}")
            print(f"   ❌ Failed downloads: {download_failures}")
        
        # Show notification status summary
        notifications_sent = sum(1 for r in self.processed_videos if r.get('notification_sent'))
        notifications_failed = sum(1 for r in self.processed_videos if not r.get('notification_sent', True))
        if notifications_sent + notifications_failed > 0:
            print(f"\n📤 NOTIFICATION STATUS:")
            print(f"   ✅ Sent: {notifications_sent}")
            print(f"   ❌ Failed: {notifications_failed}")
        
        # Create summary file
        import json
        from datetime import datetime
        summary_data = {
            'total_videos': total_videos,
            'processed': total_videos,
            'succeeded': succeeded,
            'failed': failed,
            'output_directory': str(self.pipeline.run_dir),
            'timestamp': datetime.now().isoformat(),
            'status': 'completed',
            'results': self.processed_videos
        }
        summary_file = self.pipeline.run_dir / 'batch_summary.json'
        with open(summary_file, 'w') as f:
            json.dump(summary_data, f, indent=2)
        logger.info(f"Created summary file: {summary_file}")
        
        return summary_data


def main():
    """Main function to run batch transcription processing."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Batch Transcription Processor')
    parser.add_argument('--s3-bucket-path', type=str, default=None,
                       help='S3 source bucket path for reading videos (default: from S3_BUCKET_PATH env var). '
                            'Note: Outputs are written to a different S3 bucket specified in the workflow.')
    parser.add_argument('--output-dir', type=str, default='outputs',
                       help='Output directory (default: outputs)')
    parser.add_argument('--data-dir', type=str, default='data',
                       help='Data directory (default: data)')
    parser.add_argument('--chunk-size', type=int, default=300,
                       help='Duration of each chunk in seconds (default: 300)')
    parser.add_argument('--max-workers', type=int, default=4,
                       help='Maximum number of parallel workers (default: 4)')
    parser.add_argument('--no-file-management', action='store_true',
                       help='Disable file management')
    parser.add_argument('--no-validation', action='store_true',
                       help='Disable transcript validation')
    
    args = parser.parse_args()
    
    # Check for required environment variables
    if not os.getenv('GOOGLE_API_KEY'):
        logger.error("GOOGLE_API_KEY environment variable is not set")
        return 1
    
    try:
        # Initialize processor
        processor = BatchTranscriptionProcessor(
            s3_bucket_path=args.s3_bucket_path,
            output_dir=args.output_dir,
            data_dir=args.data_dir,
            chunk_duration=args.chunk_size,
            max_workers=args.max_workers,
            enable_file_management=not args.no_file_management,
            enable_validation=not args.no_validation
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
        
        # Return 0 (success) if:
        # - No videos found (not an error)
        # - All videos processed successfully
        # Return 1 (failure) only if some videos failed to process
        if summary['total_videos'] == 0:
            logger.info("No videos to process - exiting successfully")
            return 0
        
        return 0 if summary['failed'] == 0 else 1
        
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}", exc_info=True)
        return 1


if __name__ == "__main__":
    exit(main())

