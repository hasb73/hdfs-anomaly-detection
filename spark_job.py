#!/usr/bin/env python3
"""
Enhanced Spark Streaming Job for HDFS Line-Level Log Processing
Processes individual HDFS log lines from Kafka with line-level anomaly labels,
generates embeddings, and stores in Qdrant for real-time anomaly detection
"""
# Suppress urllib3 SSL warnings
import warnings
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
warnings.filterwarnings('ignore', message='urllib3 v2 only supports OpenSSL 1.1.1+')

from pyspark.sql import SparkSession
from pyspark.sql.functions import udf, col, from_json
from pyspark.sql.types import StringType, StructType, StructField, IntegerType
import json, requests, hashlib
from qdrant_client import QdrantClient
from qdrant_client.http import models as qm

# Configuration
KAFKA_SERVERS = "localhost:9092"
KAFKA_TOPICS = "logs"
EMBEDDING_SERVICE_URL = "http://localhost:8000/embed"
QDRANT_HOST = "localhost"
QDRANT_PORT = 6333
COLLECTION = "logs_embeddings"
DIM = 384

# Initialize Qdrant client
print("🔧 Initializing Qdrant connection...")
qdrant = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)

# Create or recreate collection
try:
    qdrant.recreate_collection(
        collection_name=COLLECTION,
        vectors_config=qm.VectorParams(size=DIM, distance=qm.Distance.COSINE)
    )
    print(f"✅ Created Qdrant collection: {COLLECTION}")
except Exception as e:
    print(f"⚠️  Collection setup: {e}")

# Initialize Spark Session
print("🚀 Initializing Spark Session...")
spark = SparkSession.builder \
    .appName("HDFSLineLevelEmbeddingPipeline") \
    .config("spark.streaming.stopGracefullyOnShutdown", "true") \
    .config("spark.sql.streaming.checkpointLocation", "/tmp/spark-checkpoint-line-level") \
    .getOrCreate()

spark.sparkContext.setLogLevel("WARN")

# Define schema for HDFS line-level log messages  
hdfs_schema = StructType([
    StructField("message", StringType(), True),
    StructField("label", IntegerType(), True),
    StructField("timestamp", StringType(), True),
    StructField("index", IntegerType(), True),
    StructField("id", IntegerType(), True)  # Added for line-level data
])

# Read from Kafka
print(f"📡 Connecting to Kafka: {KAFKA_SERVERS}")
df = spark \
    .readStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", KAFKA_SERVERS) \
    .option("subscribe", KAFKA_TOPICS) \
    .option("startingOffsets", "latest") \
    .option("failOnDataLoss", "false") \
    .load()

# Parse JSON messages
json_df = df.selectExpr("CAST(value AS STRING) as raw_json")

# Extract structured data from JSON
parsed_df = json_df.withColumn(
    "parsed_data", 
    from_json(col("raw_json"), hdfs_schema)
).select(
    col("parsed_data.message").alias("message"),
    col("parsed_data.label").alias("label"),
    col("parsed_data.timestamp").alias("timestamp"),
    col("parsed_data.index").alias("index"),
    col("parsed_data.id").alias("id")
).filter(col("message").isNotNull())

def foreach_batch_hdfs(df, epoch_id):
    """Process each batch of HDFS line-level log messages"""
    print(f"\n🔄 Processing line-level batch {epoch_id}...")
    
    # Collect batch data
    rows = df.collect()
    if not rows:
        print("   No data in batch")
        return
    
    print(f"   Batch size: {len(rows)} messages")
    
    # Extract messages and metadata
    messages = []
    metadata = []
    
    for row in rows:
        messages.append(row['message'])
        metadata.append({
            'label': row['label'],
            'timestamp': row['timestamp'],
            'index': row['index'],
            'id': row['id']
        })
    
    # Generate embeddings
    try:
        print("   🧠 Generating embeddings...")
        resp = requests.post(
            EMBEDDING_SERVICE_URL, 
            json={"texts": messages}, 
            timeout=30
        )
        
        if resp.status_code != 200:
            print(f"   ❌ Embedding service error: {resp.status_code}")
            return
            
        embs = resp.json().get("embeddings", [])
        print(f"   ✅ Generated {len(embs)} embeddings")
        
    except Exception as e:
        print(f"   ❌ Embedding call failed: {e}")
        return
    
    # Prepare points for Qdrant
    points = []
    anomaly_count = 0
    
    for i, (embedding, meta) in enumerate(zip(embs, metadata)):
        # Create unique ID using hash of message + line ID
        point_id = abs(hash(f"{messages[i]}_{meta['id']}_{meta['index']}")) % (2**63)
        
        # Count anomalies
        if meta['label'] == 1:
            anomaly_count += 1
        
        point = qm.PointStruct(
            id=point_id,
            vector=embedding,
            payload={
                "text": messages[i],
                "label": meta['label'],
                "timestamp": meta['timestamp'],
                "index": meta['index'],
                "line_id": meta['id'],
                "is_anomaly": meta['label'] == 1
            }
        )
        points.append(point)
    
    # Insert into Qdrant
    try:
        print(f"   💾 Inserting {len(points)} points to Qdrant...")
        qdrant.upsert(
            collection_name=COLLECTION,
            points=points,
            wait=True
        )
        
        normal_count = len(points) - anomaly_count
        print(f"   ✅ Batch {epoch_id} processed: {normal_count} normal, {anomaly_count} anomalies")
        
    except Exception as e:
        print(f"   ❌ Qdrant insertion failed: {e}")

# Start streaming
print("🎯 Starting HDFS line-level log processing stream...")
query = parsed_df.writeStream \
    .foreachBatch(foreach_batch_hdfs) \
    .outputMode("append") \
    .trigger(processingTime='10 seconds') \
    .start()

print("📊 Streaming started! Processing HDFS line-level logs...")
print("   - Reading from Kafka topic: logs")
print("   - Processing individual log lines with line-level anomaly labels")
print("   - Generating embeddings via embedding service")
print("   - Storing vectors in Qdrant collection: logs_embeddings")
print("   - Processing every 10 seconds")
print("\nPress Ctrl+C to stop...")

try:
    query.awaitTermination()
except KeyboardInterrupt:
    print("\n⏹️  Stopping stream...")
    query.stop()
    spark.stop()
    print("✅ Stream stopped gracefully")
