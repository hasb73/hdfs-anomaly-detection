# Model Performance Dashboard

## Overview

The Model Performance Dashboard provides comprehensive insights into the individual machine learning models that make up the anomaly detection ensemble. This dashboard helps data scientists and ML engineers understand how each model contributes to the final predictions and identify potential performance issues.

## Dashboard Panels

### 1. Model Voting Distribution (Pie Chart)
- **Purpose**: Shows the percentage of anomaly votes from each model
- **Query**: Aggregates model votes from JSON data in `model_votes` column
- **Models Tracked**:
  - Decision Tree
  - MLP Neural Network  
  - SGD Classifier
  - Qdrant Similarity
- **Use Case**: Identify which models are most/least aggressive in anomaly detection

### 2. Model Vote Counts (Bar Chart)
- **Purpose**: Displays absolute counts of anomaly vs normal votes per model
- **Visualization**: Side-by-side comparison of vote counts
- **Use Case**: Understand the volume of predictions from each model

### 3. Confidence Score Distribution (Bar Chart)
- **Purpose**: Shows distribution of anomaly scores across different ranges
- **Score Ranges**: 0.0-0.1, 0.1-0.2, ..., 0.9-1.0
- **Use Case**: Identify score patterns and potential calibration issues

### 4. Hourly Performance Trends (Time Series)
- **Purpose**: Tracks performance metrics over time
- **Metrics**: Total predictions, anomalies detected, anomaly rate, processing time
- **Time Window**: Last 24 hours with hourly aggregation
- **Use Case**: Monitor performance degradation or improvements over time

### 5. Model Performance Summary (Table)
- **Purpose**: Comprehensive tabular view of all model statistics
- **Columns**: Model name, anomaly votes, normal votes, anomaly percentage
- **Features**: Color-coded anomaly percentages with thresholds
- **Use Case**: Quick reference for model comparison

### 6. Processing Time by Source (Donut Chart)
- **Purpose**: Shows average processing time breakdown by data source
- **Metrics**: Average processing time in milliseconds
- **Use Case**: Identify performance bottlenecks by data source

### 7. Confidence vs Prediction Heatmap
- **Purpose**: Visualizes relationship between confidence levels and predictions
- **Dimensions**: Confidence levels (Low/Medium/High) vs Prediction types (Normal/Anomaly)
- **Use Case**: Identify patterns in model confidence and prediction accuracy

## Key Insights

### Model Behavior Analysis
- **Ensemble Balance**: Check if any single model dominates the voting
- **Model Agreement**: Identify cases where models disagree significantly
- **Confidence Patterns**: Understand how confidence correlates with predictions

### Performance Monitoring
- **Processing Efficiency**: Monitor processing times across different sources
- **Temporal Patterns**: Track how model performance changes over time
- **Score Calibration**: Ensure anomaly scores are well-distributed

### Troubleshooting Use Cases
- **Model Drift**: Detect when individual models start behaving differently
- **Performance Degradation**: Identify processing time increases
- **Confidence Issues**: Spot models with consistently low confidence

## Dashboard Configuration

- **Refresh Rate**: 30 seconds
- **Time Range**: Last 1 hour (configurable)
- **Data Source**: SQLite anomaly detection database
- **Auto-refresh**: Enabled

## Access Information

- **URL**: http://localhost:3000/d/model-performance-dashboard
- **Dashboard ID**: `model-performance-dashboard`
- **Tags**: `anomaly-detection`, `model-performance`

## Related Dashboards

- **System Overview Dashboard**: High-level system metrics
- **Anomaly Analysis Dashboard**: Detailed anomaly pattern analysis
- **Operations Monitor Dashboard**: System health and alerts

## Technical Notes

### Query Performance
- All queries use indexed columns for optimal performance
- JSON extraction functions used for model vote analysis
- Time-based queries limited to recent data for faster response

### Data Dependencies
- Requires `anomaly_detections` table with `model_votes` JSON column
- Depends on `confidence`, `anomaly_score`, and `processing_time_ms` fields
- Uses `created_at` timestamp for time-series analysis

### Customization Options
- Time ranges can be adjusted using Grafana time picker
- Panel queries can be modified for different aggregation periods
- Thresholds and color schemes can be customized per panel