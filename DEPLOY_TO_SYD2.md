# Deploy RAG Metrics to syd2.jacobhollis.com

## Quick Deploy Instructions

### Option 1: Transfer Deployment Package

```bash
# From your local machine (where you have the code):
scp rag-metrics-deployment.tar.gz root@syd2.jacobhollis.com:/tmp/

# SSH to syd2
ssh root@syd2.jacobhollis.com

# On syd2, extract the package
cd /root/unified-intelligence-cli
tar -xzf /tmp/rag-metrics-deployment.tar.gz

# Run deployment
chmod +x scripts/deploy_syd2_root.sh
./scripts/deploy_syd2_root.sh
```

### Option 2: Git Pull (if repo is on syd2)

```bash
# SSH to syd2
ssh root@syd2.jacobhollis.com

# Navigate to project
cd /root/unified-intelligence-cli

# Pull latest changes
git pull

# Run deployment
chmod +x scripts/deploy_syd2_root.sh
./scripts/deploy_syd2_root.sh
```

### Option 3: Manual File Transfer

If you need to transfer individual files:

```bash
# From your local machine:
scp scripts/deploy_syd2_root.sh root@syd2.jacobhollis.com:/root/unified-intelligence-cli/scripts/
scp scripts/rag_metrics_server.py root@syd2.jacobhollis.com:/root/unified-intelligence-cli/scripts/
scp src/adapters/web/rag_metrics_server.py root@syd2.jacobhollis.com:/root/unified-intelligence-cli/src/adapters/web/

# Then SSH and deploy
ssh root@syd2.jacobhollis.com
cd /root/unified-intelligence-cli
chmod +x scripts/deploy_syd2_root.sh
./scripts/deploy_syd2_root.sh
```

## After Deployment

```bash
# Check service status
systemctl status rag-metrics

# Test endpoints
curl http://localhost:8080/health
curl http://localhost:8080/api/rag/metrics

# View logs
journalctl -u rag-metrics -f
```

## Files in Deployment Package

- `scripts/deploy_syd2_root.sh` - Automated deployment script
- `scripts/rag_metrics_server.py` - Standalone server
- `src/adapters/web/rag_metrics_server.py` - API implementation
- `src/adapters/web/api_server.py` - Modified API server
- `src/routing/weight_optimizer.py` - Weight optimization
- `src/routing/drift_detector.py` - Drift detection
- `src/routing/performance_feedback.py` - Performance feedback
- `src/routing/ab_testing.py` - A/B testing
- `docs/RAG_METRICS_*.md` - Documentation

## Troubleshooting

If deployment fails, check:
1. SurrealDB is running: `systemctl status surrealdb`
2. Python venv exists: `ls venv/bin/python`
3. Logs: `journalctl -u rag-metrics -n 50`

