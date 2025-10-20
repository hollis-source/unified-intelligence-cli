# RAG Metrics API Documentation

**Version**: 1.0  
**Date**: 2025-10-18  
**Status**: Production Ready

---

## Overview

The RAG Metrics API provides HTTP endpoints for monitoring and analyzing the RAG (Retrieval-Augmented Generation) system's performance, patterns, and adaptive learning capabilities.

**Base URL**: `http://localhost:8080` (configurable)  
**Protocol**: HTTP/HTTPS  
**Format**: JSON  
**Framework**: aiohttp (async)

---

## Integration

### With Existing API Server

The RAG metrics endpoints are integrated with the existing `api_server.py`:

```python
from src.adapters.web.api_server import create_app
from src.adapters.rag.surrealdb_store import SurrealDBStore

# Create app with RAG metrics enabled
db_store = SurrealDBStore(...)
await db_store.connect()

app = create_app(
    task_runner=my_task_runner,
    db_store=db_store,
    enable_rag_metrics=True  # Enable RAG endpoints
)
```

### Standalone Server

```python
from src.adapters.web.rag_metrics_server import RAGMetricsServer
from aiohttp import web

server = RAGMetricsServer()
app = web.Application()

# Add routes
from src.adapters.web.rag_metrics_server import add_rag_routes
add_rag_routes(app)

web.run_app(app, host='0.0.0.0', port=8080)
```

---

## API Endpoints

### 1. Health Check

**Endpoint**: `GET /health`  
**Description**: Check server health status  
**Authentication**: None

**Response**:
```json
{
  "status": "ok"
}
```

---

### 2. Metrics Overview

**Endpoint**: `GET /api/rag/metrics`  
**Description**: Get overview of all RAG metrics  
**Authentication**: None (add as needed)

**Response**:
```json
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

**Fields**:
- `total_patterns`: Total number of stored execution patterns
- `total_routing_decisions`: Total routing decisions tracked
- `rag_routing_accuracy`: RAG routing accuracy percentage
- `rag_enabled`: Whether RAG is currently enabled

---

### 3. Pattern Metrics

**Endpoint**: `GET /api/rag/patterns`  
**Description**: Get pattern count metrics by domain  
**Authentication**: None

**Response**:
```json
{
  "status": "ok",
  "patterns": {
    "total": 1234,
    "by_domain": {
      "backend": 456,
      "frontend": 389,
      "qa": 234,
      "devops": 155
    }
  }
}
```

**Use Cases**:
- Monitor pattern accumulation
- Identify domain coverage
- Detect imbalanced pattern distribution

---

### 4. Routing Accuracy

**Endpoint**: `GET /api/rag/routing/accuracy`  
**Description**: Get routing accuracy metrics for RAG vs baseline  
**Authentication**: None

**Response**:
```json
{
  "status": "ok",
  "accuracy": {
    "rag": 85.5,
    "baseline": 75.0,
    "improvement": 10.5
  },
  "recent_decisions": [
    {
      "task": "Implement user authentication...",
      "strategy": "rag",
      "agent": "backend-lead",
      "success": true
    }
  ]
}
```

**Fields**:
- `rag`: RAG routing accuracy (%)
- `baseline`: Baseline routing accuracy (%)
- `improvement`: Absolute improvement (percentage points)
- `recent_decisions`: Last 10 routing decisions

---

### 5. Performance Metrics

**Endpoint**: `GET /api/rag/performance`  
**Description**: Get agent performance metrics  
**Authentication**: None

**Response**:
```json
{
  "status": "ok",
  "performance": {
    "total_agents": 134,
    "top_performers": [
      {
        "agent": "qa-engineer",
        "success_rate": 100.0,
        "total_tasks": 45
      },
      {
        "agent": "frontend-lead",
        "success_rate": 95.5,
        "total_tasks": 67
      }
    ],
    "low_performers": [
      {
        "agent": "legacy-specialist",
        "success_rate": 45.0,
        "total_tasks": 20
      }
    ]
  }
}
```

**Use Cases**:
- Identify high-performing agents
- Detect underperforming agents
- Optimize routing preferences

---

### 6. Drift Detection

**Endpoint**: `GET /api/rag/drift`  
**Description**: Get drift detection status  
**Authentication**: None

**Response**:
```json
{
  "status": "ok",
  "drift": {
    "needs_reembedding": false,
    "drift_detected": false,
    "drift_score": 0.15,
    "recommendation": "Pattern distribution is stable",
    "details": {
      "drift_detection": {
        "drift_detected": false,
        "drift_score": 0.15,
        "similarity": 0.85,
        "threshold": 0.3
      },
      "domain_shifts": {
        "shift_detected": false,
        "shifts": []
      },
      "pattern_staleness": {
        "total_patterns": 1234
      }
    }
  }
}
```

**Fields**:
- `needs_reembedding`: Whether patterns should be re-embedded
- `drift_detected`: Whether concept drift was detected
- `drift_score`: Drift score (0.0-1.0, higher = more drift)
- `recommendation`: Action recommendation

**Thresholds**:
- Drift score > 0.3: Significant drift detected
- Domain shift > 15%: Significant shift detected

---

### 7. A/B Test Results

**Endpoint**: `GET /api/rag/ab-test`  
**Description**: Get A/B test results comparing RAG vs baseline  
**Authentication**: None

**Response**:
```json
{
  "status": "ok",
  "ab_test": {
    "test_name": "rag_vs_baseline",
    "control": {
      "strategy": "base",
      "total": 150,
      "successes": 112,
      "failures": 38,
      "success_rate": 74.7
    },
    "treatment": {
      "strategy": "rag",
      "total": 150,
      "successes": 128,
      "failures": 22,
      "success_rate": 85.3
    },
    "significant": true,
    "improvement": 14.2,
    "recommendation": "Deploy rag - significantly better than base",
    "sample_size_adequate": true
  }
}
```

**Fields**:
- `significant`: Whether difference is statistically significant (95% confidence)
- `improvement`: Relative improvement percentage
- `sample_size_adequate`: Whether sample size >= 30 per group

---

### 8. Weight Optimization

**Endpoint**: `GET /api/rag/weights`  
**Description**: Get weight optimization status and recommendations  
**Authentication**: None

**Response**:
```json
{
  "status": "ok",
  "optimization": {
    "total_decisions": 567,
    "domain_weights": {
      "backend": 1.15,
      "frontend": 0.95,
      "qa": 1.25
    },
    "agent_weights": {
      "backend-lead": 1.10,
      "qa-engineer": 1.30
    },
    "recommendations": [
      {
        "type": "rag_success",
        "rag_success_rate": 85.5,
        "base_success_rate": 75.0,
        "improvement": 10.5,
        "message": "RAG routing achieving +10.5% improvement over baseline",
        "suggestion": "Consider using RAG routing by default"
      }
    ]
  }
}
```

**Weight Multipliers**:
- Range: 0.5x - 2.0x
- 1.0x: Average performance
- > 1.0x: Above average (prefer)
- < 1.0x: Below average (avoid)

---

## Error Handling

All endpoints return errors in consistent format:

```json
{
  "status": "error",
  "error": "Error message description"
}
```

**HTTP Status Codes**:
- `200`: Success
- `400`: Bad request
- `500`: Internal server error
- `503`: Service unavailable

---

## Usage Examples

### cURL

```bash
# Get metrics overview
curl http://localhost:8080/api/rag/metrics

# Get routing accuracy
curl http://localhost:8080/api/rag/routing/accuracy

# Get drift detection status
curl http://localhost:8080/api/rag/drift
```

### Python

```python
import aiohttp

async def get_rag_metrics():
    async with aiohttp.ClientSession() as session:
        async with session.get('http://localhost:8080/api/rag/metrics') as response:
            data = await response.json()
            print(f"Total patterns: {data['metrics']['total_patterns']}")
```

### JavaScript

```javascript
fetch('http://localhost:8080/api/rag/metrics')
  .then(response => response.json())
  .then(data => {
    console.log('Total patterns:', data.metrics.total_patterns);
  });
```

---

## Monitoring & Alerting

### Recommended Alerts

1. **Low Pattern Count**: Alert if `total_patterns < 50`
2. **Low Accuracy**: Alert if `rag_routing_accuracy < 70%`
3. **Drift Detected**: Alert if `drift_detected = true`
4. **Underperforming RAG**: Alert if `improvement < 0%`

### Prometheus Integration

Future enhancement: Export metrics in Prometheus format at `/metrics/prometheus`

---

## Performance

**Typical Response Times**:
- `/health`: < 1ms
- `/api/rag/metrics`: 10-50ms
- `/api/rag/patterns`: 10-50ms
- `/api/rag/routing/accuracy`: 20-100ms
- `/api/rag/performance`: 50-200ms
- `/api/rag/drift`: 100-500ms
- `/api/rag/ab-test`: 50-200ms
- `/api/rag/weights`: 100-500ms

**Database Queries**: All endpoints query SurrealDB asynchronously

---

## Security Considerations

**Current**: No authentication (development)

**Production Recommendations**:
1. Add JWT authentication
2. Rate limiting (100 req/min)
3. HTTPS/TLS encryption
4. API key validation
5. CORS configuration

---

## Version History

- **1.0** (2025-10-18): Initial release
  - 8 endpoints
  - Full RAG metrics coverage
  - Integrated with api_server.py

---

## Support

For issues or questions:
- Check logs in SurrealDB
- Verify database connection
- Review error responses
- Test with `/health` endpoint first

