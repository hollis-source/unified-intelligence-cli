# Systemd Service Deployment

Run Unified Intelligence CLI as a systemd service on Linux servers.

## Table of Contents

- [Basic Service](#basic-service)
- [Advanced Configuration](#advanced-configuration)
- [Service Management](#service-management)
- [Monitoring](#monitoring)
- [Troubleshooting](#troubleshooting)

## Basic Service

### Service File

Create `/etc/systemd/system/ui-cli.service`:

```ini
[Unit]
Description=Unified Intelligence CLI Service
Documentation=https://github.com/yourusername/unified-intelligence-cli
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=ui-cli
Group=ui-cli
WorkingDirectory=/opt/ui-cli
Environment="XAI_API_KEY=your_api_key_here"
Environment="PYTHONUNBUFFERED=1"
ExecStart=/usr/local/bin/ui-cli --daemon
Restart=on-failure
RestartSec=10s
StandardOutput=journal
StandardError=journal
SyslogIdentifier=ui-cli

# Security hardening
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/opt/ui-cli/data

[Install]
WantedBy=multi-user.target
```

### Setup Script

```bash
#!/bin/bash
# setup-service.sh

set -e

echo "Setting up UI-CLI service..."

# Create service user
sudo useradd -r -s /bin/false -d /opt/ui-cli ui-cli

# Create directories
sudo mkdir -p /opt/ui-cli/{data,logs,config}
sudo chown -R ui-cli:ui-cli /opt/ui-cli

# Install UI-CLI
sudo pip install unified-intelligence-cli

# Create environment file
sudo tee /opt/ui-cli/.env > /dev/null <<EOF
XAI_API_KEY=your_api_key_here
UI_CLI_PROVIDER=grok
EOF

sudo chown ui-cli:ui-cli /opt/ui-cli/.env
sudo chmod 600 /opt/ui-cli/.env

# Copy service file
sudo cp ui-cli.service /etc/systemd/system/

# Reload systemd
sudo systemctl daemon-reload

# Enable and start service
sudo systemctl enable ui-cli
sudo systemctl start ui-cli

echo "Service setup complete!"
echo "Check status: sudo systemctl status ui-cli"
```

## Advanced Configuration

### Service with Environment File

**Service file (`/etc/systemd/system/ui-cli.service`):**

```ini
[Unit]
Description=Unified Intelligence CLI Service
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=ui-cli
Group=ui-cli
WorkingDirectory=/opt/ui-cli
EnvironmentFile=/opt/ui-cli/.env
ExecStart=/usr/local/bin/ui-cli --daemon --config /opt/ui-cli/config/config.json
Restart=on-failure
RestartSec=10s
TimeoutStopSec=30s
KillMode=mixed
StandardOutput=journal
StandardError=journal
SyslogIdentifier=ui-cli

# Resource limits
LimitNOFILE=65536
LimitNPROC=4096

# Security hardening
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/opt/ui-cli/data /opt/ui-cli/logs
ProtectKernelTunables=true
ProtectKernelModules=true
ProtectControlGroups=true
RestrictAddressFamilies=AF_INET AF_INET6 AF_UNIX
RestrictNamespaces=true
RestrictRealtime=true
RestrictSUIDSGID=true

[Install]
WantedBy=multi-user.target
```

**Environment file (`/opt/ui-cli/.env`):**

```bash
XAI_API_KEY=your_api_key_here
UI_CLI_PROVIDER=grok
UI_CLI_MODEL=grok-beta
UI_CLI_DEBUG=false
PYTHONUNBUFFERED=1
```

### Timer-Based Execution

Run tasks on a schedule using systemd timers.

**Service file (`/etc/systemd/system/ui-cli-task.service`):**

```ini
[Unit]
Description=UI-CLI Scheduled Task
After=network-online.target

[Service]
Type=oneshot
User=ui-cli
WorkingDirectory=/opt/ui-cli
EnvironmentFile=/opt/ui-cli/.env
ExecStart=/usr/local/bin/ui-cli "Daily task: Generate report"
StandardOutput=journal
StandardError=journal
```

**Timer file (`/etc/systemd/system/ui-cli-task.timer`):**

```ini
[Unit]
Description=Run UI-CLI task daily
Requires=ui-cli-task.service

[Timer]
OnCalendar=daily
OnCalendar=*-*-* 00:00:00
Persistent=true
Unit=ui-cli-task.service

[Install]
WantedBy=timers.target
```

**Enable timer:**

```bash
sudo systemctl daemon-reload
sudo systemctl enable ui-cli-task.timer
sudo systemctl start ui-cli-task.timer

# Check timer status
sudo systemctl list-timers --all
```

## Service Management

### Start/Stop/Restart

```bash
# Start service
sudo systemctl start ui-cli

# Stop service
sudo systemctl stop ui-cli

# Restart service
sudo systemctl restart ui-cli

# Reload configuration
sudo systemctl reload ui-cli
```

### Enable/Disable

```bash
# Enable (start on boot)
sudo systemctl enable ui-cli

# Disable (don't start on boot)
sudo systemctl disable ui-cli
```

### Status and Logs

```bash
# Check status
sudo systemctl status ui-cli

# View logs
sudo journalctl -u ui-cli

# Follow logs (real-time)
sudo journalctl -u ui-cli -f

# View logs since boot
sudo journalctl -u ui-cli -b

# View logs from last hour
sudo journalctl -u ui-cli --since "1 hour ago"

# View logs with priority
sudo journalctl -u ui-cli -p err
```

## Monitoring

### Health Check Script

```bash
#!/bin/bash
# health-check.sh

SERVICE="ui-cli"

if ! systemctl is-active --quiet $SERVICE; then
    echo "ERROR: $SERVICE is not running"
    systemctl restart $SERVICE
    echo "Service restarted at $(date)" >> /var/log/ui-cli-restarts.log
    exit 1
fi

echo "OK: $SERVICE is running"
exit 0
```

### Watchdog Configuration

Add to service file:

```ini
[Service]
WatchdogSec=60s
Restart=on-watchdog
```

### Monitoring with Prometheus

**Service file with metrics:**

```ini
[Service]
ExecStart=/usr/local/bin/ui-cli --daemon --metrics-port 9100
```

**Prometheus configuration:**

```yaml
scrape_configs:
  - job_name: 'ui-cli'
    static_configs:
      - targets: ['localhost:9100']
```

## Troubleshooting

### Service Won't Start

**Check service status:**
```bash
sudo systemctl status ui-cli -l
```

**Check logs:**
```bash
sudo journalctl -u ui-cli -n 50 --no-pager
```

**Verify configuration:**
```bash
# Check service file syntax
sudo systemd-analyze verify /etc/systemd/system/ui-cli.service

# Test service manually
sudo -u ui-cli /usr/local/bin/ui-cli --help
```

### Permission Issues

**Fix ownership:**
```bash
sudo chown -R ui-cli:ui-cli /opt/ui-cli
sudo chmod 700 /opt/ui-cli
sudo chmod 600 /opt/ui-cli/.env
```

**Check SELinux (if enabled):**
```bash
sudo ausearch -m avc -ts recent
sudo setsebool -P httpd_can_network_connect 1
```

### High Memory Usage

**Add memory limits to service:**
```ini
[Service]
MemoryMax=512M
MemoryHigh=400M
```

**Monitor memory:**
```bash
systemd-cgtop
```

### Service Keeps Restarting

**Check restart policy:**
```ini
[Service]
Restart=on-failure
StartLimitBurst=5
StartLimitIntervalSec=300
```

**View restart history:**
```bash
sudo journalctl -u ui-cli | grep "Started\|Stopped"
```

## Multiple Instances

### Instance Template

**Service file (`/etc/systemd/system/ui-cli@.service`):**

```ini
[Unit]
Description=UI-CLI Instance %i
After=network-online.target
PartOf=ui-cli.target

[Service]
Type=simple
User=ui-cli
WorkingDirectory=/opt/ui-cli/%i
EnvironmentFile=/opt/ui-cli/%i/.env
ExecStart=/usr/local/bin/ui-cli --daemon --instance %i
Restart=on-failure

[Install]
WantedBy=ui-cli.target
```

**Target file (`/etc/systemd/system/ui-cli.target`):**

```ini
[Unit]
Description=UI-CLI Instances
Wants=ui-cli@instance1.service ui-cli@instance2.service

[Install]
WantedBy=multi-user.target
```

**Manage instances:**

```bash
# Start specific instance
sudo systemctl start ui-cli@instance1

# Start all instances
sudo systemctl start ui-cli.target

# Check all instances
sudo systemctl status 'ui-cli@*'
```

## Backup and Recovery

### Automated Backup Script

```bash
#!/bin/bash
# backup-ui-cli.sh

BACKUP_DIR="/backups/ui-cli/$(date +%Y%m%d-%H%M%S)"
mkdir -p $BACKUP_DIR

# Stop service
sudo systemctl stop ui-cli

# Backup data
sudo tar czf $BACKUP_DIR/data.tar.gz -C /opt/ui-cli data/

# Backup config
sudo cp /opt/ui-cli/.env $BACKUP_DIR/
sudo cp /etc/systemd/system/ui-cli.service $BACKUP_DIR/

# Start service
sudo systemctl start ui-cli

echo "Backup completed: $BACKUP_DIR"
```

### Recovery Script

```bash
#!/bin/bash
# restore-ui-cli.sh

BACKUP_DIR=$1

if [ -z "$BACKUP_DIR" ]; then
    echo "Usage: $0 <backup_directory>"
    exit 1
fi

# Stop service
sudo systemctl stop ui-cli

# Restore data
sudo tar xzf $BACKUP_DIR/data.tar.gz -C /opt/ui-cli/

# Restore config
sudo cp $BACKUP_DIR/.env /opt/ui-cli/
sudo cp $BACKUP_DIR/ui-cli.service /etc/systemd/system/

# Reload and restart
sudo systemctl daemon-reload
sudo systemctl start ui-cli

echo "Restore completed from: $BACKUP_DIR"
```

## Security Hardening

### AppArmor Profile

Create `/etc/apparmor.d/usr.local.bin.ui-cli`:

```
#include <tunables/global>

/usr/local/bin/ui-cli {
  #include <abstractions/base>
  #include <abstractions/python>
  
  /usr/local/bin/ui-cli r,
  /opt/ui-cli/** rw,
  /opt/ui-cli/.env r,
  
  deny /proc/** w,
  deny /sys/** w,
}
```

### Firewall Configuration

```bash
# Allow metrics port (if using Prometheus)
sudo ufw allow 9100/tcp comment 'UI-CLI metrics'

# Limit access to specific IPs
sudo ufw allow from 10.0.0.0/8 to any port 9100
```

---

**Last Updated:** 2025-09-30
**Version:** 1.0.0
