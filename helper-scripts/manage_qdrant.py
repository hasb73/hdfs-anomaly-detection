#!/usr/bin/env python3
"""
Qdrant Collection Manager
Manage Qdrant collections - create, delete, clear, backup operations
"""
import sys
import json
from datetime import datetime
from qdrant_client import QdrantClient
from qdrant_client.http import models as qm
from typing import List, Dict

# Configuration
QDRANT_HOST = "localhost"
QDRANT_PORT = 6333
COLLECTION = "logs_embeddings"
DIM = 384

def list_collections(qdrant_client: QdrantClient):
    """List all collections"""
    try:
        collections = qdrant_client.get_collections()
        print("Available Collections:")
        if not collections.collections:
            print("  No collections found")
            return
        
        for col in collections.collections:
            print(f"  - {col.name}")
            try:
                info = qdrant_client.get_collection(col.name)
                print(f"    Points: {info.points_count}")
                print(f"    Status: {info.status}")
            except Exception as e:
                print(f"    Error getting info: {e}")
        print("")
        
    except Exception as e:
        print(f"Error listing collections: {e}")

def create_collection(qdrant_client: QdrantClient, collection_name: str, dimension: int):
    """Create a new collection"""
    try:
        qdrant_client.create_collection(
            collection_name=collection_name,
            vectors_config=qm.VectorParams(size=dimension, distance=qm.Distance.COSINE)
        )
        print(f"Created collection: {collection_name}")
        
    except Exception as e:
        print(f"Error creating collection: {e}")

def delete_collection(qdrant_client: QdrantClient, collection_name: str):
    """Delete a collection"""
    try:
        confirm = input(f"Are you sure you want to delete collection '{collection_name}'? (yes/no): ")
        if confirm.lower() == 'yes':
            qdrant_client.delete_collection(collection_name)
            print(f"Deleted collection: {collection_name}")
        else:
            print("Operation cancelled")
            
    except Exception as e:
        print(f"Error deleting collection: {e}")

def clear_collection(qdrant_client: QdrantClient, collection_name: str):
    """Clear all points from a collection"""
    try:
        info = qdrant_client.get_collection(collection_name)
        point_count = info.points_count
        
        confirm = input(f"Are you sure you want to clear {point_count} points from '{collection_name}'? (yes/no): ")
        if confirm.lower() == 'yes':
            # Recreate collection to clear all points
            qdrant_client.recreate_collection(
                collection_name=collection_name,
                vectors_config=qm.VectorParams(size=info.config.params.vectors.size, 
                                              distance=info.config.params.vectors.distance)
            )
            print(f"Cleared collection: {collection_name}")
        else:
            print("Operation cancelled")
            
    except Exception as e:
        print(f"Error clearing collection: {e}")

def backup_collection(qdrant_client: QdrantClient, collection_name: str):
    """Backup collection data to JSON file"""
    try:
        print(f"Backing up collection: {collection_name}")
        
        # Get all points
        all_points = []
        next_page_offset = None
        
        while True:
            result = qdrant_client.scroll(
                collection_name=collection_name,
                limit=100,
                offset=next_page_offset,
                with_payload=True,
                with_vectors=True
            )
            
            points, next_page_offset = result
            
            if not points:
                break
            
            for point in points:
                point_data = {
                    'id': point.id,
                    'vector': point.vector,
                    'payload': point.payload
                }
                all_points.append(point_data)
            
            print(f"  Backed up {len(all_points)} points...")
            
            if next_page_offset is None:
                break
        
        # Save to file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{collection_name}_backup_{timestamp}.json"
        
        with open(filename, 'w') as f:
            json.dump({
                'collection_name': collection_name,
                'backup_timestamp': timestamp,
                'point_count': len(all_points),
                'points': all_points
            }, f, indent=2)
        
        print(f"Backup completed: {filename}")
        print(f"Total points backed up: {len(all_points)}")
        
    except Exception as e:
        print(f"Error backing up collection: {e}")

def restore_collection(qdrant_client: QdrantClient, backup_file: str):
    """Restore collection from backup file"""
    try:
        print(f"Restoring from backup: {backup_file}")
        
        with open(backup_file, 'r') as f:
            backup_data = json.load(f)
        
        collection_name = backup_data['collection_name']
        points_data = backup_data['points']
        
        print(f"Collection: {collection_name}")
        print(f"Points to restore: {len(points_data)}")
        
        confirm = input("Proceed with restore? (yes/no): ")
        if confirm.lower() != 'yes':
            print("Operation cancelled")
            return
        
        # Create points
        points = []
        for point_data in points_data:
            point = qm.PointStruct(
                id=point_data['id'],
                vector=point_data['vector'],
                payload=point_data['payload']
            )
            points.append(point)
        
        # Insert in batches
        batch_size = 100
        for i in range(0, len(points), batch_size):
            batch = points[i:i + batch_size]
            qdrant_client.upsert(
                collection_name=collection_name,
                points=batch,
                wait=True
            )
            print(f"  Restored {min(i + batch_size, len(points))} / {len(points)} points")
        
        print("Restore completed successfully")
        
    except Exception as e:
        print(f"Error restoring collection: {e}")

def get_collection_details(qdrant_client: QdrantClient, collection_name: str):
    """Get detailed information about a collection"""
    try:
        info = qdrant_client.get_collection(collection_name)
        
        print(f"Collection Details: {collection_name}")
        print(f"  Points count: {info.points_count}")
        print(f"  Vector size: {info.config.params.vectors.size}")
        print(f"  Distance metric: {info.config.params.vectors.distance}")
        print(f"  Status: {info.status}")
        
        if hasattr(info.config.params, 'shard_number'):
            print(f"  Shard number: {info.config.params.shard_number}")
        
        print("")
        
    except Exception as e:
        print(f"Error getting collection details: {e}")

def main():
    """Main function with command line interface"""
    print("Qdrant Collection Manager")
    print("========================")
    print("")
    
    # Initialize Qdrant client
    try:
        qdrant_client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
        print(f"Connected to Qdrant at {QDRANT_HOST}:{QDRANT_PORT}")
        print("")
    except Exception as e:
        print(f"Failed to connect to Qdrant: {e}")
        return
    
    while True:
        print("Options:")
        print("1. List all collections")
        print("2. Create new collection")
        print("3. Delete collection")
        print("4. Clear collection (remove all points)")
        print("5. Get collection details")
        print("6. Backup collection to file")
        print("7. Restore collection from backup")
        print("8. Exit")
        print("")
        
        choice = input("Enter your choice (1-8): ").strip()
        print("")
        
        if choice == "1":
            list_collections(qdrant_client)
            
        elif choice == "2":
            name = input("Enter collection name: ").strip()
            if name:
                try:
                    dim = input(f"Enter vector dimension (default {DIM}): ").strip()
                    dimension = int(dim) if dim else DIM
                    create_collection(qdrant_client, name, dimension)
                except ValueError:
                    create_collection(qdrant_client, name, DIM)
                    
        elif choice == "3":
            name = input("Enter collection name to delete: ").strip()
            if name:
                delete_collection(qdrant_client, name)
                
        elif choice == "4":
            name = input("Enter collection name to clear: ").strip()
            if name:
                clear_collection(qdrant_client, name)
                
        elif choice == "5":
            name = input("Enter collection name: ").strip()
            if name:
                get_collection_details(qdrant_client, name)
                
        elif choice == "6":
            name = input("Enter collection name to backup: ").strip()
            if name:
                backup_collection(qdrant_client, name)
                
        elif choice == "7":
            filename = input("Enter backup filename: ").strip()
            if filename:
                restore_collection(qdrant_client, filename)
                
        elif choice == "8":
            print("Goodbye!")
            break
        else:
            print("Invalid choice. Please try again.")
        
        print("")

if __name__ == "__main__":
    main()
