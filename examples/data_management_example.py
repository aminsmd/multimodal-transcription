#!/usr/bin/env python3
"""
Example of how to use the data management system with the transcription pipeline.

This example demonstrates:
1. Setting up a data directory structure
2. Adding videos to the system
3. Organizing videos by type
4. Batch processing videos
5. Managing transcript outputs
"""

import os
import sys
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from data_setup import DataManager
from models import TranscriptionConfig, ModelType
from transcription_pipeline import TranscriptionPipeline


def setup_data_directory():
    """Set up the data directory structure."""
    print("=== Setting up Data Directory ===")
    
    # Initialize data manager
    dm = DataManager("example_data")
    
    # Show directory structure
    structure = dm.get_directory_structure()
    print(f"Created directory structure:")
    for name, info in structure["directories"].items():
        print(f"  - {name}: {info['path']}")
    
    return dm


def add_sample_videos(dm):
    """Add sample videos to the data directory."""
    print("\n=== Adding Sample Videos ===")
    
    # Example video paths (replace with your actual video paths)
    sample_videos = [
        "path/to/lecture1.mp4",
        "path/to/lecture2.mp4", 
        "path/to/discussion1.mp4",
        "path/to/presentation1.mp4"
    ]
    
    added_videos = []
    
    for video_path in sample_videos:
        if os.path.exists(video_path):
            try:
                video_info = dm.add_video(video_path, copy=True)
                added_videos.append(video_info)
                print(f"Added: {video_info['video_id']} ({video_info['file_size_mb']} MB)")
            except Exception as e:
                print(f"Error adding {video_path}: {e}")
        else:
            print(f"Video not found: {video_path}")
    
    return added_videos


def organize_videos_by_type(dm, videos):
    """Organize videos by type/category."""
    print("\n=== Organizing Videos by Type ===")
    
    # Define video categories
    video_categories = {
        "lectures": [v['video_id'] for v in videos if 'lecture' in v['filename'].lower()],
        "discussions": [v['video_id'] for v in videos if 'discussion' in v['filename'].lower()],
        "presentations": [v['video_id'] for v in videos if 'presentation' in v['filename'].lower()]
    }
    
    # Organize videos
    dm.organize_by_type(video_categories)
    
    for category, video_ids in video_categories.items():
        print(f"Organized {len(video_ids)} videos into '{category}' category")


def create_batch_processing_config(dm, videos):
    """Create batch processing configuration."""
    print("\n=== Creating Batch Processing Configuration ===")
    
    # Define different configurations for different video types
    configs = {
        "lectures": {
            "chunk_duration": 600,  # 10 minutes for lectures
            "max_workers": 4,
            "cleanup_uploaded_files": True,
            "force_reprocess": False
        },
        "discussions": {
            "chunk_duration": 300,  # 5 minutes for discussions
            "max_workers": 6,
            "cleanup_uploaded_files": True,
            "force_reprocess": False
        },
        "presentations": {
            "chunk_duration": 900,  # 15 minutes for presentations
            "max_workers": 2,
            "cleanup_uploaded_files": True,
            "force_reprocess": False
        }
    }
    
    # Create batch configurations for each type
    for video_type, config_template in configs.items():
        # Get videos of this type
        type_videos = [v for v in videos if video_type in v['filename'].lower()]
        
        if type_videos:
            batch_config = dm.create_batch_config(
                video_ids=[v['video_id'] for v in type_videos],
                config_template=config_template
            )
            print(f"Created batch config for {video_type}: {batch_config['batch_id']}")


def process_single_video(dm, video_id):
    """Process a single video through the transcription pipeline."""
    print(f"\n=== Processing Video: {video_id} ===")
    
    # Get video path
    video_path = dm.get_video_path(video_id)
    if not video_path:
        print(f"Video not found: {video_id}")
        return None
    
    # Create configuration
    config = TranscriptionConfig(
        video_input=str(video_path),
        chunk_duration=300,
        max_workers=4,
        model=ModelType.GEMINI_2_5_PRO,
        cleanup_uploaded_files=True,
        force_reprocess=False
    )
    
    try:
        # Initialize pipeline
        pipeline = TranscriptionPipeline("example_outputs")
        
        # Process video
        results = pipeline.process_video(config)
        
        # Update video status
        dm.update_video_status(video_id, "transcribed", 
                              transcript_path=str(results.full_transcript),
                              processing_date=results.processing_date)
        
        print(f"Successfully processed {video_id}")
        print(f"Transcript entries: {len(results.full_transcript.transcript)}")
        print(f"Cached: {results.cached}")
        
        return results
        
    except Exception as e:
        print(f"Error processing {video_id}: {e}")
        dm.update_video_status(video_id, "error", error_message=str(e))
        return None


def batch_process_videos(dm, video_ids):
    """Process multiple videos in batch."""
    print(f"\n=== Batch Processing {len(video_ids)} Videos ===")
    
    results = []
    
    for i, video_id in enumerate(video_ids, 1):
        print(f"\nProcessing video {i}/{len(video_ids)}: {video_id}")
        
        result = process_single_video(dm, video_id)
        if result:
            results.append(result)
    
    print(f"\nBatch processing completed: {len(results)}/{len(video_ids)} successful")
    return results


def export_results(dm):
    """Export video list and results."""
    print("\n=== Exporting Results ===")
    
    # Export video list
    csv_file = dm.export_video_list()
    print(f"Video list exported to: {csv_file}")
    
    # List all videos with their status
    videos = dm.list_videos()
    print(f"\nVideo Status Summary:")
    
    status_counts = {}
    for video in videos:
        status = video.get('status', 'unknown')
        status_counts[status] = status_counts.get(status, 0) + 1
    
    for status, count in status_counts.items():
        print(f"  - {status}: {count} videos")


def cleanup_and_maintenance(dm):
    """Perform cleanup and maintenance tasks."""
    print("\n=== Cleanup and Maintenance ===")
    
    # Clean up old files
    dm.cleanup_old_files(days_old=7)
    
    # Show directory sizes
    print("Directory sizes:")
    for dir_name, dir_info in dm.get_directory_structure()["directories"].items():
        dir_path = Path(dir_info["path"])
        if dir_path.exists():
            size_mb = sum(f.stat().st_size for f in dir_path.rglob('*') if f.is_file()) / (1024 * 1024)
            print(f"  - {dir_name}: {size_mb:.1f} MB")


def main():
    """Main example workflow."""
    print("Data Management Example for Transcription Pipeline")
    print("=" * 50)
    
    try:
        # Step 1: Set up data directory
        dm = setup_data_directory()
        
        # Step 2: Add sample videos (replace with your actual videos)
        print("\nNote: Replace the sample video paths with your actual video files")
        videos = add_sample_videos(dm)
        
        if not videos:
            print("No videos added. Please update the video paths in the script.")
            return
        
        # Step 3: Organize videos
        organize_videos_by_type(dm, videos)
        
        # Step 4: Create batch configurations
        create_batch_processing_config(dm, videos)
        
        # Step 5: Process a single video (if available)
        if videos:
            first_video = videos[0]
            print(f"\nProcessing first video: {first_video['video_id']}")
            result = process_single_video(dm, first_video['video_id'])
            
            if result:
                print("Single video processing successful!")
        
        # Step 6: Export results
        export_results(dm)
        
        # Step 7: Cleanup
        cleanup_and_maintenance(dm)
        
        print("\n" + "=" * 50)
        print("Example completed successfully!")
        print("\nNext steps:")
        print("1. Update video paths in the script with your actual videos")
        print("2. Run the script again to process your videos")
        print("3. Check the generated transcripts in the outputs directory")
        
    except Exception as e:
        print(f"Error in main workflow: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
