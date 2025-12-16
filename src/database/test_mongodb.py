#!/usr/bin/env python3
"""
Test script for MongoDB connection and CRUD operations.

Run this script to verify MongoDB connectivity and basic operations.
"""

from datetime import datetime
from mongodb_client import MongoDBClient


def test_mongodb_operations():
    """Test MongoDB connection and CRUD operations."""
    
    print("=" * 60)
    print("MongoDB Connection & CRUD Test")
    print("=" * 60)
    
    # Create client and connect
    client = MongoDBClient(database_name="test_db")
    
    if not client.connect():
        print("❌ Failed to connect. Exiting.")
        return False
    
    try:
        # Test collection name
        test_collection = "test_items"
        
        # ==================== CREATE ====================
        print("\n📝 Testing INSERT operations...")
        
        # Insert one document
        doc1 = {
            "name": "Test Item 1",
            "description": "This is a test document",
            "created_at": datetime.now().isoformat(),
            "tags": ["test", "example"],
            "count": 1
        }
        doc1_id = client.insert_one(test_collection, doc1)
        print(f"   ✅ Inserted document with ID: {doc1_id}")
        
        # Insert multiple documents
        docs = [
            {"name": "Test Item 2", "count": 2, "created_at": datetime.now().isoformat()},
            {"name": "Test Item 3", "count": 3, "created_at": datetime.now().isoformat()},
            {"name": "Test Item 4", "count": 4, "created_at": datetime.now().isoformat()},
        ]
        doc_ids = client.insert_many(test_collection, docs)
        print(f"   ✅ Inserted {len(doc_ids)} documents")
        
        # ==================== READ ====================
        print("\n🔍 Testing READ operations...")
        
        # Find one
        found_doc = client.find_one(test_collection, {"name": "Test Item 1"})
        if found_doc:
            print(f"   ✅ Found document: {found_doc['name']}")
        else:
            print("   ❌ Document not found")
        
        # Find many
        all_docs = client.find_many(test_collection)
        print(f"   ✅ Found {len(all_docs)} documents in collection")
        
        # Count documents
        count = client.count_documents(test_collection)
        print(f"   ✅ Total documents: {count}")
        
        # ==================== UPDATE ====================
        print("\n✏️ Testing UPDATE operations...")
        
        # Update one document
        updated = client.update_one(
            test_collection,
            {"name": "Test Item 1"},
            {"$set": {"description": "Updated description", "updated_at": datetime.now().isoformat()}}
        )
        print(f"   ✅ Updated {updated} document(s)")
        
        # Verify update
        updated_doc = client.find_one(test_collection, {"name": "Test Item 1"})
        if updated_doc and "updated_at" in updated_doc:
            print(f"   ✅ Verified update: description = '{updated_doc.get('description')}'")
        
        # ==================== DELETE ====================
        print("\n🗑️ Testing DELETE operations...")
        
        # Delete one
        deleted = client.delete_one(test_collection, {"name": "Test Item 2"})
        print(f"   ✅ Deleted {deleted} document(s)")
        
        # Verify deletion
        remaining = client.count_documents(test_collection)
        print(f"   ✅ Remaining documents: {remaining}")
        
        # ==================== CLEANUP ====================
        print("\n🧹 Cleaning up test data...")
        
        # Delete all test documents
        deleted_all = client.delete_many(test_collection, {})
        print(f"   ✅ Deleted {deleted_all} documents from test collection")
        
        # List collections
        collections = client.list_collections()
        print(f"   📋 Collections in database: {collections}")
        
        print("\n" + "=" * 60)
        print("✅ All MongoDB operations completed successfully!")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error during operations: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        client.disconnect()


if __name__ == "__main__":
    success = test_mongodb_operations()
    exit(0 if success else 1)

