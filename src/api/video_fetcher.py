#!/usr/bin/env python3
"""
API client for fetching videos that need to be transcribed.

This module handles GET requests to retrieve a list of videos
that need transcription processing.
"""

import requests
from typing import List, Dict, Any, Optional
import os


class VideoFetcher:
    """
    Client for fetching videos that need transcription from the API.
    """
    
    def __init__(self, endpoint_url: str = "https://886hed58x9.execute-api.us-east-1.amazonaws.com/prod/api/v1/files/paths/toTranscribe"):
        """
        Initialize the video fetcher.
        
        Args:
            endpoint_url: The API endpoint URL for fetching videos
        """
        self.endpoint_url = endpoint_url
        self.timeout = 30  # 30 second timeout for requests
    
    def fetch_videos(self) -> Dict[str, Any]:
        """
        Fetch the list of videos that need to be transcribed.
        
        Returns:
            Dictionary with 'success' (bool), 'videos' (list), and 'error' (str, if any)
            
        Example:
            >>> fetcher = VideoFetcher()
            >>> result = fetcher.fetch_videos()
            >>> if result['success']:
            ...     for video in result['videos']:
            ...         print(video)
        """
        try:
            # Send GET request
            response = requests.get(
                self.endpoint_url,
                timeout=self.timeout,
                headers={
                    'Content-Type': 'application/json'
                }
            )
            
            # Check if request was successful
            response.raise_for_status()
            
            # Try to parse JSON response
            try:
                response_data = response.json()
            except ValueError:
                # If response is not JSON, return text
                response_data = {'data': response.text}
            
            # Extract videos from response
            # Expected format: {"paths": [{"id": "...", "path": "..."}, ...]}
            videos = []
            if isinstance(response_data, list):
                videos = response_data
            elif isinstance(response_data, dict):
                # Try common keys (prioritize 'paths' as that's the expected format)
                if 'paths' in response_data:
                    videos = response_data['paths']
                elif 'videos' in response_data:
                    videos = response_data['videos']
                elif 'data' in response_data:
                    videos = response_data['data']
                elif 'files' in response_data:
                    videos = response_data['files']
                else:
                    # If it's a dict with string keys, assume it's a single video or list
                    videos = [response_data] if response_data else []
            
            return {
                'success': True,
                'videos': videos,
                'response': response_data,
                'status_code': response.status_code,
                'error': None
            }
            
        except requests.exceptions.Timeout:
            return {
                'success': False,
                'videos': [],
                'response': None,
                'error': f'Request timeout after {self.timeout} seconds'
            }
        except requests.exceptions.ConnectionError as e:
            return {
                'success': False,
                'videos': [],
                'response': None,
                'error': f'Connection error: {str(e)}'
            }
        except requests.exceptions.HTTPError as e:
            # Try to get error details from response
            error_msg = str(e)
            try:
                error_response = e.response.json()
                error_msg = error_response.get('message', error_msg)
            except (ValueError, AttributeError):
                pass
            
            return {
                'success': False,
                'videos': [],
                'response': None,
                'status_code': e.response.status_code if hasattr(e, 'response') else None,
                'error': f'HTTP error: {error_msg}'
            }
        except Exception as e:
            return {
                'success': False,
                'videos': [],
                'response': None,
                'error': f'Unexpected error: {str(e)}'
            }

