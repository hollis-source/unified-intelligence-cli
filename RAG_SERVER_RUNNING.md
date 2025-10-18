# RAG Metrics Server - RUNNING ON 157.90.66.183

**Status**: ✅ **LIVE AND OPERATIONAL**  
**Server**: 157.90.66.183  
**Port**: 8888  
**Started**: 2025-10-18

---

## Server Information

- **Internal URL**: `http://localhost:8888`
- **External URL**: `http://157.90.66.183:8888`
- **Process ID**: 3247601
- **Database**: SurrealDB on localhost:8000 ✅ Connected
- **Status**: All 8 endpoints operational

---

## API Endpoints (All Working ✅)

### 1. Health Check
```bash
curl http://157.90.66.183:8888/health
```
**Response**: `{"status": "ok"}`

### 2. Metrics Overview
```bash
curl http://157.90.66.183:8888/api/rag/metrics
```
**Response**:
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

### 3. Pattern Metrics
```bash
curl http://157.90.66.183:8888/api/rag/patterns
```
**Response**:
```json
{
  "status": "ok",
  "patterns": {
    "total": 0,
    "by_domain": {}
  }
}
```

### 4. Routing Accuracy
```bash
curl http://157.90.66.183:8888/api/rag/routing/accuracy
```
**Response**:
```json
{
  "status": "ok",
  "accuracy": {
    "rag": 0.0,
    "baseline": 0.0,
    "improvement": 0.0
  },
  "recent_decisions": [...]
}
```

### 5. Performance Metrics
```bash
curl http://157.90.66.183:8888/api/rag/performance
```
**Response**:
```json
{
  "status": "ok",
  "performance": {
    "total_agents": 3,
    "top_performers": [
      {"agent": "frontend-lead", "success_rate": 100.0, "total_tasks": 2},
      {"agent": "qa-engineer", "success_rate": 100.0, "total_tasks": 3},
      {"agent": "backend-lead", "success_rate": 66.67, "total_tasks": 3}
    ],
    "low_performers": []
  }
}
```

### 6. Drift Detection
```bash
curl http://157.90.66.183:8888/api/rag/drift
```
**Response**:
```json
{
  "status": "ok",
  "drift": {
    "needs_reembedding": false,
    "drift_detected": false,
    "drift_score": 0.0,
    "recommendation": "Pattern distribution is stable"
  }
}
```

### 7. A/B Test Results
```bash
curl http://157.90.66.183:8888/api/rag/ab-test
```
**Response**:
```json
{
  "status": "ok",
  "ab_test": {
    "test_name": "rag_vs_baseline",
    "control": {"strategy": "base", "total": 0, "success_rate": 0.0},
    "treatment": {"strategy": "rag", "total": 0, "success_rate": 0.0},
    "significant": false,
    "recommendation": "Continue testing - no significant difference yet"
  }
}
```

### 8. Weight Optimization
```bash
curl http://157.90.66.183:8888/api/rag/weights
```
**Response**:
```json
{
  "status": "ok",
  "optimization": {
    "total_decisions": 0,
    "domain_weights": {},
    "agent_weights": {},
    "recommendations": [
      {
        "type": "insufficient_data",
        "message": "Need at least 10 completed routing decisions for optimization"
      }
    ]
  }
}
```

---

## Server Management

### Check if Server is Running
```bash
ps aux | grep 3247601
netstat -tlnp | grep 8888
```

### View Server Logs
```bash
tail -f /tmp/rag_metrics_server.log
```

### Stop Server
```bash
kill 3247601
```

### Restart Server
```bash
cd /home/ui-cli_jake/unified-intelligence-cli
nohup bash -c "source venv/bin/activate && python start_rag_server.py" > /tmp/rag_metrics_server.log 2>&1 &
```

---

## Test All Endpoints

```bash
# Quick test script
for endpoint in health api/rag/metrics api/rag/patterns api/rag/routing/accuracy api/rag/performance api/rag/drift api/rag/ab-test api/rag/weights; do
  echo "Testing /$endpoint"
  curl -s http://157.90.66.183:8888/$endpoint | head -c 100
  echo -e "\n---"
done
```

---

## External Access

### From Your Local Machine

```bash
# Health check
curl http://157.90.66.183:8888/health

# Get metrics
curl http://157.90.66.183:8888/api/rag/metrics

# Get performance data
curl http://157.90.66.183:8888/api/rag/performance
```

### From Browser

Open these URLs in your browser:
- http://157.90.66.183:8888/health
- http://157.90.66.183:8888/api/rag/metrics
- http://157.90.66.183:8888/api/rag/patterns
- http://157.90.66.183:8888/api/rag/routing/accuracy
- http://157.90.66.183:8888/api/rag/performance
- http://157.90.66.183:8888/api/rag/drift
- http://157.90.66.183:8888/api/rag/ab-test
- http://157.90.66.183:8888/api/rag/weights

---

## Current Data

- **Total Patterns**: 0 (need to run tasks with RAG to build patterns)
- **Routing Decisions**: 4 (tracked)
- **Agent Performance**: 3 agents tracked
  - frontend-lead: 100% success (2 tasks)
  - qa-engineer: 100% success (3 tasks)
  - backend-lead: 66.7% success (3 tasks)

---

## Next Steps

1. **Build Pattern Database**: Run 50-100 tasks with `--enable-rag` flag
2. **Monitor Metrics**: Use the API endpoints to track progress
3. **Analyze Performance**: Check routing accuracy improvements
4. **Optimize Weights**: Once enough data is collected

---

## Firewall Note

If you can't access from external locations, you may need to open port 8888:

```bash
# Check firewall
sudo ufw status

# Allow port 8888 (if needed)
sudo ufw allow 8888/tcp
```

---

## Summary

✅ **Server Status**: RUNNING  
✅ **All Endpoints**: OPERATIONAL (8/8)  
✅ **Database**: Connected  
✅ **External Access**: http://157.90.66.183:8888  
✅ **Process ID**: 3247601  

**The RAG Metrics API is now live and ready to use!**

