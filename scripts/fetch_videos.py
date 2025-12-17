#!/usr/bin/env python3
"""
Script to fetch videos from the API and output them as JSON.

This script is used in GitHub Actions to get the list of videos,
which is then used to create separate ECS tasks for each video.
"""

import sys
import json
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from api.video_fetcher import VideoFetcher


def main():
    """Fetch videos and output as JSON."""
    fetcher = VideoFetcher()
    result = fetcher.fetch_videos()
    
    if not result['success']:
        print(f"Error: {result.get('error')}", file=sys.stderr)
        print(json.dumps({"videos": []}))
        return 1
    
    videos = result['videos']
    
    # Output as JSON for GitHub Actions to parse
    output = {
        "videos": videos,
        "count": len(videos),
        "status": "success"
    }
    
    print(json.dumps(output, indent=2))
    return 0


if __name__ == "__main__":
    exit(main())

