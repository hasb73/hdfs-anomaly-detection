# HDFS Production Log Processor - File Summary

## Overview
This package provides a complete solution for real-time HDFS DataNode log processing and anomaly detection in Amazon EMR production environments.

## File Structure

```
hdfs-anomaly-detection/
├── hdfs_production_log_processor.py      # Main log processor application
├── deploy_emr_log_processor.sh           # EMR deployment script
├── test_hdfs_preprocessing.py            # Preprocessing validation tests
├── requirements_production.txt           # Python dependencies
├── EMR_PRODUCTION_DEPLOYMENT.md          # Comprehensive deployment guide
└── anomaly_evaluation.py                 # Original evaluation script (reference)
```

## File Descriptions

### Core Application Files

#### `hdfs_production_log_processor.py`
**Purpose**: Main application for real-time HDFS log processing
**Key Features**:
- Real-time log file monitoring using filesystem events
- Intelligent log preprocessing to remove dynamic content
- Kafka streaming with configurable topics
- Production-ready logging and statistics
- Graceful shutdown and error handling
- EMR-optimized log filtering

**Usage**:
```bash
python3 hdfs_production_log_processor.py <log_file_path> [kafka_servers] [kafka_topic] [scoring_service_url]
```

**Classes**:
- `HDFSLogPreprocessor`: Handles log preprocessing and pattern replacement
- `HDFSLogTailer`: Monitors log files and processes new entries
- `HDFSProductionLogProcessor`: Main orchestration class

#### `deploy_emr_log_processor.sh`
**Purpose**: Automated deployment script for EMR DataNodes
**Key Features**:
- Automatic HDFS log file detection
- System dependency installation
- Python virtual environment setup
- Systemd service creation
- Configuration file generation
- Permission and validation checks

**Usage**:
```bash
sudo ./deploy_emr_log_processor.sh [log_file_path]
```

**What it does**:
1. Installs system dependencies (Python 3, pip, gcc)
2. Creates `/opt/hdfs-anomaly-detection/` directory structure
3. Sets up Python virtual environment
4. Installs Python packages
5. Creates systemd service (`hdfs-log-processor`)
6. Generates configuration files
7. Sets proper permissions

#### `test_hdfs_preprocessing.py`
**Purpose**: Validation and testing script for preprocessing logic
**Key Features**:
- Tests preprocessing patterns with sample HDFS logs
- Validates log relevance filtering
- Tests Kafka message format creation
- Pattern matching verification

**Usage**:
```bash
python3 test_hdfs_preprocessing.py
```

**Test Results** (from our run):
- ✅ Correctly filters out verbose DEBUG operations
- ✅ Includes ERROR, WARN, and anomaly-relevant logs  
- ✅ Properly replaces dynamic content (IPs, timestamps, block IDs)
- ✅ Generates correct Kafka message format

### Configuration and Dependencies

#### `requirements_production.txt` 
**Purpose**: Python dependencies for production deployment
**Dependencies**:
```
kafka-python==2.0.2    # Kafka integration
requests==2.31.0       # HTTP requests to scoring service
pandas==2.0.3          # Data processing
urllib3==2.0.4         # HTTP library
watchdog==3.0.0        # File system monitoring
setuptools>=65.0.0     # Package installation
wheel>=0.37.0          # Wheel support
```

### Documentation

#### `EMR_PRODUCTION_DEPLOYMENT.md`
**Purpose**: Comprehensive deployment and operation guide
**Sections**:
- Installation instructions
- Configuration options
- Log preprocessing details
- Service management
- Monitoring and troubleshooting
- Performance tuning
- Production checklist

### Reference Files

#### `anomaly_evaluation.py`
**Purpose**: Original evaluation script (reference implementation)
**Note**: This was the basis for the production processor but focuses on batch testing rather than real-time processing.

## Deployment Workflow

### Quick Deployment (Recommended)
```bash
# 1. Copy files to EMR DataNode
scp hdfs_production_log_processor.py hadoop@<datanode-ip>:~
scp deploy_emr_log_processor.sh hadoop@<datanode-ip>:~

# 2. SSH to DataNode and deploy
ssh hadoop@<datanode-ip>
sudo ./deploy_emr_log_processor.sh

# 3. Start service
sudo systemctl start hdfs-log-processor
sudo systemctl enable hdfs-log-processor
```

### Manual Deployment
```bash
# 1. Install dependencies
pip3 install -r requirements_production.txt

# 2. Run directly
python3 hdfs_production_log_processor.py /var/log/hadoop-hdfs/hadoop-hdfs-datanode-*.log
```

## Key Features Implemented

### Log Preprocessing
- **Dynamic Content Removal**: Timestamps, IP addresses, ports, block IDs, client IDs, UUIDs, hostnames, numeric values
- **Pattern Preservation**: Maintains error patterns and anomaly indicators
- **Smart Filtering**: Focuses on anomaly-relevant logs (ERROR, WARN, exceptions)

### Real-time Processing
- **File System Monitoring**: Uses `watchdog` for real-time log file changes
- **Kafka Integration**: Streams processed logs to configurable Kafka topics
- **Background Processing**: Runs as systemd service with auto-restart

### Production Features
- **Statistics Reporting**: Lines processed, error rates, processing speed
- **Graceful Shutdown**: Signal handling for clean termination  
- **Comprehensive Logging**: Application logs with configurable levels
- **Error Handling**: Robust error handling and recovery
- **Resource Management**: Proper file handle management and cleanup

### EMR Integration
- **Auto-discovery**: Automatically finds HDFS DataNode log files
- **Permission Handling**: Proper user/group permissions for hadoop user
- **Service Integration**: Systemd service with dependency management
- **EMR-specific Patterns**: Handles EMR-specific log formats and paths

## Message Format

### Input (Raw HDFS Log)
```
2025-09-25 09:31:02,123 ERROR org.apache.hadoop.hdfs.server.datanode.DataNode: Failed to read block blk_1073742024_1200 from disk
```

### Output (Kafka Message)
```json
{
  "text": "TIMESTAMP ERROR org.apache.hadoop.hdfs.server.datanode.DataNode: Failed to read block BLOCK_ID from disk",
  "original_text": "2025-09-25 09:31:02,123 ERROR org.apache.hadoop.hdfs.server.datanode.DataNode: Failed to read block blk_1073742024_1200 from disk",
  "log_level": "ERROR",
  "source": "hdfs_datanode", 
  "timestamp": "2025-09-26T16:51:53.731068",
  "node_type": "datanode",
  "label": null
}
```

## Integration Points

### Kafka
- **Topic**: `logs` (configurable)
- **Format**: JSON messages with original and preprocessed text
- **Compatibility**: Works with existing anomaly detection pipeline

### Scoring Service
- **Health Checks**: Optional connectivity to anomaly detection service
- **URL**: Configurable scoring service endpoint
- **Fallback**: Continues operation even if scoring service unavailable

### System Integration
- **Systemd Service**: `hdfs-log-processor.service`
- **Logs**: `/var/log/hdfs_log_processor.log` and journalctl
- **Configuration**: `/opt/hdfs-anomaly-detection/config/processor_config.json`

## Production Readiness Checklist

- ✅ **Real-time Processing**: Monitors log files using filesystem events
- ✅ **Preprocessing**: Removes dynamic content while preserving patterns
- ✅ **Kafka Integration**: Reliable message streaming with error handling
- ✅ **Service Management**: Systemd service with auto-restart
- ✅ **Logging & Monitoring**: Comprehensive logging and statistics
- ✅ **Error Handling**: Robust error handling and recovery
- ✅ **EMR Compatibility**: Designed for EMR DataNode environments
- ✅ **Security**: Proper permissions and user isolation
- ✅ **Documentation**: Complete deployment and operation guide
- ✅ **Testing**: Validation scripts and test coverage

This production-ready package provides everything needed to deploy real-time HDFS anomaly detection on Amazon EMR clusters.
