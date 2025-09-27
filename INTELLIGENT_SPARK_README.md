# Intelligent Spark Job for HDFS Log Processing

An intelligent Spark streaming job that processes HDFS log entries from Kafka, generates embeddings, and stores them in Qdrant with built-in deduplication to avoid processing the same log entries multiple times.

## Overview

The Intelligent Spark Job is designed for production environments where log entries may be reprocessed or where you want to avoid storing duplicate embeddings in your vector database. It includes smart deduplication logic that checks for existing entries before processing new ones.

## Features

### Core Functionality
- **Kafka Integration**: Consumes HDFS log messages from Kafka topics
- **Intelligent Deduplication**: Checks Qdrant for existing entries before processing
- **Embedding Generation**: Creates vector embeddings for new log entries only
- **Qdrant Storage**: Stores embeddings with metadata in Qdrant vector database
- **Production Ready**: Clean output without emoticons, optimized for server environments

### Smart Processing
- **Duplicate Detection**: Uses consistent hash-based IDs to identify existing entries
- **Batch Processing**: Efficiently processes messages in configurable batches
- **Error Handling**: Robust error handling for network and service failures
- **Performance Monitoring**: Reports processing statistics and duplicate counts

## Architecture

```
Kafka Topic (logs) → Intelligent Spark Job → Qdrant Vector Database
                          ↓
                   Duplicate Check → Skip if exists
                          ↓
                   Embedding Service → Generate vectors for new entries only
```

## Prerequisites

### Required Services
- **Apache Spark**: 3.x or higher with Kafka connector
- **Apache Kafka**: Running on localhost:9092 (configurable)
- **Qdrant Vector Database**: Running on localhost:6333 (configurable)
- **Embedding Service**: Running on localhost:8000 (configurable)

### Python Dependencies
```bash
pip install pyspark qdrant-client requests numpy
```

### Spark Packages
```bash
# Required Kafka connector package
spark-submit --packages org.apache.spark:spark-sql-kafka-0-10_2.13:4.0.0
```

## Configuration

Edit the configuration variables at the top of `intelligent_spark.py`:

```python
# Kafka Configuration
KAFKA_SERVERS = "localhost:9092"
KAFKA_TOPICS = "logs"

# Services Configuration
EMBEDDING_SERVICE_URL = "http://localhost:8000/embed"
QDRANT_HOST = "localhost"
QDRANT_PORT = 6333

# Collection Settings
COLLECTION = "logs_embeddings"
DIM = 384  # Embedding dimension
```

## Usage

### Basic Usage
```bash
# Run with Spark Submit
spark-submit --packages org.apache.spark:spark-sql-kafka-0-10_2.13:4.0.0 intelligent_spark.py
```

### Advanced Usage
```bash
# With custom Spark configuration
spark-submit \
  --packages org.apache.spark:spark-sql-kafka-0-10_2.13:4.0.0 \
  --conf spark.sql.streaming.checkpointLocation=/path/to/checkpoint \
  --conf spark.streaming.stopGracefullyOnShutdown=true \
  intelligent_spark.py
```

### Docker Usage
```bash
# If running in Docker environment
docker run -v $(pwd):/app spark:latest \
  spark-submit --packages org.apache.spark:spark-sql-kafka-0-10_2.13:4.0.0 \
  /app/intelligent_spark.py
```

## Input Data Format

The job expects JSON messages from Kafka with the following structure:

```json
{
  "text": "processed log message text",
  "original_text": "original raw log line",
  "log_level": "INFO|WARN|ERROR",
  "source": "hdfs_datanode",
  "timestamp": "2025-09-27T10:30:45.123",
  "node_type": "datanode",
  "label": null
}
```

This format matches the output from `hdfs_production_log_processor.py`.

## Output and Monitoring

### Console Output
```
Initializing Qdrant connection...
Using existing Qdrant collection: logs_embeddings
Initializing Spark Session...
Connecting to Kafka: localhost:9092
Starting intelligent HDFS log processing stream...

Processing production log batch 0...
  Batch size: 15 messages
  Checking for existing entries in Qdrant...
  Skipped 3 existing entries
  Processing 12 new messages
  Generating embeddings...
  Generated 12 embeddings
  Inserting 12 new points to Qdrant...
  Batch 0 processed: 12 new entries stored, 3 duplicates skipped
```

### Key Metrics
- **Batch Size**: Number of messages received from Kafka
- **Existing Entries**: Number of duplicates found and skipped
- **New Messages**: Number of unique entries processed
- **Embeddings Generated**: Number of vectors created
- **Points Inserted**: Number of entries stored in Qdrant

## Deduplication Logic

### Point ID Generation
```python
def generate_point_id(message: str, timestamp: str) -> int:
    """Generate consistent point ID for deduplication"""
    return abs(hash(f"{message}_{timestamp}")) % (2**63)
```

### Duplicate Detection
1. **Hash Generation**: Creates consistent hash from message text + timestamp
2. **Qdrant Query**: Checks if point ID already exists in collection
3. **Filter New Entries**: Only processes messages not found in Qdrant
4. **Batch Processing**: Efficiently handles large batches with minimal Qdrant queries

## Performance Considerations

### Optimization Settings
```python
# Processing frequency (configurable)
.trigger(processingTime='15 seconds')

# Batch size for Qdrant queries
batch_size = 1000

# Checkpoint location for fault tolerance
.config("spark.sql.streaming.checkpointLocation", "/tmp/spark-checkpoint-intelligent")
```

### Scaling Recommendations
- **Memory**: Allocate sufficient memory for Spark driver and executors
- **Network**: Ensure stable connections to Kafka, Qdrant, and embedding service
- **Checkpoint**: Use persistent storage for checkpoint location in production
- **Partitioning**: Consider Kafka topic partitioning for higher throughput

## Error Handling

### Service Failures
- **Embedding Service Down**: Batch processing pauses, retries automatically
- **Qdrant Unavailable**: Graceful error handling, continues processing when restored
- **Kafka Connection Loss**: Spark handles reconnection automatically

### Data Issues
- **Malformed JSON**: Invalid messages are logged and skipped
- **Missing Fields**: Default values used where possible
- **Empty Batches**: Handled gracefully without errors

## Integration with Other Components

### HDFS Log Processor
The intelligent Spark job works seamlessly with `hdfs_production_log_processor.py`:

```bash
# Terminal 1: Start log processor
python3 hdfs_production_log_processor.py /path/to/hdfs/logs

# Terminal 2: Start intelligent Spark job
spark-submit --packages org.apache.spark:spark-sql-kafka-0-10_2.13:4.0.0 intelligent_spark.py

# Terminal 3: Start scoring service
uvicorn enhanced_scoring_service:app --host 0.0.0.0 --port 8003
```

### Scoring Service
The stored embeddings are used by the scoring service for:
- **Similarity Search**: Finding similar log patterns
- **Anomaly Detection**: Comparing new logs against historical data
- **Real-time Scoring**: Fast vector similarity queries

## Monitoring Tools

Use the provided utilities to monitor and analyze the Qdrant collection:

```bash
# View stored entries
python3 view_qdrant.py

# Analyze embeddings
python3 analyze_embeddings.py

# Manage collections
python3 manage_qdrant.py
```

## Troubleshooting

### Common Issues

#### No Data in Batches
```
Processing production log batch 0...
  No data in batch
```
**Solution**: Check Kafka topic has messages and log processor is running

#### Embedding Service Errors
```
Embedding service error: 500
```
**Solution**: Verify embedding service is running on correct port

#### Qdrant Connection Issues
```
Error checking existing points: Connection refused
```
**Solution**: Ensure Qdrant is running and accessible

#### Memory Issues
```
OutOfMemoryError: Java heap space
```
**Solution**: Increase Spark driver/executor memory:
```bash
spark-submit --driver-memory 4g --executor-memory 4g ...
```

### Debug Mode
Enable debug logging by modifying the Spark configuration:
```python
spark.sparkContext.setLogLevel("INFO")  # Change from "WARN"
```

## Production Deployment

### Systemd Service
Create a systemd service for automatic startup:

```ini
[Unit]
Description=Intelligent Spark HDFS Log Processor
After=network.target kafka.service qdrant.service

[Service]
Type=simple
User=spark
WorkingDirectory=/opt/hdfs-anomaly-detection
ExecStart=/opt/spark/bin/spark-submit --packages org.apache.spark:spark-sql-kafka-0-10_2.13:4.0.0 intelligent_spark.py
Restart=always
RestartSec=30

[Install]
WantedBy=multi-user.target
```

### Docker Compose
```yaml
version: '3.8'
services:
  intelligent-spark:
    image: spark:latest
    volumes:
      - ./:/app
    command: >
      spark-submit 
      --packages org.apache.spark:spark-sql-kafka-0-10_2.13:4.0.0
      /app/intelligent_spark.py
    depends_on:
      - kafka
      - qdrant
      - embedding-service
```

### Monitoring and Alerting
- **Spark UI**: Monitor job progress at http://localhost:4040
- **Metrics**: Track processing rates and duplicate ratios
- **Alerts**: Set up alerts for service failures or processing delays

## License

This project is part of the HDFS Anomaly Detection system. See the main repository for licensing information.

## Contributing

When contributing to the intelligent Spark job:
1. Maintain compatibility with existing message formats
2. Preserve deduplication logic integrity
3. Add appropriate error handling for new features
4. Update documentation for configuration changes
