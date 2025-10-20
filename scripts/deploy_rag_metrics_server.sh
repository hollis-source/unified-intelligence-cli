#!/bin/bash
# Deploy RAG Metrics Server to syd2.jacobhollis.com
#
# This script deploys the RAG metrics server as a systemd service.
#
# Usage:
#   ./scripts/deploy_rag_metrics_server.sh

set -e

echo "================================================================================"
echo "RAG METRICS SERVER DEPLOYMENT"
echo "================================================================================"
echo ""

# Configuration
SERVICE_NAME="rag-metrics"
INSTALL_DIR="/home/ubuntu/unified-intelligence-cli"
VENV_DIR="$INSTALL_DIR/venv"
SERVICE_FILE="/etc/systemd/system/$SERVICE_NAME.service"

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    echo "❌ Do not run this script as root"
    echo "   Run as ubuntu user, script will use sudo when needed"
    exit 1
fi

# Check if in correct directory
if [ ! -f "scripts/rag_metrics_server.py" ]; then
    echo "❌ Must run from unified-intelligence-cli root directory"
    exit 1
fi

echo "Step 1: Check Prerequisites"
echo "--------------------------------------------------------------------------------"

# Check SurrealDB
if ! systemctl is-active --quiet surrealdb; then
    echo "⚠️  SurrealDB is not running"
    echo "   Starting SurrealDB..."
    sudo systemctl start surrealdb
    sleep 2
fi

if systemctl is-active --quiet surrealdb; then
    echo "✅ SurrealDB is running"
else
    echo "❌ SurrealDB failed to start"
    exit 1
fi

# Check Python virtual environment
if [ ! -d "$VENV_DIR" ]; then
    echo "❌ Virtual environment not found at $VENV_DIR"
    echo "   Run: python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt"
    exit 1
fi

echo "✅ Virtual environment found"
echo ""

echo "Step 2: Create systemd Service"
echo "--------------------------------------------------------------------------------"

# Create service file
sudo tee $SERVICE_FILE > /dev/null <<EOF
[Unit]
Description=RAG Metrics API Server
Documentation=https://github.com/yourusername/unified-intelligence-cli
After=network.target surrealdb.service
Requires=surrealdb.service

[Service]
Type=simple
User=ubuntu
Group=ubuntu
WorkingDirectory=$INSTALL_DIR

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
ExecStart=$VENV_DIR/bin/python $INSTALL_DIR/scripts/rag_metrics_server.py

# Restart policy
Restart=always
RestartSec=10
StartLimitInterval=200
StartLimitBurst=5

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=$SERVICE_NAME

# Security
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
EOF

echo "✅ Service file created: $SERVICE_FILE"
echo ""

echo "Step 3: Enable and Start Service"
echo "--------------------------------------------------------------------------------"

# Reload systemd
sudo systemctl daemon-reload
echo "✅ Systemd daemon reloaded"

# Enable service
sudo systemctl enable $SERVICE_NAME
echo "✅ Service enabled (will start on boot)"

# Start service
sudo systemctl start $SERVICE_NAME
echo "✅ Service started"

# Wait a moment for startup
sleep 2

echo ""

echo "Step 4: Verify Deployment"
echo "--------------------------------------------------------------------------------"

# Check service status
if systemctl is-active --quiet $SERVICE_NAME; then
    echo "✅ Service is running"
else
    echo "❌ Service failed to start"
    echo ""
    echo "Check logs with:"
    echo "  sudo journalctl -u $SERVICE_NAME -f"
    exit 1
fi

# Test health endpoint
echo ""
echo "Testing health endpoint..."
if curl -s http://localhost:8080/health | grep -q "ok"; then
    echo "✅ Health endpoint responding"
else
    echo "⚠️  Health endpoint not responding yet (may still be starting)"
fi

# Test RAG metrics endpoint
echo ""
echo "Testing RAG metrics endpoint..."
if curl -s http://localhost:8080/api/rag/metrics | grep -q "status"; then
    echo "✅ RAG metrics endpoint responding"
else
    echo "⚠️  RAG metrics endpoint not responding yet"
fi

echo ""
echo "================================================================================"
echo "DEPLOYMENT COMPLETE"
echo "================================================================================"
echo ""
echo "Service Status:"
sudo systemctl status $SERVICE_NAME --no-pager -l
echo ""
echo "Useful Commands:"
echo "  • View logs:        sudo journalctl -u $SERVICE_NAME -f"
echo "  • Restart service:  sudo systemctl restart $SERVICE_NAME"
echo "  • Stop service:     sudo systemctl stop $SERVICE_NAME"
echo "  • Service status:   sudo systemctl status $SERVICE_NAME"
echo ""
echo "Test Endpoints:"
echo "  • Health:           curl http://localhost:8080/health"
echo "  • Metrics:          curl http://localhost:8080/api/rag/metrics"
echo "  • Patterns:         curl http://localhost:8080/api/rag/patterns"
echo "  • Routing:          curl http://localhost:8080/api/rag/routing/accuracy"
echo ""
echo "External Access (if firewall configured):"
echo "  • https://syd2.jacobhollis.com:8080/api/rag/metrics"
echo ""
echo "================================================================================"

