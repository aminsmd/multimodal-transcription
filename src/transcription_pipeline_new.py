#!/usr/bin/env python3
"""
Modular Video Transcription Pipeline

A clean and modular pipeline that:
1. Processes video into smaller chunks
2. Generates multimodal transcriptions for chunks (parallel processing)
3. Outputs full transcript without segmentation

This is the new modular version of the transcription pipeline.
"""

import argparse
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from core.pipeline import TranscriptionPipeline
from models import TranscriptionConfig


def main():
    """Main function to run the transcription pipeline."""
    parser = argparse.ArgumentParser(description='Modular Video Transcription Pipeline')
    parser.add_argument('--input', type=str, required=True,
                       help='Video file path')
    parser.add_argument('--chunk-size', type=int, default=300,
                       help='Duration of each chunk in seconds (default: 300)')
    parser.add_argument('--chunk-size-mb', type=int, default=None,
                       help='Target size of each chunk in MB (alternative to --chunk-size)')
    parser.add_argument('--max-workers', type=int, default=4,
                       help='Maximum number of parallel workers for transcription (default: 4)')
    parser.add_argument('--output-dir', type=str, default='outputs',
                       help='Output directory (default: outputs)')
    parser.add_argument('--no-cleanup', action='store_true',
                       help='Skip cleanup of uploaded files from Google (default: cleanup enabled)')
    parser.add_argument('--force-reprocess', action='store_true',
                       help='Force reprocessing even if transcript exists (default: use cache)')
    parser.add_argument('--data-dir', type=str, default='data',
                       help='Data directory for file management (default: data)')
    parser.add_argument('--no-file-management', action='store_true',
                       help='Disable automatic file management (default: enabled)')
    parser.add_argument('--no-video-repository', action='store_true',
                       help='Disable video repository (database-like interface) (default: enabled)')
    
    args = parser.parse_args()
    
    try:
        # Create configuration
        config = TranscriptionConfig(
            video_input=args.input,
            chunk_duration=args.chunk_size,
            chunk_size_mb=args.chunk_size_mb,
            max_workers=args.max_workers,
            cleanup_uploaded_files=not args.no_cleanup,
            force_reprocess=args.force_reprocess,
            output_dir=args.output_dir
        )
        
        # Initialize pipeline with file management and video repository
        pipeline = TranscriptionPipeline(
            base_dir=args.output_dir,
            data_dir=args.data_dir,
            enable_file_management=not args.no_file_management,
            enable_video_repository=not args.no_video_repository
        )
        
        # Process video
        results = pipeline.process_video(config)
        
        print(f"\nTranscription pipeline completed successfully!")
        print(f"Run ID: {pipeline.run_id}")
        print(f"Video ID: {results.video_id}")
        print(f"Pipeline runs directory: {pipeline.pipeline_runs_dir}")
        print(f"Run directory: {pipeline.run_dir}")
        print(f"Cached: {results.cached}")
        
        # Clean up
        pipeline.cleanup()
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
