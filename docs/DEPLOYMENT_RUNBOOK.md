# Project Builder Production Deployment Runbook

**Version**: 1.0
**Last Updated**: 2025-10-07
**Production Readiness**: 100%

---

## Overview

This runbook provides complete operational procedures for deploying, monitoring, and maintaining Project Builder in production. Project Builder is an AI-powered autonomous code generation system using HTN (Hierarchical Task Networks), multi-agent teams, and remote file access via SSH.

**Architecture**: Clean Architecture with SurrealDB (state), Redis (LLM cache), Prometheus/Grafana (monitoring)

---

## Prerequisites

### System Requirements

- **Docker**: 20.10+ with docker-compose 2.0+
- **RAM**: Minimum 8GB (12GB recommended)
- **CPU**: 4+ cores recommended
- **Disk**: 50GB+ available (20GB for volumes, 30GB for images)
- **Network**: Outbound HTTPS (443) for LLM providers, SSH (22) for remote file access

### Access Requirements

- **SSH Private Key**: For remote codebase access (id_ed25519 format)
- **API Keys**: OpenAI, X.AI, HuggingFace tokens
- **SurrealDB Credentials**: Strong password for production database

---

## First-Time Setup

### 1. Clone Repository

```bash
git clone https://github.com/your-org/unified-intelligence-cli.git
cd unified-intelligence-cli
git checkout priority/prod-010  # Or main/production branch
```

### 2. Create Production Environment File

```bash
# Copy template
cp .env.production.example .env.production

# Edit with production values
nano .env.production
```

**Required Changes**:
- `SURREALDB_PASSWORD`: Strong password (min 16 chars, alphanumeric + symbols)
- `PB_DB_PASSWORD`: Same as SURREALDB_PASSWORD
- `OPENAI_API_KEY`: Your OpenAI API key (sk-...)
- `XAI_API_KEY`: Your X.AI API key (xai-...)
- `HUGGINGFACE_TOKEN`: Your HF token (hf_...)
- `GRAFANA_PASSWORD`: Strong password for Grafana admin

**Security**: Verify .env.production is NOT committed:
```bash
git status  # Should NOT show .env.production
grep .env.production .gitignore  # Should be present
```

### 3. Prepare SSH Keys (for Remote File Access)

**Option A: Docker Secrets (Recommended)**

```bash
# Create secrets directory
mkdir -p /srv/pb-secrets

# Copy SSH keys
cp ~/.ssh/id_ed25519 /srv/pb-secrets/pb_ssh_key
cp ~/.ssh/known_hosts /srv/pb-secrets/pb_known_hosts

# Set strict permissions
chmod 600 /srv/pb-secrets/pb_ssh_key
chmod 600 /srv/pb-secrets/pb_known_hosts
```

Uncomment in `docker-compose.production.yml`:
```yaml
volumes:
  - /srv/pb-secrets/pb_ssh_key:/run/secrets/pb_ssh_key:ro
  - /srv/pb-secrets/pb_known_hosts:/run/secrets/pb_known_hosts:ro
```

**Option B: Bind Mount**

```bash
# Create SSH directory for container user (UID 1000)
mkdir -p /srv/pb/.ssh
cp ~/.ssh/id_ed25519 /srv/pb/.ssh/
cp ~/.ssh/known_hosts /srv/pb/.ssh/
chown -R 1000:1000 /srv/pb/.ssh
chmod 700 /srv/pb/.ssh
chmod 600 /srv/pb/.ssh/id_ed25519
```

Uncomment in `docker-compose.production.yml`:
```yaml
volumes:
  - /srv/pb/.ssh:/home/pbuser/.ssh:ro
```

### 4. Initialize SurrealDB

```bash
# Start SurrealDB first
docker-compose -f docker-compose.production.yml up -d surrealdb

# Wait for startup
sleep 5

# Check health
curl -sf http://localhost:8001/health || echo "Waiting for SurrealDB..."

# Initialize schema (if not auto-initialized)
docker exec -it project-builder-db surreal import --namespace project_builder --database production /init/init.surql
```

---

## Deployment Procedures

### Standard Deployment

```bash
# 1. Pull latest code
git pull origin priority/prod-010

# 2. Rebuild images (if code changed)
docker-compose -f docker-compose.production.yml build

# 3. Start all services
docker-compose -f docker-compose.production.yml --env-file .env.production up -d

# 4. Verify health
curl -sf http://localhost:8000/health | jq .

# Expected output:
# {
#   "status": "ok",
#   "services": [
#     {"name": "db", "ok": true},
#     {"name": "cache", "ok": true},
#     {"name": "ssh", "ok": true}
#   ],
#   "uptime_seconds": 12.34,
#   "version": "1.0.0"
# }

# 5. Check logs
docker-compose -f docker-compose.production.yml logs -f project-builder
```

### Zero-Downtime Restart

```bash
# Restart without downtime (for config changes)
docker-compose -f docker-compose.production.yml restart project-builder

# Restart with fresh image (30s graceful shutdown)
docker-compose -f docker-compose.production.yml up -d --force-recreate project-builder
```

### Rollback

```bash
# 1. Identify previous working version
git log --oneline | head -10

# 2. Checkout previous commit
git checkout <previous-commit-hash>

# 3. Rebuild and deploy
docker-compose -f docker-compose.production.yml build project-builder
docker-compose -f docker-compose.production.yml up -d project-builder

# 4. Verify health
curl -sf http://localhost:8000/health
```

---

## Verification & Health Checks

### Service Status

```bash
# All services running
docker-compose -f docker-compose.production.yml ps

# Should show:
# project-builder-db         Up (healthy)
# project-builder-redis      Up (healthy)
# project-builder            Up (healthy)
# project-builder-prometheus Up
# project-builder-grafana    Up
```

### Health Endpoint

```bash
# Overall health
curl -sf http://localhost:8000/health | jq .

# Readiness (ready to handle requests)
curl -sf http://localhost:8000/ready | jq .

# Prometheus metrics
curl -sf http://localhost:8000/metrics
```

**Health Status Values**:
- **ok**: All services healthy
- **degraded**: Non-core services unhealthy (cache/ssh), but operational
- **down**: Core service (database) unhealthy - investigate immediately

### Database Connectivity

```bash
# SurrealDB health
curl -sf http://localhost:8001/health

# Query via CLI
docker exec -it project-builder-db surreal sql \
  --namespace project_builder \
  --database production \
  --user root \
  --pass "${PB_DB_PASSWORD}" \
  --endpoint http://localhost:8000 \
  --command "SELECT * FROM project LIMIT 5;"
```

### Redis Connectivity

```bash
# Redis ping
docker exec -it project-builder-redis redis-cli ping
# Expected: PONG

# Cache stats
docker exec -it project-builder-redis redis-cli INFO stats
```

### SSH Key Validation

```bash
# Check key file in container
docker exec -it project-builder ls -la /home/pbuser/.ssh/

# Expected:
# -rw------- 1 pbuser pbuser  464 Oct  7 12:00 id_ed25519
# -rw------- 1 pbuser pbuser  123 Oct  7 12:00 known_hosts

# Test SSH connection (if HEALTH_SSH_HOST configured)
docker exec -it project-builder ssh -i /home/pbuser/.ssh/id_ed25519 -o StrictHostKeyChecking=yes ${HEALTH_SSH_HOST}
```

---

## Monitoring

### Access Dashboards

- **Grafana**: http://localhost:3000 (admin / ${GRAFANA_PASSWORD})
- **Prometheus**: http://localhost:9090
- **Health Endpoint**: http://localhost:8000/health

### Key Metrics

**Project Builder Metrics** (via /metrics endpoint):
- `project_builder_uptime_seconds`: Service uptime
- `project_builder_projects_total`: Total projects executed
- `project_builder_projects_success`: Successful completions
- `project_builder_projects_failed`: Failed projects
- `project_builder_tasks_total`: Total tasks executed
- `project_builder_tasks_completed`: Completed tasks
- `project_builder_artifacts_total`: Generated artifacts count
- `project_builder_quality_score_avg`: Average artifact quality
- `project_builder_execution_time_seconds_total`: Total execution time

**System Metrics** (via node-exporter, if configured):
- CPU usage
- Memory usage
- Disk I/O
- Network traffic

### Alerting Rules

**Critical Alerts** (configured in `config/alerting.yaml`):
1. **Service Down**: Health status = "down" for >2 minutes
2. **High Error Rate**: >10% project failure rate over 10 minutes
3. **Database Unreachable**: SurrealDB connection failures >3 in 5 minutes
4. **Redis Cache Down**: Redis unhealthy for >5 minutes
5. **High Task Timeout Rate**: >20% tasks timing out

**Warning Alerts**:
1. **Degraded Status**: Health status = "degraded" for >10 minutes
2. **High Memory Usage**: Container memory >80% for >5 minutes
3. **Slow Execution**: Average task time >60s over 15 minutes

### Log Aggregation

```bash
# View all logs
docker-compose -f docker-compose.production.yml logs -f

# Filter by service
docker-compose -f docker-compose.production.yml logs -f project-builder
docker-compose -f docker-compose.production.yml logs -f surrealdb
docker-compose -f docker-compose.production.yml logs -f redis

# Filter by log level (if using structured logging)
docker-compose -f docker-compose.production.yml logs project-builder | grep ERROR
docker-compose -f docker-compose.production.yml logs project-builder | grep WARNING
```

---

## Troubleshooting

### Service Won't Start

**Symptom**: `docker-compose up` fails or service exits immediately

**Diagnosis**:
```bash
# Check logs
docker-compose -f docker-compose.production.yml logs project-builder

# Check for port conflicts
netstat -tuln | grep -E '8000|8001|6379|9090|3000'

# Check environment variables
docker-compose -f docker-compose.production.yml config | grep -A 20 project-builder
```

**Solutions**:
1. **Port conflict**: Change port mappings in docker-compose.yml
2. **Missing .env.production**: Verify file exists and is readable
3. **Invalid env vars**: Check SURREALDB_PASSWORD, API keys format
4. **Volume permissions**: Ensure volumes are writable by UID 1000

### Health Check Fails

**Symptom**: `/health` returns status "down" or "degraded"

**Diagnosis**:
```bash
# Check individual services
curl http://localhost:8001/health  # SurrealDB
docker exec project-builder-redis redis-cli ping  # Redis
docker exec project-builder ls -la /home/pbuser/.ssh/  # SSH keys
```

**Solutions**:
1. **Database down**: Check SurrealDB logs, restart if needed
   ```bash
   docker-compose -f docker-compose.production.yml restart surrealdb
   ```

2. **Redis down**: Check Redis logs, verify persistence volume
   ```bash
   docker volume inspect unified-intelligence-cli_redis-data
   docker-compose -f docker-compose.production.yml restart redis
   ```

3. **SSH keys missing**: Verify volume mount or secrets configuration
   ```bash
   # If using bind mount:
   ls -la /srv/pb/.ssh/
   # If using secrets:
   ls -la /srv/pb-secrets/
   ```

### Task Timeouts

**Symptom**: Tasks timing out frequently, validation/testing tasks incomplete

**Diagnosis**:
```bash
# Check logs for timeout warnings
docker-compose -f docker-compose.production.yml logs project-builder | grep -i timeout

# Check LLM response times
docker-compose -f docker-compose.production.yml logs project-builder | grep "Executing task"
```

**Solutions**:
1. **Increase timeout values**: Edit `src/project_builder/execution/coordinator.py` TASK_TIMEOUTS
2. **Check LLM provider latency**: Verify API key, check provider status page
3. **Increase graceful timeout**: Edit docker-compose.yml `stop_grace_period`

### High Memory Usage

**Symptom**: Container OOM killed or high memory pressure

**Diagnosis**:
```bash
# Check container stats
docker stats project-builder project-builder-redis project-builder-db

# Check memory limits
docker inspect project-builder | jq '.[0].HostConfig.Memory'
```

**Solutions**:
1. **Increase limits**: Edit docker-compose.yml `deploy.resources.limits.memory`
2. **Tune Redis**: Reduce maxmemory setting in docker-compose.yml
3. **Check for memory leaks**: Review application logs for unclosed connections

### SSH Connection Failures

**Symptom**: Tasks fail with SSH-related errors

**Diagnosis**:
```bash
# Test SSH connection manually
docker exec -it project-builder ssh -i /home/pbuser/.ssh/id_ed25519 -v user@remote-host

# Check key permissions
docker exec -it project-builder ls -la /home/pbuser/.ssh/
```

**Solutions**:
1. **Wrong permissions**: Keys must be 600, directory 700
   ```bash
   docker exec -it project-builder chmod 700 /home/pbuser/.ssh
   docker exec -it project-builder chmod 600 /home/pbuser/.ssh/id_ed25519
   ```

2. **Host key mismatch**: Update known_hosts file
3. **Network access**: Verify firewall rules allow SSH from container

---

## Backup & Recovery

### Database Backup

```bash
# Export SurrealDB data
docker exec project-builder-db surreal export \
  --namespace project_builder \
  --database production \
  --user root \
  --pass "${PB_DB_PASSWORD}" \
  --endpoint http://localhost:8000 \
  /data/backup-$(date +%Y%m%d-%H%M%S).surql

# Copy backup to host
docker cp project-builder-db:/data/backup-*.surql ./backups/
```

### Redis Backup

```bash
# Trigger Redis save
docker exec project-builder-redis redis-cli BGSAVE

# Copy RDB file
docker cp project-builder-redis:/data/dump.rdb ./backups/redis-backup-$(date +%Y%m%d-%H%M%S).rdb
```

### Volume Backup

```bash
# Backup all volumes
docker run --rm \
  -v unified-intelligence-cli_surrealdb-data:/data/surrealdb:ro \
  -v unified-intelligence-cli_redis-data:/data/redis:ro \
  -v unified-intelligence-cli_project-artifacts:/data/artifacts:ro \
  -v $(pwd)/backups:/backup \
  alpine tar czf /backup/volumes-backup-$(date +%Y%m%d-%H%M%S).tar.gz /data
```

### Restore

```bash
# Stop services
docker-compose -f docker-compose.production.yml down

# Restore volumes (from backup tar)
docker run --rm \
  -v unified-intelligence-cli_surrealdb-data:/data/surrealdb \
  -v unified-intelligence-cli_redis-data:/data/redis \
  -v unified-intelligence-cli_project-artifacts:/data/artifacts \
  -v $(pwd)/backups:/backup \
  alpine tar xzf /backup/volumes-backup-YYYYMMDD-HHMMSS.tar.gz -C /

# Restart services
docker-compose -f docker-compose.production.yml up -d
```

---

## Maintenance

### Routine Maintenance (Weekly)

1. **Check Disk Usage**:
   ```bash
   docker system df
   df -h /var/lib/docker
   ```

2. **Clean Docker Resources**:
   ```bash
   docker system prune -f
   docker volume prune -f
   ```

3. **Rotate Logs**:
   ```bash
   # Logs are auto-rotated (max 10MB, 3 files) via docker-compose logging config
   # Verify rotation working:
   docker inspect project-builder | jq '.[0].HostConfig.LogConfig'
   ```

4. **Review Metrics**:
   - Check Grafana dashboards for anomalies
   - Review project success/failure rates
   - Monitor task execution times

### Updates

**Minor Updates** (patch, config changes):
```bash
git pull origin priority/prod-010
docker-compose -f docker-compose.production.yml restart project-builder
```

**Major Updates** (new features, breaking changes):
```bash
# 1. Backup first
./scripts/backup-all.sh  # Create if needed

# 2. Pull and review changes
git pull origin priority/prod-010
git log --oneline -10

# 3. Update dependencies
docker-compose -f docker-compose.production.yml build --no-cache project-builder

# 4. Stop, update, start
docker-compose -f docker-compose.production.yml down
docker-compose -f docker-compose.production.yml up -d

# 5. Verify
curl -sf http://localhost:8000/health
```

---

## Security

### Access Control

- **Grafana**: Change default admin password immediately
- **Prometheus**: Configure authentication if exposed publicly
- **SurrealDB**: Use strong passwords, rotate periodically
- **API Keys**: Rotate every 90 days, never commit to VCS

### Network Security

```yaml
# Firewall rules (example using ufw)
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 8000/tcp  # Project Builder health (if public)
sudo ufw deny 8001/tcp   # SurrealDB (internal only)
sudo ufw deny 6379/tcp   # Redis (internal only)
sudo ufw deny 9090/tcp   # Prometheus (internal only)
```

### SSH Key Rotation

```bash
# 1. Generate new key pair
ssh-keygen -t ed25519 -f /srv/pb-secrets/pb_ssh_key_new

# 2. Add new public key to remote hosts
ssh-copy-id -i /srv/pb-secrets/pb_ssh_key_new user@remote-host

# 3. Update volume mount or secrets
cp /srv/pb-secrets/pb_ssh_key_new /srv/pb-secrets/pb_ssh_key

# 4. Restart service
docker-compose -f docker-compose.production.yml restart project-builder

# 5. Verify
curl -sf http://localhost:8000/health | jq '.services[] | select(.name=="ssh")'
```

---

## Contact & Escalation

### On-Call Procedures

1. **Critical Alert**: Page on-call engineer immediately
2. **Warning Alert**: Slack notification to ops channel
3. **Info**: Log to monitoring dashboard

### Escalation Path

1. **L1**: DevOps Engineer (initial response)
2. **L2**: Platform Lead (persistent issues)
3. **L3**: Engineering Manager (service outage >1 hour)

### Support Channels

- **Slack**: #project-builder-ops
- **PagerDuty**: project-builder-oncall
- **Documentation**: https://docs.internal/project-builder
- **Issues**: https://github.com/your-org/unified-intelligence-cli/issues

---

## Appendix

### Service Ports

| Service | Port | Description |
|---------|------|-------------|
| Project Builder | 8000 | Health, metrics, API |
| SurrealDB | 8001 | Database HTTP/WebSocket |
| Redis | 6379 | Cache |
| Prometheus | 9090 | Metrics collection |
| Grafana | 3000 | Monitoring dashboard |

### Environment Variables Reference

See `.env.production.example` for complete list with descriptions.

### Architecture Diagram

```
┌─────────────────────────────────────────────────────────┐
│  Production Environment                                  │
│                                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │              │  │              │  │              │ │
│  │  SurrealDB   │◀─┤   Project    │  │    Redis     │ │
│  │  (State)     │  │   Builder    ├─▶│   (Cache)    │ │
│  │              │  │              │  │              │ │
│  └──────────────┘  └───────┬──────┘  └──────────────┘ │
│                            │                            │
│                            │ SSH                        │
│                            ▼                            │
│                    ┌──────────────┐                     │
│                    │   Remote     │                     │
│                    │  Codebase    │                     │
│                    └──────────────┘                     │
│                                                          │
│  ┌──────────────┐  ┌──────────────┐                    │
│  │  Prometheus  │◀─┤   Grafana    │                    │
│  │  (Metrics)   │  │  (Dashboard) │                    │
│  └──────────────┘  └──────────────┘                    │
└─────────────────────────────────────────────────────────┘
```

---

**Document Version**: 1.0
**Last Review**: 2025-10-07
**Next Review Due**: 2025-11-07
