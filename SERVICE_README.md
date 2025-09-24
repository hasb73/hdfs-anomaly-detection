# HDFS Anomaly Detection Engine V2 - Service Management

## Quick Start

### Start the service in background:
```bash
./start_scoring_service.sh
```

### Check service status:
```bash
./check_scoring_service.sh
```

### Stop the service:
```bash
./stop_scoring_service.sh
```

## Manual Commands

### Start manually in background:
```bash
export ENABLE_KAFKA_CONSUMER=true
nohup python3 enhanced_scoring_service_v2.py --background > scoring_service_v2.log 2>&1 &
```

### Start manually in foreground:
```bash
export ENABLE_KAFKA_CONSUMER=true
python3 enhanced_scoring_service_v2.py
```

## Configuration

### Environment Variables (automatically set by start script):
- `ENABLE_KAFKA_CONSUMER=true` (always enabled now)
- `ENSEMBLE_MODEL_PATH_V2` - Path to ensemble model V2
- `EMBEDDING_SERVICE_URL` - Embedding service URL (default: http://localhost:8000)
- `KAFKA_SERVERS` - Kafka servers (default: localhost:9092)
- `KAFKA_TOPIC` - Kafka topic (default: logs)
- `REDIS_HOST` - Redis host (default: localhost)
- `REDIS_PORT` - Redis port (default: 6379)
- `QDRANT_HOST` - Qdrant host (default: localhost)
- `QDRANT_PORT` - Qdrant port (default: 6333)
- `ANOMALY_DB_PATH` - SQLite database path (default: anomaly_detection_v2.db)

## Service Endpoints

- **Health Check**: `GET http://localhost:8003/health`
- **Predict Single**: `POST http://localhost:8003/predict`
- **Predict Batch**: `POST http://localhost:8003/predict_batch`
- **Statistics**: `GET http://localhost:8003/stats`
- **Recent Anomalies**: `GET http://localhost:8003/anomalies`
- **Accuracy Report**: `GET http://localhost:8003/accuracy`
- **Submit Feedback**: `POST http://localhost:8003/feedback`
- **Reset Stats**: `POST http://localhost:8003/reset`
- **Cache Stats**: `GET http://localhost:8003/cache/stats`
- **Clear Cache**: `DELETE http://localhost:8003/cache`
- **Qdrant Stats**: `GET http://localhost:8003/qdrant/stats`
- **Search Similar**: `GET http://localhost:8003/search?query=<text>&limit=10`

## Key Features

✅ **Kafka Consumer**: Always enabled, processes messages from Kafka topic  
✅ **Ensemble V2**: Uses trained Decision Tree, MLP, SGD, and Qdrant models  
✅ **Weighted Voting**: F1-based weights for optimal ensemble performance  
✅ **Caching**: Redis-based caching for improved performance  
✅ **Vector Search**: Qdrant integration for similarity-based anomaly detection  
✅ **Accuracy Tracking**: Real-time accuracy metrics with feedback support  
✅ **Background Execution**: Runs as daemon process with logging  
✅ **Database Storage**: SQLite database for persistent anomaly storage  

## Logs

- Service logs: `scoring_service_v2.log`
- Process management: Use the provided shell scripts
- Real-time monitoring: Check the log file with `tail -f scoring_service_v2.log`

## Troubleshooting

### Service won't start:
1. Check if required services are running (Kafka, Redis, Qdrant, Embedding service)
2. Verify model file exists at the specified path
3. Check log file for detailed error messages

### Service not responding:
1. Use `./check_scoring_service.sh` to verify status
2. Check if port 8003 is available: `lsof -i :8003`
3. Restart: `./stop_scoring_service.sh && ./start_scoring_service.sh`

### Performance issues:
1. Check `/stats` endpoint for performance metrics
2. Monitor Redis cache hit rate: `/cache/stats`
3. Review database size and performance snapshots
