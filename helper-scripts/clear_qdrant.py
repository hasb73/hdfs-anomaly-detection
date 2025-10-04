#!/usr/bin/env python3
"""
Qdrant Collection Manager - Clear all embeddings
"""
from qdrant_client import QdrantClient
import sys

def clear_qdrant_collections():
    """Clear all collections in Qdrant"""
    print("🗑️  QDRANT COLLECTION CLEANER")
    print("=" * 50)
    
    try:
        # Connect to Qdrant
        client = QdrantClient(host="localhost", port=6333)
        
        # Get all collections
        collections = client.get_collections()
        collection_names = [col.name for col in collections.collections]
        
        if not collection_names:
            print("📭 No collections found - Qdrant is already empty!")
            return
        
        print(f"📋 Found collections: {collection_names}")
        
        # Ask for confirmation
        response = input(f"\n⚠️  Are you sure you want to DELETE ALL collections? (yes/no): ")
        if response.lower() not in ['yes', 'y']:
            print("❌ Operation cancelled")
            return
        
        # Delete each collection
        for collection_name in collection_names:
            try:
                print(f"🗑️  Deleting collection: {collection_name}")
                client.delete_collection(collection_name)
                print(f"✅ Deleted: {collection_name}")
            except Exception as e:
                print(f"❌ Failed to delete {collection_name}: {e}")
        
        print(f"\n🎉 Successfully cleared all collections!")
        
        # Verify collections are gone
        remaining = client.get_collections()
        if remaining.collections:
            print(f"⚠️  Warning: {len(remaining.collections)} collections still remain")
        else:
            print(f"✅ Confirmed: All collections have been removed")
            
    except Exception as e:
        print(f"❌ Error connecting to Qdrant: {e}")
        print(f"💡 Make sure Qdrant is running on localhost:6333")
        sys.exit(1)

def clear_specific_collection(collection_name="logs_embeddings"):
    """Clear a specific collection"""
    print(f"🗑️  CLEARING COLLECTION: {collection_name}")
    print("=" * 50)
    
    try:
        client = QdrantClient(host="localhost", port=6333)
        
        # Check if collection exists
        collections = client.get_collections()
        collection_names = [col.name for col in collections.collections]
        
        if collection_name not in collection_names:
            print(f"⚠️  Collection '{collection_name}' not found!")
            print(f"📋 Available collections: {collection_names}")
            return
        
        # Get collection info
        info = client.get_collection(collection_name)
        point_count = info.points_count
        
        print(f"📊 Collection: {collection_name}")
        print(f"📈 Points to delete: {point_count}")
        
        if point_count == 0:
            print("📭 Collection is already empty!")
            return
        
        # Ask for confirmation
        response = input(f"\n⚠️  Delete {point_count} points from '{collection_name}'? (yes/no): ")
        if response.lower() not in ['yes', 'y']:
            print("❌ Operation cancelled")
            return
        
        # Delete the collection (faster than deleting individual points)
        client.delete_collection(collection_name)
        print(f"✅ Collection '{collection_name}' deleted successfully!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    print("🔧 Qdrant Collection Manager")
    print("1. Clear all collections")
    print("2. Clear specific collection (logs_embeddings)")
    print("3. Exit")
    
    choice = input("\nSelect option (1-3): ").strip()
    
    if choice == "1":
        clear_qdrant_collections()
    elif choice == "2":
        clear_specific_collection()
    elif choice == "3":
        print("👋 Goodbye!")
    else:
        print("❌ Invalid choice")
