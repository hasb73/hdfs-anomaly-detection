#!/usr/bin/env python3
"""
Intelligent Spark Streaming Job for HDFS Log Processing
Processes HDFS log lines from Kafka, generates embeddings, and stores in Qdrant.
Includes duplicate detection to avoid re-processing existing log entries.
The scoring service handles anomaly detection and predictions.
"""
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
from typing import List, Dict, Set

# Configuration
KAFKA_SERVERS = "localhost:9092"
KAFKA_TOPICS = "logs"
EMBEDDING_SERVICE_URL = "http://localhost:8000/embed"
QDRANT_HOST = "localhost"
QDRANT_PORT = 6333
COLLECTION = "logs_embeddings"
DIM = 384

# Initialize Qdrant client
print("Initializing Qdrant connection...")
qdrant = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)

# Ensure collection exists
try:
    collections = qdrant.get_collections()
    collection_names = [col.name for col in collections.collections]
    
    if COLLECTION not in collection_names:
        qdrant.create_collection(
            collection_name=COLLECTION,
            vectors_config=qm.VectorParams(size=DIM, distance=qm.Distance.COSINE)
        )
        print(f"Created Qdrant collection: {COLLECTION}")
    else:
        print(f"Using existing Qdrant collection: {COLLECTION}")
except Exception as e:
    print(f"Collection setup error: {e}")

# Initialize Spark Session
print("Initializing Spark Session...")
spark = SparkSession.builder \
    .appName("IntelligentHDFSLogProcessor") \
    .config("spark.streaming.stopGracefullyOnShutdown", "true") \
    .config("spark.sql.streaming.checkpointLocation", "/tmp/spark-checkpoint-intelligent") \
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
print(f"Connecting to Kafka: {KAFKA_SERVERS}")
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
    col("parsed_data.text").alias("message"),
    col("parsed_data.original_text").alias("original_text"),
    col("parsed_data.log_level").alias("log_level"),
    col("parsed_data.source").alias("source"),
    col("parsed_data.timestamp").alias("timestamp"),
    col("parsed_data.node_type").alias("node_type"),
    col("parsed_data.label").alias("label")
).filter(col("message").isNotNull())

def generate_point_id(message: str, timestamp: str) -> int:
    """Generate consistent point ID for deduplication"""
    return abs(hash(f"{message}_{timestamp}")) % (2**63)

def check_existing_points(point_ids: List[int]) -> Set[int]:
    """Check which point IDs already exist in Qdrant"""
    existing_ids = set()
    
    try:
        # Query Qdrant to check for existing points
        # We'll use scroll to get all points and check IDs
        # For large collections, this could be optimized with filters
        
        batch_size = 1000
        for i in range(0, len(point_ids), batch_size):
            batch_ids = point_ids[i:i + batch_size]
            
            try:
                points = qdrant.retrieve(
                    collection_name=COLLECTION,
                    ids=batch_ids,
                    with_payload=False,
                    with_vectors=False
                )
                
                for point in points:
                    existing_ids.add(point.id)
                    
            except Exception as e:
                # If retrieve fails, assume points don't exist
                print(f"Warning: Could not check batch of IDs: {e}")
                
    except Exception as e:
        print(f"Error checking existing points: {e}")
        
    return existing_ids

def foreach_batch_hdfs(df, epoch_id):
    """Process each batch of HDFS production log messages with intelligent deduplication"""
    print(f"Processing production log batch {epoch_id}...")
    
    # Collect batch data
    rows = df.collect()
    if not rows:
        print("  No data in batch")
        return
    
    print(f"  Batch size: {len(rows)} messages")
    
    # Extract messages and metadata
    messages = []
    metadata = []
    point_ids = []
    
    for row in rows:
        message = row['message']
        timestamp = row['timestamp']
        point_id = generate_point_id(message, timestamp)
        
        messages.append(message)
        point_ids.append(point_id)
        metadata.append({
            'point_id': point_id,
            'timestamp': timestamp,
            'original_text': row['original_text'],
            'log_level': row['log_level'],
            'source': row['source'],
            'node_type': row['node_type']
        })
    
    # Check for existing entries
    print("  Checking for existing entries in Qdrant...")
    existing_ids = check_existing_points(point_ids)
    
    # Filter out existing entries
    new_messages = []
    new_metadata = []
    
    for i, (message, meta) in enumerate(zip(messages, metadata)):
        if meta['point_id'] not in existing_ids:
            new_messages.append(message)
            new_metadata.append(meta)
    
    skipped_count = len(messages) - len(new_messages)
    if skipped_count > 0:
        print(f"  Skipped {skipped_count} existing entries")
    
    if not new_messages:
        print("  No new messages to process")
        return
    
    print(f"  Processing {len(new_messages)} new messages")
    
    # Generate embeddings for new messages only
    try:
        print("  Generating embeddings...")
        resp = requests.post(
            EMBEDDING_SERVICE_URL, 
            json={"texts": new_messages}, 
            timeout=60
        )
        
        if resp.status_code != 200:
            print(f"  Embedding service error: {resp.status_code}")
            return
            
        embs = resp.json().get("embeddings", [])
        print(f"  Generated {len(embs)} embeddings")
        
    except Exception as e:
        print(f"  Embedding call failed: {e}")
        return
    
    # Prepare points for Qdrant
    points = []
    
    for embedding, meta in zip(embs, new_metadata):
        point = qm.PointStruct(
            id=meta['point_id'],
            vector=embedding,
            payload={
                "text": new_messages[new_metadata.index(meta)],
                "original_text": meta['original_text'],
                "timestamp": meta['timestamp'],
                "log_level": meta['log_level'],
                "source": meta['source'],
                "node_type": meta['node_type']
            }
        )
        points.append(point)
    
    # Insert into Qdrant
    try:
        print(f"  Inserting {len(points)} new points to Qdrant...")
        qdrant.upsert(
            collection_name=COLLECTION,
            points=points,
            wait=True
        )
        
        print(f"  Batch {epoch_id} processed: {len(points)} new entries stored, {skipped_count} duplicates skipped")
        
    except Exception as e:
        print(f"  Qdrant insertion failed: {e}")

# Start streaming
print("Starting intelligent HDFS log processing stream...")
query = parsed_df.writeStream \
    .foreachBatch(foreach_batch_hdfs) \
    .outputMode("append") \
    .trigger(processingTime='15 seconds') \
    .start()

print("Streaming started! Intelligent HDFS log processing...")
print("  - Reading from Kafka topic: logs")
print("  - Checking for existing entries to avoid duplicates")
print("  - Processing only new HDFS log entries")
print("  - Generating embeddings for new entries only")
print("  - Storing vectors in Qdrant collection: logs_embeddings")
print("  - Scoring service will handle anomaly detection")
print("  - Processing every 15 seconds")
print("")
print("Press Ctrl+C to stop...")

try:
    query.awaitTermination()
except KeyboardInterrupt:
    print("")
    print("Stopping stream...")
    query.stop()
    spark.stop()
    print("Stream stopped gracefully")
