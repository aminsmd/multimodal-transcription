#!/usr/bin/env python3
"""
Test script to verify MongoDB integration with the pipeline.

This tests that the pipeline can save transcription results to MongoDB.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database import TranscriptionStorage, load_pipeline_result_from_file


def test_pipeline_mongodb_integration():
    """Test that pipeline results can be saved to MongoDB."""
    
    print("=" * 60)
    print("Pipeline MongoDB Integration Test")
    print("=" * 60)
    
    # Find an existing pipeline result file
    outputs_dir = Path(__file__).parent.parent.parent / "outputs" / "pipeline_runs"
    
    result_file = None
    for run_dir in sorted(outputs_dir.iterdir(), reverse=True):
        if run_dir.is_dir():
            for f in run_dir.iterdir():
                if f.name.endswith("_pipeline_results.json"):
                    result_file = f
                    break
        if result_file:
            break
    
    if not result_file:
        print("❌ No pipeline result files found. Run a transcription first.")
        return False
    
    print(f"\n📁 Using pipeline result: {result_file.name}")
    
    # Load the pipeline result
    pipeline_result = load_pipeline_result_from_file(str(result_file))
    video_id = pipeline_result.get("video_id", "unknown")
    
    print(f"📹 Video ID: {video_id}")
    
    # Simulate what the pipeline does
    print("\n🔄 Simulating pipeline MongoDB save...")
    
    with TranscriptionStorage(database_name="multimodal_transcription") as storage:
        # Clean up any existing test data first
        storage.delete_transcription(video_id)
        
        # Save like the pipeline does
        try:
            mongodb_doc_id = storage.save_transcription_result(pipeline_result)
            print(f"✅ Saved to MongoDB with ID: {mongodb_doc_id}")
        except Exception as e:
            print(f"❌ Failed to save to MongoDB: {e}")
            return False
        
        # Verify we can retrieve it
        retrieved = storage.get_transcription_by_video_id(video_id)
        if retrieved:
            print(f"✅ Retrieved from MongoDB: {retrieved['video_id']}")
            
            # Check some fields
            entries = retrieved.get("full_transcript", {}).get("transcript", [])
            print(f"   - Transcript entries: {len(entries)}")
            print(f"   - Processing date: {retrieved.get('processing_date', 'N/A')}")
            print(f"   - Created at: {retrieved.get('created_at', 'N/A')}")
        else:
            print("❌ Failed to retrieve from MongoDB")
            return False
        
        # Get stats
        stats = storage.get_stats()
        print(f"\n📊 MongoDB Stats:")
        print(f"   - Total transcriptions: {stats['total_transcriptions']}")
        
        # Clean up
        print("\n🧹 Cleaning up...")
        storage.delete_transcription(video_id)
        print("   ✅ Test data cleaned up")
    
    print("\n" + "=" * 60)
    print("✅ Pipeline MongoDB integration test passed!")
    print("=" * 60)
    print("\nYou can now use the pipeline with --enable-mongodb flag:")
    print("  python src/transcription_pipeline.py --input video.mp4 --enable-mongodb")
    
    return True


if __name__ == "__main__":
    success = test_pipeline_mongodb_integration()
    exit(0 if success else 1)

