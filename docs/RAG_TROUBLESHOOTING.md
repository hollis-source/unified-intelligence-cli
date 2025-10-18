# RAG System Troubleshooting Guide

**Version**: 1.0  
**Date**: 2025-10-18

---

## Table of Contents

1. [Common Issues](#common-issues)
2. [Error Messages](#error-messages)
3. [Performance Issues](#performance-issues)
4. [Database Issues](#database-issues)
5. [API Issues](#api-issues)
6. [Deployment Issues](#deployment-issues)
7. [Diagnostic Commands](#diagnostic-commands)

---

## Common Issues

### Issue: Low Routing Accuracy (< 70%)

**Symptoms**:
- Alert: "RAG routing accuracy is low"
- Poor task routing results
- Agents receiving wrong tasks

**Causes**:
- Insufficient training patterns
- Poor quality patterns
- Outdated patterns (drift)

**Solutions**:

```bash
# 1. Check pattern count
curl http://157.90.66.183:8888/api/rag/patterns

# 2. If count < 50, build more patterns
python main.py --enable-rag "task description 1"
python main.py --enable-rag "task description 2"
# ... repeat 50-100 times

# 3. Check for drift
curl http://157.90.66.183:8888/api/rag/drift

# 4. If drift detected, re-embed patterns
python scripts/embed_patterns.py --force-reembed
```

---

### Issue: Insufficient Patterns

**Symptoms**:
- Alert: "Insufficient patterns: X (minimum: 50)"
- RAG routing falls back to baseline
- Low confidence scores

**Causes**:
- New system (not enough data)
- Patterns not being stored
- Database connection issues

**Solutions**:

```bash
# 1. Check current pattern count
curl http://157.90.66.183:8888/api/rag/patterns

# 2. Verify patterns are being stored
# Run a task and check if count increases
python main.py --enable-rag "test task"
curl http://157.90.66.183:8888/api/rag/patterns

# 3. If not increasing, check database
systemctl status surrealdb
journalctl -u surrealdb -n 50

# 4. Build patterns systematically
for i in {1..50}; do
  python main.py --enable-rag "Task $i: implement feature"
done
```

---

### Issue: Pattern Drift Detected

**Symptoms**:
- Alert: "Pattern drift detected"
- Drift score > 0.3
- Recommendation: "Re-embed patterns"

**Causes**:
- Task types have changed
- New domains introduced
- Old patterns no longer relevant

**Solutions**:

```bash
# 1. Check drift details
curl http://157.90.66.183:8888/api/rag/drift

# 2. Review significant changes
# Look at "significant_changes" in response

# 3. Re-embed patterns with new data
python scripts/embed_patterns.py --reembed-all

# 4. Verify drift is resolved
curl http://157.90.66.183:8888/api/rag/drift
```

---

### Issue: Server Not Responding

**Symptoms**:
- Connection refused
- Timeout errors
- 502/503 errors

**Causes**:
- Server not running
- Port blocked
- Database connection failed

**Solutions**:

```bash
# 1. Check if server is running
ps aux | grep start_rag_server
netstat -tlnp | grep 8888

# 2. Check server logs
tail -f /tmp/rag_metrics_server.log

# 3. Restart server
pkill -f start_rag_server
cd /home/ui-cli_jake/unified-intelligence-cli
python start_rag_server.py &

# 4. Check firewall
sudo ufw status
sudo ufw allow 8888/tcp

# 5. Test locally first
curl http://localhost:8888/health
```

---

## Error Messages

### "Failed to connect to SurrealDB"

**Error**:
```
❌ Failed to connect: Connection refused
```

**Solutions**:

```bash
# 1. Check if SurrealDB is running
systemctl status surrealdb

# 2. Start SurrealDB if not running
systemctl start surrealdb

# 3. Check SurrealDB logs
journalctl -u surrealdb -n 50

# 4. Verify connection URL
echo $SURREALDB_URL
# Should be: ws://localhost:8000

# 5. Test connection manually
curl http://localhost:8000/health
```

---

### "Event loop already running"

**Error**:
```
RuntimeError: This event loop is already running
```

**Solutions**:

```bash
# This happens when running in Jupyter or async context
# Use subprocess instead:

nohup python start_rag_server.py > /tmp/rag_server.log 2>&1 &

# Or use the deployment script:
./scripts/deploy_syd2_root.sh
```

---

### "Insufficient data for optimization"

**Error**:
```
Need at least 10 completed routing decisions for optimization
```

**Solutions**:

```bash
# 1. Check current decision count
curl http://157.90.66.183:8888/api/rag/metrics

# 2. Run more tasks to generate decisions
python main.py --enable-rag "task 1"
python main.py --enable-rag "task 2"
# ... until you have 10+ decisions

# 3. Verify decisions are being tracked
curl http://157.90.66.183:8888/api/rag/routing/accuracy
```

---

## Performance Issues

### Slow API Responses

**Symptoms**:
- API calls taking > 1 second
- Timeouts
- High latency

**Diagnosis**:

```bash
# 1. Test each endpoint
time curl http://157.90.66.183:8888/health
time curl http://157.90.66.183:8888/api/rag/metrics
time curl http://157.90.66.183:8888/api/rag/drift

# 2. Check database performance
# SurrealDB should respond in < 10ms

# 3. Check server load
top
htop
```

**Solutions**:

```bash
# 1. Restart server
pkill -f start_rag_server
python start_rag_server.py &

# 2. Optimize database
# Ensure indexes are created
# Limit query result sizes

# 3. Check for memory leaks
ps aux | grep python
# If memory usage is high, restart server
```

---

### High Memory Usage

**Symptoms**:
- Server using > 1GB RAM
- Out of memory errors
- Slow performance

**Solutions**:

```bash
# 1. Check memory usage
ps aux | grep start_rag_server

# 2. Restart server to clear memory
pkill -f start_rag_server
python start_rag_server.py &

# 3. Limit pattern cache size
# Edit configuration to reduce cache

# 4. Monitor memory over time
watch -n 5 'ps aux | grep start_rag_server'
```

---

## Database Issues

### Database Connection Lost

**Symptoms**:
- Alert: "Database connection failed"
- 500 errors from API
- "Connection closed" errors

**Solutions**:

```bash
# 1. Check SurrealDB status
systemctl status surrealdb

# 2. Restart SurrealDB
systemctl restart surrealdb

# 3. Restart RAG server
pkill -f start_rag_server
sleep 3
python start_rag_server.py &

# 4. Verify connection
curl http://157.90.66.183:8888/api/rag/alerts
```

---

### Database Query Errors

**Symptoms**:
- SQL syntax errors
- "Table not found" errors
- Empty results

**Solutions**:

```bash
# 1. Check database schema
# Connect to SurrealDB and verify tables exist

# 2. Recreate tables if needed
python scripts/setup_database.py

# 3. Check query syntax in logs
tail -f /tmp/rag_metrics_server.log | grep "SELECT"

# 4. Test queries manually
# Use SurrealDB CLI to test queries
```

---

## API Issues

### 404 Not Found

**Symptoms**:
- Endpoint returns 404
- "Route not found" error

**Solutions**:

```bash
# 1. Verify endpoint URL
# Correct: /api/rag/metrics
# Wrong: /api/metrics

# 2. Check available routes
curl http://157.90.66.183:8888/health

# 3. Restart server with latest code
pkill -f start_rag_server
git pull  # if using git
python start_rag_server.py &
```

---

### 500 Internal Server Error

**Symptoms**:
- API returns 500
- Error in response body

**Solutions**:

```bash
# 1. Check server logs
tail -f /tmp/rag_metrics_server.log

# 2. Look for stack traces
grep -A 20 "Traceback" /tmp/rag_metrics_server.log

# 3. Test with simpler endpoint
curl http://157.90.66.183:8888/health

# 4. Restart server
pkill -f start_rag_server
python start_rag_server.py &
```

---

## Deployment Issues

### Port Already in Use

**Error**:
```
OSError: [Errno 98] Address already in use
```

**Solutions**:

```bash
# 1. Find process using port 8888
netstat -tlnp | grep 8888
lsof -i :8888

# 2. Kill the process
kill <PID>

# 3. Or use a different port
export PORT=8889
python start_rag_server.py &
```

---

### Permission Denied

**Error**:
```
PermissionError: [Errno 13] Permission denied
```

**Solutions**:

```bash
# 1. Check file permissions
ls -la start_rag_server.py

# 2. Make executable
chmod +x start_rag_server.py

# 3. Check directory permissions
ls -la /tmp/

# 4. Run with appropriate user
# Don't run as root unless necessary
```

---

## Diagnostic Commands

### Quick Health Check

```bash
#!/bin/bash
echo "=== RAG System Health Check ==="

echo "1. Server Status:"
ps aux | grep start_rag_server | grep -v grep && echo "✅ Running" || echo "❌ Not running"

echo "2. Database Status:"
systemctl is-active surrealdb && echo "✅ Running" || echo "❌ Not running"

echo "3. API Health:"
curl -s http://localhost:8888/health | grep -q "ok" && echo "✅ Healthy" || echo "❌ Unhealthy"

echo "4. Alerts:"
curl -s http://localhost:8888/api/rag/alerts | grep -o '"total_alerts":[0-9]*'

echo "5. Pattern Count:"
curl -s http://localhost:8888/api/rag/patterns | grep -o '"total":[0-9]*'
```

### Collect Diagnostic Info

```bash
#!/bin/bash
echo "=== Collecting Diagnostic Info ==="

# Server logs
echo "Server Logs (last 50 lines):"
tail -50 /tmp/rag_metrics_server.log

# Database logs
echo "Database Logs (last 20 lines):"
journalctl -u surrealdb -n 20

# System info
echo "System Info:"
uname -a
free -h
df -h

# Network info
echo "Network Info:"
netstat -tlnp | grep 8888

# Process info
echo "Process Info:"
ps aux | grep -E "start_rag_server|surrealdb" | grep -v grep
```

---

## Getting Help

If you can't resolve the issue:

1. **Collect diagnostic info** using commands above
2. **Check logs**: `/tmp/rag_metrics_server.log`
3. **Test endpoints**: Start with `/health`, then others
4. **Review documentation**: [RAG_SYSTEM_README.md](RAG_SYSTEM_README.md)
5. **Check alerts**: `curl http://157.90.66.183:8888/api/rag/alerts`

---

**Last Updated**: 2025-10-18

