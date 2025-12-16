#!/usr/bin/env python3
"""
MongoDB client module for connecting to MongoDB Atlas.

This module provides a MongoDB connection interface using pymongo.
"""

import os
from typing import Optional, Dict, Any, List
from pathlib import Path

from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from pymongo.database import Database
from pymongo.collection import Collection
from dotenv import load_dotenv


class MongoDBClient:
    """
    MongoDB client wrapper for connecting to MongoDB Atlas.
    
    Handles connection management and provides basic CRUD operations.
    """
    
    def __init__(self, database_name: str = "multimodal_transcription"):
        """
        Initialize the MongoDB client.
        
        Args:
            database_name: Name of the database to use
        """
        # Load environment variables from .env file (check project root)
        # Find the project root by looking for .env file
        current_dir = Path(__file__).parent
        for parent in [current_dir] + list(current_dir.parents):
            env_path = parent / ".env"
            if env_path.exists():
                load_dotenv(env_path)
                break
        else:
            # Try default load_dotenv behavior
            load_dotenv()
        
        # Check for MongoDB URI in multiple environment variable names
        # MONGO_CONNECTION_STRING is used in production (Docker/ECS)
        # MONGO_URI_SECRET is used for local development
        self.uri = os.getenv("MONGO_CONNECTION_STRING") or os.getenv("MONGO_URI_SECRET")
        if not self.uri:
            raise ValueError("MONGO_URI_SECRET environment variable is not set")
        
        self.database_name = database_name
        self._client: Optional[MongoClient] = None
        self._db: Optional[Database] = None
    
    def connect(self) -> bool:
        """
        Establish connection to MongoDB.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            self._client = MongoClient(self.uri, server_api=ServerApi('1'))
            # Ping to confirm connection
            self._client.admin.command('ping')
            self._db = self._client[self.database_name]
            print(f"✅ Successfully connected to MongoDB database: {self.database_name}")
            return True
        except Exception as e:
            print(f"❌ Failed to connect to MongoDB: {e}")
            return False
    
    def disconnect(self):
        """Close the MongoDB connection."""
        if self._client:
            self._client.close()
            self._client = None
            self._db = None
            print("🔌 Disconnected from MongoDB")
    
    def get_collection(self, collection_name: str) -> Collection:
        """
        Get a collection from the database.
        
        Args:
            collection_name: Name of the collection
            
        Returns:
            Collection object
        """
        if not self._db:
            raise RuntimeError("Not connected to database. Call connect() first.")
        return self._db[collection_name]
    
    # ==================== CRUD Operations ====================
    
    def insert_one(self, collection_name: str, document: Dict[str, Any]) -> str:
        """
        Insert a single document into a collection.
        
        Args:
            collection_name: Name of the collection
            document: Document to insert
            
        Returns:
            Inserted document ID as string
        """
        collection = self.get_collection(collection_name)
        result = collection.insert_one(document)
        return str(result.inserted_id)
    
    def insert_many(self, collection_name: str, documents: List[Dict[str, Any]]) -> List[str]:
        """
        Insert multiple documents into a collection.
        
        Args:
            collection_name: Name of the collection
            documents: List of documents to insert
            
        Returns:
            List of inserted document IDs as strings
        """
        collection = self.get_collection(collection_name)
        result = collection.insert_many(documents)
        return [str(id) for id in result.inserted_ids]
    
    def find_one(self, collection_name: str, query: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Find a single document matching the query.
        
        Args:
            collection_name: Name of the collection
            query: Query filter
            
        Returns:
            Matching document or None
        """
        collection = self.get_collection(collection_name)
        return collection.find_one(query)
    
    def find_many(self, collection_name: str, query: Dict[str, Any] = None, 
                  limit: int = 0) -> List[Dict[str, Any]]:
        """
        Find multiple documents matching the query.
        
        Args:
            collection_name: Name of the collection
            query: Query filter (empty dict for all documents)
            limit: Maximum number of documents to return (0 = no limit)
            
        Returns:
            List of matching documents
        """
        collection = self.get_collection(collection_name)
        query = query or {}
        cursor = collection.find(query)
        if limit > 0:
            cursor = cursor.limit(limit)
        return list(cursor)
    
    def update_one(self, collection_name: str, query: Dict[str, Any], 
                   update: Dict[str, Any], upsert: bool = False) -> int:
        """
        Update a single document matching the query.
        
        Args:
            collection_name: Name of the collection
            query: Query filter
            update: Update operations (use $set, $inc, etc.)
            upsert: If True, insert document if not found
            
        Returns:
            Number of documents modified
        """
        collection = self.get_collection(collection_name)
        result = collection.update_one(query, update, upsert=upsert)
        return result.modified_count
    
    def delete_one(self, collection_name: str, query: Dict[str, Any]) -> int:
        """
        Delete a single document matching the query.
        
        Args:
            collection_name: Name of the collection
            query: Query filter
            
        Returns:
            Number of documents deleted
        """
        collection = self.get_collection(collection_name)
        result = collection.delete_one(query)
        return result.deleted_count
    
    def delete_many(self, collection_name: str, query: Dict[str, Any]) -> int:
        """
        Delete multiple documents matching the query.
        
        Args:
            collection_name: Name of the collection
            query: Query filter
            
        Returns:
            Number of documents deleted
        """
        collection = self.get_collection(collection_name)
        result = collection.delete_many(query)
        return result.deleted_count
    
    def count_documents(self, collection_name: str, query: Dict[str, Any] = None) -> int:
        """
        Count documents matching the query.
        
        Args:
            collection_name: Name of the collection
            query: Query filter (empty dict for all documents)
            
        Returns:
            Number of matching documents
        """
        collection = self.get_collection(collection_name)
        query = query or {}
        return collection.count_documents(query)
    
    def list_collections(self) -> List[str]:
        """
        List all collections in the database.
        
        Returns:
            List of collection names
        """
        if not self._db:
            raise RuntimeError("Not connected to database. Call connect() first.")
        return self._db.list_collection_names()
    
    # ==================== Context Manager ====================
    
    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()
        return False


# Convenience function for quick connection test
def test_connection() -> bool:
    """
    Test MongoDB connection using environment variables.
    
    Returns:
        True if connection successful, False otherwise
    """
    try:
        with MongoDBClient() as client:
            return True
    except Exception as e:
        print(f"Connection test failed: {e}")
        return False


if __name__ == "__main__":
    # Quick connection test when run directly
    test_connection()

