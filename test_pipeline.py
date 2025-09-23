#!/usr/bin/env python3
"""
Test script for the standalone transcription pipeline.

This script performs basic tests to ensure the pipeline is working correctly.
"""

import os
import sys
import tempfile
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from transcription_pipeline import TranscriptionPipeline

def test_pipeline_initialization():
    """Test pipeline initialization."""
    print("Testing pipeline initialization...")
    
    try:
        # Test with default output directory
        pipeline = TranscriptionPipeline()
        assert pipeline.base_dir.exists()
        assert pipeline.run_dir.exists()
        assert (pipeline.run_dir / "videos").exists()
        assert (pipeline.run_dir / "chunks").exists()
        assert (pipeline.run_dir / "transcripts").exists()
        print("✓ Pipeline initialization successful")
        return True
    except Exception as e:
        print(f"✗ Pipeline initialization failed: {str(e)}")
        return False

def test_pipeline_with_custom_directory():
    """Test pipeline with custom output directory."""
    print("Testing pipeline with custom directory...")
    
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            pipeline = TranscriptionPipeline(temp_dir)
            assert pipeline.base_dir == Path(temp_dir)
            assert pipeline.run_dir.exists()
            print("✓ Custom directory initialization successful")
            return True
    except Exception as e:
        print(f"✗ Custom directory initialization failed: {str(e)}")
        return False

def test_video_id_generation():
    """Test video ID generation."""
    print("Testing video ID generation...")
    
    try:
        pipeline = TranscriptionPipeline()
        
        # Test local video ID
        local_id = pipeline.get_video_id("/path/to/video.mp4")
        assert local_id == "video"
        print("✓ Local video ID generation successful")
        
        return True
    except Exception as e:
        print(f"✗ Video ID generation failed: {str(e)}")
        return False

def test_timestamp_parsing():
    """Test timestamp parsing functionality."""
    print("Testing timestamp parsing...")
    
    try:
        pipeline = TranscriptionPipeline()
        
        # Test various timestamp formats
        test_cases = [
            ("00:05", 5.0),
            ("01:30", 90.0),
            ("02:15.500", 135.5),
            ("00:01:30", 90.0),
            ("01:02:30.500", 3750.5)
        ]
        
        for timestamp_str, expected_seconds in test_cases:
            result = pipeline.parse_timestamp(timestamp_str)
            assert abs(result - expected_seconds) < 0.1, f"Expected {expected_seconds}, got {result}"
        
        print("✓ Timestamp parsing successful")
        return True
    except Exception as e:
        print(f"✗ Timestamp parsing failed: {str(e)}")
        return False

def test_timestamp_formatting():
    """Test timestamp formatting functionality."""
    print("Testing timestamp formatting...")
    
    try:
        pipeline = TranscriptionPipeline()
        
        # Test various timestamp formatting
        test_cases = [
            (5.0, "00:00:05.000"),
            (90.0, "00:01:30.000"),
            (135.5, "00:02:15.500"),
            (3750.5, "01:02:30.500")
        ]
        
        for seconds, expected_format in test_cases:
            result = pipeline.format_timestamp(seconds)
            assert result == expected_format, f"Expected {expected_format}, got {result}"
        
        print("✓ Timestamp formatting successful")
        return True
    except Exception as e:
        print(f"✗ Timestamp formatting failed: {str(e)}")
        return False

def test_prompt_generation():
    """Test prompt generation functionality."""
    print("Testing prompt generation...")
    
    try:
        pipeline = TranscriptionPipeline()
        
        # Test prompt generation
        prompt = pipeline.get_transcript_prompt(
            video_duration=300,
            chunk_start=0,
            chunk_end=300
        )
        
        assert isinstance(prompt, str)
        assert len(prompt) > 100  # Should be a substantial prompt
        assert "transcript" in prompt.lower()
        assert "json" in prompt.lower()
        
        print("✓ Prompt generation successful")
        return True
    except Exception as e:
        print(f"✗ Prompt generation failed: {str(e)}")
        return False

def test_transcript_entry_processing():
    """Test transcript entry processing."""
    print("Testing transcript entry processing...")
    
    try:
        pipeline = TranscriptionPipeline()
        
        # Test entry processing
        test_entry = {
            "type": "utterance",
            "start_time": "00:05",
            "end_time": "00:08",
            "speaker": "teacher",
            "spoken_text": "Hello class"
        }
        
        processed_entry = pipeline._process_transcript_entry(test_entry, 0, 0, 300)
        
        assert "absolute_start_time" in processed_entry
        assert "absolute_end_time" in processed_entry
        assert "absolute_start_timestamp" in processed_entry
        assert "absolute_end_timestamp" in processed_entry
        
        print("✓ Transcript entry processing successful")
        return True
    except Exception as e:
        print(f"✗ Transcript entry processing failed: {str(e)}")
        return False

def run_all_tests():
    """Run all tests."""
    print("=" * 60)
    print("STANDALONE TRANSCRIPTION PIPELINE TESTS")
    print("=" * 60)
    
    tests = [
        test_pipeline_initialization,
        test_pipeline_with_custom_directory,
        test_video_id_generation,
        test_timestamp_parsing,
        test_timestamp_formatting,
        test_prompt_generation,
        test_transcript_entry_processing
    ]
    
    passed = 0
    total = len(tests)
    
    for test_func in tests:
        try:
            if test_func():
                passed += 1
        except Exception as e:
            print(f"✗ Test {test_func.__name__} failed with exception: {str(e)}")
        print()
    
    print("=" * 60)
    print(f"TEST RESULTS: {passed}/{total} tests passed")
    print("=" * 60)
    
    if passed == total:
        print("🎉 All tests passed!")
        return 0
    else:
        print(f"❌ {total - passed} tests failed")
        return 1

def main():
    """Main test function."""
    # Check if we're in the right directory
    if not Path("src/transcription_pipeline.py").exists():
        print("Error: Please run this script from the standalone_transcription_pipeline directory")
        return 1
    
    return run_all_tests()

if __name__ == "__main__":
    exit(main())
