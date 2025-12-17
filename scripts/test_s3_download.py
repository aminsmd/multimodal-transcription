#!/usr/bin/env python3
"""
Test script for S3 video download functionality.

This script tests downloading videos from S3 using the video paths
returned from the API.
"""

import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from api.video_fetcher import VideoFetcher
# Import S3 utils directly to avoid dependency issues
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src" / "utils"))
from s3_utils import get_s3_bucket_path, construct_s3_url, download_video_from_s3


def test_s3_download():
    """Test S3 video download."""
    print("=" * 70)
    print("Testing S3 Video Download")
    print("=" * 70)
    
    # Check for S3_BUCKET_PATH environment variable
    try:
        s3_bucket_name = get_s3_bucket_path()
        print(f"\n📦 S3 Source Bucket: {s3_bucket_name}")
    except ValueError as e:
        print(f"\n❌ Error: {e}")
        print("Please set S3_BUCKET_PATH environment variable")
        print("Example: export S3_BUCKET_PATH='bci-prod-upload'")
        return False
    
    # Fetch videos from API
    print("\n🔄 Fetching videos from API...")
    fetcher = VideoFetcher()
    result = fetcher.fetch_videos()
    
    if not result['success']:
        print(f"❌ Failed to fetch videos: {result.get('error')}")
        return False
    
    videos = result['videos']
    if not videos:
        print("⚠️  No videos found to test")
        return False
    
    print(f"✅ Found {len(videos)} videos")
    
    # Test with first video only (to avoid downloading too many)
    test_video = videos[0]
    
    if isinstance(test_video, dict):
        video_id = test_video.get('id', 'unknown')
        video_path = test_video.get('path', '')
    else:
        video_id = 'unknown'
        video_path = str(test_video)
    
    print(f"\n📹 Testing with video:")
    print(f"   ID: {video_id}")
    print(f"   Path: {video_path}")
    
    # Construct S3 URL
    s3_url = construct_s3_url(s3_bucket_name, video_path)
    print(f"\n🔗 S3 URL: {s3_url}")
    
    # Test download (just check if file exists, don't download full file)
    print(f"\n🔄 Testing S3 access...")
    print("   (This will attempt to download the video file)")
    
    try:
        # Download to a temporary location
        local_path = f"/tmp/test_video_{video_id}.mp4"
        
        downloaded_path, success = download_video_from_s3(
            s3_url,
            local_path=local_path,
            region_name="us-east-1"  # bci-prod-upload is in us-east-1
        )
        
        if success:
            # Check file size
            file_size = os.path.getsize(downloaded_path)
            file_size_mb = file_size / (1024 * 1024)
            
            print(f"\n✅ Successfully downloaded video!")
            print(f"   Local path: {downloaded_path}")
            print(f"   File size: {file_size_mb:.2f} MB ({file_size:,} bytes)")
            
            # Clean up
            try:
                os.remove(downloaded_path)
                print(f"   🧹 Cleaned up test file")
            except Exception as e:
                print(f"   ⚠️  Could not clean up: {e}")
            
            return True
        else:
            print(f"\n❌ Failed to download video")
            return False
            
    except Exception as e:
        print(f"\n❌ Error during download: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main function."""
    try:
        success = test_s3_download()
        return 0 if success else 1
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())

