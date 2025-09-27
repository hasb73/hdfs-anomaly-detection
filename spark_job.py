#!/usr/bin/env python3
"""
Production Spark Streaming Job for HDFS Log Processing
Processes HDFS log lines from Kafka, generates embeddings, and stores in Qdrant.
The scoring service handles anoprint("📊 Streaming started! Processing HDFS production logs...")
print("   - Reading from Kafka topic: logs")
print("   - Processing HDFS log entries from production system")
print("   - Generating embeddings via embedding service")
print("   - Storing vectors in Qdrant collection: logs_embeddings")
print("   - Scoring service will handle anomaly detection")
print("   - Processing every 10 seconds")etection and predictions.
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

# Define schema for HDFS production log messages from hdfs_production_log_processor
hdfs_schema = StructType([
    StructField("text", StringType(), True),           # Processed log text
    StructField("original_text", StringType(), True),  # Original raw log line
    StructField("log_level", StringType(), True),      # INFO, WARN, ERROR, etc.
    StructField("source", StringType(), True),         # hdfs_datanode
    StructField("timestamp", StringType(), True),      # ISO timestamp
    StructField("node_type", StringType(), True),      # datanode
    StructField("label", IntegerType(), True)          # Anomaly label (nullable)
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

# Add debug function to inspect raw JSON
def debug_json_parsing():
    print("🔍 Sample JSON messages from Kafka:")
    sample_df = json_df.limit(5)
    for row in sample_df.collect():
        print(f"   Raw JSON: {row.raw_json}")

# Extract structured data from JSON - Updated to match hdfs_production_log_processor format
parsed_df = json_df.withColumn(
    "parsed_data", 
    from_json(col("raw_json"), hdfs_schema)
).select(
    col("parsed_data.text").alias("message"),                    # Use 'text' field as message
    col("parsed_data.original_text").alias("original_text"),    # Keep original for reference
    col("parsed_data.log_level").alias("log_level"),            # Log severity level
    col("parsed_data.source").alias("source"),                  # Source identifier
    col("parsed_data.timestamp").alias("timestamp"),            # Processing timestamp
    col("parsed_data.node_type").alias("node_type"),            # Node type
    col("parsed_data.label").alias("label")                     # Anomaly label (nullable)
).filter(col("message").isNotNull())

def foreach_batch_hdfs(df, epoch_id):
    """Process each batch of HDFS production log messages"""
    print(f"\n🔄 Processing production log batch {epoch_id}...")
    
    # Debug: Show schema and sample data
    print(f"   📊 DataFrame schema: {df.schema}")
    
    # Collect batch data
    rows = df.collect()
    if not rows:
        print("   No data in batch")
        return
    
    # Debug: Show first few rows
    print(f"   📝 Sample row: {rows[0] if rows else 'None'}")
    
    print(f"   Batch size: {len(rows)} messages")
    
    # Extract messages and metadata - Production mode: no labels needed
    messages = []
    metadata = []
    
    for row in rows:
        messages.append(row['message'])
        metadata.append({
            'timestamp': row['timestamp'],
            'original_text': row['original_text'],
            'log_level': row['log_level'],
            'source': row['source'],
            'node_type': row['node_type']
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
            print(f"    Embedding service error: {resp.status_code}")
            return
            
        embs = resp.json().get("embeddings", [])
        print(f"   Generated {len(embs)} embeddings")
        
    except Exception as e:
        print(f"    Embedding call failed: {e}")
        return
    
    # Prepare points for Qdrant - Production mode: just store embeddings
    points = []
    
    for i, (embedding, meta) in enumerate(zip(embs, metadata)):
        # Create unique ID using hash of message + timestamp
        point_id = abs(hash(f"{messages[i]}_{meta['timestamp']}")) % (2**63)
        
        point = qm.PointStruct(
            id=point_id,
            vector=embedding,
            payload={
                "text": messages[i],
                "original_text": meta['original_text'],
                "timestamp": meta['timestamp'],
                "log_level": meta['log_level'],
                "source": meta['source'],
                "node_type": meta['node_type']
                # Note: No label or is_anomaly - scoring service will determine this
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
        
        print(f"   ✅ Batch {epoch_id} processed: {len(points)} log entries stored in Qdrant")
        
    except Exception as e:
        print(f"   ❌ Qdrant insertion failed: {e}")

# Start streaming
print("🎯 Starting HDFS line-level log processing stream...")
query = parsed_df.writeStream \
    .foreachBatch(foreach_batch_hdfs) \
    .outputMode("append") \
    .trigger(processingTime='10 seconds') \
    .start()

print(" Streaming started! Processing HDFS line-level logs...")
print("   - Reading from Kafka topic: logs")
print("   - Processing individual log lines with line-level anomaly labels")
print("   - Generating embeddings via embedding service")
print("   - Storing vectors in Qdrant collection: logs_embeddings")
print("   - Processing every 10 seconds")
print("\nPress Ctrl+C to stop...")

try:
    query.awaitTermination()
except KeyboardInterrupt:
    print("\n  Stopping stream...")
    query.stop()
    spark.stop()
    print(" Stream stopped gracefully")
