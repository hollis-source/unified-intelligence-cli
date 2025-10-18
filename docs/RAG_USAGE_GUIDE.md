# RAG System - Usage Guide

**Version**: 1.0  
**Date**: 2025-10-18  
**Audience**: Developers, DevOps, System Administrators

---

## Table of Contents

1. [Getting Started](#getting-started)
2. [Basic Usage](#basic-usage)
3. [Advanced Usage](#advanced-usage)
4. [API Usage](#api-usage)
5. [Monitoring](#monitoring)
6. [Best Practices](#best-practices)
7. [Examples](#examples)

---

## Getting Started

### Prerequisites

- Python 3.8+
- SurrealDB running on localhost:8000
- Virtual environment activated
- RAG metrics server running

### Quick Start

```bash
# 1. Ensure SurrealDB is running
systemctl status surrealdb

# 2. Start RAG metrics server
cd /home/ui-cli_jake/unified-intelligence-cli
python start_rag_server.py &

# 3. Verify server is running
curl http://localhost:8888/health
```

---

## Basic Usage

### Running Tasks with RAG

```bash
# Enable RAG for a single task
python main.py --enable-rag "Implement user authentication"

# Run multiple tasks to build patterns
python main.py --enable-rag "Fix database connection issue"
python main.py --enable-rag "Add unit tests for login"
python main.py --enable-rag "Deploy to production"
```

### Checking Metrics

```bash
# Get metrics overview
curl http://localhost:8888/api/rag/metrics

# Check pattern count
curl http://localhost:8888/api/rag/patterns

# View routing accuracy
curl http://localhost:8888/api/rag/routing/accuracy
```

### Monitoring Alerts

```bash
# Check current alerts
curl http://localhost:8888/api/rag/alerts

# View alert summary
curl http://localhost:8888/api/rag/alerts | jq '.alerts.total_alerts'
```

---

## Advanced Usage

### Building a Pattern Database

To get the best results from RAG, build a diverse pattern database:

```bash
#!/bin/bash
# build_patterns.sh - Build RAG pattern database

TASKS=(
  "Implement user authentication with JWT"
  "Fix memory leak in background worker"
  "Add integration tests for payment API"
  "Optimize database query performance"
  "Deploy microservice to Kubernetes"
  "Write documentation for REST API"
  "Refactor legacy code in user module"
  "Set up CI/CD pipeline with GitHub Actions"
  "Debug production error in checkout flow"
  "Add monitoring alerts for API latency"
)

for task in "${TASKS[@]}"; do
  echo "Running: $task"
  python main.py --enable-rag "$task"
  sleep 2
done

echo "Pattern database built!"
curl http://localhost:8888/api/rag/patterns
```

### Weight Optimization

```bash
# Get current weights
curl http://localhost:8888/api/rag/weights

# Run optimization (happens automatically after 10+ decisions)
# Or trigger manually:
python -c "
import asyncio
from src.routing.weight_optimizer import WeightOptimizer
from src.adapters.rag.surrealdb_store import SurrealDBStore
from src.adapters.llm.rag_config import RAGConfig

async def optimize():
    config = RAGConfig()
    store = SurrealDBStore(
        url='ws://localhost:8000',
        namespace=config.db_namespace,
        database=config.db_database,
        user=config.db_user,
        password=config.db_password
    )
    await store.connect()
    
    optimizer = WeightOptimizer(db_store=store)
    results = await optimizer.run_optimization_cycle()
    
    print('Optimization Results:')
    print(f'Domain weights: {results[\"domain_weights\"]}')
    print(f'Agent weights: {results[\"agent_weights\"]}')
    
    await store.close()

asyncio.run(optimize())
"
```

### Drift Detection

```bash
# Check for drift
curl http://localhost:8888/api/rag/drift

# Get detailed drift report
curl http://localhost:8888/api/rag/drift | jq '.drift.details'

# If drift detected, re-embed patterns
python scripts/reembed_patterns.py
```

### A/B Testing

```bash
# Run A/B test
curl http://localhost:8888/api/rag/ab-test

# Get statistical significance
curl http://localhost:8888/api/rag/ab-test | jq '.ab_test.significant'

# View improvement percentage
curl http://localhost:8888/api/rag/ab-test | jq '.ab_test.improvement'
```

---

## API Usage

### Python Client

```python
import aiohttp
import asyncio

async def get_rag_metrics():
    """Get RAG metrics from API."""
    async with aiohttp.ClientSession() as session:
        # Get metrics overview
        async with session.get('http://localhost:8888/api/rag/metrics') as resp:
            metrics = await resp.json()
            print(f"Total patterns: {metrics['metrics']['total_patterns']}")
            print(f"RAG accuracy: {metrics['metrics']['rag_routing_accuracy']:.1f}%")
        
        # Get performance data
        async with session.get('http://localhost:8888/api/rag/performance') as resp:
            perf = await resp.json()
            print(f"\nTop performers:")
            for agent in perf['performance']['top_performers'][:3]:
                print(f"  {agent['agent']}: {agent['success_rate']:.1f}%")
        
        # Check alerts
        async with session.get('http://localhost:8888/api/rag/alerts') as resp:
            alerts = await resp.json()
            print(f"\nTotal alerts: {alerts['alerts']['total_alerts']}")

asyncio.run(get_rag_metrics())
```

### JavaScript/Node.js Client

```javascript
const fetch = require('node-fetch');

async function getRAGMetrics() {
  // Get metrics
  const metricsResp = await fetch('http://localhost:8888/api/rag/metrics');
  const metrics = await metricsResp.json();
  console.log(`Total patterns: ${metrics.metrics.total_patterns}`);
  console.log(`RAG accuracy: ${metrics.metrics.rag_routing_accuracy}%`);
  
  // Get alerts
  const alertsResp = await fetch('http://localhost:8888/api/rag/alerts');
  const alerts = await alertsResp.json();
  console.log(`Total alerts: ${alerts.alerts.total_alerts}`);
}

getRAGMetrics();
```

### cURL Examples

```bash
# Get all metrics
curl -s http://localhost:8888/api/rag/metrics | jq .

# Get specific metric
curl -s http://localhost:8888/api/rag/metrics | jq '.metrics.total_patterns'

# Get routing accuracy
curl -s http://localhost:8888/api/rag/routing/accuracy | jq '.accuracy'

# Get drift status
curl -s http://localhost:8888/api/rag/drift | jq '.drift.drift_detected'

# Get alerts by severity
curl -s http://localhost:8888/api/rag/alerts | jq '.alerts.by_severity'
```

---

## Monitoring

### Real-Time Monitoring Script

```bash
#!/bin/bash
# monitor_rag.sh - Real-time RAG monitoring

while true; do
  clear
  echo "=== RAG System Monitor ==="
  echo "Time: $(date)"
  echo ""
  
  # Metrics
  echo "Metrics:"
  curl -s http://localhost:8888/api/rag/metrics | jq -r '
    "  Patterns: \(.metrics.total_patterns)",
    "  Decisions: \(.metrics.total_routing_decisions)",
    "  Accuracy: \(.metrics.rag_routing_accuracy)%"
  '
  echo ""
  
  # Alerts
  echo "Alerts:"
  curl -s http://localhost:8888/api/rag/alerts | jq -r '
    "  Total: \(.alerts.total_alerts)",
    "  Critical: \(.alerts.by_severity.critical)",
    "  Error: \(.alerts.by_severity.error)",
    "  Warning: \(.alerts.by_severity.warning)"
  '
  echo ""
  
  # Performance
  echo "Top Performers:"
  curl -s http://localhost:8888/api/rag/performance | jq -r '
    .performance.top_performers[:3][] |
    "  \(.agent): \(.success_rate)%"
  '
  
  sleep 5
done
```

### Prometheus Integration (Future)

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'rag_metrics'
    static_configs:
      - targets: ['localhost:8888']
    metrics_path: '/metrics/prometheus'
    scrape_interval: 15s
```

---

## Best Practices

### 1. Build Sufficient Patterns

```bash
# Minimum: 50 patterns
# Recommended: 100-200 patterns
# Optimal: 500+ patterns

# Check current count
curl -s http://localhost:8888/api/rag/patterns | jq '.patterns.total'
```

### 2. Monitor Accuracy Regularly

```bash
# Set up daily accuracy check
cat > /etc/cron.daily/rag-accuracy-check << 'EOF'
#!/bin/bash
ACCURACY=$(curl -s http://localhost:8888/api/rag/routing/accuracy | jq -r '.accuracy.rag')
if (( $(echo "$ACCURACY < 70" | bc -l) )); then
  echo "RAG accuracy low: $ACCURACY%" | mail -s "RAG Alert" admin@example.com
fi
EOF
chmod +x /etc/cron.daily/rag-accuracy-check
```

### 3. Handle Drift Proactively

```bash
# Check drift weekly
0 0 * * 0 curl -s http://localhost:8888/api/rag/drift | \
  jq -r 'if .drift.drift_detected then "Drift detected!" else empty end' | \
  mail -s "RAG Drift Alert" admin@example.com
```

### 4. Use A/B Testing for Validation

```bash
# Run A/B test before deploying RAG to production
curl -s http://localhost:8888/api/rag/ab-test | jq '
  if .ab_test.significant and .ab_test.improvement > 5 then
    "✅ RAG validated: +\(.ab_test.improvement)% improvement"
  else
    "⚠️  RAG not validated yet"
  end
'
```

### 5. Optimize Weights Periodically

```bash
# Weekly weight optimization
0 0 * * 0 curl -s http://localhost:8888/api/rag/weights > /tmp/rag_weights.json
```

---

## Examples

### Example 1: Daily RAG Health Check

```bash
#!/bin/bash
# daily_rag_health.sh

echo "RAG Health Check - $(date)"

# 1. Check server
if ! curl -s http://localhost:8888/health | grep -q "ok"; then
  echo "❌ Server not responding"
  exit 1
fi
echo "✅ Server healthy"

# 2. Check patterns
PATTERNS=$(curl -s http://localhost:8888/api/rag/patterns | jq -r '.patterns.total')
if [ "$PATTERNS" -lt 50 ]; then
  echo "⚠️  Low pattern count: $PATTERNS (need 50+)"
else
  echo "✅ Pattern count: $PATTERNS"
fi

# 3. Check accuracy
ACCURACY=$(curl -s http://localhost:8888/api/rag/routing/accuracy | jq -r '.accuracy.rag')
if (( $(echo "$ACCURACY < 70" | bc -l) )); then
  echo "⚠️  Low accuracy: $ACCURACY%"
else
  echo "✅ Accuracy: $ACCURACY%"
fi

# 4. Check alerts
ALERTS=$(curl -s http://localhost:8888/api/rag/alerts | jq -r '.alerts.total_alerts')
echo "ℹ️  Active alerts: $ALERTS"
```

### Example 2: Pattern Database Builder

```python
#!/usr/bin/env python3
"""Build RAG pattern database from task list."""

import subprocess
import time

# Task categories
TASKS = {
    "backend": [
        "Implement REST API endpoint",
        "Fix database connection pool",
        "Optimize SQL query performance",
        "Add caching layer with Redis",
    ],
    "frontend": [
        "Create React component",
        "Fix CSS layout issue",
        "Add form validation",
        "Optimize bundle size",
    ],
    "qa": [
        "Write unit tests",
        "Create integration test suite",
        "Add E2E tests with Cypress",
        "Perform load testing",
    ],
    "devops": [
        "Deploy to Kubernetes",
        "Set up CI/CD pipeline",
        "Configure monitoring alerts",
        "Optimize Docker image",
    ]
}

def run_task(task):
    """Run task with RAG enabled."""
    cmd = ["python", "main.py", "--enable-rag", task]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode == 0

def main():
    total = sum(len(tasks) for tasks in TASKS.values())
    completed = 0
    
    print(f"Building pattern database with {total} tasks...")
    
    for category, tasks in TASKS.items():
        print(f"\n{category.upper()} tasks:")
        for task in tasks:
            print(f"  Running: {task}")
            if run_task(task):
                completed += 1
                print(f"  ✅ Complete ({completed}/{total})")
            else:
                print(f"  ❌ Failed")
            time.sleep(2)
    
    print(f"\n✅ Pattern database built: {completed}/{total} tasks")

if __name__ == "__main__":
    main()
```

### Example 3: Automated Monitoring Dashboard

```python
#!/usr/bin/env python3
"""Simple RAG monitoring dashboard."""

import asyncio
import aiohttp
from datetime import datetime

async def fetch_metrics():
    """Fetch all RAG metrics."""
    async with aiohttp.ClientSession() as session:
        endpoints = {
            "metrics": "http://localhost:8888/api/rag/metrics",
            "patterns": "http://localhost:8888/api/rag/patterns",
            "accuracy": "http://localhost:8888/api/rag/routing/accuracy",
            "performance": "http://localhost:8888/api/rag/performance",
            "drift": "http://localhost:8888/api/rag/drift",
            "alerts": "http://localhost:8888/api/rag/alerts",
        }
        
        results = {}
        for name, url in endpoints.items():
            async with session.get(url) as resp:
                results[name] = await resp.json()
        
        return results

def display_dashboard(metrics):
    """Display metrics dashboard."""
    print("\033[2J\033[H")  # Clear screen
    print("=" * 80)
    print(f"RAG MONITORING DASHBOARD - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    print()
    
    # Overview
    m = metrics["metrics"]["metrics"]
    print("OVERVIEW:")
    print(f"  Patterns: {m['total_patterns']}")
    print(f"  Decisions: {m['total_routing_decisions']}")
    print(f"  RAG Accuracy: {m['rag_routing_accuracy']:.1f}%")
    print()
    
    # Accuracy
    acc = metrics["accuracy"]["accuracy"]
    print("ROUTING ACCURACY:")
    print(f"  RAG: {acc['rag']:.1f}%")
    print(f"  Baseline: {acc['baseline']:.1f}%")
    print(f"  Improvement: {acc['improvement']:+.1f}%")
    print()
    
    # Alerts
    alerts = metrics["alerts"]["alerts"]
    print("ALERTS:")
    print(f"  Total: {alerts['total_alerts']}")
    print(f"  Critical: {alerts['by_severity']['critical']}")
    print(f"  Error: {alerts['by_severity']['error']}")
    print(f"  Warning: {alerts['by_severity']['warning']}")
    print()
    
    # Top Performers
    perf = metrics["performance"]["performance"]
    print("TOP PERFORMERS:")
    for agent in perf['top_performers'][:3]:
        print(f"  {agent['agent']}: {agent['success_rate']:.1f}%")

async def main():
    """Main monitoring loop."""
    while True:
        try:
            metrics = await fetch_metrics()
            display_dashboard(metrics)
        except Exception as e:
            print(f"Error: {e}")
        
        await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(main())
```

---

## Next Steps

1. **Build Patterns**: Run 50-100 tasks with `--enable-rag`
2. **Monitor Metrics**: Check dashboard regularly
3. **Optimize Weights**: Run optimization after 10+ decisions
4. **Validate with A/B Testing**: Ensure statistical significance
5. **Deploy to Production**: Once accuracy > 70%

---

**For more information**:
- [RAG System README](RAG_SYSTEM_README.md)
- [API Reference](RAG_METRICS_API.md)
- [Troubleshooting Guide](RAG_TROUBLESHOOTING.md)

---

**Last Updated**: 2025-10-18

