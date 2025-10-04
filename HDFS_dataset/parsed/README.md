# Parsed HDFS Data

## Overview
Structured and processed HDFS log data ready for machine learning and analysis.

## Files
- `HDFS.log_structured.csv` - Fully parsed and structured log entries
- `HDFS.log_templates.csv` - Extracted log templates and patterns

## Data Format
**HDFS.log_structured.csv** contains:
- **Timestamp**: Log entry timestamp
- **Component**: HDFS system component (DataNode, NameNode, etc.)
- **Template**: Standardized log template
- **Parameters**: Extracted variable parameters
- **Block ID**: Unique block identifier for anomaly correlation

**HDFS.log_templates.csv** contains:
- **Template ID**: Unique template identifier
- **Template**: Log pattern with parameter placeholders
- **Count**: Frequency of template occurrence

## Usage
This structured data is used by:
- Training module for model development
- Evaluation module for testing
- Analysis scripts for research

## Processing
Generated from raw HDFS.log using the parsing utilities with template extraction and parameter normalization for consistent ML feature engineering.
