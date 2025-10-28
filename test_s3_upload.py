#!/usr/bin/env python3
"""
Test S3 upload and basic functionality without requiring API key.
This tests the S3 setup and basic pipeline functionality.
"""

import boto3
import os
from pathlib import Path

def test_s3_setup():
    """Test S3 bucket access and upload functionality."""
    
    print("🧪 Testing S3 Setup")
    print("=" * 30)
    
    # S3 configuration
    s3_bucket = "multimodal-transcription-videos-1761690600"
    
    try:
        # Initialize S3 client
        s3_client = boto3.client('s3', region_name='us-east-2')
        
        # Test bucket access
        print(f"📦 Testing access to bucket: {s3_bucket}")
        response = s3_client.head_bucket(Bucket=s3_bucket)
        print("✅ Bucket access successful")
        
        # List existing files
        print(f"\n📋 Files in bucket:")
        response = s3_client.list_objects_v2(Bucket=s3_bucket, Prefix="test-videos/")
        if 'Contents' in response:
            for obj in response['Contents']:
                print(f"   📄 {obj['Key']} ({obj['Size']} bytes)")
        else:
            print("   No files found")
        
        # Test creating a test file
        print(f"\n📝 Creating test file...")
        test_content = "This is a test file for deployed pipeline testing"
        s3_client.put_object(
            Bucket=s3_bucket,
            Key="deployed-test-outputs/test-file.txt",
            Body=test_content.encode('utf-8')
        )
        print("✅ Test file created successfully")
        
        # List output directory
        print(f"\n📋 Files in output directory:")
        response = s3_client.list_objects_v2(Bucket=s3_bucket, Prefix="deployed-test-outputs/")
        if 'Contents' in response:
            for obj in response['Contents']:
                print(f"   📄 {obj['Key']} ({obj['Size']} bytes)")
        else:
            print("   No files found")
        
        print(f"\n✅ S3 setup test completed successfully!")
        print(f"🎯 Ready for deployed testing!")
        print(f"📁 S3 Bucket: s3://{s3_bucket}")
        print(f"📁 Test Video: s3://{s3_bucket}/test-videos/Adam_2024-03-03_6_32_PM.mp4")
        print(f"📁 Output Dir: s3://{s3_bucket}/deployed-test-outputs/")
        
        return True
        
    except Exception as e:
        print(f"❌ S3 setup test failed: {str(e)}")
        return False

def test_pipeline_imports():
    """Test that pipeline modules can be imported."""
    
    print(f"\n🧪 Testing Pipeline Imports")
    print("=" * 30)
    
    try:
        # Add src to path
        import sys
        sys.path.insert(0, str(Path(__file__).parent / "src"))
        
        # Test imports
        from transcription_pipeline import TranscriptionPipeline
        from models import TranscriptionConfig
        print("✅ Pipeline imports successful")
        
        # Test pipeline initialization
        pipeline = TranscriptionPipeline("test_outputs")
        print("✅ Pipeline initialization successful")
        
        return True
        
    except Exception as e:
        print(f"❌ Pipeline import test failed: {str(e)}")
        return False

def main():
    """Run all tests."""
    
    print("🚀 Deployed Code Testing Setup")
    print("=" * 40)
    
    # Test S3 setup
    s3_ok = test_s3_setup()
    
    # Test pipeline imports
    pipeline_ok = test_pipeline_imports()
    
    print(f"\n📊 Test Results:")
    print(f"   S3 Setup: {'✅ PASS' if s3_ok else '❌ FAIL'}")
    print(f"   Pipeline: {'✅ PASS' if pipeline_ok else '❌ FAIL'}")
    
    if s3_ok and pipeline_ok:
        print(f"\n🎉 All tests passed! Ready for deployed testing.")
        print(f"\nNext steps:")
        print(f"1. Set GOOGLE_API_KEY environment variable")
        print(f"2. Run: python test_deployed_s3_storage.py")
        print(f"3. Or trigger GitHub Actions workflow manually")
        return 0
    else:
        print(f"\n❌ Some tests failed. Please fix issues before proceeding.")
        return 1

if __name__ == "__main__":
    exit(main())
