#!/usr/bin/env python3
"""
MongoDB storage for transcription results.

This module provides functions to save and retrieve transcription results from MongoDB.
"""

import json
from datetime import datetime
from typing import Optional, Dict, Any, List
from pathlib import Path
from bson import ObjectId

try:
    from .mongodb_client import MongoDBClient
except ImportError:
    from mongodb_client import MongoDBClient


class TranscriptionStorage:
    """
    Handles storing and retrieving transcription results in MongoDB.
    """
    
    # Collection names
    TRANSCRIPTIONS_COLLECTION = "transcriptions"
    TRANSCRIPT_ENTRIES_COLLECTION = "transcript_entries"
    
    def __init__(self, database_name: str = "multimodal_transcription"):
        """
        Initialize the transcription storage.
        
        Args:
            database_name: Name of the MongoDB database
        """
        self.client = MongoDBClient(database_name=database_name)
        self._connected = False
    
    def connect(self) -> bool:
        """Connect to MongoDB."""
        self._connected = self.client.connect()
        return self._connected
    
    def disconnect(self):
        """Disconnect from MongoDB."""
        self.client.disconnect()
        self._connected = False
    
    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()
        return False
    
    def save_transcription_result(self, pipeline_result: Dict[str, Any]) -> str:
        """
        Save a complete transcription result to MongoDB.
        
        This stores the main transcription document and optionally 
        the individual transcript entries in a separate collection for querying.
        
        Args:
            pipeline_result: The pipeline results dictionary
            
        Returns:
            The MongoDB document ID as string
        """
        if not self._connected:
            raise RuntimeError("Not connected to MongoDB. Call connect() first.")
        
        # Add metadata
        doc = {
            **pipeline_result,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }
        
        # Convert ObjectId to string if present (for serialization)
        if "_id" in doc:
            del doc["_id"]
        
        # Insert the main document
        doc_id = self.client.insert_one(self.TRANSCRIPTIONS_COLLECTION, doc)
        
        print(f"✅ Saved transcription result with ID: {doc_id}")
        return doc_id
    
    def save_transcript_entries_separately(self, video_id: str, 
                                            transcription_id: str,
                                            entries: List[Dict]) -> int:
        """
        Save individual transcript entries to a separate collection.
        
        This allows for more efficient querying of individual entries.
        
        Args:
            video_id: The video ID
            transcription_id: The parent transcription document ID
            entries: List of transcript entries
            
        Returns:
            Number of entries saved
        """
        if not entries:
            return 0
        
        # Add references to each entry
        docs = []
        for i, entry in enumerate(entries):
            doc = {
                **entry,
                "video_id": video_id,
                "transcription_id": transcription_id,
                "entry_index": i,
                "created_at": datetime.now().isoformat()
            }
            docs.append(doc)
        
        ids = self.client.insert_many(self.TRANSCRIPT_ENTRIES_COLLECTION, docs)
        print(f"✅ Saved {len(ids)} transcript entries")
        return len(ids)
    
    def get_transcription_by_id(self, transcription_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a transcription result by its MongoDB ID.
        
        Args:
            transcription_id: The MongoDB document ID
            
        Returns:
            The transcription document or None
        """
        doc = self.client.find_one(
            self.TRANSCRIPTIONS_COLLECTION, 
            {"_id": ObjectId(transcription_id)}
        )
        if doc:
            doc["_id"] = str(doc["_id"])
        return doc
    
    def get_transcription_by_video_id(self, video_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a transcription result by video ID.
        
        Args:
            video_id: The video ID
            
        Returns:
            The transcription document or None
        """
        doc = self.client.find_one(
            self.TRANSCRIPTIONS_COLLECTION, 
            {"video_id": video_id}
        )
        if doc:
            doc["_id"] = str(doc["_id"])
        return doc
    
    def list_transcriptions(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        List recent transcription results.
        
        Args:
            limit: Maximum number of results to return
            
        Returns:
            List of transcription documents (without full transcript data)
        """
        docs = self.client.find_many(
            self.TRANSCRIPTIONS_COLLECTION,
            {},
            limit=limit
        )
        
        # Convert ObjectId to string and remove large fields for listing
        results = []
        for doc in docs:
            summary = {
                "_id": str(doc["_id"]),
                "video_id": doc.get("video_id"),
                "original_input": doc.get("original_input"),
                "processing_date": doc.get("processing_date"),
                "created_at": doc.get("created_at"),
                "chunk_duration": doc.get("chunk_duration"),
                "max_workers": doc.get("max_workers"),
            }
            
            # Add entry count if available
            if "full_transcript" in doc and "transcript" in doc["full_transcript"]:
                summary["entry_count"] = len(doc["full_transcript"]["transcript"])
            
            results.append(summary)
        
        return results
    
    def search_transcript_entries(self, video_id: str, 
                                   speaker: Optional[str] = None,
                                   text_contains: Optional[str] = None,
                                   entry_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Search transcript entries within a transcription.
        
        Args:
            video_id: The video ID to search in
            speaker: Filter by speaker name
            text_contains: Filter by text content (regex)
            entry_type: Filter by entry type (utterance, event)
            
        Returns:
            List of matching transcript entries
        """
        # First get the transcription
        doc = self.get_transcription_by_video_id(video_id)
        if not doc:
            return []
        
        # Get all entries from full_transcript
        entries = doc.get("full_transcript", {}).get("transcript", [])
        
        # Filter entries
        results = []
        for entry in entries:
            # Filter by speaker
            if speaker and entry.get("speaker", "").lower() != speaker.lower():
                continue
            
            # Filter by text content
            if text_contains:
                text = entry.get("spoken_text", "") or entry.get("event_description", "")
                if text_contains.lower() not in text.lower():
                    continue
            
            # Filter by type
            if entry_type and entry.get("type") != entry_type:
                continue
            
            results.append(entry)
        
        return results
    
    def delete_transcription(self, video_id: str) -> bool:
        """
        Delete a transcription by video ID.
        
        Args:
            video_id: The video ID
            
        Returns:
            True if deleted, False if not found
        """
        deleted = self.client.delete_one(
            self.TRANSCRIPTIONS_COLLECTION,
            {"video_id": video_id}
        )
        
        # Also delete any separate entries
        self.client.delete_many(
            self.TRANSCRIPT_ENTRIES_COLLECTION,
            {"video_id": video_id}
        )
        
        return deleted > 0
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get storage statistics.
        
        Returns:
            Dictionary with stats
        """
        return {
            "total_transcriptions": self.client.count_documents(self.TRANSCRIPTIONS_COLLECTION),
            "total_entries": self.client.count_documents(self.TRANSCRIPT_ENTRIES_COLLECTION),
            "collections": self.client.list_collections()
        }


def load_pipeline_result_from_file(file_path: str) -> Dict[str, Any]:
    """
    Load a pipeline result from a JSON file.
    
    Args:
        file_path: Path to the JSON file
        
    Returns:
        The pipeline result dictionary
    """
    with open(file_path, 'r') as f:
        return json.load(f)

