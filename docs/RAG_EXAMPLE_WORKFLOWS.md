# RAG System - Example Workflows

**Version**: 1.0  
**Date**: 2025-10-18

---

## Table of Contents

1. [Workflow 1: Initial Setup](#workflow-1-initial-setup)
2. [Workflow 2: Building Pattern Database](#workflow-2-building-pattern-database)
3. [Workflow 3: Production Deployment](#workflow-3-production-deployment)
4. [Workflow 4: Continuous Monitoring](#workflow-4-continuous-monitoring)
5. [Workflow 5: Performance Optimization](#workflow-5-performance-optimization)
6. [Workflow 6: Drift Management](#workflow-6-drift-management)

---

## Workflow 1: Initial Setup

**Goal**: Set up RAG system from scratch

**Time**: 15 minutes

### Steps

```bash
# 1. Verify prerequisites
systemctl status surrealdb
python --version
source venv/bin/activate

# 2. Start RAG metrics server
cd /home/ui-cli_jake/unified-intelligence-cli
python start_rag_server.py &

# 3. Wait for server to start
sleep 5

# 4. Verify server is running
curl http://localhost:8888/health
# Expected: {"status": "ok"}

# 5. Check initial metrics
curl http://localhost:8888/api/rag/metrics
# Expected: total_patterns: 0, rag_enabled: true

# 6. Check alerts (should have 2 warnings for new system)
curl http://localhost:8888/api/rag/alerts
# Expected: low_accuracy, insufficient_patterns

# 7. Run first test task
python main.py --enable-rag "Test task: implement hello world"

# 8. Verify pattern was stored
curl http://localhost:8888/api/rag/patterns
# Expected: total: 1
```

**Success Criteria**:
- ✅ Server responding on port 8888
- ✅ Health check returns "ok"
- ✅ First pattern stored successfully
- ✅ Alerts showing expected warnings

---

## Workflow 2: Building Pattern Database

**Goal**: Build a comprehensive pattern database

**Time**: 2-4 hours (depending on task count)

### Strategy

Build patterns across all domains for balanced coverage:

```bash
#!/bin/bash
# build_balanced_patterns.sh

# Backend tasks (20)
BACKEND_TASKS=(
  "Implement REST API for user management"
  "Add database migration for new schema"
  "Fix memory leak in background worker"
  "Optimize SQL query for dashboard"
  "Add caching layer with Redis"
  "Implement rate limiting middleware"
  "Fix authentication token expiry bug"
  "Add logging for API requests"
  "Optimize database connection pool"
  "Implement webhook handler"
  "Add input validation for API"
  "Fix race condition in payment processing"
  "Implement background job queue"
  "Add database indexes for performance"
  "Fix N+1 query problem"
  "Implement API versioning"
  "Add health check endpoint"
  "Fix timeout in external API call"
  "Implement data export feature"
  "Add pagination to list endpoints"
)

# Frontend tasks (15)
FRONTEND_TASKS=(
  "Create login form component"
  "Fix responsive layout on mobile"
  "Add form validation with error messages"
  "Implement dark mode toggle"
  "Fix CSS alignment issue"
  "Add loading spinner component"
  "Optimize bundle size with code splitting"
  "Fix memory leak in React component"
  "Add accessibility features"
  "Implement infinite scroll"
  "Fix cross-browser compatibility"
  "Add animation to page transitions"
  "Implement search autocomplete"
  "Fix state management bug"
  "Add error boundary component"
)

# QA tasks (10)
QA_TASKS=(
  "Write unit tests for authentication"
  "Create integration test suite"
  "Add E2E tests with Cypress"
  "Perform load testing on API"
  "Write BDD scenarios for checkout"
  "Add test coverage reporting"
  "Create test data fixtures"
  "Implement visual regression tests"
  "Add API contract tests"
  "Perform security testing"
)

# DevOps tasks (10)
DEVOPS_TASKS=(
  "Deploy application to Kubernetes"
  "Set up CI/CD pipeline"
  "Configure monitoring with Prometheus"
  "Add alerting rules"
  "Optimize Docker image size"
  "Set up log aggregation"
  "Configure auto-scaling"
  "Implement blue-green deployment"
  "Add backup automation"
  "Configure SSL certificates"
)

# Run all tasks
run_tasks() {
  local category=$1
  shift
  local tasks=("$@")
  
  echo "Running $category tasks..."
  for task in "${tasks[@]}"; do
    echo "  Task: $task"
    python main.py --enable-rag "$task"
    sleep 2
  done
}

run_tasks "BACKEND" "${BACKEND_TASKS[@]}"
run_tasks "FRONTEND" "${FRONTEND_TASKS[@]}"
run_tasks "QA" "${QA_TASKS[@]}"
run_tasks "DEVOPS" "${DEVOPS_TASKS[@]}"

# Check final pattern count
echo ""
echo "Pattern database built!"
curl -s http://localhost:8888/api/rag/patterns | jq '.patterns'
```

**Progress Tracking**:

```bash
# Check progress periodically
watch -n 10 'curl -s http://localhost:8888/api/rag/patterns | jq ".patterns.total"'

# Check domain distribution
curl -s http://localhost:8888/api/rag/patterns | jq '.patterns.by_domain'
```

**Success Criteria**:
- ✅ 50+ total patterns
- ✅ Balanced distribution across domains
- ✅ No "insufficient_patterns" alert

---

## Workflow 3: Production Deployment

**Goal**: Deploy RAG system to production

**Time**: 30 minutes

### Pre-Deployment Checklist

```bash
# 1. Verify pattern count
PATTERNS=$(curl -s http://localhost:8888/api/rag/patterns | jq -r '.patterns.total')
if [ "$PATTERNS" -lt 50 ]; then
  echo "❌ Need at least 50 patterns (have $PATTERNS)"
  exit 1
fi
echo "✅ Pattern count: $PATTERNS"

# 2. Check accuracy
ACCURACY=$(curl -s http://localhost:8888/api/rag/routing/accuracy | jq -r '.accuracy.rag')
if (( $(echo "$ACCURACY < 70" | bc -l) )); then
  echo "❌ Accuracy too low: $ACCURACY% (need 70%+)"
  exit 1
fi
echo "✅ Accuracy: $ACCURACY%"

# 3. Run A/B test
SIGNIFICANT=$(curl -s http://localhost:8888/api/rag/ab-test | jq -r '.ab_test.significant')
if [ "$SIGNIFICANT" != "true" ]; then
  echo "⚠️  A/B test not significant yet"
fi

# 4. Check for critical alerts
CRITICAL=$(curl -s http://localhost:8888/api/rag/alerts | jq -r '.alerts.by_severity.critical')
if [ "$CRITICAL" -gt 0 ]; then
  echo "❌ Critical alerts present"
  exit 1
fi
echo "✅ No critical alerts"
```

### Deployment Steps

```bash
# 1. Create systemd service
sudo tee /etc/systemd/system/rag-metrics.service << 'EOF'
[Unit]
Description=RAG Metrics API Server
After=network.target surrealdb.service

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/unified-intelligence-cli
Environment="SURREALDB_URL=ws://localhost:8000"
Environment="HOST=0.0.0.0"
Environment="PORT=8888"
ExecStart=/home/ubuntu/unified-intelligence-cli/venv/bin/python start_rag_server.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# 2. Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable rag-metrics
sudo systemctl start rag-metrics

# 3. Verify service is running
sudo systemctl status rag-metrics

# 4. Test endpoints
curl http://localhost:8888/health
curl http://localhost:8888/api/rag/metrics

# 5. Configure firewall (if needed)
sudo ufw allow 8888/tcp

# 6. Set up monitoring
# Add to cron for daily health checks
(crontab -l 2>/dev/null; echo "0 9 * * * /usr/local/bin/rag_health_check.sh") | crontab -
```

**Success Criteria**:
- ✅ Service running and enabled
- ✅ All endpoints responding
- ✅ No critical alerts
- ✅ Monitoring configured

---

## Workflow 4: Continuous Monitoring

**Goal**: Monitor RAG system health continuously

**Time**: Ongoing

### Daily Monitoring Script

```bash
#!/bin/bash
# /usr/local/bin/rag_daily_monitor.sh

LOG_FILE="/var/log/rag_monitor.log"
ALERT_EMAIL="admin@example.com"

log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

alert() {
  echo "$1" | mail -s "RAG Alert" "$ALERT_EMAIL"
  log "ALERT: $1"
}

# Check server health
if ! curl -s http://localhost:8888/health | grep -q "ok"; then
  alert "RAG server not responding"
  exit 1
fi
log "Server health: OK"

# Check pattern count
PATTERNS=$(curl -s http://localhost:8888/api/rag/patterns | jq -r '.patterns.total')
log "Pattern count: $PATTERNS"

# Check accuracy
ACCURACY=$(curl -s http://localhost:8888/api/rag/routing/accuracy | jq -r '.accuracy.rag')
log "Accuracy: $ACCURACY%"

if (( $(echo "$ACCURACY < 70" | bc -l) )); then
  alert "RAG accuracy low: $ACCURACY%"
fi

# Check for critical alerts
CRITICAL=$(curl -s http://localhost:8888/api/rag/alerts | jq -r '.alerts.by_severity.critical')
if [ "$CRITICAL" -gt 0 ]; then
  alert "Critical alerts: $CRITICAL"
fi

# Check drift
DRIFT=$(curl -s http://localhost:8888/api/rag/drift | jq -r '.drift.drift_detected')
if [ "$DRIFT" = "true" ]; then
  alert "Pattern drift detected"
fi

log "Daily monitoring complete"
```

### Weekly Report

```bash
#!/bin/bash
# /usr/local/bin/rag_weekly_report.sh

REPORT_FILE="/tmp/rag_weekly_report.txt"

cat > "$REPORT_FILE" << EOF
RAG System Weekly Report
========================
Date: $(date '+%Y-%m-%d')

Metrics:
$(curl -s http://localhost:8888/api/rag/metrics | jq '.metrics')

Routing Accuracy:
$(curl -s http://localhost:8888/api/rag/routing/accuracy | jq '.accuracy')

Top Performers:
$(curl -s http://localhost:8888/api/rag/performance | jq '.performance.top_performers[:5]')

Alerts Summary:
$(curl -s http://localhost:8888/api/rag/alerts | jq '.alerts.by_severity')

A/B Test Results:
$(curl -s http://localhost:8888/api/rag/ab-test | jq '.ab_test')
EOF

mail -s "RAG Weekly Report" admin@example.com < "$REPORT_FILE"
```

**Success Criteria**:
- ✅ Daily health checks running
- ✅ Weekly reports generated
- ✅ Alerts configured
- ✅ Logs being collected

---

## Workflow 5: Performance Optimization

**Goal**: Optimize RAG system performance

**Time**: 1-2 hours

### Optimization Steps

```bash
# 1. Analyze current performance
curl -s http://localhost:8888/api/rag/performance | jq '.performance'

# 2. Run weight optimization
curl -s http://localhost:8888/api/rag/weights | jq '.optimization'

# 3. Identify low performers
curl -s http://localhost:8888/api/rag/performance | jq '.performance.low_performers'

# 4. Check routing decisions
curl -s http://localhost:8888/api/rag/routing/accuracy | jq '.recent_decisions'

# 5. Analyze domain distribution
curl -s http://localhost:8888/api/rag/patterns | jq '.patterns.by_domain'

# 6. Run A/B test for validation
curl -s http://localhost:8888/api/rag/ab-test | jq '
  {
    significant: .ab_test.significant,
    improvement: .ab_test.improvement,
    recommendation: .ab_test.recommendation
  }
'
```

### Optimization Actions

```python
#!/usr/bin/env python3
"""Optimize RAG system performance."""

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
    
    # Run optimization
    results = await optimizer.run_optimization_cycle()
    
    print("Optimization Results:")
    print(f"Domain weights: {results['domain_weights']}")
    print(f"Agent weights: {results['agent_weights']}")
    print(f"Recommendations: {results['recommendations']}")
    
    await store.close()

asyncio.run(optimize())
```

**Success Criteria**:
- ✅ Weights optimized
- ✅ Low performers identified
- ✅ Accuracy improved
- ✅ A/B test validates improvements

---

## Workflow 6: Drift Management

**Goal**: Detect and handle pattern drift

**Time**: 30 minutes

### Drift Detection

```bash
# 1. Check for drift
DRIFT_REPORT=$(curl -s http://localhost:8888/api/rag/drift)

# 2. Parse drift status
DRIFT_DETECTED=$(echo "$DRIFT_REPORT" | jq -r '.drift.drift_detected')
DRIFT_SCORE=$(echo "$DRIFT_REPORT" | jq -r '.drift.drift_score')

echo "Drift detected: $DRIFT_DETECTED"
echo "Drift score: $DRIFT_SCORE"

# 3. If drift detected, get details
if [ "$DRIFT_DETECTED" = "true" ]; then
  echo "Drift details:"
  echo "$DRIFT_REPORT" | jq '.drift.details'
fi
```

### Drift Remediation

```bash
#!/bin/bash
# handle_drift.sh

# 1. Check drift
DRIFT=$(curl -s http://localhost:8888/api/rag/drift | jq -r '.drift.drift_detected')

if [ "$DRIFT" = "true" ]; then
  echo "Drift detected! Taking action..."
  
  # 2. Backup current patterns
  curl -s http://localhost:8888/api/rag/patterns > /backup/patterns_$(date +%Y%m%d).json
  
  # 3. Re-embed patterns (if script exists)
  if [ -f "scripts/reembed_patterns.py" ]; then
    python scripts/reembed_patterns.py
  fi
  
  # 4. Verify drift is resolved
  sleep 10
  NEW_DRIFT=$(curl -s http://localhost:8888/api/rag/drift | jq -r '.drift.drift_detected')
  
  if [ "$NEW_DRIFT" = "false" ]; then
    echo "✅ Drift resolved"
  else
    echo "⚠️  Drift still present"
  fi
else
  echo "No drift detected"
fi
```

**Success Criteria**:
- ✅ Drift detected when patterns change
- ✅ Remediation actions taken
- ✅ Drift resolved after re-embedding
- ✅ System accuracy maintained

---

## Summary

These workflows cover the complete lifecycle of the RAG system:

1. **Initial Setup** - Get started quickly
2. **Building Patterns** - Create comprehensive database
3. **Production Deployment** - Deploy safely
4. **Continuous Monitoring** - Stay informed
5. **Performance Optimization** - Improve over time
6. **Drift Management** - Handle changes

For more information, see:
- [RAG Usage Guide](RAG_USAGE_GUIDE.md)
- [RAG System README](RAG_SYSTEM_README.md)
- [Troubleshooting Guide](RAG_TROUBLESHOOTING.md)

---

**Last Updated**: 2025-10-18

