# RAG Metrics Integration Guide

**Date**: 2025-10-18  
**Status**: Production Ready

---

## Overview

This guide shows how to integrate RAG metrics endpoints with your existing web server infrastructure.

---

## Integration Steps

### Step 1: Import Required Modules

```python
from src.adapters.web.api_server import create_app
from src.adapters.rag.surrealdb_store import SurrealDBStore
from src.adapters.llm.rag_config import RAGConfig
```

### Step 2: Initialize Database Connection

```python
import os
import asyncio

async def setup_rag_metrics():
    # Load configuration
    config = RAGConfig()
    db_url = os.getenv("SURREALDB_URL", "ws://localhost:8000")
    
    # Create database connection
    db_store = SurrealDBStore(
        url=db_url,
        namespace=config.db_namespace,
        database=config.db_database,
        user=config.db_user,
        password=config.db_password
    )
    
    # Connect
    await db_store.connect()
    
    return db_store
```

### Step 3: Create App with RAG Metrics

```python
from aiohttp import web

async def main():
    # Setup database
    db_store = await setup_rag_metrics()
    
    # Define your task runner
    async def task_runner(tasks):
        # Your task execution logic
        return {"tasks_processed": len(tasks)}
    
    # Create app with RAG metrics enabled
    app = create_app(
        task_runner=task_runner,
        db_store=db_store,
        enable_rag_metrics=True  # Enable RAG endpoints
    )
    
    # Run server
    web.run_app(app, host='0.0.0.0', port=8080)

if __name__ == "__main__":
    asyncio.run(main())
```

---

## Available Endpoints

Once integrated, the following endpoints are available:

### Core Endpoints (Existing)
- `GET /health` - Health check
- `POST /api/v1/tasks` - Submit tasks

### RAG Metrics Endpoints (New)
- `GET /api/rag/metrics` - Metrics overview
- `GET /api/rag/patterns` - Pattern metrics
- `GET /api/rag/routing/accuracy` - Routing accuracy
- `GET /api/rag/performance` - Performance metrics
- `GET /api/rag/drift` - Drift detection
- `GET /api/rag/ab-test` - A/B test results
- `GET /api/rag/weights` - Weight optimization

---

## Testing the Integration

### 1. Local Testing

```bash
# Start your server
python your_server.py

# Test health endpoint
curl http://localhost:8080/health

# Test RAG metrics
curl http://localhost:8080/api/rag/metrics
```

### 2. Remote Testing (syd2.jacobhollis.com)

```bash
# Test health endpoint
curl https://syd2.jacobhollis.com:8080/health

# Test RAG metrics overview
curl https://syd2.jacobhollis.com:8080/api/rag/metrics

# Test routing accuracy
curl https://syd2.jacobhollis.com:8080/api/rag/routing/accuracy

# Test drift detection
curl https://syd2.jacobhollis.com:8080/api/rag/drift
```

### 3. Python Client Example

```python
import aiohttp
import asyncio

async def get_rag_metrics(base_url="https://syd2.jacobhollis.com:8080"):
    async with aiohttp.ClientSession() as session:
        # Get metrics overview
        async with session.get(f"{base_url}/api/rag/metrics") as response:
            if response.status == 200:
                data = await response.json()
                print(f"Total patterns: {data['metrics']['total_patterns']}")
                print(f"RAG accuracy: {data['metrics']['rag_routing_accuracy']:.1f}%")
            else:
                print(f"Error: {response.status}")
        
        # Get routing accuracy
        async with session.get(f"{base_url}/api/rag/routing/accuracy") as response:
            if response.status == 200:
                data = await response.json()
                accuracy = data['accuracy']
                print(f"RAG: {accuracy['rag']:.1f}%")
                print(f"Baseline: {accuracy['baseline']:.1f}%")
                print(f"Improvement: {accuracy['improvement']:+.1f}%")

asyncio.run(get_rag_metrics())
```

---

## Deployment to syd2.jacobhollis.com

### Option 1: Update Existing Server

If you have an existing server script, modify it:

```python
# Before
app = create_app(task_runner)

# After
db_store = await setup_rag_metrics()
app = create_app(task_runner, db_store=db_store, enable_rag_metrics=True)
```

### Option 2: Create New Server Script

Create `scripts/rag_metrics_server.py`:

```python
#!/usr/bin/env python3
"""RAG Metrics Server for syd2.jacobhollis.com"""

import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from aiohttp import web
from src.adapters.web.api_server import create_app
from src.adapters.rag.surrealdb_store import SurrealDBStore
from src.adapters.llm.rag_config import RAGConfig


async def task_runner(tasks):
    """Task runner implementation."""
    # Your task execution logic here
    return {"tasks_processed": len(tasks)}


async def main():
    # Setup database
    config = RAGConfig()
    db_url = os.getenv("SURREALDB_URL", "ws://localhost:8000")
    
    db_store = SurrealDBStore(
        url=db_url,
        namespace=config.db_namespace,
        database=config.db_database,
        user=config.db_user,
        password=config.db_password
    )
    
    await db_store.connect()
    print("✅ Connected to SurrealDB")
    
    # Create app
    app = create_app(
        task_runner=task_runner,
        db_store=db_store,
        enable_rag_metrics=True
    )
    
    # Run server
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8080"))
    
    print(f"🚀 Starting server on {host}:{port}")
    web.run_app(app, host=host, port=port)


if __name__ == "__main__":
    asyncio.run(main())
```

Deploy:
```bash
# On syd2.jacobhollis.com
cd /path/to/unified-intelligence-cli
python scripts/rag_metrics_server.py
```

---

## Verification

### Check Endpoints are Available

```bash
# List all routes
curl https://syd2.jacobhollis.com:8080/api/rag/metrics | jq .

# Expected output:
{
  "status": "ok",
  "metrics": {
    "total_patterns": 1234,
    "total_routing_decisions": 567,
    "rag_routing_accuracy": 85.5,
    "rag_enabled": true
  }
}
```

### Monitor Logs

```bash
# Check server logs
tail -f /var/log/rag_metrics_server.log

# Look for:
# ✅ Connected to SurrealDB
# 🚀 Starting server on 0.0.0.0:8080
```

---

## Configuration

### Environment Variables

```bash
# SurrealDB connection
export SURREALDB_URL="ws://localhost:8000"
export SURREALDB_NAMESPACE="rag"
export SURREALDB_DATABASE="patterns"
export SURREALDB_USER="root"
export SURREALDB_PASSWORD="root"

# Server configuration
export HOST="0.0.0.0"
export PORT="8080"
```

### systemd Service (Production)

Create `/etc/systemd/system/rag-metrics.service`:

```ini
[Unit]
Description=RAG Metrics API Server
After=network.target surrealdb.service

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/unified-intelligence-cli
Environment="SURREALDB_URL=ws://localhost:8000"
Environment="HOST=0.0.0.0"
Environment="PORT=8080"
ExecStart=/home/ubuntu/unified-intelligence-cli/venv/bin/python scripts/rag_metrics_server.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable rag-metrics
sudo systemctl start rag-metrics
sudo systemctl status rag-metrics
```

---

## Monitoring

### Health Check

```bash
# Simple health check
curl https://syd2.jacobhollis.com:8080/health

# Expected: {"status": "ok"}
```

### Metrics Collection

```bash
# Collect all metrics
curl https://syd2.jacobhollis.com:8080/api/rag/metrics > metrics.json
curl https://syd2.jacobhollis.com:8080/api/rag/patterns >> metrics.json
curl https://syd2.jacobhollis.com:8080/api/rag/performance >> metrics.json
```

### Automated Monitoring Script

```bash
#!/bin/bash
# monitor_rag_metrics.sh

BASE_URL="https://syd2.jacobhollis.com:8080"

echo "RAG Metrics Dashboard"
echo "===================="

# Get metrics
METRICS=$(curl -s $BASE_URL/api/rag/metrics)
echo "Total Patterns: $(echo $METRICS | jq -r '.metrics.total_patterns')"
echo "RAG Accuracy: $(echo $METRICS | jq -r '.metrics.rag_routing_accuracy')%"

# Get drift status
DRIFT=$(curl -s $BASE_URL/api/rag/drift)
echo "Drift Detected: $(echo $DRIFT | jq -r '.drift.drift_detected')"
echo "Needs Reembedding: $(echo $DRIFT | jq -r '.drift.needs_reembedding')"
```

---

## Troubleshooting

### Issue: Connection Refused

```bash
# Check if server is running
sudo systemctl status rag-metrics

# Check if port is open
sudo netstat -tlnp | grep 8080

# Check firewall
sudo ufw status
```

### Issue: Database Connection Failed

```bash
# Check SurrealDB is running
sudo systemctl status surrealdb

# Test connection
curl http://localhost:8000/health
```

### Issue: 500 Internal Server Error

```bash
# Check server logs
journalctl -u rag-metrics -f

# Check database logs
journalctl -u surrealdb -f
```

---

## Next Steps

1. **Deploy to syd2**: Follow deployment steps above
2. **Test endpoints**: Use curl commands to verify
3. **Monitor metrics**: Set up automated monitoring
4. **Add alerting**: Implement alerting system (Phase 5, Task 2)
5. **Create dashboard**: Build web UI for metrics visualization

---

## Support

For issues:
1. Check logs: `journalctl -u rag-metrics -f`
2. Verify database: `curl http://localhost:8000/health`
3. Test endpoints: `curl http://localhost:8080/health`
4. Review documentation: `docs/RAG_METRICS_API.md`

