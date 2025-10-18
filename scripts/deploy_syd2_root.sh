#!/bin/bash
# Deploy RAG Metrics Server to syd2.jacobhollis.com (Root Access)
#
# This script deploys the RAG metrics server when running as root.
#
# Usage:
#   ssh root@syd2.jacobhollis.com
#   cd /root/unified-intelligence-cli  # or wherever the project is
#   ./scripts/deploy_syd2_root.sh

set -e

echo "================================================================================"
echo "RAG METRICS SERVER DEPLOYMENT (ROOT)"
echo "================================================================================"
echo ""

# Detect current user
CURRENT_USER=$(whoami)
echo "Running as: $CURRENT_USER"

# Detect project directory
PROJECT_DIR=$(pwd)
echo "Project directory: $PROJECT_DIR"

# Configuration
SERVICE_NAME="rag-metrics"
VENV_DIR="$PROJECT_DIR/venv"
SERVICE_FILE="/etc/systemd/system/$SERVICE_NAME.service"

# Verify we're in the right directory
if [ ! -f "scripts/rag_metrics_server.py" ]; then
    echo "❌ Error: Must run from unified-intelligence-cli root directory"
    echo "   Current directory: $PROJECT_DIR"
    echo "   Expected file: scripts/rag_metrics_server.py"
    exit 1
fi

echo "✅ Project directory verified"
echo ""

echo "Step 1: Check Prerequisites"
echo "--------------------------------------------------------------------------------"

# Check SurrealDB
if systemctl is-active --quiet surrealdb 2>/dev/null; then
    echo "✅ SurrealDB is running"
elif command -v surreal &> /dev/null; then
    echo "⚠️  SurrealDB installed but not running"
    echo "   Starting SurrealDB..."
    systemctl start surrealdb 2>/dev/null || echo "   (Could not start via systemd, may need manual start)"
else
    echo "⚠️  SurrealDB not found"
    echo "   Install with: curl -sSf https://install.surrealdb.com | sh"
fi

# Check Python virtual environment
if [ ! -d "$VENV_DIR" ]; then
    echo "⚠️  Virtual environment not found"
    echo "   Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
    echo "   Installing dependencies..."
    "$VENV_DIR/bin/pip" install --upgrade pip
    "$VENV_DIR/bin/pip" install -r requirements.txt
    echo "✅ Virtual environment created"
else
    echo "✅ Virtual environment found"
fi

echo ""

echo "Step 2: Create systemd Service"
echo "--------------------------------------------------------------------------------"

# Create service file
cat > $SERVICE_FILE << EOF
[Unit]
Description=RAG Metrics API Server
Documentation=https://github.com/yourusername/unified-intelligence-cli
After=network.target surrealdb.service

[Service]
Type=simple
User=$CURRENT_USER
Group=$CURRENT_USER
WorkingDirectory=$PROJECT_DIR

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
ExecStart=$VENV_DIR/bin/python $PROJECT_DIR/scripts/rag_metrics_server.py

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
systemctl daemon-reload
echo "✅ Systemd daemon reloaded"

# Enable service
systemctl enable $SERVICE_NAME
echo "✅ Service enabled (will start on boot)"

# Stop service if already running
if systemctl is-active --quiet $SERVICE_NAME; then
    echo "⚠️  Service already running, restarting..."
    systemctl restart $SERVICE_NAME
else
    # Start service
    systemctl start $SERVICE_NAME
fi

echo "✅ Service started"

# Wait a moment for startup
sleep 3

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
    echo "  journalctl -u $SERVICE_NAME -n 50"
    exit 1
fi

# Test health endpoint
echo ""
echo "Testing health endpoint..."
sleep 1
if curl -s http://localhost:8080/health | grep -q "ok"; then
    echo "✅ Health endpoint responding"
else
    echo "⚠️  Health endpoint not responding yet"
    echo "   Service may still be starting up..."
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
systemctl status $SERVICE_NAME --no-pager -l | head -20
echo ""
echo "Useful Commands:"
echo "  • View logs:        journalctl -u $SERVICE_NAME -f"
echo "  • Restart service:  systemctl restart $SERVICE_NAME"
echo "  • Stop service:     systemctl stop $SERVICE_NAME"
echo "  • Service status:   systemctl status $SERVICE_NAME"
echo ""
echo "Test Endpoints (on syd2):"
echo "  • Health:           curl http://localhost:8080/health"
echo "  • Metrics:          curl http://localhost:8080/api/rag/metrics"
echo "  • Patterns:         curl http://localhost:8080/api/rag/patterns"
echo "  • Routing:          curl http://localhost:8080/api/rag/routing/accuracy"
echo "  • Performance:      curl http://localhost:8080/api/rag/performance"
echo "  • Drift:            curl http://localhost:8080/api/rag/drift"
echo "  • A/B Test:         curl http://localhost:8080/api/rag/ab-test"
echo "  • Weights:          curl http://localhost:8080/api/rag/weights"
echo ""
echo "External Access (from your local machine):"
echo "  • curl https://syd2.jacobhollis.com:8080/api/rag/metrics"
echo ""
echo "View Live Logs:"
echo "  • journalctl -u $SERVICE_NAME -f"
echo ""
echo "================================================================================"
echo "✅ RAG Metrics Server is now running on port 8080"
echo "================================================================================"

