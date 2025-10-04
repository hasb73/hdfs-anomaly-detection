# HDFS Dataset

## Overview
Primary HDFS log dataset containing 575,000 log entries with ground truth labels for anomaly detection research.

## Files
- `HDFS.log` - Raw HDFS log data (575K records) - to be downloaded from loghub
- `parser.py` - DRAIN3 Log parsing and preprocessing utilities
- `parsed/` - Directory containing structured log data
  - `HDFS.log_structured.csv` - Parsed and structured log entries
  - `HDFS.log_templates.csv` - Extracted log templates (49)
- `labels/` - Ground truth anomaly labels
  - `anomaly_label.csv` - Binary anomaly classifications at block level

## Dataset Details
- **Total Records**: 575,649 log entries
- **Time Range**: Production HDFS cluster logs
- **Format**: Semi-structured text logs with timestamps
- **Labels**: Binary classification (normal/anomaly)
- **Source**: Real-world Hadoop Distributed File System

## Features
- **Pre-processed Data**: Ready-to-use structured format
- **Template Extraction**: Automated log template identification
- **Ground Truth**: Manually verified anomaly labels
- **Research Ready**: Academic-grade dataset for ML research

## Usage
```bash
# Parse raw logs (if needed)
python3 HDFS_dataset/parser.py

# Structured data available at:
# - HDFS_dataset/parsed/HDFS.log_structured.csv
# - HDFS_dataset/labels/anomaly_label.csv
```

## Data Format
- **Structured CSV**: Timestamp, component, log template, parameters
- **Labels CSV**: Block ID, anomaly status (0=normal, 1=anomaly)
- **Templates**: Unique log patterns with parameter placeholders
