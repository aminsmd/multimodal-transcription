#!/usr/bin/env python3
"""
Batch processor for video transcription.

This module handles batch processing of videos from a database queue.
It's designed to run in Docker containers and process videos automatically.
"""

import os
import sys
import time
import logging
from pathlib import Path
from typing import List, Optional
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from core.pipeline import TranscriptionPipeline
from database import VideoDatabase, VideoMetadata, VideoStatus
from models import TranscriptionConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class BatchProcessor:
    """
    Batch processor for video transcription.
    
    This class handles the complete batch processing workflow:
    1. Query database for pending videos
    2. Process each video through the transcription pipeline
    3. Update database with results
    """
    
    def __init__(self, 
                 database_path: str = "data/video_database.json",
                 base_dir: str = "outputs",
                 data_dir: str = "data",
                 max_videos_per_run: Optional[int] = None,
                 enable_file_management: bool = True,
                 enable_validation: bool = True):
        """
        Initialize the batch processor.
        
        Args:
            database_path: Path to the video database JSON file
            base_dir: Base directory for outputs
            data_dir: Data directory for file management
            max_videos_per_run: Maximum videos to process per run (None for all)
            enable_file_management: Whether to enable file management
            enable_validation: Whether to enable transcript validation
        """
        self.database = VideoDatabase(database_path)
        self.max_videos_per_run = max_videos_per_run
        self.enable_file_management = enable_file_management
        self.enable_validation = enable_validation
        
        # Initialize pipeline
        self.pipeline = TranscriptionPipeline(
            base_dir=base_dir,
            data_dir=data_dir,
            enable_file_management=False,  # Disable file management for batch processing
            enable_video_repository=False,  # We're using our own database
            enable_validation=enable_validation
        )
        
        logger.info(f"Batch processor initialized")
        logger.info(f"Database: {database_path}")
        logger.info(f"Base directory: {base_dir}")
        logger.info(f"Max videos per run: {max_videos_per_run or 'unlimited'}")
    
    def get_pending_videos(self) -> List[VideoMetadata]:
        """
        Get videos that need to be processed.
        
        Returns:
            List of VideoMetadata objects
        """
        pending_videos = self.database.get_pending_videos(limit=self.max_videos_per_run)
        logger.info(f"Found {len(pending_videos)} pending videos")
        return pending_videos
    
    def process_single_video(self, video_metadata: VideoMetadata) -> bool:
        """
        Process a single video.
        
        Args:
            video_metadata: VideoMetadata object to process
            
        Returns:
            True if successful, False otherwise
        """
        video_id = video_metadata.video_id
        logger.info(f"Processing video: {video_id}")
        
        try:
            # Mark video as processing
            self.database.mark_video_processing(video_id, self.pipeline.run_id)
            
            # Create transcription config
            config = self.database.create_transcription_config(video_metadata)
            logger.info(f"Config: chunk_duration={config.chunk_duration}, max_workers={config.max_workers}")
            
            # Process video
            start_time = time.time()
            results = self.pipeline.process_video(config)
            processing_time = time.time() - start_time
            
            # Get transcript path
            transcript_path = self.pipeline.run_dir / 'transcripts' / f'{video_id}_full_transcript.json'
            
            # Mark video as completed
            self.database.mark_video_completed(
                video_id, 
                str(transcript_path), 
                self.pipeline.run_id
            )
            
            logger.info(f"Successfully processed {video_id} in {processing_time:.2f} seconds")
            logger.info(f"Transcript saved to: {transcript_path}")
            
            return True
            
        except Exception as e:
            error_message = str(e)
            logger.error(f"Failed to process {video_id}: {error_message}")
            
            # Mark video as failed
            self.database.mark_video_failed(video_id, error_message, self.pipeline.run_id)
            
            return False
    
    def process_batch(self) -> dict:
        """
        Process a batch of videos.
        
        Returns:
            Dictionary with processing results
        """
        logger.info("Starting batch processing")
        
        # Get pending videos
        pending_videos = self.get_pending_videos()
        
        if not pending_videos:
            logger.info("No pending videos to process")
            return {
                "total_videos": 0,
                "processed": 0,
                "failed": 0,
                "skipped": 0,
                "processing_time": 0.0
            }
        
        # Process each video
        start_time = time.time()
        processed = 0
        failed = 0
        
        for video_metadata in pending_videos:
            logger.info(f"Processing video {processed + failed + 1}/{len(pending_videos)}: {video_metadata.video_id}")
            
            success = self.process_single_video(video_metadata)
            
            if success:
                processed += 1
            else:
                failed += 1
            
            # Log progress
            logger.info(f"Progress: {processed + failed}/{len(pending_videos)} videos processed")
        
        total_time = time.time() - start_time
        
        # Log final results
        logger.info(f"Batch processing completed in {total_time:.2f} seconds")
        logger.info(f"Results: {processed} processed, {failed} failed")
        
        return {
            "total_videos": len(pending_videos),
            "processed": processed,
            "failed": failed,
            "skipped": 0,
            "processing_time": total_time
        }
    
    def get_database_stats(self) -> dict:
        """Get database statistics."""
        return self.database.get_database_stats()
    
    def cleanup(self):
        """Clean up resources."""
        self.pipeline.cleanup()
        logger.info("Batch processor cleanup completed")


def main():
    """Main entry point for batch processing."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Batch video transcription processor")
    parser.add_argument("--database", default="data/video_database.json", 
                       help="Path to video database JSON file")
    parser.add_argument("--base-dir", default="outputs", 
                       help="Base directory for outputs")
    parser.add_argument("--data-dir", default="data", 
                       help="Data directory for file management")
    parser.add_argument("--max-videos", type=int, default=None,
                       help="Maximum videos to process per run")
    parser.add_argument("--no-file-management", action="store_true",
                       help="Disable file management")
    parser.add_argument("--no-validation", action="store_true",
                       help="Disable transcript validation")
    parser.add_argument("--verbose", "-v", action="store_true",
                       help="Enable verbose logging")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Initialize batch processor
    processor = BatchProcessor(
        database_path=args.database,
        base_dir=args.base_dir,
        data_dir=args.data_dir,
        max_videos_per_run=args.max_videos,
        enable_file_management=not args.no_file_management,
        enable_validation=not args.no_validation
    )
    
    try:
        # Process batch
        results = processor.process_batch()
        
        # Print results
        print("\n" + "="*50)
        print("BATCH PROCESSING RESULTS")
        print("="*50)
        print(f"Total videos: {results['total_videos']}")
        print(f"Processed: {results['processed']}")
        print(f"Failed: {results['failed']}")
        print(f"Processing time: {results['processing_time']:.2f} seconds")
        
        # Print database stats
        stats = processor.get_database_stats()
        print(f"\nDatabase stats:")
        print(f"  Pending: {stats['pending_videos']}")
        print(f"  Processed: {stats['processed_videos']}")
        print(f"  Failed: {stats['failed_videos']}")
        
    except KeyboardInterrupt:
        logger.info("Batch processing interrupted by user")
    except Exception as e:
        logger.error(f"Batch processing failed: {str(e)}")
        sys.exit(1)
    finally:
        processor.cleanup()


if __name__ == "__main__":
    main()
