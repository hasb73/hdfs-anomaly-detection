from qdrant_client import QdrantClient
import json

client = QdrantClient(host='localhost', port=6333)

print('🔍 HDFS QDRANT EMBEDDINGS VIEWER')
print('=' * 50)

try:
    # Check if hdfs_logs collection exists
    collections = client.get_collections()
    collection_names = [col.name for col in collections.collections]
    
    print(f'📋 Available collections: {collection_names}')
    
    # Try to get logs_embeddings collection (HDFS data)
    collection_name = 'training_embeddings'
    if collection_name not in collection_names:
        print(f'⚠️  Collection "{collection_name}" not found!')
        print(f'💡 Available collections: {collection_names}')
        print(f'� Run the Spark job to create and populate the collection')
        exit(1)
    
    # Get collection info
    info = client.get_collection(collection_name)
    print(f'📊 Collection: {collection_name}')
    print(f'📈 Total Points: {info.points_count}')
    print(f'📐 Vector Dimensions: {info.config.params.vectors.size}')
    print(f'🔍 Distance Metric: {info.config.params.vectors.distance}')
    print()
    
    if info.points_count == 0:
        print('📭 Collection is empty. Run the streaming pipeline to populate it.')
        exit(0)
    
    # Get a sample of points with their embeddings
    print('📄 Sample HDFS Log Embeddings (with vectors):')
    print('-' * 40)
    
    # Use scroll to get points with vectors
    points, next_page = client.scroll(
        collection_name=collection_name,
        limit=10,  # Reduced to 10 for better readability
        with_vectors=True
    )
    
    for i, point in enumerate(points, 1):
        print(f'Entry {i}:')
        print(f'  📋 ID: {point.id}')
        message = point.payload.get('text', point.payload.get('message', 'N/A'))
        print(f'  📝 Message: {message}')
        print(f'  🏷️  Label: {point.payload.get("label", "N/A")} ({"🔴 ANOMALY" if point.payload.get("label") == 1 else "🟢 NORMAL"})')
        print(f'  🕐 Timestamp: {point.payload.get("timestamp", "N/A")}')
        # Extract block_id from message if available
        block_id = 'N/A'
        if message != 'N/A' and 'blk_' in message:
            import re
            match = re.search(r'blk_[0-9-]+', message)
            block_id = match.group(0) if match else 'N/A'
        print(f'  🔧 Block ID: {block_id}')
        if point.vector:
            print(f'  🧮 Vector (first 5): {point.vector[:5]}')
            print(f'  📏 Vector Length: {len(point.vector)}')
        else:
            print(f'  ⚠️  Vector: None/Empty')
        print()
        
    # Show statistics about vector data
    print('📊 HDFS VECTOR STATISTICS:')
    print('-' * 30)
    non_empty_vectors = sum(1 for p in points if p.vector and len(p.vector) > 0)
    anomaly_count = sum(1 for p in points if p.payload.get("label") == 1)
    normal_count = sum(1 for p in points if p.payload.get("label") == 0)
    
    print(f'Points with vectors: {non_empty_vectors}/{len(points)}')
    print(f'Normal logs: {normal_count}')
    print(f'Anomaly logs: {anomaly_count}')
    print(f'Anomaly ratio: {anomaly_count/len(points)*100:.1f}%')
    
    # Show recent anomalies if any
    if anomaly_count > 0:
        print(f'\n🔴 Recent Anomaly Examples:')
        print('-' * 30)
        anomalies = [p for p in points if p.payload.get("label") == 1]
        for i, point in enumerate(anomalies[:3], 1):
            msg = point.payload.get('text', point.payload.get('message', 'N/A'))
            print(f'{i}. {msg}')
    
except Exception as e:
    print(f'❌ Error accessing Qdrant: {e}')
    print(f'💡 Make sure Qdrant is running and the HDFS pipeline has created data')