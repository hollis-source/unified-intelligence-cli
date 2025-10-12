# Kubernetes Deployment for Project Builder

Production-ready Kubernetes manifests for deploying Project Builder with all dependencies.

## Prerequisites

- Kubernetes cluster (1.24+)
- kubectl configured
- Docker image: `project-builder:latest` pushed to container registry
- Storage class configured (for PersistentVolumes)
- cert-manager (optional, for TLS)

## Quick Start

### 1. Create Secrets

**IMPORTANT**: Never commit secrets to version control. Create secrets manually:

```bash
kubectl create namespace project-builder

kubectl create secret generic project-builder-secrets \
  --from-literal=surrealdb_root_password='YOUR_SECURE_PASSWORD' \
  --from-literal=redis_password='YOUR_SECURE_PASSWORD' \
  --from-literal=xai_api_key='YOUR_XAI_API_KEY' \
  --from-literal=huggingface_token='YOUR_HF_TOKEN' \
  --from-literal=github_token='YOUR_GITHUB_TOKEN' \
  --from-literal=replicate_api_token='YOUR_REPLICATE_TOKEN' \
  --from-literal=grafana_admin_password='YOUR_SECURE_PASSWORD' \
  --namespace project-builder
```

### 2. Deploy Using Kustomize

```bash
# Apply all manifests
kubectl apply -k deploy/k8s/

# Verify deployment
kubectl get all -n project-builder

# Check pod status
kubectl get pods -n project-builder -w

# View logs
kubectl logs -f deployment/project-builder -n project-builder
```

### 3. Verify Health

```bash
# Port-forward to access health endpoint
kubectl port-forward svc/project-builder 8000:8000 -n project-builder

# Check health
curl http://localhost:8000/health

# Check metrics
curl http://localhost:8000/metrics
```

## Manual Deployment (without Kustomize)

```bash
# Apply manifests in order
kubectl apply -f deploy/k8s/namespace.yaml
kubectl apply -f deploy/k8s/configmap.yaml
# Create secrets (see above)
kubectl apply -f deploy/k8s/rbac.yaml
kubectl apply -f deploy/k8s/pvc.yaml
kubectl apply -f deploy/k8s/project-builder-deployment.yaml
kubectl apply -f deploy/k8s/project-builder-service.yaml
kubectl apply -f deploy/k8s/hpa.yaml
```

## Manifest Files

| File | Purpose |
|------|---------|
| `namespace.yaml` | Create dedicated namespace |
| `secrets.yaml.template` | Template for secrets (DO NOT commit real values) |
| `configmap.yaml` | Non-sensitive configuration |
| `rbac.yaml` | ServiceAccount and RBAC rules |
| `pvc.yaml` | PersistentVolumeClaims for artifacts and logs |
| `project-builder-deployment.yaml` | Main application deployment |
| `project-builder-service.yaml` | ClusterIP service |
| `hpa.yaml` | Horizontal Pod Autoscaler (2-10 replicas) |
| `kustomization.yaml` | Kustomize configuration |

## Configuration

### Resource Requirements

Per pod:
- **Requests**: 500m CPU, 1Gi memory
- **Limits**: 2000m CPU, 4Gi memory

### Autoscaling

- **Min replicas**: 2
- **Max replicas**: 10
- **Target CPU**: 70%
- **Target Memory**: 80%

### Storage

- **Artifacts PVC**: 50Gi (ReadWriteMany)
- **Logs PVC**: 10Gi (ReadWriteMany)

Adjust `storageClassName` in `pvc.yaml` to match your cluster.

## Security

### Pod Security

- `runAsNonRoot: true`
- `runAsUser: 1000`
- `allowPrivilegeEscalation: false`
- `readOnlyRootFilesystem: true` (where possible)
- Drop all capabilities

### Secrets Management

**Best Practices**:
1. Use external secrets management (e.g., Sealed Secrets, External Secrets Operator)
2. Never commit secrets to Git
3. Rotate secrets regularly
4. Use RBAC to limit secret access

**Alternative Secret Methods**:

```bash
# From file
kubectl create secret generic project-builder-secrets \
  --from-file=./secrets/ \
  --namespace project-builder

# From env file
kubectl create secret generic project-builder-secrets \
  --from-env-file=./secrets.env \
  --namespace project-builder
```

## Monitoring

### Health Checks

- **Liveness**: `/health` (30s interval, 30s initial delay)
- **Readiness**: `/ready` (10s interval, 10s initial delay)
- **Startup**: `/health` (10s interval, up to 5min startup time)

### Prometheus Metrics

Metrics exposed at `/metrics` on port 8000. Pods are annotated for Prometheus auto-discovery:

```yaml
prometheus.io/scrape: "true"
prometheus.io/port: "8000"
prometheus.io/path: "/metrics"
```

## Troubleshooting

### Pod Crash Loop

```bash
# Check pod logs
kubectl logs -f pod/<POD_NAME> -n project-builder

# Check previous logs
kubectl logs -f pod/<POD_NAME> --previous -n project-builder

# Describe pod for events
kubectl describe pod/<POD_NAME> -n project-builder
```

### Secrets Not Found

```bash
# Verify secret exists
kubectl get secrets -n project-builder

# Check secret contents (base64 encoded)
kubectl get secret project-builder-secrets -o yaml -n project-builder
```

### PVC Pending

```bash
# Check PVC status
kubectl get pvc -n project-builder

# Describe PVC for events
kubectl describe pvc project-artifacts-pvc -n project-builder

# Check available storage classes
kubectl get storageclass
```

### Service Not Accessible

```bash
# Check service
kubectl get svc -n project-builder

# Check endpoints
kubectl get endpoints -n project-builder

# Port forward for testing
kubectl port-forward svc/project-builder 8000:8000 -n project-builder
```

## Cleanup

```bash
# Delete all resources
kubectl delete -k deploy/k8s/

# Or delete namespace (removes everything)
kubectl delete namespace project-builder
```

## Production Checklist

- [ ] Secrets created securely (not committed to Git)
- [ ] Storage class configured and available
- [ ] Resource requests/limits reviewed for your workload
- [ ] Health check intervals appropriate for your SLA
- [ ] HPA min/max replicas configured
- [ ] Prometheus monitoring configured
- [ ] Log aggregation configured (ELK, Loki, CloudWatch)
- [ ] Backup strategy for PersistentVolumes
- [ ] Disaster recovery plan documented
- [ ] RBAC reviewed and minimal permissions granted
- [ ] Network policies configured (if required)
- [ ] TLS certificates configured (if exposing externally)

## Next Steps

1. Deploy supporting services (SurrealDB, Redis, Prometheus, Grafana)
2. Configure ingress for external access
3. Set up CI/CD pipeline for automated deployments
4. Configure monitoring dashboards
5. Set up alerting rules
6. Document runbooks for common issues
