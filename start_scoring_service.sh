#!/bin/bash

# HDFS Anomaly Detection Engine V2 - Background Starter Script
# This script starts the enhanced scoring service in the background

echo "🚀 Starting HDFS Anomaly Detection Engine V2 in background..."

# Set environment variables
export ENABLE_KAFKA_CONSUMER=true
export ENSEMBLE_MODEL_PATH="./ensemble/models/line_level_ensemble_v2/line_level_ensemble_v2_results.joblib"
export EMBEDDING_SERVICE_URL="http://localhost:8000"
export KAFKA_SERVERS="localhost:9092"
export KAFKA_TOPIC="logs"
export REDIS_HOST="localhost"
export REDIS_PORT="6379"
export QDRANT_HOST="localhost"
export QDRANT_PORT="6333"
export ANOMALY_DB_PATH="anomaly_detection.db"

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Change to the project directory
cd "$SCRIPT_DIR"

# Check if the service is already running
if pgrep -f "enhanced_scoring_service.py" > /dev/null; then
    echo "⚠️  Enhanced scoring service V2 is already running!"
    echo "Use 'pkill -f enhanced_scoring_service.py' to stop it first."
    exit 1
fi

# Start the service in the background
echo " Kafka consumer: ALWAYS ENABLED"
echo " Model path: $ENSEMBLE_MODEL_PATH"
echo " Service will be available at: http://localhost:8003"
echo ""

# Run in background and redirect output to log file
nohup /usr/bin/python3 enhanced_scoring_service.py --background > scoring_service.log 2>&1 &

# Get the process ID
SERVICE_PID=$!
echo " Enhanced scoring service V2 started in background!"
echo " Process ID: $SERVICE_PID"
echo " Log file: scoring_service.log"
echo " Check status: curl http://localhost:8003/health"
echo ""
echo "To stop the service:"
echo "  kill $SERVICE_PID"
echo "  or"
echo "  pkill -f enhanced_scoring_service.py"
echo ""

# Wait a moment and check if service started successfully
sleep 3
if ps -p $SERVICE_PID > /dev/null; then
    echo " Service is running successfully!"
    
    # Try to test the health endpoint
    if command -v curl &> /dev/null; then
        echo " Testing health endpoint..."
        sleep 2
        curl -s http://localhost:8003/health | head -c 200 && echo ""
    fi
else
    echo " Service failed to start. Check scoring_service.log for details."
    exit 1
fi
