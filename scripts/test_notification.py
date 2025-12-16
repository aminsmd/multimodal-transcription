#!/usr/bin/env python3
"""
Test script for the notification client.

This script tests the notification functionality by sending test requests
to the API endpoint with different status values.
"""

import sys
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from api.notification_client import NotificationClient, TranscriptionStatus


def test_completed_notification():
    """Test sending a 'Completed' status notification."""
    print("=" * 60)
    print("Test 1: Sending 'Completed' status notification")
    print("=" * 60)
    
    client = NotificationClient()
    video_id = "69302f4e1e218dd429c848a2"
    
    print(f"Video ID: {video_id}")
    print(f"Status: Completed")
    print(f"Endpoint: {client.endpoint_url}")
    print("\nSending notification...")
    
    result = client.notify_completion(video_id, TranscriptionStatus.COMPLETED)
    
    if result['success']:
        print("✅ Notification sent successfully!")
        print(f"Status Code: {result.get('status_code', 'N/A')}")
        print(f"Response: {result.get('response', {})}")
    else:
        print("❌ Notification failed!")
        print(f"Error: {result.get('error', 'Unknown error')}")
        if 'status_code' in result:
            print(f"Status Code: {result['status_code']}")
    
    return result['success']


def test_error_notification():
    """Test sending an 'Error' status notification."""
    print("\n" + "=" * 60)
    print("Test 2: Sending 'Error' status notification")
    print("=" * 60)
    
    client = NotificationClient()
    video_id = "693adfa7d4d2ee267628b20f"
    error_message = "Test error: Transcription processing failed"
    
    print(f"Video ID: {video_id}")
    print(f"Status: Error")
    print(f"Error Message: {error_message}")
    print(f"Endpoint: {client.endpoint_url}")
    print("\nSending notification...")
    
    result = client.notify_completion(
        video_id,
        TranscriptionStatus.ERROR,
        error_message
    )
    
    if result['success']:
        print("✅ Notification sent successfully!")
        print(f"Status Code: {result.get('status_code', 'N/A')}")
        print(f"Response: {result.get('response', {})}")
    else:
        print("❌ Notification failed!")
        print(f"Error: {result.get('error', 'Unknown error')}")
        if 'status_code' in result:
            print(f"Status Code: {result['status_code']}")
    
    return result['success']


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("Notification Client Test Suite")
    print("=" * 60)
    
    results = []
    
    # Run tests
    try:
        results.append(("Completed Notification", test_completed_notification()))
        results.append(("Error Notification", test_error_notification()))
    except KeyboardInterrupt:
        print("\n\n⚠️  Tests interrupted by user")
        return 1
    except Exception as e:
        print(f"\n\n❌ Unexpected error during testing: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1
    
    # Print summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    for test_name, success in results:
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"{test_name}: {status}")
    
    all_passed = all(result[1] for result in results)
    
    if all_passed:
        print("\n✅ All main tests passed!")
        return 0
    else:
        print("\n❌ Some tests failed. Check the output above for details.")
        return 1


if __name__ == "__main__":
    exit(main())

