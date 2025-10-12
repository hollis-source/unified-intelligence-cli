# PriorityWorker Docker Deployment Guide

**Generated**: 2025-10-04
**Status**: Phase 3-4 Implementation Complete

---

## Overview

This guide covers containerized deployment of PriorityWorker with:
- Metrics Dashboard (port 8080)
- Alerting System (email/webhook/log)
- Docker Compose orchestration
- Multi-worker horizontal scaling

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                Docker Compose Network                    │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌──────────────┐      ┌──────────────┐               │
│  │ PriorityWorker│◄────►│    Redis     │               │
│  │   (Worker 1)  │      │ (Task Queue) │               │
│  │  Port: 8080   │      │  Port: 6379  │               │
│  └───────┬───────┘      └──────────────┘               │
│          │                                               │
│          │  ┌──────────────┐                            │
│          └─►│ Metrics API  │                            │
│             │ /health      │                            │
│             │ /metrics     │                            │
│             │ /prometheus  │                            │
│             └──────────────┘                            │
│                                                          │
│  ┌──────────────┐                                       │
│  │ AlertMonitor │──► Email/Slack/Discord                │
│  │   (Daemon)   │                                       │
│  └──────────────┘                                       │
│                                                          │
│  Multi-Worker Scaling:                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │  Worker 1    │  │  Worker 2    │  │  Worker N    │ │
│  │  Port: 8080  │  │  Port: 8081  │  │  Port: 808N  │ │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘ │
│         └─────────────┬──────────────────────┘         │
│                       ▼                                 │
│                  Redis (Shared)                         │
│          (Atomic task claiming via SETNX)               │
└─────────────────────────────────────────────────────────┘
```

## Prerequisites

- Docker 20.10+
- Docker Compose 1.29+
- Git repository initialized
- XAI API key (for LLM access)

## Quick Start

### 1. Single Worker Deployment

```bash
# Build PriorityWorker image
docker build -f Dockerfile.priority-worker -t priority-worker:latest .

# Start services (Redis + PriorityWorker)
docker-compose up -d redis priority-worker

# Check logs
docker-compose logs -f priority-worker

# Access metrics dashboard
curl http://localhost:8080/health
curl http://localhost:8080/metrics
```

### 2. Multi-Worker Deployment

```bash
# Edit docker-compose.yml, uncomment and set:
# deploy:
#   replicas: 4  # 4 workers

# Start with scaling
docker-compose up -d --scale priority-worker=4

# Verify workers
docker-compose ps

# Check each worker's metrics
curl http://localhost:8080/health  # Worker 1
curl http://localhost:8081/health  # Worker 2
curl http://localhost:8082/health  # Worker 3
curl http://localhost:8083/health  # Worker 4
```

## Configuration

### Environment Variables

Create `.env` file in project root:

```bash
# API Keys
XAI_API_KEY=your-xai-api-key-here

# Worker Configuration
WORKER_ID=${HOSTNAME}  # Auto-set to container hostname

# Redis Connection (defaults)
REDIS_HOST=redis
REDIS_PORT=6379
```

### Alerting Configuration

Edit `config/alerting.yaml`:

```yaml
channels:
  - type: email
    smtp_host: smtp.gmail.com
    smtp_port: 587
    smtp_user: your-email@gmail.com
    smtp_password: your-app-password
    from_address: alerting@yourdomain.com
    to_addresses:
      - admin@yourdomain.com

  - type: webhook
    webhook_url: https://hooks.slack.com/services/YOUR/WEBHOOK
    webhook_type: slack
```

### Start Alert Monitor

```bash
# As separate container
docker run -d \
  --name alert-monitor \
  --network ui-cli-network \
  -v $(pwd)/logs:/app/logs:ro \
  -v $(pwd)/config:/app/config:ro \
  priority-worker:latest \
  python3 scripts/alert_monitor.py --config config/alerting.yaml --daemon

# Or as cron job (every 5 minutes)
*/5 * * * * docker exec priority-worker-1 python3 scripts/alert_monitor.py --config config/alerting.yaml --once
```

## Monitoring

### Metrics Dashboard Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /` | HTML dashboard |
| `GET /health` | Process health (PID, uptime, memory, CPU) |
| `GET /metrics` | Task metrics (success rate, latency) |
| `GET /status` | Daemon status (cycle state, last run) |
| `GET /metrics/prometheus` | Prometheus format |

### Health Checks

Docker automatically runs health checks every 60s:

```bash
# Check health status
docker inspect priority-worker --format='{{.State.Health.Status}}'

# View health logs
docker inspect priority-worker --format='{{range .State.Health.Log}}{{.Output}}{{end}}'
```

### Logs

```bash
# Real-time logs
docker-compose logs -f priority-worker

# Last 100 lines
docker-compose logs --tail=100 priority-worker

# Logs for specific worker
docker-compose logs priority-worker-1
```

## Scaling Operations

### Horizontal Scaling (Add Workers)

```bash
# Scale to 4 workers
docker-compose up -d --scale priority-worker=4

# Scale down to 2 workers
docker-compose up -d --scale priority-worker=2

# Check running workers
docker-compose ps priority-worker
```

### Vertical Scaling (Resource Limits)

Edit `docker-compose.yml`:

```yaml
priority-worker:
  deploy:
    resources:
      limits:
        cpus: '4.0'      # Increase CPU
        memory: 2G       # Increase memory
      reservations:
        cpus: '1.0'
        memory: 512M
```

### Performance Expectations

| Workers | Expected Throughput | Resource Usage |
|---------|---------------------|----------------|
| N=1 | Baseline (10 tasks/cycle) | 256MB, 0.5 CPU |
| N=2 | 1.8x baseline | 512MB, 1.0 CPU |
| N=4 | 3.2x baseline | 1GB, 2.0 CPU |
| N=8 | 5.5x baseline | 2GB, 4.0 CPU |

> Note: Gains plateau at N>10 due to Redis/Git contention

## Deployment Commands

### Development

```bash
# Build and start with live code updates
docker-compose up --build

# Rebuild after code changes
docker-compose build priority-worker
docker-compose up -d priority-worker
```

### Production

```bash
# Build production image
docker build -f Dockerfile.priority-worker -t priority-worker:production .

# Tag and push (if using registry)
docker tag priority-worker:production registry.example.com/priority-worker:latest
docker push registry.example.com/priority-worker:latest

# Deploy
docker-compose -f docker-compose.prod.yml up -d

# Zero-downtime rolling update
docker-compose up -d --no-deps --build priority-worker
```

### Backup and Recovery

```bash
# Backup Redis data
docker run --rm -v priority-worker-redis:/data -v $(pwd)/backups:/backups \
  alpine tar czf /backups/redis-backup-$(date +%Y%m%d).tar.gz /data

# Restore Redis data
docker run --rm -v priority-worker-redis:/data -v $(pwd)/backups:/backups \
  alpine tar xzf /backups/redis-backup-20251004.tar.gz -C /

# Backup Git repository
tar czf repo-backup-$(date +%Y%m%d).tar.gz .git/
```

## Troubleshooting

### Worker Not Starting

```bash
# Check logs
docker-compose logs priority-worker

# Common issues:
# 1. Missing XAI_API_KEY
#    Solution: Add to .env file

# 2. Redis not accessible
docker-compose exec priority-worker ping redis
#    Solution: Ensure Redis is healthy

# 3. Git not configured
docker-compose exec priority-worker git config --list
#    Solution: Already configured in Dockerfile
```

### Metrics Dashboard Not Accessible

```bash
# Check if dashboard is running
docker-compose exec priority-worker curl http://localhost:8080/health

# Check port mapping
docker-compose port priority-worker 8080

# Check firewall
sudo ufw status
sudo ufw allow 8080/tcp
```

### High Memory Usage

```bash
# Check memory per worker
docker stats priority-worker

# If >500MB, alert should fire
# Check alert logs
docker-compose logs alert-monitor

# Restart worker to reclaim memory
docker-compose restart priority-worker
```

### Multi-Worker Conflicts

```bash
# Verify atomic task claiming
docker-compose logs priority-worker | grep "claimed task"

# Should see each task claimed by only ONE worker
# If duplicates, check Redis connection

# Inspect Redis locks
docker-compose exec redis redis-cli keys "priority:*"
docker-compose exec redis redis-cli get "priority:lock:prod-001"
```

## Migration from Native to Container

### Step-by-Step Migration

```bash
# 1. Stop native daemon
touch /tmp/priority_worker_stop
ps aux | grep priority_worker.py
kill <PID>

# 2. Export current state
cp logs/priority_worker_production.log logs/native_final.log
cp data/metrics/priority_worker_*.json data/metrics/native/

# 3. Ensure Git is committed
git status
git add .
git commit -m "Pre-containerization checkpoint"

# 4. Build and start container
docker-compose up -d redis priority-worker

# 5. Verify containerized daemon
curl http://localhost:8080/health

# 6. Monitor first cycle
docker-compose logs -f priority-worker

# 7. Compare metrics
curl http://localhost:8080/metrics
cat data/metrics/native/priority_worker_*.json
```

## Security Considerations

### Non-Root User

Container runs as `workeruser` (UID 1000), not root.

### Read-Only Filesystem

Config files mounted read-only:

```yaml
volumes:
  - ./config:/app/config:ro
```

### Network Isolation

Services on private bridge network:

```bash
# Only exposed ports accessible from host
docker network inspect ui-cli-network
```

### Secrets Management

Do not commit `.env` file:

```bash
echo ".env" >> .gitignore
```

Use Docker secrets for production:

```yaml
secrets:
  xai_api_key:
    external: true

services:
  priority-worker:
    secrets:
      - xai_api_key
```

## Resource Management

### Resource Limits (Per Worker)

```yaml
deploy:
  resources:
    limits:
      cpus: '2.0'      # Max 2 CPU cores
      memory: 1G       # Max 1GB RAM
    reservations:
      cpus: '0.5'      # Min 0.5 CPU cores
      memory: 256M     # Min 256MB RAM
```

### Disk Space Management

```bash
# Check Docker disk usage
docker system df

# Clean up old images
docker image prune -a

# Clean up stopped containers
docker container prune

# Clean up unused volumes
docker volume prune
```

## Next Steps

1. **Test Deployment**: Run single worker for 24h cycle
2. **Enable Alerting**: Configure email/Slack webhooks
3. **Scale Horizontally**: Test with 2-4 workers
4. **Monitor Performance**: Track throughput gains
5. **Optimize Resources**: Tune CPU/memory limits based on metrics

---

**Implementation Status**: ✅ Phase 3-4 Complete
**Generated by**: ULTRATHINK design → Implementation
**Last Updated**: 2025-10-04
