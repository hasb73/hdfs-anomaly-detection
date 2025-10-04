# HDFS Anomaly Labels

## Overview
Ground truth anomaly labels for the HDFS dataset providing supervised learning targets.

## Files
- `anomaly_label.csv` - Binary anomaly classifications for HDFS blocks

## Data Format
The CSV file contains:
- **Block ID**: Unique HDFS block identifier
- **Label**: Binary classification (0=normal, 1=anomaly)

## Label Distribution
- **Normal Blocks**: Majority of blocks (typical HDFS operations)
- **Anomaly Blocks**: Minority class representing system failures, errors, or unusual patterns
- **Quality**: Manually verified and validated labels

## Usage
These labels are used for:
- **Supervised Training**: Target values for classification models
- **Evaluation**: Ground truth for performance metrics
- **Validation**: Model accuracy assessment
- **Research**: Academic benchmarking and comparison

## Source
Labels are derived from system logs, error reports, and domain expert knowledge to ensure high-quality ground truth for anomaly detection research.
