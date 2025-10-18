# RAG Metrics API - Quick Start Guide

**For**: syd2.jacobhollis.com deployment  
**Date**: 2025-10-18

---

## 🚀 Quick Deploy (3 Steps)

### 1. Deploy to syd2

```bash
# SSH to syd2
ssh ubuntu@syd2.jacobhollis.com

# Navigate to project
cd /home/ubuntu/unified-intelligence-cli

# Run deployment script
./scripts/deploy_rag_metrics_server.sh
```

### 2. Verify Deployment

```bash
# Check service status
sudo systemctl status rag-metrics

# Test health endpoint
curl http://localhost:8080/health

# Test RAG metrics
curl http://localhost:8080/api/rag/metrics
```

### 3. Access Externally

```bash
# From your local machine
curl https://syd2.jacobhollis.com:8080/api/rag/metrics
```

---

## 📊 Available Endpoints

| Endpoint | Description | Response Time |
|----------|-------------|---------------|
| `GET /health` | Health check | < 1ms |
| `GET /api/rag/metrics` | Metrics overview | 10-50ms |
| `GET /api/rag/patterns` | Pattern metrics by domain | 10-50ms |
| `GET /api/rag/routing/accuracy` | RAG vs baseline accuracy | 20-100ms |
| `GET /api/rag/performance` | Agent performance | 50-200ms |
| `GET /api/rag/drift` | Drift detection status | 100-500ms |
| `GET /api/rag/ab-test` | A/B test results | 50-200ms |
| `GET /api/rag/weights` | Weight optimization | 100-500ms |

---

## 🔧 Common Commands

### Service Management

```bash
# Start service
sudo systemctl start rag-metrics

# Stop service
sudo systemctl stop rag-metrics

# Restart service
sudo systemctl restart rag-metrics

# Check status
sudo systemctl status rag-metrics

# View logs (live)
sudo journalctl -u rag-metrics -f

# View last 100 lines
sudo journalctl -u rag-metrics -n 100
```

### Testing Endpoints

```bash
# Health check
curl http://localhost:8080/health

# Metrics overview
curl http://localhost:8080/api/rag/metrics | jq .

# Routing accuracy
curl http://localhost:8080/api/rag/routing/accuracy | jq .

# Performance metrics
curl http://localhost:8080/api/rag/performance | jq .

# Drift detection
curl http://localhost:8080/api/rag/drift | jq .

# A/B test results
curl http://localhost:8080/api/rag/ab-test | jq .
```

---

## 📈 Example Responses

### Metrics Overview

```bash
curl http://localhost:8080/api/rag/metrics
```

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

### Routing Accuracy

```bash
curl http://localhost:8080/api/rag/routing/accuracy
```

```json
{
  "status": "ok",
  "accuracy": {
    "rag": 85.5,
    "baseline": 75.0,
    "improvement": 10.5
  },
  "recent_decisions": [...]
}
```

### Drift Detection

```bash
curl http://localhost:8080/api/rag/drift
```

```json
{
  "status": "ok",
  "drift": {
    "needs_reembedding": false,
    "drift_detected": false,
    "drift_score": 0.15,
    "recommendation": "Pattern distribution is stable"
  }
}
```

---

## 🐛 Troubleshooting

### Service Won't Start

```bash
# Check logs
sudo journalctl -u rag-metrics -n 50

# Check SurrealDB
sudo systemctl status surrealdb

# Test SurrealDB connection
curl http://localhost:8000/health
```

### Connection Refused

```bash
# Check if service is running
sudo systemctl status rag-metrics

# Check if port is open
sudo netstat -tlnp | grep 8080

# Check firewall
sudo ufw status
```

### Database Errors

```bash
# Restart SurrealDB
sudo systemctl restart surrealdb

# Restart RAG metrics server
sudo systemctl restart rag-metrics

# Check both services
sudo systemctl status surrealdb rag-metrics
```

---

## 🔒 Security Notes

**Current Setup**: No authentication (development)

**For Production**:
1. Add JWT authentication
2. Configure HTTPS/TLS
3. Set up rate limiting
4. Configure firewall rules
5. Use environment-specific credentials

---

## 📝 Configuration

### Environment Variables

Edit `/etc/systemd/system/rag-metrics.service`:

```ini
Environment="SURREALDB_URL=ws://localhost:8000"
Environment="HOST=0.0.0.0"
Environment="PORT=8080"
```

After changes:
```bash
sudo systemctl daemon-reload
sudo systemctl restart rag-metrics
```

---

## 📚 Full Documentation

- **API Reference**: `docs/RAG_METRICS_API.md`
- **Integration Guide**: `docs/RAG_METRICS_INTEGRATION_GUIDE.md`
- **Server Code**: `src/adapters/web/rag_metrics_server.py`
- **Deployment Script**: `scripts/deploy_rag_metrics_server.sh`

---

## ✅ Verification Checklist

- [ ] Service deployed: `sudo systemctl status rag-metrics`
- [ ] Health endpoint works: `curl http://localhost:8080/health`
- [ ] RAG metrics work: `curl http://localhost:8080/api/rag/metrics`
- [ ] SurrealDB connected: Check logs for "Connected to SurrealDB"
- [ ] External access works: `curl https://syd2.jacobhollis.com:8080/health`
- [ ] Logs are clean: `sudo journalctl -u rag-metrics -n 20`

---

## 🎯 Next Steps

1. **Deploy**: Run `./scripts/deploy_rag_metrics_server.sh`
2. **Test**: Verify all endpoints respond
3. **Monitor**: Set up log monitoring
4. **Secure**: Add authentication (if needed)
5. **Dashboard**: Build web UI for visualization

---

## 💡 Tips

- Use `jq` for pretty JSON: `curl ... | jq .`
- Monitor logs in real-time: `sudo journalctl -u rag-metrics -f`
- Check service on boot: `sudo systemctl is-enabled rag-metrics`
- View all endpoints: Check server startup output

---

**Status**: ✅ Ready for deployment to syd2.jacobhollis.com

