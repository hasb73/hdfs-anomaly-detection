from qdrant_client import QdrantClient
client = QdrantClient(host="localhost", port=6333)

# HDFS collection name (using existing logs_embeddings collection)
COL = "training_embeddings"

print(f"🔍 HDFS QDRANT ENTRIES VIEWER")
print("=" * 50)

try:
    # Check if collection exists
    collections = client.get_collections()
    collection_names = [col.name for col in collections.collections]
    
    if COL not in collection_names:
        print(f'⚠️  Collection "{COL}" not found!')
        print(f'📋 Available collections: {collection_names}')
        print(f'🚀 Run the Spark streaming job to create and populate the collection')
        exit(1)

    # Get collection info first
    info = client.get_collection(COL)
    total_points = info.points_count
    print(f"📊 Collection: {COL}")
    print(f"📈 Total Points: {total_points}")
    print(f"📐 Vector Dimensions: {info.config.params.vectors.size}")
    print()

    if total_points == 0:
        print('📭 Collection is empty. Run the streaming pipeline to populate it.')
        exit(0)

    # Method 1: Get recent entries (first 20)
    print("📄 Recent 20 HDFS log entries:")
    print("-" * 40)
    points, _ = client.scroll(
        collection_name=COL,
        limit=20,
        with_vectors=False
    )

    normal_count = 0
    anomaly_count = 0
    
    for i, point in enumerate(points, 1):
        message = point.payload.get('text', point.payload.get('message', 'N/A'))
        label = point.payload.get('label', 'N/A')
        timestamp = point.payload.get('timestamp', 'N/A')
        # Extract block_id from message if available
        block_id = 'N/A'
        if message != 'N/A' and 'blk_' in message:
            import re
            match = re.search(r'blk_[0-9-]+', message)
            block_id = match.group(0) if match else 'N/A'
        
        if label == 1:
            status = "🔴 ANOMALY"
            anomaly_count += 1
        elif label == 0:
            status = "🟢 NORMAL"
            normal_count += 1
        else:
            status = "❓ UNKNOWN"
        
        print(f"{i:2d}. {status} | ID: {point.id}")
        print(f"    📝 {message}")
        print(f"    🕐 {timestamp} | 🔧 Block: {block_id}")
        print()

    print("=" * 50)
    print(f"📊 STATISTICS FOR DISPLAYED ENTRIES:")
    print(f"   🟢 Normal: {normal_count}")
    print(f"   🔴 Anomalies: {anomaly_count}")
    print(f"   📈 Total shown: {len(points)}")
    if len(points) > 0:
        print(f"   📊 Anomaly rate: {anomaly_count/len(points)*100:.1f}%")

    # Show anomaly examples if available
    if anomaly_count > 0:
        print(f"\n🔴 ANOMALY EXAMPLES:")
        print("-" * 20)
        anomalies = [p for p in points if p.payload.get('label') == 1]
        for i, point in enumerate(anomalies[:5], 1):
            msg = point.payload.get('text', point.payload.get('message', 'N/A'))
            print(f"{i}. {msg}")

except Exception as e:
    print(f'❌ Error accessing Qdrant: {e}')
    print(f'💡 Make sure Qdrant is running and the HDFS pipeline has created data')
