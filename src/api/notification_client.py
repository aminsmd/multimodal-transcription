#!/usr/bin/env python3
"""
Notification client for sending transcription completion status to external API.

This module handles POST requests to notify external services when transcription
is complete or has encountered an error.
"""

import requests
from typing import Optional, Dict, Any
from enum import Enum


class TranscriptionStatus(str, Enum):
    """Status values for transcription completion."""
    COMPLETED = "Completed"
    ERROR = "Error"


class NotificationClient:
    """
    Client for sending transcription completion notifications to external API.
    """
    
    def __init__(self, endpoint_url: str = "https://nv6ktiaxob.execute-api.us-east-1.amazonaws.com/stage/api/v1/files/aiEncoding-Complete"):
        """
        Initialize the notification client.
        
        Args:
            endpoint_url: The API endpoint URL for sending notifications
        """
        self.endpoint_url = endpoint_url
        self.timeout = 30  # 30 second timeout for requests
    
    def notify_completion(
        self,
        video_id: str,
        status: TranscriptionStatus = TranscriptionStatus.COMPLETED,
        error: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send a notification to the API endpoint about transcription completion.
        
        Args:
            video_id: The video ID to report status for
            status: Either 'Completed' or 'Error'
            error: Error message (required if status is 'Error', optional otherwise)
            
        Returns:
            Dictionary with 'success' (bool), 'response' (dict), and 'error' (str, if any)
            
        Example:
            >>> client = NotificationClient()
            >>> result = client.notify_completion("69302f4e1e218dd429c848a2", TranscriptionStatus.COMPLETED)
            >>> if result['success']:
            ...     print("Notification sent successfully")
        """
        # Validate inputs
        if not video_id:
            return {
                'success': False,
                'response': None,
                'error': 'video_id is required'
            }
        
        if status == TranscriptionStatus.ERROR and not error:
            return {
                'success': False,
                'response': None,
                'error': 'error message is required when status is "Error"'
            }
        
        # Prepare request body
        body = {
            'videoId': video_id,
            'status': status.value
        }
        
        # Only include error field if status is Error
        if status == TranscriptionStatus.ERROR and error:
            body['error'] = error
        
        try:
            # Send POST request
            response = requests.post(
                self.endpoint_url,
                json=body,
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
                response_data = {'message': response.text}
            
            return {
                'success': True,
                'response': response_data,
                'status_code': response.status_code,
                'error': None
            }
            
        except requests.exceptions.Timeout:
            return {
                'success': False,
                'response': None,
                'error': f'Request timeout after {self.timeout} seconds'
            }
        except requests.exceptions.ConnectionError as e:
            return {
                'success': False,
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
                'response': None,
                'status_code': e.response.status_code if hasattr(e, 'response') else None,
                'error': f'HTTP error: {error_msg}'
            }
        except Exception as e:
            return {
                'success': False,
                'response': None,
                'error': f'Unexpected error: {str(e)}'
            }
    
    def notify_success(self, video_id: str) -> Dict[str, Any]:
        """
        Convenience method to notify successful transcription completion.
        
        Args:
            video_id: The video ID that was successfully transcribed
            
        Returns:
            Dictionary with notification result
        """
        return self.notify_completion(video_id, TranscriptionStatus.COMPLETED)
    
    def notify_error(self, video_id: str, error_message: str) -> Dict[str, Any]:
        """
        Convenience method to notify transcription error.
        
        Args:
            video_id: The video ID that encountered an error
            error_message: Description of the error
            
        Returns:
            Dictionary with notification result
        """
        return self.notify_completion(video_id, TranscriptionStatus.ERROR, error_message)


