# HDFS Production Log Processor for EMR

Real-time HDFS DataNode log processing and anomaly detection for Amazon EMR clusters.

## Overview

This system monitors HDFS DataNode logs in real-time, preprocesses them to remove dynamic content (timestamps, IPs, block IDs), and streams cleaned logs to Kafka for anomaly detection. It's designed to run directly on EMR DataNodes in production environments.

## Features

- **Real-time Log Processing**: Monitors HDFS DataNode logs using file system events
- **Intelligent Preprocessing**: Removes dynamic content while preserving anomaly patterns
- **Kafka Integration**: Streams processed logs to Kafka for downstream processing
- **Production Ready**: Systemd service, logging, statistics, graceful shutdown
- **EMR Optimized**: Designed specifically for Amazon EMR DataNode environments

## Architecture

```
HDFS DataNode Logs → Log Processor → Kafka → Anomaly Detection Service
                           ↓
                    Statistics & Monitoring
```

## Installation on EMR

### Prerequisites

- Amazon EMR cluster with DataNode
- Root access to the DataNode
- Python 3.8+ available
- Network access to Kafka and scoring service

### Quick Deployment

1. **Copy files to EMR DataNode**:
```bash
# Copy the processor files to your EMR DataNode
scp hdfs_production_log_processor.py hadoop@<datanode-ip>:~
scp deploy_emr_log_processor.sh hadoop@<datanode-ip>:~
```

2. **Run deployment script**:
```bash
# SSH to your EMR DataNode
ssh hadoop@<datanode-ip>

# Make deployment script executable and run
chmod +x deploy_emr_log_processor.sh
sudo ./deploy_emr_log_processor.sh
```

3. **Start the service**:
```bash
# Start the service
sudo systemctl start hdfs-log-processor

# Enable auto-start on boot
sudo systemctl enable hdfs-log-processor

# Check status
sudo systemctl status hdfs-log-processor
```

### Manual Installation

If you need to customize the installation:

```bash
# 1. Create installation directory
sudo mkdir -p /opt/hdfs-anomaly-detection
sudo chown hadoop:hadoop /opt/hdfs-anomaly-detection

# 2. Setup Python environment
python3 -m venv /opt/hdfs-anomaly-detection/venv
source /opt/hdfs-anomaly-detection/venv/bin/activate
pip install -r requirements_production.txt

# 3. Copy application files
cp hdfs_production_log_processor.py /opt/hdfs-anomaly-detection/

# 4. Run manually
cd /opt/hdfs-anomaly-detection
./venv/bin/python hdfs_production_log_processor.py \
    /var/log/hadoop-hdfs/hadoop-hdfs-datanode-*.log \
    localhost:9092 \
    logs \
    http://localhost:8003
```

## Configuration

### Command Line Usage

```bash
python3 hdfs_production_log_processor.py <log_file_path> [kafka_servers] [kafka_topic] [scoring_service_url]
```

**Parameters**:
- `log_file_path`: Path to HDFS DataNode log file (supports wildcards)
- `kafka_servers`: Kafka bootstrap servers (default: localhost:9092)
- `kafka_topic`: Kafka topic name (default: logs)
- `scoring_service_url`: Anomaly detection service URL (default: http://localhost:8003)

### Example Usage

```bash
# Basic usage with default settings
python3 hdfs_production_log_processor.py /var/log/hadoop-hdfs/hadoop-hdfs-datanode-*.log

# Custom Kafka and scoring service
python3 hdfs_production_log_processor.py \
    /var/log/hadoop-hdfs/hadoop-hdfs-datanode-ip-172-31-36-192.eu-west-1.compute.internal.log \
    kafka-cluster:9092 \
    hdfs-logs \
    http://anomaly-service:8003
```

## Log Preprocessing

The system intelligently preprocesses HDFS logs to remove dynamic content while preserving anomaly patterns:

### Original Log Example
```
2025-09-25 09:30:54,737 DEBUG org.apache.hadoop.hdfs.server.datanode.DataNode.clienttrace (DataXceiver for client DFSClient_NONMAPREDUCE_-56011767_1 at /172.31.36.192:38172 [Sending block BP-904282469-172.31.36.192-1758638658492:blk_1073742023_1199]): src: /172.31.39.152:9866, dest: /172.31.36.192:38172, volume: , bytes: 40, op: HDFS_READ, cliID: DFSClient_NONMAPREDUCE_-56011767_1, offset: 0, srvID: 4afa7677-552a-4246-84f6-54ae00a35b76, blockid: BP-904282469-172.31.36.192-1758638658492:blk_1073742023_1199, duration(ns): 119030
```

### Preprocessed Log
```
TIMESTAMP DEBUG org.apache.hadoop.hdfs.server.datanode.DataNode.clienttrace (DataXceiver for client CLIENT [Sending block BLOCK_POOL:BLOCK_ID]): src: IP_ADDR:PORT, dest: IP_ADDR:PORT, volume: PATH, bytes: NUM, op: HDFS_READ, cliID: CLIENT_ID, offset: NUM, srvID: UUID, blockid: BLOCK_POOL:BLOCK_ID, duration(ns): NUM
```

### Preprocessing Rules

- **Timestamps**: `2025-09-25 09:30:54,737` → `TIMESTAMP`
- **IP Addresses**: `172.31.36.192` → `IP_ADDR`
- **Ports**: `:38172` → `:PORT`
- **Block IDs**: `blk_1073742023_1199` → `BLOCK_ID`
- **Client IDs**: `DFSClient_NONMAPREDUCE_-56011767_1` → `CLIENT_ID`
- **UUIDs**: `4afa7677-552a-4246-84f6-54ae00a35b76` → `UUID`
- **Hostnames**: `ip-172-31-36-192.eu-west-1.compute.internal` → `HOSTNAME`
- **Numeric Values**: `bytes: 40`, `offset: 0`, `duration(ns): 119030` → `bytes: NUM`, `offset: NUM`, `duration(ns): NUM`

## Kafka Message Format

Messages sent to Kafka include both original and preprocessed logs:

```json
{
    "text": "TIMESTAMP ERROR org.apache.hadoop.hdfs.server.datanode.DataNode: Failed to read block BLOCK_ID",
    "original_text": "2025-09-25 09:30:54,737 ERROR org.apache.hadoop.hdfs.server.datanode.DataNode: Failed to read block blk_1073742023_1199",
    "log_level": "ERROR",
    "source": "hdfs_datanode",
    "timestamp": "2025-09-26T10:30:54.737Z",
    "node_type": "datanode",
    "label": null
}
```

## Monitoring and Statistics

The processor provides comprehensive monitoring:

### Real-time Statistics
- Lines read from log files
- Lines processed and sent to Kafka
- Processing rate (lines/second)
- Error count
- Cache hit rates

### Log Filtering
The system intelligently filters logs to focus on anomaly-relevant entries:
- **Includes**: ERROR, WARN, Exception, Failed, timeout, connection issues
- **Excludes**: Verbose DEBUG operations (routine reads/writes)

### Statistics Output Example
```
📊 Stats: 1540 read, 127 processed, 127 sent to Kafka, 0 errors, 12.3 lines/sec
```

## Service Management

### Systemd Service Commands

```bash
# Start service
sudo systemctl start hdfs-log-processor

# Stop service
sudo systemctl stop hdfs-log-processor

# Restart service
sudo systemctl restart hdfs-log-processor

# Check status
sudo systemctl status hdfs-log-processor

# View logs
sudo journalctl -u hdfs-log-processor -f

# Enable auto-start
sudo systemctl enable hdfs-log-processor

# Disable auto-start
sudo systemctl disable hdfs-log-processor
```

### Manual Control

```bash
# Start manually
/opt/hdfs-anomaly-detection/start_processor.sh

# Check if running
ps aux | grep hdfs_production_log_processor

# Kill process
pkill -f hdfs_production_log_processor
```

## Logs and Debugging

### Application Logs
```bash
# Service logs
sudo journalctl -u hdfs-log-processor -f

# Application log file
tail -f /opt/hdfs-anomaly-detection/logs/hdfs_log_processor.log
```

### Debug Information
```bash
# Check HDFS log file permissions
ls -la /var/log/hadoop-hdfs/

# Test Kafka connectivity
echo "test message" | kafka-console-producer.sh --bootstrap-server localhost:9092 --topic logs

# Check scoring service
curl http://localhost:8003/health
```

## Troubleshooting

### Common Issues

1. **Log file not found**
   ```bash
   # Find HDFS DataNode logs
   find /var/log -name "*datanode*.log" 2>/dev/null
   ```

2. **Permission denied**
   ```bash
   # Fix log file permissions
   sudo chmod 644 /var/log/hadoop-hdfs/*.log
   sudo chown hadoop:hadoop /var/log/hadoop-hdfs/*.log
   ```

3. **Kafka connection failed**
   ```bash
   # Check Kafka status
   sudo systemctl status kafka
   
   # Test Kafka connectivity
   telnet localhost 9092
   ```

4. **Python dependencies missing**
   ```bash
   # Reinstall dependencies
   /opt/hdfs-anomaly-detection/venv/bin/pip install -r requirements_production.txt
   ```

### Performance Tuning

1. **Increase file descriptor limits**:
   ```bash
   # Add to /etc/security/limits.conf
   hadoop soft nofile 65536
   hadoop hard nofile 65536
   ```

2. **Adjust Kafka producer settings** in the code:
   ```python
   self.producer = KafkaProducer(
       batch_size=32768,  # Increase batch size
       linger_ms=50,      # Increase batching delay
       compression_type='gzip'  # Enable compression
   )
   ```

## Integration with Anomaly Detection

This processor is designed to work with the existing anomaly detection pipeline:

1. **Kafka Topic**: Sends preprocessed logs to `logs` topic
2. **Message Format**: Compatible with existing scoring service
3. **Labels**: Initially `null`, filled by anomaly detection service
4. **Metadata**: Includes log level, source, timestamp for analysis

## Production Deployment Checklist

- [ ] EMR DataNode access configured
- [ ] Kafka cluster accessible
- [ ] Scoring service running
- [ ] Log file permissions correct
- [ ] Service installed and enabled
- [ ] Monitoring configured
- [ ] Backup/recovery procedures in place
- [ ] Resource limits configured
- [ ] Network security groups allow Kafka traffic

## Support and Maintenance

### Regular Maintenance Tasks

1. **Monitor disk usage**: Log files can grow large
2. **Check service health**: Ensure service is running
3. **Update dependencies**: Keep Python packages updated
4. **Review statistics**: Monitor processing rates and errors
5. **Log rotation**: Configure log rotation for application logs

### Health Checks

```bash
# Service health check script
#!/bin/bash
if systemctl is-active --quiet hdfs-log-processor; then
    echo "✅ HDFS Log Processor is running"
else
    echo "❌ HDFS Log Processor is not running"
    sudo systemctl start hdfs-log-processor
fi
```

This production-ready system provides robust, real-time HDFS log processing for anomaly detection in EMR environments.
