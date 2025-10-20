# Container Deployment Guide

Deploy the autonomous orchestrator and priority workers with Docker and Kubernetes. This guide provides production-ready examples with non-root containers, health checks, persistence, and monitoring.

---

## Why Containerize?
- Consistent, reproducible environments
- Scalable worker pools (K8s auto-scaling)
- Operational standards (health checks, metrics, logs)

---

## Docker: Autonomous Worker Image

Use this example Dockerfile to run the autonomous development loop inside a container (pattern follows `Dockerfile.project-builder`).

```Dockerfile
# Stage 1: Builder
FROM python:3.12-slim AS builder
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends gcc && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# Stage 2: Runtime
FROM python:3.12-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends git curl tini && rm -rf /var/lib/apt/lists/*
COPY --from=builder /root/.local /opt/python-packages
COPY src/ ./src/
COPY autonomous_dev_tool.py ./
COPY LICENSE ./
ENV PATH=/opt/python-packages/bin:$PATH \
    PYTHONPATH=/app:/opt/python-packages/lib/python3.12/site-packages:$PYTHONPATH \
    PYTHONUNBUFFERED=1
RUN useradd -m -u 1000 uiuser && chown -R uiuser:uiuser /app && chmod -R 755 /opt/python-packages
USER uiuser
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
  CMD python -c "import http.server, socketserver; print('ok')" || exit 1
ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["python", "autonomous_dev_tool.py", "run", "--mode", "fast", "--continuous"]
```

Notes:
- Based on our production `Dockerfile.project-builder` (multi-stage, non-root, tini, healthcheck)
- Adjust CMD to run a finite number of iterations if preferred

---

## Docker Compose: Orchestrator + SurrealDB + Monitoring

Example `docker-compose.yml`:

```yaml
version: "3.9"
services:
  orchestrator:
    build: .
    image: unified-intelligence/orchestrator:latest
    environment:
      - AUTONOMOUS_SSH_HOST=${AUTONOMOUS_SSH_HOST}
      - AUTONOMOUS_WORKING_DIR=${AUTONOMOUS_WORKING_DIR:-/root}
      - AUTONOMOUS_MODEL=${AUTONOMOUS_MODEL:-sonnet4}
    volumes:
      - ./priorities.yaml:/app/priorities.yaml:ro
      - ui-metrics:/home/ui-cli/.ui-cli
    restart: unless-stopped
    depends_on:
      - surreal

  surreal:
    image: surrealdb/surrealdb:latest
    command: start --bind 0.0.0.0:8000 file:///data
    ports: ["8000:8000"]
    volumes:
      - surreal-data:/data
    restart: unless-stopped

  prometheus:
    image: prom/prometheus:latest
    ports: ["9090:9090"]
    volumes:
      - ./k8s/prometheus-deployment.yaml:/etc/prometheus/prometheus.yml:ro

  grafana:
    image: grafana/grafana:latest
    ports: ["3000:3000"]

volumes:
  ui-metrics: {}
  surreal-data: {}
```

Secrets: inject SSH keys via Docker secrets or mounted volumes (do not bake into images).

---

## Kubernetes Deployment (High Availability)

We recommend deploying the orchestrator as a Deployment with:
- 3 replicas for HA
- HPA 2-10 pods on CPU targets
- NetworkPolicies restricting egress

Reference manifests exist in `k8s/` for a similar stack (Project Builder, Prometheus, Grafana, SurrealDB):
- `k8s/project-builder-deployment.yaml`
- `k8s/prometheus-deployment.yaml`, `k8s/grafana-deployment.yaml`
- `k8s/surrealdb-deployment.yaml`
- `k8s/hpa.yaml`, `k8s/network-policy.yaml`

Example Deployment (orchestrator):
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ui-orchestrator
  namespace: agentspace
spec:
  replicas: 3
  selector:
    matchLabels: { app: ui-orchestrator }
  template:
    metadata:
      labels: { app: ui-orchestrator }
    spec:
      serviceAccountName: default
      containers:
        - name: orchestrator
          image: unified-intelligence/orchestrator:latest
          imagePullPolicy: IfNotPresent
          args: ["python", "autonomous_dev_tool.py", "run", "--mode", "fast", "--continuous"]
          env:
            - name: AUTONOMOUS_SSH_HOST
              valueFrom: { secretKeyRef: { name: orchestrator-secrets, key: ssh_host } }
            - name: AUTONOMOUS_WORKING_DIR
              value: "/root"
            - name: AUTONOMOUS_MODEL
              value: "sonnet4"
          volumeMounts:
            - name: priorities
              mountPath: /app/priorities.yaml
              subPath: priorities.yaml
          resources:
            requests: { cpu: "250m", memory: "512Mi" }
            limits: { cpu: "1", memory: "1Gi" }
          livenessProbe:
            httpGet: { path: /health, port: 8000 }
            initialDelaySeconds: 20
            periodSeconds: 30
          readinessProbe:
            httpGet: { path: /health, port: 8000 }
            initialDelaySeconds: 10
            periodSeconds: 15
      volumes:
        - name: priorities
          configMap:
            name: priorities-config
```

Example HPA:
```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: ui-orchestrator-hpa
  namespace: agentspace
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: ui-orchestrator
  minReplicas: 2
  maxReplicas: 10
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 60
```

NetworkPolicy example:
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: ui-orchestrator-egress
  namespace: agentspace
spec:
  podSelector: { matchLabels: { app: ui-orchestrator } }
  policyTypes: [ Egress ]
  egress:
    - to:
        - namespaceSelector: { matchLabels: { name: monitoring } }
        - namespaceSelector: { matchLabels: { name: database } }
      ports:
        - protocol: TCP
          port: 8000
        - protocol: TCP
          port: 9090
```

---

## Monitoring

- Prometheus: scrape app metrics (exporter can be added to the CLI or sidecar)
- Grafana: dashboards for iteration metrics and success rate
- Logs: structured JSON logging recommended for production

---

## Production Checklist

- Non-root containers (see USER setup in Dockerfile)
- Resource requests/limits defined
- Secrets management (SSH keys, API keys via K8s Secrets)
- Health checks (liveness/readiness) and graceful shutdown (tini)
- Persistence for metrics (`~/.ui-cli`) and SurrealDB data
- Backup/restore plan for metrics database
- Network policies limiting egress

---

## References
- Docker baseline: `Dockerfile.project-builder`
- Kubernetes manifests: `k8s/`
- Orchestrator: `src/claude_orchestrator/orchestrators/autonomous_orchestrator.py`
- CLI: `autonomous_dev_tool.py`
- Priority goals: `priorities.yaml`

