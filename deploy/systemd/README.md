# systemd Deployment for Project Builder

Production systemd service configuration for bare-metal or VPS deployment.

## Prerequisites

- Ubuntu/Debian Linux (20.04+ or equivalent)
- Docker and Docker Compose installed
- Python 3.12+ with venv
- systemd (standard on most Linux distributions)
- Non-root user with sudo access

## Quick Start

### 1. Install Dependencies

```bash
# Update system
sudo apt-get update && sudo apt-get upgrade -y

# Install Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
newgrp docker

# Install Python and venv
sudo apt-get install -y python3.12 python3.12-venv python3-pip git curl

# Clone repository
cd /home/ui-cli_jake
git clone https://github.com/unified-intelligence-cli.git
cd unified-intelligence-cli

# Create virtual environment
python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure Secrets

```bash
# Create secrets directory
sudo mkdir -p /etc/project-builder
sudo chown ui-cli_jake:ui-cli_jake /etc/project-builder

# Copy template and populate with real values
cp deploy/systemd/secrets.env.template /etc/project-builder/secrets.env

# Edit with your credentials
nano /etc/project-builder/secrets.env

# Secure permissions
chmod 600 /etc/project-builder/secrets.env
```

### 3. Install systemd Service

```bash
# Copy service file
sudo cp deploy/systemd/project-builder.service /etc/systemd/system/

# Reload systemd
sudo systemctl daemon-reload

# Enable service (start on boot)
sudo systemctl enable project-builder.service

# Start service
sudo systemctl start project-builder.service

# Check status
sudo systemctl status project-builder.service
```

### 4. Verify Deployment

```bash
# Check service logs
sudo journalctl -u project-builder.service -f

# Check health endpoint
curl http://localhost:8000/health

# Check metrics
curl http://localhost:8000/metrics
```

## Service Management

### Start/Stop/Restart

```bash
# Start
sudo systemctl start project-builder.service

# Stop
sudo systemctl stop project-builder.service

# Restart
sudo systemctl restart project-builder.service

# Reload configuration (no downtime)
sudo systemctl reload project-builder.service
```

### View Logs

```bash
# Follow logs (tail -f)
sudo journalctl -u project-builder.service -f

# View recent logs
sudo journalctl -u project-builder.service -n 100

# View logs since boot
sudo journalctl -u project-builder.service -b

# View logs for specific time range
sudo journalctl -u project-builder.service --since "1 hour ago"
```

### Enable/Disable Auto-start

```bash
# Enable (start on boot)
sudo systemctl enable project-builder.service

# Disable (don't start on boot)
sudo systemctl disable project-builder.service

# Check if enabled
sudo systemctl is-enabled project-builder.service
```

## Configuration

### Environment Variables

Non-sensitive configuration is set in the service file:
- `PB_ENV=production`
- `PB_LOG_LEVEL=INFO`
- `PB_LOG_FORMAT=json`

Sensitive configuration is in `/etc/project-builder/secrets.env`:
- Database passwords
- API keys
- Tokens

### Resource Limits

Configured in `project-builder.service`:
- **Memory**: 4GB max, 3GB high
- **CPU**: 400% (4 cores)
- **Tasks**: 200 max processes

Adjust in service file if needed:
```ini
MemoryMax=4G
MemoryHigh=3G
CPUQuota=400%
```

### Security Hardening

The service includes multiple security features:
- `NoNewPrivileges=true` - Prevent privilege escalation
- `PrivateTmp=true` - Private /tmp directory
- `ProtectSystem=strict` - Read-only system directories
- `ProtectHome=read-only` - Read-only home (except specified paths)
- `RestrictAddressFamilies` - Limit network protocols
- `PrivateDevices=true` - No access to devices

## Docker Services

The service automatically manages Docker containers:

```bash
# Check running containers
docker ps

# View logs
docker logs project-builder-db
docker logs project-builder-redis
docker logs project-builder-prometheus

# Restart containers manually
docker compose -f docker-compose.production.yml restart
```

## Health Monitoring

### Watchdog

The service includes a watchdog timer (60s). If the health server doesn't respond, systemd will restart the service.

### Manual Health Check

```bash
# HTTP health check
curl http://localhost:8000/health

# Expected response:
# {"status":"healthy","uptime":123.45,"version":"1.0.0"}

# Metrics endpoint
curl http://localhost:8000/metrics
```

### Service Status

```bash
# Full status
sudo systemctl status project-builder.service

# Is service running?
sudo systemctl is-active project-builder.service

# Is service enabled?
sudo systemctl is-enabled project-builder.service

# Is service failed?
sudo systemctl is-failed project-builder.service
```

## Troubleshooting

### Service Won't Start

```bash
# Check service status
sudo systemctl status project-builder.service

# View detailed logs
sudo journalctl -u project-builder.service -xe

# Verify secrets file exists
ls -la /etc/project-builder/secrets.env

# Check file permissions
stat /etc/project-builder/secrets.env

# Test Docker services
docker compose -f docker-compose.production.yml up -d
```

### Permission Errors

```bash
# Fix ownership
sudo chown -R ui-cli_jake:ui-cli_jake /home/ui-cli_jake/unified-intelligence-cli

# Fix log directory permissions
mkdir -p logs data projects
chmod 755 logs data projects

# Verify service user
id ui-cli_jake
```

### Docker Connection Issues

```bash
# Check Docker daemon
sudo systemctl status docker

# Verify user in docker group
groups ui-cli_jake

# Add user to docker group (if missing)
sudo usermod -aG docker ui-cli_jake
newgrp docker
```

### Database Connection Errors

```bash
# Check SurrealDB container
docker logs project-builder-db

# Test database connection
curl http://localhost:8000/health

# Restart database
docker compose -f docker-compose.production.yml restart surrealdb
```

### Memory Issues

```bash
# Check memory usage
sudo systemctl show project-builder.service | grep Memory

# View resource limits
sudo systemctl show project-builder.service | grep -E '(Memory|CPU|Tasks)'

# Increase limits in service file
sudo nano /etc/systemd/system/project-builder.service
sudo systemctl daemon-reload
sudo systemctl restart project-builder.service
```

## Updating

### Code Update

```bash
# Pull latest code
cd /home/ui-cli_jake/unified-intelligence-cli
git pull origin main

# Update dependencies
source venv/bin/activate
pip install -r requirements.txt --upgrade

# Restart service
sudo systemctl restart project-builder.service
```

### Service File Update

```bash
# Copy updated service file
sudo cp deploy/systemd/project-builder.service /etc/systemd/system/

# Reload systemd
sudo systemctl daemon-reload

# Restart service
sudo systemctl restart project-builder.service
```

## Backup and Restore

### Backup

```bash
# Backup data directory
tar -czf project-builder-backup-$(date +%Y%m%d).tar.gz \
  /home/ui-cli_jake/unified-intelligence-cli/data \
  /home/ui-cli_jake/unified-intelligence-cli/projects \
  /etc/project-builder/secrets.env

# Backup Docker volumes
docker run --rm -v project-builder-data:/data \
  -v $(pwd):/backup alpine \
  tar -czf /backup/surrealdb-backup-$(date +%Y%m%d).tar.gz -C /data .
```

### Restore

```bash
# Stop service
sudo systemctl stop project-builder.service

# Restore data
tar -xzf project-builder-backup-YYYYMMDD.tar.gz -C /

# Restore Docker volumes
docker run --rm -v project-builder-data:/data \
  -v $(pwd):/backup alpine \
  tar -xzf /backup/surrealdb-backup-YYYYMMDD.tar.gz -C /data

# Start service
sudo systemctl start project-builder.service
```

## Monitoring

### Log Rotation

systemd journal handles log rotation automatically. Configure retention:

```bash
# Edit journald config
sudo nano /etc/systemd/journald.conf

# Set retention
SystemMaxUse=1G
SystemMaxFileSize=100M
MaxRetentionSec=1month

# Restart journald
sudo systemctl restart systemd-journald
```

### Integration with Monitoring Tools

Export logs to external tools:

```bash
# To syslog
sudo journalctl -u project-builder.service -f | logger -t project-builder

# To file
sudo journalctl -u project-builder.service -f > /var/log/project-builder.log

# To remote syslog
sudo journalctl -u project-builder.service -f | \
  logger -n syslog.example.com -P 514 -t project-builder
```

## Production Checklist

- [ ] Secrets file created and secured (600 permissions)
- [ ] Service enabled for auto-start
- [ ] Health checks verified
- [ ] Logs reviewed for errors
- [ ] Resource limits appropriate for workload
- [ ] Firewall configured (if needed)
- [ ] Monitoring configured
- [ ] Backup strategy implemented
- [ ] Update procedure documented
- [ ] Runbook created for common issues
- [ ] On-call contact information updated

## Security Best Practices

1. **Secrets Management**
   - Never commit secrets to Git
   - Use 600 permissions on secrets files
   - Rotate credentials regularly
   - Use different passwords for each service

2. **System Hardening**
   - Keep system updated: `sudo apt-get update && sudo apt-get upgrade`
   - Use firewall: `sudo ufw enable && sudo ufw allow 8000/tcp`
   - Monitor logs regularly
   - Use fail2ban for SSH protection

3. **Docker Security**
   - Use official images only
   - Keep images updated
   - Scan images for vulnerabilities
   - Use read-only volumes where possible

## Support

For issues or questions:
- GitHub Issues: https://github.com/unified-intelligence-cli/issues
- Documentation: https://github.com/unified-intelligence-cli/docs
- Logs: `sudo journalctl -u project-builder.service -n 100`
