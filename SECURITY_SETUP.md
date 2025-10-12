# Security Setup Guide

## Prerequisites

### 1. Add Development Domains to /etc/hosts

Add the following line to `/etc/hosts`:

```bash
sudo sh -c 'echo "127.0.0.1 db.dev.local grafana.dev.local traefik.dev.local" >> /etc/hosts'
```

Verify:
```bash
grep "dev.local" /etc/hosts
```

### 2. Verify Secrets are Present

Ensure all secret files exist with proper permissions:

```bash
ls -la secrets/
```

Expected files (all should be 600 permissions):
- `surrealdb_root_user`
- `surrealdb_root_password`
- `redis_password`
- `grafana_admin_password`
- `xai_api_key`
- `huggingface_token`
- `github_token`
- `replicate_api_token`

### 3. Verify TLS Certificates

Check development certificates:

```bash
ls -la certs/dev/
```

Expected files (600 permissions):
- `privkey.pem` (RSA 4096-bit private key)
- `fullchain.pem` (Self-signed certificate for *.dev.local)

## Starting the Stack

```bash
docker compose -f docker-compose.production.yml up -d
```

## Accessing Services

All services are accessed via HTTPS through Traefik:

- **SurrealDB**: `wss://db.dev.local` (WebSocket Secure)
- **Grafana**: `https://grafana.dev.local`
- **Traefik Dashboard**: `https://traefik.dev.local` (if enabled)

## Testing TLS Connections

### Test SurrealDB Connection

```bash
curl -k https://db.dev.local/health
```

### Test Grafana

```bash
curl -k https://grafana.dev.local/api/health
```

### Test Traefik

```bash
curl -k https://traefik.dev.local/api/overview
```

## Security Features Implemented

✅ **Docker Secrets**: All sensitive data in `/run/secrets/*`  
✅ **TLS Termination**: Traefik handles HTTPS (port 443)  
✅ **Network Segmentation**: `internal_net` (internal only) + `ingress_net` (Traefik routing)  
✅ **No Direct Port Exposure**: Only Traefik ports 80/443 exposed  
✅ **Non-Root Users**: All services run as non-root  
✅ **Security Hardening**: `no-new-privileges`, `cap_drop: ALL`, read-only filesystems where possible  
✅ **Secret Reading Logic**: Application code reads from `*_FILE` environment variables  

## Troubleshooting

### Services Won't Start

Check logs:
```bash
docker compose -f docker-compose.production.yml logs -f
```

### Secret Mount Issues

Verify secrets are accessible:
```bash
docker compose -f docker-compose.production.yml exec project-builder ls -la /run/secrets/
```

### TLS Certificate Issues

Regenerate development certificates:
```bash
openssl req -x509 -newkey rsa:4096 -nodes \
  -keyout certs/dev/privkey.pem \
  -out certs/dev/fullchain.pem \
  -days 365 \
  -subj "/CN=*.dev.local/O=Unified Intelligence CLI/C=US"
chmod 600 certs/dev/*.pem
```

### Permission Denied on Volumes

Fix SurrealDB volume permissions:
```bash
docker volume inspect project-builder_surrealdb-data
sudo chown -R 1000:1000 <volume-mount-path>
```

## Production Deployment

For production (Let's Encrypt TLS):

1. Set `ACME_EMAIL` environment variable
2. Update domain names in Traefik labels (replace `*.dev.local` with actual domains)
3. Ensure ports 80/443 are accessible from internet (for ACME challenge)
4. Remove self-signed certs volume mount from Traefik service

See `docker-compose.production.yml` for details.
