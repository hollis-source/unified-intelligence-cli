# Docker Deployment Examples

Production-ready Docker deployment configurations for Unified Intelligence CLI.

## Table of Contents

- [Basic Deployment](#basic-deployment)
- [Production Deployment](#production-deployment)
- [Multi-Container Setup](#multi-container-setup)
- [Kubernetes Deployment](#kubernetes-deployment)
- [Docker Swarm](#docker-swarm)

## Basic Deployment

### Single Container

```bash
# Pull latest image
docker pull username/unified-intelligence-cli:latest

# Run with API key
docker run -d \
  --name ui-cli \
  -e XAI_API_KEY=$XAI_API_KEY \
  --restart unless-stopped \
  username/unified-intelligence-cli:latest
```

### With Volume Mount

```bash
docker run -d \
  --name ui-cli \
  -e XAI_API_KEY=$XAI_API_KEY \
  -v $(pwd)/workspace:/workspace \
  -v $(pwd)/logs:/app/logs \
  --restart unless-stopped \
  username/unified-intelligence-cli:latest
```

## Production Deployment

### docker-compose.yml (Production)

```yaml
version: '3.8'

services:
  ui-cli:
    image: username/unified-intelligence-cli:1.0.0
    container_name: ui-cli-prod
    restart: always
    environment:
      - XAI_API_KEY=${XAI_API_KEY}
      - UI_CLI_PROVIDER=grok
      - UI_CLI_DEBUG=false
      - PYTHONUNBUFFERED=1
    volumes:
      - ./data:/workspace:rw
      - ./logs:/app/logs:rw
      - ./config:/app/config:ro
    networks:
      - ui-cli-network
    healthcheck:
      test: ["CMD", "python", "-c", "import src.main; print('healthy')"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 5s
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 512M
        reservations:
          cpus: '0.5'
          memory: 256M

networks:
  ui-cli-network:
    driver: bridge

volumes:
  data:
    driver: local
  logs:
    driver: local
```

### Deploy

```bash
# Create production .env file
cat > .env <<EOF
XAI_API_KEY=your_production_api_key
EOF

# Deploy
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f ui-cli

# Stop
docker-compose down
```

## Multi-Container Setup

### With Redis Cache

```yaml
version: '3.8'

services:
  ui-cli:
    image: username/unified-intelligence-cli:1.0.0
    depends_on:
      - redis
    environment:
      - XAI_API_KEY=${XAI_API_KEY}
      - REDIS_HOST=redis
      - REDIS_PORT=6379
    networks:
      - ui-cli-network
    restart: always

  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes
    volumes:
      - redis-data:/data
    networks:
      - ui-cli-network
    restart: always
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 30s
      timeout: 3s
      retries: 3

networks:
  ui-cli-network:
    driver: bridge

volumes:
  redis-data:
    driver: local
```

## Kubernetes Deployment

### deployment.yaml

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ui-cli
  labels:
    app: ui-cli
spec:
  replicas: 3
  selector:
    matchLabels:
      app: ui-cli
  template:
    metadata:
      labels:
        app: ui-cli
    spec:
      containers:
      - name: ui-cli
        image: username/unified-intelligence-cli:1.0.0
        imagePullPolicy: Always
        env:
        - name: XAI_API_KEY
          valueFrom:
            secretKeyRef:
              name: ui-cli-secrets
              key: xai-api-key
        - name: UI_CLI_PROVIDER
          value: "grok"
        resources:
          requests:
            memory: "256Mi"
            cpu: "500m"
          limits:
            memory: "512Mi"
            cpu: "1000m"
        livenessProbe:
          exec:
            command:
            - python
            - -c
            - "import src.main; print('healthy')"
          initialDelaySeconds: 10
          periodSeconds: 30
        readinessProbe:
          exec:
            command:
            - python
            - -c
            - "import src.main; print('ready')"
          initialDelaySeconds: 5
          periodSeconds: 10
        volumeMounts:
        - name: workspace
          mountPath: /workspace
        - name: config
          mountPath: /app/config
          readOnly: true
      volumes:
      - name: workspace
        persistentVolumeClaim:
          claimName: ui-cli-workspace-pvc
      - name: config
        configMap:
          name: ui-cli-config
---
apiVersion: v1
kind: Secret
metadata:
  name: ui-cli-secrets
type: Opaque
stringData:
  xai-api-key: "your_api_key_here"
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: ui-cli-config
data:
  config.json: |
    {
      "provider": "grok",
      "model": "grok-beta"
    }
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: ui-cli-workspace-pvc
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 10Gi
```

### Deploy to Kubernetes

```bash
# Create namespace
kubectl create namespace ui-cli

# Apply configuration
kubectl apply -f deployment.yaml -n ui-cli

# Check status
kubectl get pods -n ui-cli

# View logs
kubectl logs -f deployment/ui-cli -n ui-cli

# Scale
kubectl scale deployment ui-cli --replicas=5 -n ui-cli

# Delete
kubectl delete -f deployment.yaml -n ui-cli
```

## Docker Swarm

### stack.yml

```yaml
version: '3.8'

services:
  ui-cli:
    image: username/unified-intelligence-cli:1.0.0
    deploy:
      replicas: 3
      update_config:
        parallelism: 1
        delay: 10s
        order: start-first
      rollback_config:
        parallelism: 1
        delay: 10s
      restart_policy:
        condition: on-failure
        delay: 5s
        max_attempts: 3
      resources:
        limits:
          cpus: '1'
          memory: 512M
        reservations:
          cpus: '0.5'
          memory: 256M
    environment:
      - XAI_API_KEY=${XAI_API_KEY}
    networks:
      - ui-cli-network
    volumes:
      - ui-cli-data:/workspace

networks:
  ui-cli-network:
    driver: overlay
    attachable: true

volumes:
  ui-cli-data:
    driver: local
```

### Deploy to Swarm

```bash
# Initialize swarm (if not already)
docker swarm init

# Deploy stack
docker stack deploy -c stack.yml ui-cli

# Check services
docker stack services ui-cli

# View logs
docker service logs ui-cli_ui-cli -f

# Scale service
docker service scale ui-cli_ui-cli=5

# Update service
docker service update --image username/unified-intelligence-cli:1.0.1 ui-cli_ui-cli

# Remove stack
docker stack rm ui-cli
```

## Security Best Practices

### 1. Use Secrets for API Keys

```bash
# Docker Swarm secrets
echo "your_api_key" | docker secret create xai_api_key -

# Update stack.yml
services:
  ui-cli:
    secrets:
      - xai_api_key
    environment:
      - XAI_API_KEY_FILE=/run/secrets/xai_api_key

secrets:
  xai_api_key:
    external: true
```

### 2. Run as Non-Root User

Already implemented in Dockerfile:
```dockerfile
USER appuser
```

### 3. Read-Only Filesystem

```yaml
services:
  ui-cli:
    read_only: true
    tmpfs:
      - /tmp
      - /app/logs
```

### 4. Network Isolation

```yaml
networks:
  ui-cli-network:
    internal: true
```

## Monitoring

### Prometheus Integration

```yaml
services:
  ui-cli:
    labels:
      - "prometheus.scrape=true"
      - "prometheus.port=8000"
      - "prometheus.path=/metrics"

  prometheus:
    image: prom/prometheus:latest
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
    ports:
      - "9090:9090"
```

### Logging with ELK Stack

```yaml
services:
  ui-cli:
    logging:
      driver: "gelf"
      options:
        gelf-address: "udp://localhost:12201"
        tag: "ui-cli"
```

## Backup and Recovery

### Backup Script

```bash
#!/bin/bash
# backup.sh

BACKUP_DIR="/backups/ui-cli/$(date +%Y%m%d)"
mkdir -p $BACKUP_DIR

# Backup volumes
docker run --rm \
  -v ui-cli-data:/source:ro \
  -v $BACKUP_DIR:/backup \
  alpine \
  tar czf /backup/workspace.tar.gz -C /source .

echo "Backup completed: $BACKUP_DIR/workspace.tar.gz"
```

### Restore Script

```bash
#!/bin/bash
# restore.sh

BACKUP_FILE=$1

docker run --rm \
  -v ui-cli-data:/target \
  -v $(dirname $BACKUP_FILE):/backup:ro \
  alpine \
  tar xzf /backup/$(basename $BACKUP_FILE) -C /target

echo "Restore completed from: $BACKUP_FILE"
```

## Troubleshooting

### Check Container Health

```bash
docker inspect --format='{{json .State.Health}}' ui-cli | jq
```

### View Container Resources

```bash
docker stats ui-cli
```

### Debug Container

```bash
docker exec -it ui-cli /bin/bash
```

### Check Logs

```bash
docker logs ui-cli --tail 100 -f
```

---

**Last Updated:** 2025-09-30
**Version:** 1.0.0
