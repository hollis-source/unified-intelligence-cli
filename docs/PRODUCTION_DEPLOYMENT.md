# Production Deployment Guide

**Sprint 1: Production Deployment**
**Date**: 2025-10-07
**Status**: Ready for Production

---

## Overview

This guide provides step-by-step instructions for deploying the **Project Builder** to production using Docker Compose with PostgreSQL, Prometheus, and Grafana.

### Architecture

```
┌─────────────────┐
│  Project        │
│  Builder        │◄──── LLM APIs (xAI, OpenAI, HF)
│  (Python)       │
└────────┬────────┘
         │
    ┌────┴───────────────────┐
    │                        │
┌───▼───────┐    ┌──────────▼─────┐
│PostgreSQL │    │  Prometheus    │
│(State DB) │    │  (Metrics)     │
└───────────┘    └──────────┬─────┘
                            │
                    ┌───────▼────────┐
                    │    Grafana     │
                    │ (Visualization)│
                    └────────────────┘
```

---

## Prerequisites

### Required Software
- **Docker**: 20.10+ ([Install](https://docs.docker.com/get-docker/))
- **Docker Compose**: 2.0+ ([Install](https://docs.docker.com/compose/install/))
- **Git**: For cloning repository

### Required Environment Variables
Create a `.env` file in the project root:

```bash
# LLM Provider API Keys
XAI_API_KEY=your_xai_api_key_here
OPENAI_API_KEY=your_openai_api_key_here  # Optional fallback
HUGGINGFACE_TOKEN=your_hf_token_here

# Database Password (change in production!)
PB_DB_PASSWORD=your_secure_password_here

# Grafana Admin Credentials
GRAFANA_USER=admin
GRAFANA_PASSWORD=your_secure_password_here

# Application Configuration
PB_LOG_LEVEL=INFO
```

**Security Note**: Never commit `.env` to version control. Add to `.gitignore`.

---

## Quick Start

### 1. Clone Repository
```bash
git clone https://github.com/your-org/unified-intelligence-cli.git
cd unified-intelligence-cli
```

### 2. Configure Environment
```bash
cp .env.example .env
# Edit .env with your API keys and passwords
nano .env
```

### 3. Build Images
```bash
docker-compose -f docker-compose.production.yml build
```

### 4. Start Services
```bash
docker-compose -f docker-compose.production.yml up -d
```

### 5. Verify Deployment
```bash
# Check service health
curl http://localhost:8000/health

# Check Prometheus
open http://localhost:9090

# Check Grafana
open http://localhost:3000
```

---

## Service Endpoints

| Service | URL | Purpose |
|---------|-----|---------|
| **Project Builder Health** | http://localhost:8000/health | Health check |
| **Project Builder Metrics** | http://localhost:8000/metrics | Prometheus metrics |
| **Prometheus** | http://localhost:9090 | Metrics collection |
| **Grafana** | http://localhost:3000 | Visualization (admin/changeme) |
| **PostgreSQL** | localhost:5432 | Database (internal) |

---

## Production Configuration

### Database Setup

PostgreSQL is automatically initialized with the schema on first startup via `scripts/init-db.sql`.

**Manual Access**:
```bash
docker exec -it project-builder-db psql -U pb_user -d project_builder
```

**Backup Database**:
```bash
docker exec project-builder-db pg_dump -U pb_user project_builder > backup.sql
```

**Restore Database**:
```bash
docker exec -i project-builder-db psql -U pb_user project_builder < backup.sql
```

### Monitoring Setup

#### Prometheus
- Scrapes Project Builder metrics every 10s
- Retention: 30 days
- Config: `config/prometheus.yml`

**Query Examples**:
```promql
# Total projects
project_builder_projects_total

# Success rate
rate(project_builder_projects_success[5m]) / rate(project_builder_projects_total[5m])

# Average quality score
project_builder_quality_score_avg
```

#### Grafana
- Pre-configured Prometheus datasource
- Default credentials: admin / changeme (change immediately!)
- Dashboards: `config/grafana/dashboards/`

**Create Custom Dashboard**:
1. Login to Grafana (http://localhost:3000)
2. Click "+" → "Dashboard"
3. Add panels with Prometheus queries
4. Save dashboard

---

## Scaling

### Horizontal Scaling (Multiple Replicas)

Edit `docker-compose.production.yml`:
```yaml
project-builder:
  deploy:
    replicas: 3  # Run 3 instances
```

Then:
```bash
docker-compose -f docker-compose.production.yml up -d --scale project-builder=3
```

### Resource Limits

Current limits (per service):
- **Project Builder**: 4 CPU, 4GB RAM
- **PostgreSQL**: 1 CPU, 512MB RAM
- **Prometheus**: 0.5 CPU, 512MB RAM
- **Grafana**: 0.5 CPU, 256MB RAM

Adjust in `docker-compose.production.yml` under `deploy.resources`.

---

## Logging

### Structured JSON Logging

Project Builder logs in JSON format for production:
```json
{
  "timestamp": "2025-10-07T10:30:00Z",
  "level": "INFO",
  "logger": "project_builder.execution",
  "message": "Project completed successfully",
  "project_id": "test-project-1",
  "duration_s": 45.2
}
```

### View Logs
```bash
# Project Builder logs
docker logs -f project-builder

# PostgreSQL logs
docker logs -f project-builder-db

# All services
docker-compose -f docker-compose.production.yml logs -f
```

### Log Rotation

Configured in `docker-compose.production.yml`:
- Max size: 10MB per file
- Max files: 3 (30MB total per service)

For long-term log storage, consider:
- **ELK Stack** (Elasticsearch, Logstash, Kibana)
- **Loki** (Grafana Loki)
- **CloudWatch** (AWS)

---

## Security

### Production Security Checklist

- [x] Non-root user in Docker containers
- [x] Read-only config volumes
- [ ] **Change default passwords** (Grafana, PostgreSQL)
- [ ] Use secrets management (Vault, AWS Secrets Manager)
- [ ] Enable TLS/SSL for external access
- [ ] Configure firewall rules
- [ ] Regular security updates (`docker-compose pull`)
- [ ] Audit logs regularly

### Secrets Management

**Production**: Use Docker secrets or external secrets manager:
```yaml
# docker-compose.production.yml (with secrets)
secrets:
  db_password:
    external: true

services:
  postgres:
    secrets:
      - db_password
```

---

## Backup Strategy

### Automated Backups

**Daily PostgreSQL Backup** (cron job):
```bash
#!/bin/bash
# /etc/cron.daily/backup-project-builder-db

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR=/backups/project-builder
mkdir -p $BACKUP_DIR

docker exec project-builder-db pg_dump -U pb_user project_builder \
  | gzip > $BACKUP_DIR/backup_$DATE.sql.gz

# Keep last 7 days
find $BACKUP_DIR -name "backup_*.sql.gz" -mtime +7 -delete
```

### Volume Backups
```bash
# Backup all volumes
docker run --rm \
  -v project-builder_postgres-data:/data \
  -v $(pwd):/backup \
  alpine tar czf /backup/postgres-data-backup.tar.gz /data
```

---

## Troubleshooting

### Service Won't Start

**Check logs**:
```bash
docker-compose -f docker-compose.production.yml logs project-builder
```

**Common issues**:
1. **Port conflict**: Another service using 8000/5432/9090/3000
   - Solution: Change port mapping in `docker-compose.production.yml`
2. **Missing API keys**: XAI_API_KEY not set
   - Solution: Add to `.env` file
3. **Database connection failed**: PostgreSQL not ready
   - Solution: Wait 10s for health check, or restart

### Database Migration Failed

```bash
# Check PostgreSQL logs
docker logs project-builder-db

# Manually run init script
docker exec -i project-builder-db psql -U pb_user project_builder < scripts/init-db.sql
```

### Metrics Not Showing

```bash
# Check Prometheus targets
open http://localhost:9090/targets

# Should show "project-builder" as UP
# If DOWN, check Project Builder health endpoint
curl http://localhost:8000/health
```

---

## Performance Tuning

### PostgreSQL Tuning

Edit PostgreSQL config (requires custom image):
```sql
# Increase connections for high concurrency
max_connections = 200

# Increase shared buffers for caching
shared_buffers = 256MB

# Increase work memory for complex queries
work_mem = 8MB
```

### Project Builder Tuning

Environment variables:
```bash
# Increase worker threads (if supported)
PB_WORKERS=4

# Adjust timeout for long-running tasks
PB_TASK_TIMEOUT=600  # 10 minutes
```

---

## Monitoring Alerts

### Prometheus Alerting Rules

Create `config/alerts.yml`:
```yaml
groups:
  - name: project_builder
    interval: 30s
    rules:
      - alert: HighFailureRate
        expr: rate(project_builder_projects_failed[5m]) > 0.1
        for: 5m
        annotations:
          summary: "High project failure rate detected"

      - alert: LowQualityScore
        expr: project_builder_quality_score_avg < 70
        for: 10m
        annotations:
          summary: "Average quality score below threshold"
```

---

## Kubernetes Deployment (Optional)

### Convert Docker Compose to K8s

```bash
# Install kompose
curl -L https://github.com/kubernetes/kompose/releases/download/v1.31.2/kompose-linux-amd64 -o kompose
chmod +x kompose

# Convert
kompose convert -f docker-compose.production.yml
```

### Deploy to K8s
```bash
kubectl apply -f postgres-deployment.yaml
kubectl apply -f project-builder-deployment.yaml
kubectl apply -f prometheus-deployment.yaml
kubectl apply -f grafana-deployment.yaml
```

---

## Cost Estimation

### AWS Deployment (Example)

**Infrastructure** (t3.medium + RDS):
- EC2 t3.medium: $30/month
- RDS PostgreSQL db.t3.micro: $15/month
- EBS Storage (20GB): $2/month
- **Total Infrastructure**: ~$47/month

**LLM API Costs** (variable):
- xAI Grok-2: ~$5/1M tokens
- Estimated 10M tokens/month: $50/month

**Total Monthly Cost**: ~$100/month (with moderate usage)

---

## Support

### Resources
- **Documentation**: `/docs`
- **Issues**: [GitHub Issues](https://github.com/your-org/unified-intelligence-cli/issues)
- **Logs**: Check `docker logs` for all services

### Health Checks
```bash
# Quick health check script
./scripts/health-check.sh
```

---

## Changelog

### Version 1.0.0 (2025-10-07)
- Initial production deployment
- PostgreSQL state management
- Prometheus + Grafana monitoring
- Health check endpoints
- Structured JSON logging
- Docker Compose orchestration
