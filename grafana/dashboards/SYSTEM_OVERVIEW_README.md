# System Overview Dashboard

## Overview

The System Overview Dashboard provides a comprehensive real-time view of the anomaly detection system's performance and health. This dashboard is designed for system administrators and operators who need to monitor the overall system status at a glance.

## Dashboard Features

### 1. Real-time Performance Metrics

**Accuracy Gauge**
- Displays current system accuracy as a percentage
- Color-coded thresholds: Green (≥85%), Yellow (70-85%), Red (<70%)
- Updates every 30 seconds
- Based on predictions from the last hour

**Precision Gauge**
- Shows current precision metric from the latest performance evaluation
- Same color-coding as accuracy gauge
- Sourced from the `performance_metrics` table

**Recall Gauge**
- Displays current recall metric
- Color-coded for quick status assessment
- Real-time updates from performance metrics

**F1 Score Gauge**
- Shows the harmonic mean of precision and recall
- Critical metric for overall model performance assessment
- Color-coded thresholds for immediate status recognition

### 2. Anomaly Rate Monitoring

**Anomaly Rate Gauge**
- Displays the percentage of predictions classified as anomalies in the last hour
- Configurable thresholds: Green (0-30%), Yellow (30-50%), Red (>50%)
- Helps identify unusual spikes in anomaly detection
- Essential for detecting system drift or data quality issues

### 3. Processing Performance

**Average Processing Time Gauge**
- Shows average processing time per prediction in milliseconds
- Thresholds: Green (≤100ms), Yellow (100-200ms), Red (>200ms)
- Critical for monitoring system performance and scalability
- Based on the last hour of processing data

### 4. System Health Indicator

**Health Status Panel**
- Combines accuracy and processing time into a single health indicator
- Status levels:
  - **Healthy**: Accuracy ≥90% AND Processing time ≤100ms
  - **Warning**: Accuracy ≥80% AND Processing time ≤200ms
  - **Critical**: Below warning thresholds
- Color-coded background for immediate visual feedback

### 5. Performance Trends

**Time Series Chart**
- Displays hourly trends over the last 24 hours
- Multiple metrics on one chart:
  - Hourly accuracy percentage
  - Average processing time
  - Average confidence percentage
  - Anomaly rate percentage
- Helps identify patterns and performance degradation over time

### 6. Prediction Distribution

**Pie Chart Visualization**
- Shows the distribution of normal vs anomaly predictions in the last hour
- Helps understand the current workload composition
- Useful for identifying unusual patterns in data flow

## Data Sources

The dashboard queries data from two main tables:

### anomaly_detections Table
- Individual prediction records with timestamps
- Contains: `predicted_label`, `actual_label`, `anomaly_score`, `confidence`, `processing_time_ms`, `is_correct`
- Used for real-time calculations and trend analysis

### performance_metrics Table
- Aggregated performance statistics
- Contains: `accuracy`, `precision`, `recall`, `f1_score`, `total_predictions`
- Used for official performance metrics display

## Refresh and Time Settings

- **Auto-refresh**: 30 seconds
- **Default time range**: Last 1 hour
- **Trend analysis**: Last 24 hours
- **Time zone**: System default

## Thresholds and Alerts

### Performance Thresholds
- **Accuracy**: Warning <90%, Critical <80%
- **Processing Time**: Warning >100ms, Critical >200ms
- **Anomaly Rate**: Warning >30%, Critical >50%

### Visual Indicators
- **Green**: System performing optimally
- **Yellow**: Performance degradation detected
- **Red**: Critical issues requiring attention

## Usage Guidelines

### For System Administrators
1. Monitor the System Health Status panel for overall system state
2. Check performance gauges for any metrics below acceptable thresholds
3. Use the Performance Trends chart to identify degradation patterns
4. Monitor Anomaly Rate for unusual spikes that might indicate data quality issues

### For Operations Teams
1. Set up alerts based on the health status and threshold breaches
2. Use processing time metrics to plan capacity and scaling
3. Monitor prediction distribution to understand workload patterns
4. Track trends to identify optimal maintenance windows

### Troubleshooting
- **No Data**: Check if the anomaly detection system is running and writing to the database
- **Stale Data**: Verify database connectivity and recent prediction activity
- **Performance Issues**: Check processing time trends and system resource utilization

## Technical Details

### Query Performance
- All queries are optimized for real-time performance
- Time-based filtering uses indexed timestamp columns
- Aggregations are limited to recent data to maintain responsiveness

### Database Requirements
- SQLite database with `anomaly_detections` and `performance_metrics` tables
- Proper indexing on timestamp columns for optimal performance
- Regular database maintenance for consistent performance

### Grafana Configuration
- Uses the frser-sqlite-datasource plugin
- Configured for 30-second refresh intervals
- Responsive design for desktop and tablet viewing

## Customization

### Modifying Thresholds
To adjust performance thresholds, edit the gauge panel configurations:
1. Open the dashboard in edit mode
2. Select the gauge panel to modify
3. Update the threshold values in the Field options
4. Save the dashboard

### Adding New Metrics
To add additional metrics:
1. Create new SQL queries based on available database columns
2. Add new panels using the Grafana panel editor
3. Configure appropriate visualizations and thresholds
4. Update this documentation

### Time Range Adjustments
Default time ranges can be modified in the dashboard settings:
- Panel-specific time overrides in individual panel settings
- Global time range in dashboard time picker settings

## Related Dashboards

This dashboard is part of a comprehensive monitoring suite:
- **Model Performance Dashboard**: Detailed model analysis and confusion matrices
- **Anomaly Analysis Dashboard**: Deep dive into anomaly patterns and sources
- **Operations Monitor Dashboard**: System alerts and operational metrics

## Support and Maintenance

### Regular Maintenance
- Monitor dashboard performance and query execution times
- Update thresholds based on system performance baselines
- Review and optimize queries as data volume grows

### Troubleshooting Resources
- Check Grafana logs for query errors
- Validate database connectivity using the test scripts
- Review system resource utilization during high-load periods