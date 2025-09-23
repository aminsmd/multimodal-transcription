#!/usr/bin/env python3
"""
Quick setup script for data directory structure.

This script helps you quickly set up a proper data directory structure
for organizing your videos and managing transcription pipeline outputs.
"""

import os
import sys
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from data_setup import DataManager


def main():
    """Quick setup for data directory."""
    print("🎬 Transcription Pipeline Data Setup")
    print("=" * 40)
    
    # Get base directory from user
    base_dir = input("Enter base directory for your data (default: 'data'): ").strip()
    if not base_dir:
        base_dir = "data"
    
    print(f"\nSetting up data directory: {base_dir}")
    
    try:
        # Initialize data manager
        dm = DataManager(base_dir)
        
        print("✅ Data directory structure created successfully!")
        
        # Show the structure
        print(f"\n📁 Directory Structure:")
        print(f"   {base_dir}/")
        print(f"   ├── 📁 videos/")
        print(f"   │   ├── 📁 raw/          # Put your original videos here")
        print(f"   │   └── 📁 processed/    # Processed videos will go here")
        print(f"   ├── 📁 transcripts/")
        print(f"   │   ├── 📁 full/         # Complete transcript JSON files")
        print(f"   │   ├── 📁 clean/       # Minimal transcript JSON files")
        print(f"   │   └── 📁 text/         # Human-readable text files")
        print(f"   ├── 📁 cache/            # Processing cache")
        print(f"   ├── 📁 metadata/         # Video metadata")
        print(f"   └── 📁 processed/        # Final outputs")
        
        # Ask if user wants to add videos
        add_videos = input("\nDo you want to add some videos now? (y/n): ").strip().lower()
        
        if add_videos == 'y':
            print("\n📹 Adding Videos")
            print("Enter video file paths (one per line, press Enter with empty line to finish):")
            
            video_paths = []
            while True:
                path = input("Video path: ").strip()
                if not path:
                    break
                video_paths.append(path)
            
            if video_paths:
                print(f"\nAdding {len(video_paths)} videos...")
                
                for video_path in video_paths:
                    if os.path.exists(video_path):
                        try:
                            video_info = dm.add_video(video_path, copy=True)
                            print(f"  ✅ Added: {video_info['video_id']} ({video_info['file_size_mb']} MB)")
                        except Exception as e:
                            print(f"  ❌ Error adding {video_path}: {e}")
                    else:
                        print(f"  ❌ File not found: {video_path}")
                
                # Show added videos
                videos = dm.list_videos()
                print(f"\n📋 Total videos in system: {len(videos)}")
                
                for video in videos:
                    print(f"  - {video['video_id']}: {video['filename']} ({video['file_size_mb']} MB)")
        
        # Show next steps
        print(f"\n🚀 Next Steps:")
        print(f"1. Add your video files to: {base_dir}/videos/raw/")
        print(f"2. Run the transcription pipeline:")
        print(f"   python src/transcription_pipeline.py --input /path/to/video.mp4")
        print(f"3. Or use the data management system:")
        print(f"   python examples/data_management_example.py")
        
        print(f"\n📚 For more information, see:")
        print(f"   - DATA_SETUP_GUIDE.md")
        print(f"   - examples/data_management_example.py")
        
        print(f"\n✅ Setup completed successfully!")
        
    except Exception as e:
        print(f"❌ Error during setup: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
