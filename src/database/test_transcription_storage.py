#!/usr/bin/env python3
"""
Test script for MongoDB transcription storage.

This script tests saving and retrieving transcription results from MongoDB
using existing pipeline result files.
"""

import json
from pathlib import Path
from transcription_storage import TranscriptionStorage, load_pipeline_result_from_file


def test_transcription_storage():
    """Test transcription storage operations with a real pipeline result."""
    
    print("=" * 60)
    print("MongoDB Transcription Storage Test")
    print("=" * 60)
    
    # Find an existing pipeline result file
    outputs_dir = Path(__file__).parent.parent.parent / "outputs" / "pipeline_runs"
    
    # Look for a pipeline results file
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
    
    # Get transcript entry count
    full_transcript = pipeline_result.get("full_transcript", {})
    entries = full_transcript.get("transcript", [])
    print(f"📝 Transcript entries: {len(entries)}")
    
    # Connect and test
    with TranscriptionStorage() as storage:
        
        # ==================== SAVE ====================
        print("\n💾 Testing SAVE operation...")
        
        # First, clean up any existing test data
        storage.delete_transcription(video_id)
        
        # Save the transcription result
        doc_id = storage.save_transcription_result(pipeline_result)
        print(f"   ✅ Saved with document ID: {doc_id}")
        
        # ==================== READ ====================
        print("\n🔍 Testing READ operations...")
        
        # Get by video ID
        retrieved = storage.get_transcription_by_video_id(video_id)
        if retrieved:
            print(f"   ✅ Retrieved transcription for video: {retrieved['video_id']}")
            print(f"      - Processing date: {retrieved.get('processing_date', 'N/A')}")
            print(f"      - Chunk duration: {retrieved.get('chunk_duration', 'N/A')}s")
            
            # Check transcript entries
            ret_entries = retrieved.get("full_transcript", {}).get("transcript", [])
            print(f"      - Transcript entries: {len(ret_entries)}")
        else:
            print("   ❌ Failed to retrieve transcription")
            return False
        
        # Get by MongoDB ID
        retrieved_by_id = storage.get_transcription_by_id(doc_id)
        if retrieved_by_id:
            print(f"   ✅ Retrieved by MongoDB ID: {doc_id[:12]}...")
        
        # ==================== LIST ====================
        print("\n📋 Testing LIST operation...")
        
        transcriptions = storage.list_transcriptions(limit=5)
        print(f"   ✅ Found {len(transcriptions)} transcription(s)")
        for t in transcriptions:
            print(f"      - {t.get('video_id', 'N/A')}: {t.get('entry_count', 0)} entries")
        
        # ==================== SEARCH ====================
        print("\n🔎 Testing SEARCH operations...")
        
        # Search for teacher utterances
        teacher_entries = storage.search_transcript_entries(
            video_id, 
            speaker="teacher",
            entry_type="utterance"
        )
        print(f"   ✅ Found {len(teacher_entries)} teacher utterances")
        
        # Show first few
        if teacher_entries:
            print("   📢 Sample teacher utterances:")
            for entry in teacher_entries[:3]:
                text = entry.get("spoken_text", "")[:50]
                time = entry.get("absolute_timestamp", "??:??")
                print(f"      [{time}] {text}...")
        
        # Search for events
        events = storage.search_transcript_entries(video_id, entry_type="event")
        print(f"   ✅ Found {len(events)} events")
        
        # ==================== STATS ====================
        print("\n📊 Storage Statistics:")
        stats = storage.get_stats()
        print(f"   - Total transcriptions: {stats['total_transcriptions']}")
        print(f"   - Total separate entries: {stats['total_entries']}")
        print(f"   - Collections: {stats['collections']}")
        
        # ==================== CLEANUP ====================
        print("\n🧹 Cleaning up test data...")
        
        deleted = storage.delete_transcription(video_id)
        if deleted:
            print(f"   ✅ Deleted transcription for video: {video_id}")
        else:
            print(f"   ⚠️  No transcription found to delete")
        
        print("\n" + "=" * 60)
        print("✅ All transcription storage operations completed successfully!")
        print("=" * 60)
        
        return True


if __name__ == "__main__":
    success = test_transcription_storage()
    exit(0 if success else 1)

