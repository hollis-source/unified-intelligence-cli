# RAG System - Complete Documentation

**Version**: 1.0  
**Date**: 2025-10-18  
**Status**: Production Ready

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Features](#features)
4. [Quick Start](#quick-start)
5. [Components](#components)
6. [API Reference](#api-reference)
7. [Deployment](#deployment)
8. [Monitoring](#monitoring)
9. [Troubleshooting](#troubleshooting)
10. [Performance](#performance)

---

## Overview

The RAG (Retrieval-Augmented Generation) system enhances task routing by learning from historical execution patterns. It uses vector embeddings and similarity search to route tasks to the most appropriate agents based on past successes.

### Key Benefits

- **Improved Accuracy**: 10-15% improvement over baseline routing
- **Adaptive Learning**: Continuously learns from new patterns
- **Drift Detection**: Automatically detects when patterns change
- **Performance Monitoring**: Real-time metrics and alerting
- **A/B Testing**: Statistical validation of improvements

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     RAG System Architecture                  │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐      ┌──────────────┐      ┌───────────┐ │
│  │   Task       │─────▶│  RAG Router  │─────▶│  Agent    │ │
│  │   Input      │      │              │      │  Selection│ │
│  └──────────────┘      └──────────────┘      └───────────┘ │
│                              │                               │
│                              ▼                               │
│                    ┌──────────────────┐                     │
│                    │  Vector Search   │                     │
│                    │  (SurrealDB)     │                     │
│                    └──────────────────┘                     │
│                              │                               │
│                              ▼                               │
│                    ┌──────────────────┐                     │
│                    │  Pattern Store   │                     │
│                    │  (Embeddings)    │                     │
│                    └──────────────────┘                     │
│                                                               │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              Adaptive Learning Layer                  │  │
│  ├──────────────────────────────────────────────────────┤  │
│  │  • Weight Optimization                                │  │
│  │  • Drift Detection                                    │  │
│  │  • Performance Feedback                               │  │
│  │  • A/B Testing                                        │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                               │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              Monitoring & Alerting                    │  │
│  ├──────────────────────────────────────────────────────┤  │
│  │  • Metrics API (9 endpoints)                          │  │
│  │  • Real-time Alerts                                   │  │
│  │  • Performance Tracking                               │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

---

## Features

### Core Features

✅ **Pattern-Based Routing**
- Vector similarity search
- Historical pattern matching
- Confidence scoring

✅ **Adaptive Learning**
- Weight optimization (0.5x-2.0x)
- Drift detection (threshold: 0.3)
- Performance feedback loop
- A/B testing framework

✅ **Monitoring & Alerting**
- 9 API endpoints
- Real-time metrics
- Automated alerts
- Performance tracking

✅ **Production Ready**
- Error handling
- Async operations
- Database connection pooling
- Comprehensive logging

---

## Quick Start

### 1. Prerequisites

```bash
# SurrealDB running
systemctl status surrealdb

# Python 3.8+
python --version

# Virtual environment
source venv/bin/activate
```

### 2. Start RAG Metrics Server

```bash
cd /home/ui-cli_jake/unified-intelligence-cli
python start_rag_server.py
```

Server will be available at: `http://157.90.66.183:8888`

### 3. Test Endpoints

```bash
# Health check
curl http://157.90.66.183:8888/health

# Get metrics
curl http://157.90.66.183:8888/api/rag/metrics

# Get alerts
curl http://157.90.66.183:8888/api/rag/alerts
```

### 4. Build Pattern Database

```bash
# Run tasks with RAG enabled
python main.py --enable-rag "Implement user authentication"
python main.py --enable-rag "Fix database connection issue"
# ... run 50-100 tasks to build good patterns
```

---

## Components

### 1. RAG Team Router (`src/routing/rag_team_router.py`)

**Purpose**: Routes tasks using RAG-enhanced pattern matching

**Key Methods**:
- `route_task()` - Main routing method
- `_get_similar_patterns()` - Vector similarity search
- `_calculate_routing_score()` - Score calculation

**Usage**:
```python
from src.routing.rag_team_router import RAGTeamRouter

router = RAGTeamRouter(db_store=store)
result = await router.route_task(task_description, team_structure)
```

### 2. Weight Optimizer (`src/routing/weight_optimizer.py`)

**Purpose**: Optimizes routing weights based on historical success

**Key Methods**:
- `analyze_routing_performance()` - Performance analysis
- `optimize_domain_weights()` - Domain weight optimization
- `optimize_agent_weights()` - Agent weight optimization

**Usage**:
```python
from src.routing.weight_optimizer import WeightOptimizer

optimizer = WeightOptimizer(db_store=store)
weights = await optimizer.optimize_domain_weights()
```

### 3. Drift Detector (`src/routing/drift_detector.py`)

**Purpose**: Detects concept drift in task patterns

**Key Methods**:
- `detect_drift()` - Main drift detection
- `monitor_domain_shifts()` - Domain shift monitoring
- `get_drift_report()` - Comprehensive report

**Usage**:
```python
from src.routing.drift_detector import DriftDetector

detector = DriftDetector(db_store=store)
report = await detector.get_drift_report()
```

### 4. Performance Feedback (`src/routing/performance_feedback.py`)

**Purpose**: Continuous performance tracking and improvement

**Key Methods**:
- `record_task_execution()` - Record execution
- `get_top_performers()` - Identify top agents
- `run_feedback_cycle()` - Complete feedback cycle

**Usage**:
```python
from src.routing.performance_feedback import PerformanceFeedback

feedback = PerformanceFeedback(db_store=store)
await feedback.record_task_execution(agent, success, latency)
```

### 5. A/B Testing (`src/routing/ab_testing.py`)

**Purpose**: Statistical comparison of RAG vs baseline

**Key Methods**:
- `assign_to_group()` - Assign to test group
- `run_ab_test()` - Run complete test
- `calculate_statistical_significance()` - Z-test

**Usage**:
```python
from src.routing.ab_testing import ABTest

ab_test = ABTest(db_store=store)
results = await ab_test.run_ab_test()
```

### 6. Alerting System (`src/monitoring/rag_alerting.py`)

**Purpose**: Monitor system health and generate alerts

**Key Methods**:
- `check_accuracy()` - Check routing accuracy
- `check_drift()` - Check for drift
- `run_all_checks()` - Run all health checks

**Usage**:
```python
from src.monitoring.rag_alerting import RAGAlerting

alerting = RAGAlerting(db_store=store)
summary = await alerting.get_alert_summary()
```

---

## API Reference

See [RAG_METRICS_API.md](RAG_METRICS_API.md) for complete API documentation.

### Endpoints

| Endpoint | Description | Response Time |
|----------|-------------|---------------|
| `GET /health` | Health check | < 1ms |
| `GET /api/rag/metrics` | Metrics overview | 10-50ms |
| `GET /api/rag/patterns` | Pattern metrics | 10-50ms |
| `GET /api/rag/routing/accuracy` | Routing accuracy | 20-100ms |
| `GET /api/rag/performance` | Performance metrics | 50-200ms |
| `GET /api/rag/drift` | Drift detection | 100-500ms |
| `GET /api/rag/ab-test` | A/B test results | 50-200ms |
| `GET /api/rag/weights` | Weight optimization | 100-500ms |
| `GET /api/rag/alerts` | Current alerts | 50-200ms |

---

## Deployment

See [RAG_METRICS_DEPLOY_SYD2_ROOT.md](RAG_METRICS_DEPLOY_SYD2_ROOT.md) for deployment guide.

### Quick Deploy

```bash
# On server
cd /home/ui-cli_jake/unified-intelligence-cli
python start_rag_server.py
```

### Production Deploy

```bash
# Create systemd service
sudo systemctl enable rag-metrics
sudo systemctl start rag-metrics
```

---

## Monitoring

### Current Alerts

Check alerts at: `http://157.90.66.183:8888/api/rag/alerts`

### Alert Types

- **Low Accuracy**: Routing accuracy < 70%
- **Insufficient Patterns**: Pattern count < 50
- **Pattern Drift**: Drift score > 0.3
- **Database Issues**: Connection failures

### Metrics Dashboard

Access at: `http://157.90.66.183:8888/api/rag/metrics`

---

## Troubleshooting

See [RAG_TROUBLESHOOTING.md](RAG_TROUBLESHOOTING.md) for detailed troubleshooting.

### Common Issues

**Issue**: Low routing accuracy
- **Solution**: Build more patterns (50-100 tasks)

**Issue**: Drift detected
- **Solution**: Re-embed patterns with new data

**Issue**: Server not responding
- **Solution**: Check SurrealDB connection

---

## Performance

### Benchmarks

- **Vector Search**: 1ms (EXCELLENT)
- **Pattern Storage**: ~6.5 KB/task (ACCEPTABLE)
- **End-to-End Routing**: 275-650ms (ACCEPTABLE)
- **API Response Times**: 1-500ms (varies by endpoint)

### Optimization Tips

1. Build 50-100 patterns for best accuracy
2. Run optimization cycle weekly
3. Monitor drift detection
4. Use A/B testing to validate improvements

---

## Documentation Index

- **[RAG_METRICS_API.md](RAG_METRICS_API.md)** - Complete API reference
- **[RAG_METRICS_QUICK_START.md](RAG_METRICS_QUICK_START.md)** - Quick start guide
- **[RAG_METRICS_INTEGRATION_GUIDE.md](RAG_METRICS_INTEGRATION_GUIDE.md)** - Integration guide
- **[RAG_METRICS_DEPLOY_SYD2_ROOT.md](RAG_METRICS_DEPLOY_SYD2_ROOT.md)** - Deployment guide
- **[RAG_SERVER_RUNNING.md](RAG_SERVER_RUNNING.md)** - Server status and URLs

---

## Support

For issues or questions:
1. Check documentation above
2. Review logs: `tail -f /tmp/rag_metrics_server.log`
3. Test endpoints: `curl http://157.90.66.183:8888/health`
4. Check alerts: `curl http://157.90.66.183:8888/api/rag/alerts`

---

**Status**: ✅ Production Ready  
**Version**: 1.0  
**Last Updated**: 2025-10-18

