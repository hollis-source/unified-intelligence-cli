# RAG Metrics API - Deploy to syd2 (Root Access)

**Server**: syd2.jacobhollis.com  
**Access**: root  
**Date**: 2025-10-18

---

## Quick Deploy (Copy-Paste Commands)

### Step 1: SSH to syd2

```bash
ssh root@syd2.jacobhollis.com
```

### Step 2: Navigate to Project

```bash
# Find the unified-intelligence-cli directory
cd /root/unified-intelligence-cli || cd /home/*/unified-intelligence-cli || cd /opt/unified-intelligence-cli

# Verify you're in the right place
ls -la scripts/rag_metrics_server.py
```

### Step 3: Check Prerequisites

```bash
# Check if SurrealDB is running
systemctl status surrealdb

# If not running, start it
systemctl start surrealdb

# Check Python virtual environment
ls -la venv/bin/python

# If venv doesn't exist, create it
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Step 4: Deploy RAG Metrics Server

```bash
# Make scripts executable
chmod +x scripts/rag_metrics_server.py
chmod +x scripts/deploy_rag_metrics_server.sh

# Run deployment (as root, it will handle permissions)
./scripts/deploy_rag_metrics_server.sh
```

**OR** if the script expects ubuntu user, deploy manually:

```bash
# Create systemd service file
cat > /etc/systemd/system/rag-metrics.service << 'EOF'
[Unit]
Description=RAG Metrics API Server
Documentation=https://github.com/yourusername/unified-intelligence-cli
After=network.target surrealdb.service
Requires=surrealdb.service

[Service]
Type=simple
User=root
Group=root
WorkingDirectory=/root/unified-intelligence-cli

# Environment variables
Environment="SURREALDB_URL=ws://localhost:8000"
Environment="SURREALDB_NAMESPACE=rag"
Environment="SURREALDB_DATABASE=patterns"
Environment="SURREALDB_USER=root"
Environment="SURREALDB_PASSWORD=root"
Environment="HOST=0.0.0.0"
Environment="PORT=8080"
Environment="PYTHONUNBUFFERED=1"

# Start command
ExecStart=/root/unified-intelligence-cli/venv/bin/python /root/unified-intelligence-cli/scripts/rag_metrics_server.py

# Restart policy
Restart=always
RestartSec=10
StartLimitInterval=200
StartLimitBurst=5

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=rag-metrics

# Security
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd
systemctl daemon-reload

# Enable service (start on boot)
systemctl enable rag-metrics

# Start service
systemctl start rag-metrics

# Check status
systemctl status rag-metrics
```

### Step 5: Verify Deployment

```bash
# Check service is running
systemctl status rag-metrics

# Test health endpoint
curl http://localhost:8080/health

# Test RAG metrics endpoint
curl http://localhost:8080/api/rag/metrics

# View logs
journalctl -u rag-metrics -n 50
```

### Step 6: Test External Access

```bash
# From syd2 server
curl http://localhost:8080/api/rag/metrics | jq .

# From your local machine (different terminal)
curl https://syd2.jacobhollis.com:8080/api/rag/metrics
```

---

## Alternative: Quick Manual Start (No systemd)

If you just want to test without systemd:

```bash
# Navigate to project
cd /root/unified-intelligence-cli

# Activate virtual environment
source venv/bin/activate

# Set environment variables
export SURREALDB_URL="ws://localhost:8000"
export HOST="0.0.0.0"
export PORT="8080"

# Run server directly
python scripts/rag_metrics_server.py
```

Press `Ctrl+C` to stop.

---

## Troubleshooting

### Issue: Project Directory Not Found

```bash
# Search for the project
find / -name "unified-intelligence-cli" -type d 2>/dev/null

# Or check common locations
ls -la /root/unified-intelligence-cli
ls -la /home/ubuntu/unified-intelligence-cli
ls -la /opt/unified-intelligence-cli
```

### Issue: SurrealDB Not Running

```bash
# Check if SurrealDB is installed
which surreal

# Check service status
systemctl status surrealdb

# Start SurrealDB
systemctl start surrealdb

# If not installed, install it
curl -sSf https://install.surrealdb.com | sh
```

### Issue: Port 8080 Already in Use

```bash
# Check what's using port 8080
netstat -tlnp | grep 8080

# Kill the process (if safe)
kill -9 <PID>

# Or use a different port
export PORT="8081"
```

### Issue: Virtual Environment Missing

```bash
# Create virtual environment
cd /root/unified-intelligence-cli
python3 -m venv venv

# Activate and install dependencies
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### Issue: Permission Denied

```bash
# Fix permissions (if needed)
chown -R root:root /root/unified-intelligence-cli
chmod +x scripts/*.py
chmod +x scripts/*.sh
```

---

## Service Management Commands

```bash
# Start service
systemctl start rag-metrics

# Stop service
systemctl stop rag-metrics

# Restart service
systemctl restart rag-metrics

# Check status
systemctl status rag-metrics

# Enable auto-start on boot
systemctl enable rag-metrics

# Disable auto-start
systemctl disable rag-metrics

# View logs (live)
journalctl -u rag-metrics -f

# View last 100 lines
journalctl -u rag-metrics -n 100

# View logs since boot
journalctl -u rag-metrics -b
```

---

## Testing All Endpoints

```bash
# Health check
curl http://localhost:8080/health

# Metrics overview
curl http://localhost:8080/api/rag/metrics | jq .

# Pattern metrics
curl http://localhost:8080/api/rag/patterns | jq .

# Routing accuracy
curl http://localhost:8080/api/rag/routing/accuracy | jq .

# Performance metrics
curl http://localhost:8080/api/rag/performance | jq .

# Drift detection
curl http://localhost:8080/api/rag/drift | jq .

# A/B test results
curl http://localhost:8080/api/rag/ab-test | jq .

# Weight optimization
curl http://localhost:8080/api/rag/weights | jq .
```

---

## Firewall Configuration (If Needed)

```bash
# Check firewall status
ufw status

# Allow port 8080 (if needed)
ufw allow 8080/tcp

# Reload firewall
ufw reload
```

---

## Configuration Changes

### Change Port

Edit `/etc/systemd/system/rag-metrics.service`:

```ini
Environment="PORT=8081"
```

Then:
```bash
systemctl daemon-reload
systemctl restart rag-metrics
```

### Change SurrealDB URL

Edit `/etc/systemd/system/rag-metrics.service`:

```ini
Environment="SURREALDB_URL=ws://your-db-host:8000"
```

Then:
```bash
systemctl daemon-reload
systemctl restart rag-metrics
```

---

## Verification Checklist

- [ ] SSH to syd2: `ssh root@syd2.jacobhollis.com`
- [ ] Project directory found
- [ ] SurrealDB running: `systemctl status surrealdb`
- [ ] Virtual environment exists: `ls venv/bin/python`
- [ ] Service deployed: `systemctl status rag-metrics`
- [ ] Health endpoint works: `curl http://localhost:8080/health`
- [ ] RAG metrics work: `curl http://localhost:8080/api/rag/metrics`
- [ ] External access works: `curl https://syd2.jacobhollis.com:8080/health`
- [ ] Logs are clean: `journalctl -u rag-metrics -n 20`

---

## Expected Output

### Successful Deployment

```
✅ Connected to SurrealDB
✅ Service file created: /etc/systemd/system/rag-metrics.service
✅ Systemd daemon reloaded
✅ Service enabled (will start on boot)
✅ Service started
✅ Service is running
✅ Health endpoint responding
✅ RAG metrics endpoint responding
```

### Health Check Response

```json
{
  "status": "ok"
}
```

### Metrics Response

```json
{
  "status": "ok",
  "metrics": {
    "total_patterns": 0,
    "total_routing_decisions": 4,
    "rag_routing_accuracy": 0.0,
    "rag_enabled": true
  }
}
```

---

## Quick Reference

| Command | Description |
|---------|-------------|
| `systemctl status rag-metrics` | Check service status |
| `journalctl -u rag-metrics -f` | View live logs |
| `curl http://localhost:8080/health` | Test health endpoint |
| `systemctl restart rag-metrics` | Restart service |
| `systemctl stop rag-metrics` | Stop service |

---

## Next Steps After Deployment

1. **Verify**: Test all endpoints
2. **Monitor**: Watch logs for errors
3. **Secure**: Add authentication if needed
4. **Dashboard**: Build web UI for visualization
5. **Alerts**: Set up monitoring alerts

---

**Status**: Ready for deployment with root access on syd2.jacobhollis.com

