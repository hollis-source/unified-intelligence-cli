# Production Deployment - Quick Start Guide

## 🚀 Quick Setup (5 Minutes)

### 1. Generate Secrets and Certificates
```bash
chmod +x scripts/setup-production-secrets.sh
./scripts/setup-production-secrets.sh
```

### 2. Update API Keys
```bash
# Edit these files with your actual API keys
nano ./secrets/xai_api_key
nano ./secrets/huggingface_token
nano ./secrets/github_token
nano ./secrets/replicate_api_token
```

### 3. Configure Local DNS (Development)
```bash
sudo tee -a /etc/hosts <<EOF
127.0.0.1 db.dev.local
127.0.0.1 grafana.dev.local
127.0.0.1 traefik.dev.local
EOF
```

### 4. Start Services
```bash
docker-compose -f docker-compose.production.yml up -d
```

### 5. Verify Deployment
```bash
# Check all services are running
docker-compose -f docker-compose.production.yml ps

# Get Grafana admin password
cat ./secrets/grafana_admin_password

# Access Grafana
open https://grafana.dev.local
```

## 📋 Common Operations

### View Service Logs
```bash
# All services
docker-compose -f docker-compose.production.yml logs -f

# Specific service
docker-compose -f docker-compose.production.yml logs -f traefik
docker-compose -f docker-compose.production.yml logs -f surrealdb
docker-compose -f docker-compose.production.yml logs -f project-builder
```

### Restart Services
```bash
# All services
docker-compose -f docker-compose.production.yml restart

# Specific service
docker-compose -f docker-compose.production.yml restart traefik
```

### Stop Services
```bash
# Stop all services (keep data)
docker-compose -f docker-compose.production.yml down

# Stop and remove volumes (DELETE ALL DATA)
docker-compose -f docker-compose.production.yml down -v
```

### Update Services
```bash
# Pull latest images
docker-compose -f docker-compose.production.yml pull

# Rebuild and restart
docker-compose -f docker-compose.production.yml up -d --build
```

### View Service Status
```bash
# Check health status
docker-compose -f docker-compose.production.yml ps

# Detailed service info
docker inspect project-builder-traefik
docker inspect project-builder-db
```

## 🔐 Access Credentials

### Grafana
- **URL:** https://grafana.dev.local
- **Username:** `admin`
- **Password:** `cat ./secrets/grafana_admin_password`

### SurrealDB
- **WebSocket:** `wss://db.dev.local/rpc`
- **HTTP:** `https://db.dev.local`
- **Username:** `root`
- **Password:** `cat ./secrets/surrealdb_root_password`

### Redis
- **Host:** `redis:6379` (internal only)
- **Password:** `cat ./secrets/redis_password`

### Traefik Dashboard
- **URL:** https://traefik.dev.local
- **Authentication:** None (secure this in production!)

## 🔧 Troubleshooting

### Service Won't Start
```bash
# Check logs for errors
docker-compose -f docker-compose.production.yml logs <service>

# Check secret files exist
ls -la ./secrets/

# Verify permissions
chmod 600 ./secrets/*
```

### Can't Access HTTPS Services
```bash
# Check Traefik is running
docker ps | grep traefik

# Check DNS resolution
ping db.dev.local

# Check certificates
ls -la ./certs/dev/

# View Traefik logs
docker logs project-builder-traefik
```

### Database Connection Errors
```bash
# Check SurrealDB is running
docker ps | grep surrealdb

# Test database connectivity
docker exec project-builder-db surreal version

# Check password secret
cat ./secrets/surrealdb_root_password | hexdump -C
```

### Permission Denied on Volumes
```bash
# Fix SurrealDB volume permissions
docker run --rm -v project-builder-surrealdb-data:/data alpine chown -R 1000:1000 /data

# Fix Redis volume permissions
docker run --rm -v project-builder-redis-data:/data alpine chown -R 999:999 /data

# Fix Grafana volume permissions
docker run --rm -v project-builder-grafana-data:/data alpine chown -R 472:472 /data
```

## 📊 Monitoring

### View Metrics
```bash
# Prometheus (internal only - use port forwarding)
docker exec -it project-builder-prometheus wget -qO- http://localhost:9090/metrics

# Grafana dashboards
open https://grafana.dev.local
```

### Check Resource Usage
```bash
# All containers
docker stats

# Specific container
docker stats project-builder
```

### View Health Checks
```bash
# Check health status
docker inspect --format='{{.State.Health.Status}}' project-builder
docker inspect --format='{{.State.Health.Status}}' project-builder-redis
docker inspect --format='{{.State.Health.Status}}' project-builder-grafana
```

## 🔄 Backup and Restore

### Backup Volumes
```bash
# Create backup directory
mkdir -p ./backups

# Backup SurrealDB data
docker run --rm -v project-builder-surrealdb-data:/data -v $(pwd)/backups:/backup alpine tar czf /backup/surrealdb-$(date +%Y%m%d-%H%M%S).tar.gz -C /data .

# Backup Grafana data
docker run --rm -v project-builder-grafana-data:/data -v $(pwd)/backups:/backup alpine tar czf /backup/grafana-$(date +%Y%m%d-%H%M%S).tar.gz -C /data .

# Backup Prometheus data
docker run --rm -v project-builder-prometheus-data:/data -v $(pwd)/backups:/backup alpine tar czf /backup/prometheus-$(date +%Y%m%d-%H%M%S).tar.gz -C /data .
```

### Restore Volumes
```bash
# Restore SurrealDB data
docker run --rm -v project-builder-surrealdb-data:/data -v $(pwd)/backups:/backup alpine sh -c "cd /data && tar xzf /backup/surrealdb-YYYYMMDD-HHMMSS.tar.gz"

# Restore Grafana data
docker run --rm -v project-builder-grafana-data:/data -v $(pwd)/backups:/backup alpine sh -c "cd /data && tar xzf /backup/grafana-YYYYMMDD-HHMMSS.tar.gz"
```

## 🔐 Security Operations

### Rotate Secrets
```bash
# Generate new password
NEW_PASSWORD=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-32)

# Update secret file
echo -n "$NEW_PASSWORD" > ./secrets/redis_password

# Restart service to pick up new secret
docker-compose -f docker-compose.production.yml restart redis
```

### Update TLS Certificates
```bash
# Replace certificates in ./certs/dev/
cp /path/to/new/cert.pem ./certs/dev/cert.pem
cp /path/to/new/key.pem ./certs/dev/key.pem

# Restart Traefik
docker-compose -f docker-compose.production.yml restart traefik
```

### View Secret Values (Debugging Only)
```bash
# View all secrets
for secret in ./secrets/*; do
  echo "$(basename $secret): $(cat $secret)"
done

# View specific secret
cat ./secrets/grafana_admin_password
```

## 📈 Performance Tuning

### Adjust Resource Limits
Edit `docker-compose.production.yml` and modify the `deploy.resources` section:

```yaml
deploy:
  resources:
    limits:
      cpus: '2.0'      # Increase CPU limit
      memory: 2G       # Increase memory limit
    reservations:
      cpus: '0.5'
      memory: 512M
```

Then restart:
```bash
docker-compose -f docker-compose.production.yml up -d
```

### Scale Services
```bash
# Scale project-builder to 3 replicas
docker-compose -f docker-compose.production.yml up -d --scale project-builder=3
```

## 🌐 Production Deployment

### Update for Production Domain
1. Update DNS records to point to your server
2. Update Traefik labels in `docker-compose.production.yml`:
   ```yaml
   - "traefik.http.routers.grafana.rule=Host(`grafana.yourdomain.com`)"
   ```
3. Configure Let's Encrypt (see PRODUCTION-SECURITY.md)
4. Update Grafana root URL:
   ```yaml
   - GF_SERVER_ROOT_URL=https://grafana.yourdomain.com
   ```

### Enable Let's Encrypt
Add to Traefik service in `docker-compose.production.yml`:
```yaml
command:
  # ... existing commands ...
  - --certificatesresolvers.letsencrypt.acme.email=your-email@example.com
  - --certificatesresolvers.letsencrypt.acme.storage=/letsencrypt/acme.json
  - --certificatesresolvers.letsencrypt.acme.tlschallenge=true

volumes:
  # ... existing volumes ...
  - letsencrypt-data:/letsencrypt
```

Update router labels:
```yaml
labels:
  - "traefik.http.routers.grafana.tls.certresolver=letsencrypt"
```

## 📚 Additional Resources

- **Full Security Documentation:** [PRODUCTION-SECURITY.md](./PRODUCTION-SECURITY.md)
- **Docker Compose Reference:** [docker-compose.production.yml](../docker-compose.production.yml)
- **Traefik Configuration:** [config/traefik/tls.yml](../config/traefik/tls.yml)
- **Setup Script:** [scripts/setup-production-secrets.sh](../scripts/setup-production-secrets.sh)

## 🆘 Getting Help

If you encounter issues:
1. Check logs: `docker-compose -f docker-compose.production.yml logs`
2. Review [PRODUCTION-SECURITY.md](./PRODUCTION-SECURITY.md) troubleshooting section
3. Verify all secrets are properly configured
4. Check network connectivity and DNS resolution
5. Ensure certificates are valid and readable

## ✅ Production Readiness Checklist

Before deploying to production:

- [ ] All API keys updated in `./secrets/`
- [ ] TLS certificates replaced with CA-signed or Let's Encrypt
- [ ] DNS records configured for production domain
- [ ] Firewall rules configured (allow only 80/443)
- [ ] Traefik dashboard secured or disabled
- [ ] Backup strategy implemented
- [ ] Monitoring alerts configured
- [ ] Log aggregation configured
- [ ] Secrets rotation policy defined
- [ ] Disaster recovery plan documented
- [ ] Load testing completed
- [ ] Security audit performed

