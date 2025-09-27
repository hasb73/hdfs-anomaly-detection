# Grafana Anomaly Detection Dashboards

This directory contains all Grafana-related files for the anomaly detection monitoring system.

## 📁 Directory Structure

```
grafana/
├── dashboards/                          # Dashboard JSON files
│   ├── simple-anomaly-dashboard.json    # Simple monitoring dashboard
│   ├── system-overview-dashboard.json   # Comprehensive system dashboard
│   └── SYSTEM_OVERVIEW_README.md        # Dashboard documentation
├── provisioning/                        # Grafana provisioning configs
│   ├── datasources/                     # Datasource configurations
│   └── dashboards/                      # Dashboard provisioning
├── deploy_dashboards.py                 # Dashboard deployment script
├── docker-compose-grafana.yml           # Docker Compose configuration
├── grafana.ini                          # Grafana configuration
├── start-grafana.sh                     # Start Grafana script
├── stop-grafana.sh                      # Stop Grafana script
├── test-grafana-setup.sh                # Setup validation script
└── README.md                            # This file
```

## 🚀 Quick Start

### 1. Start Grafana
```bash
cd grafana
./start-grafana.sh
```

### 2. Deploy Dashboards
```bash
cd grafana
python3 deploy_dashboards.py
```

### 3. Access Grafana
- **URL**: http://localhost:3000
- **Username**: admin
- **Password**: admin123

## 📊 Available Dashboards

### Simple Anomaly Dashboard
- **Purpose**: Basic monitoring with key metrics
- **Panels**: Total Anomalies + Average Processing Time
- **Best for**: Quick status checks

### System Overview Dashboard  
- **Purpose**: Comprehensive system monitoring
- **Panels**: All metrics, gauges, health indicators, charts
- **Best for**: Detailed analysis and troubleshooting

## 🔧 Management Scripts

### Start/Stop Grafana
```bash
./start-grafana.sh    # Start Grafana container
./stop-grafana.sh     # Stop Grafana container
```

### Deploy Dashboards
```bash
python3 deploy_dashboards.py    # Deploy all dashboards from dashboards/
```

### Test Setup
```bash
./test-grafana-setup.sh    # Validate Grafana configuration
```

## 📋 Requirements

- Docker and Docker Compose
- Python 3 with requests library
- SQLite database file (`../anomaly_detection.db`)

## 🔧 Configuration

### Datasource
- **Type**: SQLite (frser-sqlite-datasource plugin)
- **Database**: `../anomaly_detection.db`
- **Auto-provisioned**: Yes

### Dashboards
- **Auto-provisioned**: Yes (from `dashboards/` directory)
- **Refresh**: 30 seconds
- **Time Range**: Last 1 hour (configurable)

## 🎯 Adding New Dashboards

1. Create dashboard JSON file in `dashboards/` directory
2. Run `python3 deploy_dashboards.py`
3. Dashboard will be automatically deployed to Grafana

## 🐛 Troubleshooting

### Grafana Won't Start
```bash
# Check if database exists
ls -la ../anomaly_detection.db

# Validate Docker Compose config
docker-compose -f docker-compose-grafana.yml config

# Check logs
docker-compose -f docker-compose-grafana.yml logs grafana
```

### No Data in Dashboards
```bash
# Test database connection
python3 test_sqlite_datasource.py

# Check datasource configuration
cat provisioning/datasources/sqlite.yml
```

### Dashboard Not Loading
```bash
# Redeploy dashboards
python3 deploy_dashboards.py

# Check dashboard files
ls -la dashboards/*.json
```

## 📈 Current Data

The dashboards display real-time data from your anomaly detection system:
- **Total Anomalies**: Live count of detected anomalies
- **Processing Time**: Average processing time per prediction
- **System Health**: Overall system status
- **Anomaly Rate**: Percentage of predictions that are anomalies

## 🎉 Features

- ✅ **Auto-provisioning**: Dashboards and datasources configured automatically
- ✅ **Real-time updates**: Data refreshes every 30 seconds
- ✅ **Responsive design**: Works on desktop and mobile
- ✅ **Easy deployment**: Single script deploys all dashboards
- ✅ **Health monitoring**: System status indicators
- ✅ **Performance metrics**: Processing time and throughput tracking