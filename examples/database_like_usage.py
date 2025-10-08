#!/usr/bin/env python3
"""
Example demonstrating database-like video management.

This example shows how to use the new VideoRepository and VideoEntity
classes to manage videos in a database-like manner, making the system
more compatible with future database deployments.
"""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from storage.video_repository import VideoRepository, VideoEntity
from models import TranscriptionConfig
from core.pipeline import TranscriptionPipeline


def demonstrate_video_repository():
    """Demonstrate video repository functionality."""
    print("=== Video Repository Demo ===")
    
    # Initialize repository
    repository = VideoRepository("data")
    
    # List all videos in repository
    print(f"\nVideos in repository: {repository.count()}")
    for video in repository.list_all():
        print(f"  - {video.video_id}: {video.filename} ({video.status})")
    
    # Get repository statistics
    stats = repository.get_repository_stats()
    print(f"\nRepository stats:")
    print(f"  Total videos: {stats['total_videos']}")
    print(f"  Total size: {stats['total_size_mb']:.2f} MB")
    print(f"  Status counts: {stats['status_counts']}")


def demonstrate_video_lookup():
    """Demonstrate video lookup by different methods."""
    print("\n=== Video Lookup Demo ===")
    
    repository = VideoRepository("data")
    
    # Example video IDs (you can replace with actual ones)
    example_video_id = "Adam_2024-03-03_6_32_PM"
    
    # Lookup by ID
    video = repository.find_by_id(example_video_id)
    if video:
        print(f"Found video by ID: {video.filename}")
        print(f"  Path: {video.file_path}")
        print(f"  Status: {video.status}")
        print(f"  Size: {video.get_file_size_mb():.2f} MB")
    else:
        print(f"Video not found by ID: {example_video_id}")
    
    # Search by filename
    search_results = repository.search("Adam", field="filename")
    print(f"\nSearch results for 'Adam': {len(search_results)} videos")
    for video in search_results:
        print(f"  - {video.filename} ({video.status})")


def demonstrate_pipeline_with_repository():
    """Demonstrate pipeline usage with repository."""
    print("\n=== Pipeline with Repository Demo ===")
    
    # Initialize pipeline with repository enabled
    pipeline = TranscriptionPipeline(
        base_dir="outputs",
        data_dir="data",
        enable_file_management=True,
        enable_video_repository=True
    )
    
    # Example: Process a video by ID instead of file path
    # This demonstrates the database-like interface
    video_id = "Adam_2024-03-03_6_32_PM"  # Replace with actual video ID
    
    try:
        # Create config using video ID (database-like lookup)
        config = TranscriptionConfig(
            video_input=video_id,  # This will be resolved by repository
            chunk_duration=300,
            max_workers=2
        )
        
        print(f"Processing video by ID: {video_id}")
        print(f"Repository enabled: {pipeline.video_repository is not None}")
        
        # The pipeline will automatically resolve the video ID to file path
        # This is similar to how a database would work - you query by ID
        # and get back the actual file path
        
        # Note: Uncomment the following lines to actually process the video
        # results = pipeline.process_video(config)
        # print(f"Processing completed: {results.video_id}")
        
    except Exception as e:
        print(f"Demo error (expected if video not found): {e}")


def demonstrate_database_compatibility():
    """Demonstrate database-compatible features."""
    print("\n=== Database Compatibility Demo ===")
    
    repository = VideoRepository("data")
    
    # Show how the system is structured for database compatibility
    print("Database-compatible features:")
    print("1. Video lookup by ID (like primary key)")
    print("2. Video lookup by hash (like unique constraint)")
    print("3. Video lookup by filename (like indexed field)")
    print("4. Status tracking (like database status field)")
    print("5. Metadata storage (like database columns)")
    
    # Example of how this would work with a real database
    print("\nExample database-like operations:")
    
    # Find by ID (primary key lookup)
    video = repository.find_by_id("example_id")
    if video:
        print(f"✓ Found video by ID: {video.video_id}")
    
    # Find by hash (unique constraint lookup)
    video = repository.find_by_hash("example_hash")
    if video:
        print(f"✓ Found video by hash: {video.file_hash}")
    
    # Update status (like database update)
    if video:
        video.update_status("processing", run_id="test_run")
        repository.save(video)
        print(f"✓ Updated video status to: {video.status}")
    
    # List with filters (like database query with WHERE clause)
    processed_videos = repository.list_all(status="transcribed")
    print(f"✓ Found {len(processed_videos)} processed videos")


def main():
    """Main demonstration function."""
    print("Database-like Video Management Demo")
    print("=" * 50)
    
    try:
        demonstrate_video_repository()
        demonstrate_video_lookup()
        demonstrate_pipeline_with_repository()
        demonstrate_database_compatibility()
        
        print("\n" + "=" * 50)
        print("Demo completed successfully!")
        print("\nKey benefits of the database-like interface:")
        print("1. Video lookup by ID instead of file paths")
        print("2. Automatic file resolution and validation")
        print("3. Status tracking and metadata management")
        print("4. Easy transition to real database (AWS RDS, etc.)")
        print("5. Consistent interface for video operations")
        
    except Exception as e:
        print(f"Demo error: {e}")
        print("This is expected if no videos are in the repository yet.")


if __name__ == "__main__":
    main()
