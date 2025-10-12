# Production Security Architecture

## Overview

This document describes the security-hardened production deployment architecture for Project Builder, implementing defense-in-depth principles with network segmentation, secrets management, TLS termination, and container hardening.

## Security Features

### 1. **Docker Secrets Management**
- ✅ All sensitive data stored in Docker secrets (not environment variables)
- ✅ Secrets loaded from `./secrets/` directory
- ✅ Applications read secrets via `*_FILE` environment variables
- ✅ Secrets never logged or exposed in container metadata

**Secrets:**
- `surrealdb_root_user` - Database admin username
- `surrealdb_root_password` - Database admin password
- `redis_password` - Redis authentication password
- `grafana_admin_password` - Grafana admin password
- `xai_api_key` - X.AI API key
- `huggingface_token` - Hugging Face API token
- `github_token` - GitHub API token
- `replicate_api_token` - Replicate API token

### 2. **Network Segmentation**
- ✅ Two isolated networks: `ingress_net` (frontend) and `internal_net` (backend)
- ✅ Internal network has `internal: true` (no external routing)
- ✅ Only Traefik bridges both networks
- ✅ Backend services (Redis, Prometheus, Project Builder) isolated on internal network

**Network Architecture:**
```
Internet → Traefik (80/443) → ingress_net → SurrealDB, Grafana
                              ↓
                         internal_net → Redis, Prometheus, Project Builder
```

### 3. **TLS Termination**
- ✅ Traefik handles all TLS termination
- ✅ Automatic HTTP → HTTPS redirect
- ✅ TLS 1.2+ with modern cipher suites
- ✅ Development: Self-signed certificates for `*.dev.local`
- ✅ Production: Ready for Let's Encrypt or CA-signed certificates

**Exposed Services:**
- `wss://db.dev.local` - SurrealDB (WebSocket Secure)
- `https://grafana.dev.local` - Grafana dashboards
- `https://traefik.dev.local` - Traefik dashboard (optional)

### 4. **Port Exposure**
- ✅ Only Traefik exposes ports to host (80, 443)
- ✅ All other services use internal networking only
- ✅ No direct database or cache access from outside

**Before (Insecure):**
```
Host ports: 8001 (SurrealDB), 6379 (Redis), 9090 (Prometheus), 3000 (Grafana)
Risk: Direct access to backend services
```

**After (Secure):**
```
Host ports: 80 (HTTP redirect), 443 (HTTPS)
Access: All services behind Traefik reverse proxy
```

### 5. **Container Hardening**
- ✅ Non-root users for all services
- ✅ `no-new-privileges` security option
- ✅ `cap_drop: ALL` (drop all Linux capabilities)
- ✅ Read-only root filesystem where possible (Redis)
- ✅ Minimal base images (Alpine, distroless)

**User IDs:**
- Traefik: `65532:65532` (non-root)
- SurrealDB: `1000:1000` (non-root)
- Redis: `999:999` (redis user)
- Project Builder: `1000:1000` (pbuser)
- Prometheus: `65534:65534` (nobody)
- Grafana: `472:472` (grafana user)

### 6. **Resource Limits**
- ✅ CPU and memory limits for all services
- ✅ Prevents resource exhaustion attacks
- ✅ Ensures fair resource allocation

### 7. **Logging and Monitoring**
- ✅ JSON structured logging
- ✅ Log rotation (10MB max, 3 files)
- ✅ Prometheus metrics for all services
- ✅ Grafana dashboards for visualization

## Setup Instructions

### Prerequisites
- Docker 20.10+ with Compose V2
- OpenSSL (for certificate generation)
- Bash shell

### Step 1: Generate Secrets and Certificates

Run the setup script to generate all required secrets and TLS certificates:

```bash
chmod +x scripts/setup-production-secrets.sh
./scripts/setup-production-secrets.sh
```

This script will:
1. Create `./secrets/` directory with all required secret files
2. Generate strong random passwords for database, Redis, and Grafana
3. Create placeholder files for API keys (you must update these)
4. Generate self-signed TLS certificates for development (`./certs/dev/`)
5. Set proper file permissions (600 for secrets, 600 for private keys)

### Step 2: Update API Keys

Edit the following files in `./secrets/` and replace placeholders with your actual API keys:

```bash
# X.AI API Key
echo -n "your_xai_api_key" > ./secrets/xai_api_key

# Hugging Face Token
echo -n "your_huggingface_token" > ./secrets/huggingface_token

# GitHub Token
echo -n "your_github_token" > ./secrets/github_token

# Replicate API Token
echo -n "your_replicate_api_token" > ./secrets/replicate_api_token
```

**Important:** Use `echo -n` (no newline) to avoid trailing newlines in secret files.

### Step 3: Configure DNS (Development)

Add the following entries to `/etc/hosts` for local development:

```bash
sudo tee -a /etc/hosts <<EOF
127.0.0.1 db.dev.local
127.0.0.1 grafana.dev.local
127.0.0.1 traefik.dev.local
EOF
```

### Step 4: Start Services

Start all services in production mode:

```bash
docker-compose -f docker-compose.production.yml up -d
```

### Step 5: Verify Deployment

Check service health:

```bash
# Check all services are running
docker-compose -f docker-compose.production.yml ps

# Check Traefik logs
docker logs project-builder-traefik

# Check SurrealDB logs
docker logs project-builder-db

# Test HTTPS endpoints
curl -k https://grafana.dev.local/api/health
curl -k https://db.dev.local/health
```

### Step 6: Access Services

**Grafana:**
- URL: https://grafana.dev.local
- Username: `admin`
- Password: `cat ./secrets/grafana_admin_password`

**SurrealDB:**
- WebSocket: `wss://db.dev.local/rpc`
- HTTP: `https://db.dev.local`
- Username: `root`
- Password: `cat ./secrets/surrealdb_root_password`

**Traefik Dashboard (optional):**
- URL: https://traefik.dev.local
- No authentication (secure this in production!)

## Production Deployment

### Let's Encrypt TLS Certificates

For production, replace self-signed certificates with Let's Encrypt:

1. Update `docker-compose.production.yml` Traefik configuration:

```yaml
traefik:
  command:
    # ... existing commands ...
    
    # Let's Encrypt configuration
    - --certificatesresolvers.letsencrypt.acme.email=your-email@example.com
    - --certificatesresolvers.letsencrypt.acme.storage=/letsencrypt/acme.json
    - --certificatesresolvers.letsencrypt.acme.tlschallenge=true
  
  volumes:
    # ... existing volumes ...
    - letsencrypt-data:/letsencrypt
```

2. Update router labels to use Let's Encrypt:

```yaml
labels:
  - "traefik.http.routers.grafana.tls.certresolver=letsencrypt"
```

3. Add volume for Let's Encrypt data:

```yaml
volumes:
  letsencrypt-data:
    driver: local
```

### Production Checklist

- [ ] Replace self-signed certificates with CA-signed or Let's Encrypt
- [ ] Update DNS records to point to production server
- [ ] Secure Traefik dashboard (add authentication or disable)
- [ ] Review and update resource limits based on load testing
- [ ] Configure external log aggregation (ELK, Splunk, etc.)
- [ ] Set up automated backups for volumes
- [ ] Configure firewall rules (allow only 80/443)
- [ ] Enable Docker Content Trust (image signing)
- [ ] Implement secrets rotation policy
- [ ] Set up monitoring alerts (Prometheus Alertmanager)
- [ ] Review and harden Prometheus scrape configs
- [ ] Configure Grafana SMTP for alerts
- [ ] Implement rate limiting in Traefik
- [ ] Add WAF rules (Traefik middleware)
- [ ] Set up intrusion detection (Fail2ban, etc.)

## Security Best Practices

### Secrets Management

**DO:**
- ✅ Use Docker secrets for all sensitive data
- ✅ Rotate secrets regularly (90 days recommended)
- ✅ Use strong, randomly generated passwords (32+ characters)
- ✅ Restrict secret file permissions (600)
- ✅ Never commit secrets to version control

**DON'T:**
- ❌ Use environment variables for secrets
- ❌ Hardcode credentials in code or configs
- ❌ Share secrets via insecure channels
- ❌ Reuse passwords across services
- ❌ Log secrets or expose in error messages

### Network Security

**DO:**
- ✅ Use network segmentation (internal vs. ingress)
- ✅ Minimize exposed ports (only 80/443)
- ✅ Use TLS for all external communication
- ✅ Implement rate limiting and DDoS protection
- ✅ Monitor network traffic for anomalies

**DON'T:**
- ❌ Expose backend services directly to internet
- ❌ Use unencrypted protocols (HTTP, plain WebSocket)
- ❌ Allow unrestricted network access between services
- ❌ Disable TLS certificate validation
- ❌ Use weak cipher suites or TLS 1.0/1.1

### Container Security

**DO:**
- ✅ Run containers as non-root users
- ✅ Drop all unnecessary Linux capabilities
- ✅ Use read-only root filesystems where possible
- ✅ Enable `no-new-privileges` security option
- ✅ Use minimal base images (Alpine, distroless)
- ✅ Scan images for vulnerabilities regularly

**DON'T:**
- ❌ Run containers as root (UID 0)
- ❌ Grant unnecessary capabilities (CAP_SYS_ADMIN, etc.)
- ❌ Use `privileged: true`
- ❌ Mount Docker socket unless absolutely necessary
- ❌ Use `latest` tags in production

## Troubleshooting

### Secrets Not Loading

**Symptom:** Service fails to start with authentication errors

**Solution:**
1. Check secret files exist: `ls -la ./secrets/`
2. Verify file permissions: `chmod 600 ./secrets/*`
3. Check for trailing newlines: `hexdump -C ./secrets/redis_password`
4. Verify secret is mounted: `docker exec <container> ls -la /run/secrets/`

### TLS Certificate Errors

**Symptom:** Browser shows "Your connection is not private"

**Solution:**
1. For development: Accept self-signed certificate in browser
2. For production: Verify CA-signed certificate is valid
3. Check certificate SAN includes domain: `openssl x509 -in cert.pem -text -noout`
4. Verify Traefik can read certificates: `docker logs project-builder-traefik`

### Network Connectivity Issues

**Symptom:** Services can't communicate with each other

**Solution:**
1. Check networks are created: `docker network ls`
2. Verify services are on correct networks: `docker inspect <container>`
3. Test internal connectivity: `docker exec <container> ping <service>`
4. Check Traefik routing: `docker logs project-builder-traefik | grep <service>`

### Permission Denied Errors

**Symptom:** Container fails to write to volumes

**Solution:**
1. Check volume ownership: `docker volume inspect <volume>`
2. Verify user ID matches volume permissions
3. For SurrealDB: `docker run --rm -v surrealdb-data:/data alpine chown -R 1000:1000 /data`
4. For Redis: `docker run --rm -v redis-data:/data alpine chown -R 999:999 /data`

## References

- [Docker Secrets Documentation](https://docs.docker.com/engine/swarm/secrets/)
- [Traefik Documentation](https://doc.traefik.io/traefik/)
- [OWASP Docker Security Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Docker_Security_Cheat_Sheet.html)
- [CIS Docker Benchmark](https://www.cisecurity.org/benchmark/docker)
- [SurrealDB Security Best Practices](https://surrealdb.com/docs/security/authentication)

