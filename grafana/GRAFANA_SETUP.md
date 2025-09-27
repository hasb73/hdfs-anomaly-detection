# Grafana Anomaly Detection Dashboards Setup

This setup provides a Docker-based Grafana environment with SQLite support for visualizing anomaly detection data.

## Prerequisites

- Docker and Docker Compose installed
- `anomaly_detection.db` SQLite database file in the project root
- Port 3000 available on your system

## Quick Start

1. **Start Grafana:**
   ```bash
   ./start-grafana.sh
   ```

2. **Verify Setup (Optional):**
   ```bash
   ./verify-grafana-setup.sh
   ```

3. **Access Grafana:**
   - URL: http://localhost:3000
   - Username: `admin`
   - Password: `admin123`

4. **Stop Grafana:**
   ```bash
   ./stop-grafana.sh
   ```

## Configuration Details

### Docker Compose Configuration
- **File:** `docker-compose-grafana.yml`
- **Container:** `anomaly-grafana`
- **Port:** 3000 (host) → 3000 (container)
- **Plugins:** SQLite datasource plugin (`frser-sqlite-datasource`)

### Volume Mounts
- `./anomaly_detection.db` → `/var/lib/grafana/data/anomaly_detection.db` (read-only)
- `grafana-data` → `/var/lib/grafana` (persistent Grafana data)
- `grafana-logs` → `/var/log/grafana` (log files)
- `./grafana/provisioning` → `/etc/grafana/provisioning` (configuration)
- `./grafana/dashboards` → `/var/lib/grafana/dashboards` (dashboard files)

### Environment Variables
- **Security:** Admin credentials, user signup disabled
- **Plugins:** SQLite datasource auto-installation
- **Database:** SQLite backend for Grafana metadata
- **Analytics:** Disabled for privacy

### Data Source Configuration
- **Name:** AnomalyDetectionDB
- **Type:** SQLite (frser-sqlite-datasource)
- **Path:** `/var/lib/grafana/data/anomaly_detection.db`
- **Access:** Proxy mode for security

## Directory Structure

```
├── docker-compose-grafana.yml    # Main Docker Compose configuration
├── start-grafana.sh             # Startup script
├── stop-grafana.sh              # Stop script
├── grafana/
│   ├── grafana.ini              # Grafana configuration
│   ├── provisioning/
│   │   ├── datasources/
│   │   │   └── sqlite.yml       # SQLite datasource config
│   │   └── dashboards/
│   │       └── dashboards.yml   # Dashboard provisioning config
│   └── dashboards/              # Dashboard JSON files (to be added)
└── anomaly_detection.db         # SQLite database (required)
```

## Troubleshooting

### Common Issues

1. **Port 3000 already in use:**
   ```bash
   # Check what's using port 3000
   lsof -i :3000
   # Kill the process or change the port in docker-compose-grafana.yml
   ```

2. **Database file not found:**
   - Ensure `anomaly_detection.db` exists in the project root
   - Check file permissions (should be readable)

3. **Plugin installation fails:**
   ```bash
   # Check container logs
   docker-compose -f docker-compose-grafana.yml logs grafana
   ```

4. **Grafana won't start:**
   ```bash
   # View detailed logs
   docker-compose -f docker-compose-grafana.yml logs -f grafana
   ```

### Useful Commands

```bash
# View container status
docker-compose -f docker-compose-grafana.yml ps

# View logs
docker-compose -f docker-compose-grafana.yml logs -f grafana

# Restart Grafana
docker-compose -f docker-compose-grafana.yml restart grafana

# Remove all data and start fresh
docker-compose -f docker-compose-grafana.yml down -v
./start-grafana.sh

# Access container shell
docker-compose -f docker-compose-grafana.yml exec grafana /bin/bash
```

## Security Notes

- Default admin credentials are set to `admin/admin123`
- Change these credentials in production environments
- The SQLite database is mounted read-only for security
- Anonymous access is disabled
- User signup is disabled

## Next Steps

After completing this setup:
1. Configure the SQLite data source (automatically provisioned)
2. Create dashboard configurations
3. Import or create dashboard panels
4. Set up alerting rules
5. Configure user access and permissions

## Health Check

The container includes a health check that verifies Grafana is responding on port 3000. You can check the health status with:

```bash
docker-compose -f docker-compose-grafana.yml ps
```

Look for "healthy" status in the State column.