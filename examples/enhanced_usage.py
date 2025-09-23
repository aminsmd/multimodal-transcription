#!/usr/bin/env python3
"""
Enhanced usage example with integrated file management.

This example demonstrates the new file management system integrated
with the transcription pipeline.
"""

import os
import sys
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from transcription_pipeline import TranscriptionPipeline
from models import TranscriptionConfig, ModelType
from core.file_manager import create_file_manager


def demonstrate_file_management():
    """Demonstrate the file management system."""
    print("=== File Management Demonstration ===")
    
    # Initialize file manager
    file_manager = create_file_manager("example_data", auto_organize=True)
    
    # Add some sample videos (replace with your actual video paths)
    sample_videos = [
        "path/to/lecture1.mp4",
        "path/to/lecture2.mp4",
        "path/to/discussion1.mp4"
    ]
    
    print("Adding videos to management system...")
    for video_path in sample_videos:
        if os.path.exists(video_path):
            try:
                video_info = file_manager.add_video(video_path)
                print(f"  ✅ Added: {video_info['video_id']} ({video_info['file_size_mb']} MB)")
            except Exception as e:
                print(f"  ❌ Error adding {video_path}: {e}")
        else:
            print(f"  ⚠️  File not found: {video_path}")
    
    # List managed videos
    videos = file_manager.list_videos()
    print(f"\nManaged videos: {len(videos)}")
    for video in videos:
        print(f"  - {video['video_id']}: {video['filename']} ({video['status']})")
    
    # Get file statistics
    stats = file_manager.get_file_stats()
    print(f"\nFile Statistics:")
    print(f"  - Total videos: {stats['total_videos']}")
    print(f"  - Total size: {stats['total_size_mb']:.1f} MB")
    print(f"  - Status counts: {stats['status_counts']}")
    
    return file_manager


def demonstrate_automatic_file_resolution():
    """Demonstrate automatic file resolution."""
    print("\n=== Automatic File Resolution ===")
    
    # Initialize pipeline with file management
    pipeline = TranscriptionPipeline(
        base_dir="example_outputs",
        data_dir="example_data",
        enable_file_management=True
    )
    
    # Example: Process video by ID (if it exists in the system)
    video_id = "example_video_id"  # Replace with actual video ID
    
    # Create configuration - the pipeline will automatically resolve the path
    config = TranscriptionConfig(
        video_input=video_id,  # Can be path, ID, or filename
        chunk_duration=300,
        max_workers=4,
        model=ModelType.GEMINI_2_5_PRO,
        cleanup_uploaded_files=True,
        force_reprocess=False
    )
    
    print(f"Processing video: {config.video_input}")
    print(f"File management enabled: {pipeline.file_manager is not None}")
    
    # The pipeline will automatically:
    # 1. Resolve the video path through file management
    # 2. Validate the video file
    # 3. Check for existing transcripts
    # 4. Process if needed
    # 5. Update file management status
    
    try:
        results = pipeline.process_video(config)
        print(f"✅ Processing completed!")
        print(f"  - Video ID: {results.video_id}")
        print(f"  - Cached: {results.cached}")
        print(f"  - Transcript entries: {len(results.full_transcript.transcript)}")
        
        return results
    except Exception as e:
        print(f"❌ Error processing video: {e}")
        return None


def demonstrate_batch_processing():
    """Demonstrate batch processing with file management."""
    print("\n=== Batch Processing with File Management ===")
    
    # Initialize pipeline
    pipeline = TranscriptionPipeline(
        base_dir="example_outputs",
        data_dir="example_data",
        enable_file_management=True
    )
    
    # Get all raw videos
    file_manager = pipeline.file_manager
    raw_videos = file_manager.list_videos(status="raw")
    
    print(f"Found {len(raw_videos)} raw videos to process")
    
    # Process each video
    results = []
    for i, video in enumerate(raw_videos, 1):
        print(f"\nProcessing video {i}/{len(raw_videos)}: {video['video_id']}")
        
        # Create configuration
        config = TranscriptionConfig(
            video_input=video['video_id'],  # Use video ID
            chunk_duration=300,
            max_workers=4,
            cleanup_uploaded_files=True,
            force_reprocess=False
        )
        
        try:
            result = pipeline.process_video(config)
            results.append(result)
            print(f"  ✅ Success: {result.video_id}")
        except Exception as e:
            print(f"  ❌ Error: {e}")
    
    print(f"\nBatch processing completed: {len(results)}/{len(raw_videos)} successful")
    return results


def demonstrate_file_organization():
    """Demonstrate file organization features."""
    print("\n=== File Organization ===")
    
    file_manager = create_file_manager("example_data")
    
    # Organize videos by type
    organization_rules = {
        "lectures": [],  # Add video IDs for lectures
        "discussions": [],  # Add video IDs for discussions
        "presentations": []  # Add video IDs for presentations
    }
    
    # Get all videos and categorize them
    all_videos = file_manager.list_videos()
    for video in all_videos:
        filename = video['filename'].lower()
        if 'lecture' in filename:
            organization_rules['lectures'].append(video['video_id'])
        elif 'discussion' in filename:
            organization_rules['discussions'].append(video['video_id'])
        elif 'presentation' in filename:
            organization_rules['presentations'].append(video['video_id'])
    
    # Apply organization
    file_manager.organize_videos(organization_rules)
    
    # Export video list
    csv_file = file_manager.export_video_list()
    print(f"Video list exported to: {csv_file}")
    
    # Show directory structure
    structure = file_manager.get_directory_structure()
    print(f"\nDirectory structure:")
    for name, info in structure['directories'].items():
        print(f"  - {name}: {info['path']}")


def demonstrate_advanced_features():
    """Demonstrate advanced file management features."""
    print("\n=== Advanced Features ===")
    
    file_manager = create_file_manager("example_data")
    
    # Get file statistics
    stats = file_manager.get_file_stats()
    print(f"File Statistics:")
    print(f"  - Total videos: {stats['total_videos']}")
    print(f"  - Total size: {stats['total_size_mb']:.1f} MB")
    print(f"  - Status distribution: {stats['status_counts']}")
    print(f"  - File types: {stats['file_types']}")
    
    # Cleanup old files
    print(f"\nCleaning up old files...")
    file_manager.cleanup_old_files(days_old=7)
    
    # Refresh registry
    print(f"Refreshing file registry...")
    file_manager.refresh_registry()
    
    # Show managed files
    videos = file_manager.list_videos()
    print(f"\nManaged files:")
    for video in videos:
        status = video.get('status', 'unknown')
        size_mb = video.get('file_size_mb', 0)
        print(f"  - {video['video_id']}: {video['filename']} ({size_mb:.1f} MB, {status})")


def main():
    """Main demonstration function."""
    print("🎬 Enhanced Transcription Pipeline with File Management")
    print("=" * 60)
    
    try:
        # Step 1: Demonstrate file management
        file_manager = demonstrate_file_management()
        
        # Step 2: Demonstrate automatic file resolution
        result = demonstrate_automatic_file_resolution()
        
        # Step 3: Demonstrate batch processing
        batch_results = demonstrate_batch_processing()
        
        # Step 4: Demonstrate file organization
        demonstrate_file_organization()
        
        # Step 5: Demonstrate advanced features
        demonstrate_advanced_features()
        
        print("\n" + "=" * 60)
        print("✅ Enhanced demonstration completed successfully!")
        print("\nKey Features Demonstrated:")
        print("  - Automatic file management and organization")
        print("  - File path resolution (by path, ID, or filename)")
        print("  - Video validation and deduplication")
        print("  - Batch processing with status tracking")
        print("  - File organization by type")
        print("  - Statistics and cleanup")
        
        print("\nNext Steps:")
        print("1. Add your actual video files to the data directory")
        print("2. Run the transcription pipeline with file management")
        print("3. Use the file manager to organize and track your videos")
        
    except Exception as e:
        print(f"❌ Error in demonstration: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
