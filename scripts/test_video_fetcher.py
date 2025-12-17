#!/usr/bin/env python3
"""
Test script for the video fetcher API client.

This script tests fetching videos from the API endpoint to verify
connectivity and response format.
"""

import sys
import json
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from api.video_fetcher import VideoFetcher


def test_video_fetcher():
    """Test the video fetcher."""
    print("=" * 70)
    print("Testing Video Fetcher")
    print("=" * 70)
    
    # Initialize fetcher
    fetcher = VideoFetcher()
    print(f"\n📡 Endpoint URL: {fetcher.endpoint_url}")
    print(f"⏱️  Timeout: {fetcher.timeout} seconds")
    
    # Fetch videos
    print("\n🔄 Fetching videos from API...")
    result = fetcher.fetch_videos()
    
    # Display results
    print("\n" + "=" * 70)
    print("Results")
    print("=" * 70)
    
    if result['success']:
        print("✅ API call successful!")
        print(f"📊 Status Code: {result.get('status_code', 'N/A')}")
        print(f"📹 Number of videos: {len(result['videos'])}")
        
        if result['videos']:
            print("\n📋 Video List:")
            for i, video in enumerate(result['videos'][:5], 1):  # Show first 5
                if isinstance(video, dict):
                    video_id = video.get('id', 'N/A')
                    video_path = video.get('path', 'N/A')
                    print(f"  {i}. ID: {video_id}")
                    print(f"     Path: {video_path}")
                else:
                    print(f"  {i}. {video}")
            
            if len(result['videos']) > 5:
                print(f"  ... and {len(result['videos']) - 5} more videos")
            
            print("\n📄 Full Response (first video):")
            if result['videos']:
                print(json.dumps(result['videos'][0], indent=2))
        else:
            print("⚠️  No videos found in response")
            print("\n📄 Full Response:")
            print(json.dumps(result.get('response', {}), indent=2))
    else:
        print("❌ API call failed!")
        print(f"📋 Error: {result.get('error', 'Unknown error')}")
        print(f"📊 Status Code: {result.get('status_code', 'N/A')}")
        
        if result.get('response'):
            print("\n📄 Response:")
            try:
                print(json.dumps(result['response'], indent=2))
            except:
                print(result['response'])
        
        # Try to get more details from the raw response if available
        print("\n💡 Troubleshooting:")
        print("  - Check if the API endpoint is accessible")
        print("  - Verify if authentication is required")
        print("  - Check if the endpoint URL is correct")
        print("  - The API might be temporarily unavailable (500 error)")
    
    return result['success']


def main():
    """Main function."""
    try:
        success = test_video_fetcher()
        return 0 if success else 1
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())

