# SQLite Data Source Configuration for Grafana

## Overview

This document describes the SQLite data source configuration for the Grafana anomaly detection dashboards. The configuration includes connection settings, error handling, performance optimization, and comprehensive testing.

## Configuration Files

### 1. Primary Data Source Configuration
**File:** `grafana/provisioning/datasources/sqlite.yml`

```yaml
apiVersion: 1
datasources:
  - name: AnomalyDetectionDB
    type: frser-sqlite-datasource
    access: proxy
    url: file:///var/lib/grafana/data/anomaly_detection.db
    isDefault: true
    editable: true
    jsonData:
      path: /var/lib/grafana/data/anomaly_detection.db
      maxOpenConns: 10
      maxIdleConns: 2
      connMaxLifetime: 14400
      queryTimeout: 30
      validateConnection: true
    uid: anomaly-detection-sqlite
    orgId: 1
```

### 2. Advanced Configuration (Optional)
**File:** `grafana/provisioning/datasources/sqlite_advanced.yml`

Includes additional features:
- Connection retry logic
- Query caching
- SQLite-specific optimizations
- Backup data source configuration

## Database Schema

The SQLite database contains two main tables:

### anomaly_detections
- **Primary Key:** `id` (INTEGER, AUTO INCREMENT)
- **Temporal Fields:** `timestamp`, `created_at`
- **Prediction Data:** `predicted_label`, `actual_label`, `anomaly_score`, `confidence`
- **Metadata:** `text`, `text_hash`, `source`, `model_votes`
- **Performance:** `processing_time_ms`, `is_correct`

### performance_metrics
- **Primary Key:** `id` (INTEGER, AUTO INCREMENT)
- **Metrics:** `accuracy`, `precision`, `recall`, `f1_score`
- **Confusion Matrix:** `true_positives`, `false_positives`, `true_negatives`, `false_negatives`
- **Aggregates:** `total_predictions`, `avg_processing_time_ms`
- **Temporal:** `timestamp`, `created_at`

## Connection Configuration

### Connection Pool Settings
- **Max Open Connections:** 10
- **Max Idle Connections:** 2
- **Connection Lifetime:** 4 hours (14400 seconds)
- **Query Timeout:** 30 seconds

### Error Handling
- **Connection Validation:** Enabled
- **Retry Attempts:** 3 (in advanced config)
- **Retry Delay:** 1 second between attempts
- **Timeout Handling:** Graceful degradation with cached data

### Performance Optimization
- **Query Caching:** Enabled (5-minute cache)
- **SQLite WAL Mode:** Write-Ahead Logging for better concurrency
- **Busy Timeout:** 30 seconds
- **Cache Size:** 10,000 pages

## Validation and Testing

### 1. Database Connection Test
```bash
# Run from project root directory
python3 grafana/test_sqlite_datasource.py
```

**Features:**
- Connection establishment validation
- Schema structure verification
- Data quality assessment
- Query performance testing
- Comprehensive reporting

### 2. Grafana Integration Test
```bash
# Run from project root directory
./grafana/validate_grafana_datasource.sh
```

**Features:**
- Grafana service status check
- Database accessibility from container
- Data source API validation
- Sample query execution
- Provisioning configuration validation

### 3. Test Query Collection
**File:** `grafana/grafana_test_queries.sql`

Contains 18 comprehensive test queries covering:
- System overview metrics
- Model performance analysis
- Anomaly detection patterns
- Operations monitoring
- Alert conditions
- Data freshness checks

## Query Categories

### System Overview Queries
1. **Real-time Metrics:** Current accuracy, processing time, anomaly rate
2. **Health Status:** System health based on performance thresholds
3. **Anomaly Rate:** Current anomaly detection rate with time windows

### Model Performance Queries
4. **Confusion Matrix:** Prediction accuracy breakdown
5. **Model Voting:** Individual model contribution analysis
6. **Confidence Distribution:** Score distribution and accuracy correlation
7. **Performance Trends:** Time-series performance metrics

### Anomaly Analysis Queries
8. **Anomaly Timeline:** Recent anomaly events with details
9. **Source Analysis:** Performance breakdown by data source
10. **Score Distribution:** Anomaly score patterns comparison

### Operations Monitoring Queries
11. **Processing Performance:** Response time metrics and trends
12. **Error Rate Monitoring:** Prediction accuracy and missing data tracking
13. **Data Volume:** Daily prediction volumes and source activity

### Performance Metrics Queries
14. **Latest Metrics:** Current performance from dedicated metrics table
15. **Metrics Trends:** Historical performance trend analysis

### Alert and Health Queries
16. **Alert Conditions:** Threshold-based alert status checking
17. **Data Freshness:** Data staleness and health monitoring
18. **Database Statistics:** Overall system statistics and health

## Security Configuration

### Authentication
- **Admin User:** admin
- **Admin Password:** admin123 (change in production)
- **Anonymous Access:** Disabled
- **User Registration:** Disabled

### File Permissions
- **Database File:** Read-only mount in container
- **Grafana Data:** Persistent volume with proper permissions
- **Configuration Files:** Read-only provisioning mounts

## Troubleshooting

### Common Issues

1. **Database Not Found**
   - Verify volume mount in `docker-compose-grafana.yml`
   - Check file path: `./anomaly_detection.db:/var/lib/grafana/data/anomaly_detection.db:ro`

2. **Connection Timeout**
   - Increase `queryTimeout` in data source configuration
   - Check database file permissions
   - Verify SQLite plugin installation

3. **Query Performance Issues**
   - Review query complexity and add appropriate indexes
   - Increase connection pool size if needed
   - Enable query caching for frequently accessed data

4. **Data Source Not Found**
   - Check provisioning directory mount
   - Verify YAML syntax in configuration files
   - Restart Grafana container to reload configuration

### Performance Optimization

1. **Database Indexes**
   - Existing indexes on `timestamp`, `predicted_label`, `actual_label`, `text_hash`
   - Consider additional indexes based on query patterns

2. **Query Optimization**
   - Use time-based filtering for large datasets
   - Limit result sets with appropriate LIMIT clauses
   - Aggregate data at query time rather than storing pre-aggregated results

3. **Connection Management**
   - Monitor connection pool usage
   - Adjust pool size based on concurrent dashboard users
   - Use connection validation to handle stale connections

## Monitoring and Maintenance

### Health Checks
- **Grafana Health:** `curl http://localhost:3000/api/health`
- **Data Source Test:** Via Grafana UI or API
- **Database Connectivity:** SQLite command-line tools

### Regular Maintenance
- **Database Vacuum:** Periodic SQLite VACUUM for performance
- **Log Rotation:** Grafana and application log management
- **Backup Strategy:** Regular database and configuration backups

### Performance Monitoring
- **Query Performance:** Monitor slow queries and optimize
- **Dashboard Load Times:** Track user experience metrics
- **Resource Usage:** Monitor CPU, memory, and disk usage

## Integration with Docker Compose

The configuration integrates with the existing Docker Compose setup:

```yaml
services:
  grafana:
    image: grafana/grafana:latest
    environment:
      - GF_INSTALL_PLUGINS=frser-sqlite-datasource
    volumes:
      - ./anomaly_detection.db:/var/lib/grafana/data/anomaly_detection.db:ro
      - ./grafana/provisioning:/etc/grafana/provisioning:ro
```

## Next Steps

After completing this configuration:

1. **Start Grafana:** `docker-compose -f docker-compose-grafana.yml up -d`
2. **Validate Setup:** Run validation scripts
3. **Create Dashboards:** Use the configured data source to build dashboards
4. **Monitor Performance:** Track query performance and optimize as needed
5. **Set Up Alerts:** Configure Grafana alerts based on the available metrics

## Files Created/Modified

- ✅ `grafana/provisioning/datasources/sqlite.yml` - Enhanced with connection settings
- ✅ `grafana/provisioning/datasources/sqlite_advanced.yml` - Advanced configuration
- ✅ `grafana/test_sqlite_datasource.py` - Comprehensive database testing
- ✅ `grafana/validate_grafana_datasource.sh` - Grafana integration validation
- ✅ `grafana/grafana_test_queries.sql` - Complete query test suite
- ✅ `grafana/SQLITE_DATASOURCE_CONFIG.md` - This documentation

The SQLite data source is now fully configured with robust error handling, performance optimization, and comprehensive testing capabilities.