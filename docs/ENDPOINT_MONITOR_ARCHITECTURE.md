# P1.2: Endpoint Monitoring & Auto-Wake Architecture

**Status**: Design Phase
**Priority**: High (P1.2)
**Effort**: 16 hours
**Complexity**: Medium
**Created**: 2025-10-12

## Executive Summary

Automated health monitoring and auto-wake service for scale-to-zero inference endpoints (HF Inference API, Replicate, Modal, etc.). Prevents cold start delays for critical endpoints through pre-emptive warming and provides fallback chains for reliability.

**Key Capabilities**:
- 🏥 **Health Monitoring**: Periodic health checks via async polling (60s default)
- 🔥 **Auto-Wake**: Detect sleeping endpoints and send wake-up requests
- 🔄 **Fallback Chains**: Primary → Secondary → Tertiary routing on failure
- 📊 **Observability**: Prometheus metrics + Grafana dashboards
- 🚨 **Alerting**: AlertManager integration for critical issues

## Problem Statement

### Current Issues

1. **Cold Start Delays**: HF Inference Endpoints scale to zero after inactivity
   - First request after scale-down: 30-60s latency
   - User experience degradation for production workloads
   - No visibility into endpoint sleep state

2. **No Fallback Strategy**: Single point of failure
   - Endpoint down → entire system blocked
   - No automated failover mechanism
   - Manual intervention required

3. **Limited Observability**: Hard to diagnose endpoint issues
   - No health metrics over time
   - No alerting on endpoint failures
   - Dashboard gaps for endpoint status

### Success Criteria

- ✅ Critical endpoints stay warm (< 5s cold start probability)
- ✅ Auto-failover completes in < 10s
- ✅ Health check overhead < 1% of inference cost
- ✅ 99.9% uptime for monitored endpoints
- ✅ Mean time to detection (MTTD) < 120s

## Architecture Overview

### Clean Architecture Layers

```
┌─────────────────────────────────────────────────────────────┐
│                      Presentation Layer                      │
│  - CLI (manual wake/check commands)                         │
│  - Prometheus metrics HTTP endpoint (:9090/metrics)         │
│  - Health check HTTP endpoint (:8080/health)                │
└─────────────────────────────────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                       Use Cases Layer                        │
│  - CheckEndpointHealth (poll + record)                      │
│  - WakeEndpoint (detect sleep → send wake request)          │
│  - ExecuteFallbackChain (primary fail → try secondary)      │
│  - RecordHealthMetrics (export to Prometheus)               │
│  - DetectAnomalies (pattern-based failure detection)        │
└─────────────────────────────────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                       Domain Layer                           │
│  Entities:                                                   │
│    - Endpoint (id, url, provider, priority, state)          │
│    - HealthStatus (healthy, sleeping, failed, last_check)   │
│    - FallbackChain (primary, secondary, tertiary)           │
│    - WakeStrategy (always, priority_based, reactive)        │
│  Interfaces:                                                 │
│    - IHealthChecker (abstract health check)                 │
│    - IWaker (abstract wake mechanism)                       │
│    - IMetricsExporter (abstract metrics export)             │
└─────────────────────────────────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                      Adapters Layer                          │
│  External Services:                                          │
│    - HFInferenceHealthAdapter (HF-specific health check)    │
│    - ReplicateHealthAdapter (Replicate-specific)            │
│    - PrometheusMetricsAdapter (export to Prometheus)        │
│  Infrastructure:                                             │
│    - YAMLConfigRepository (read endpoint config)            │
│    - AsyncHTTPClient (async requests for parallel checks)   │
└─────────────────────────────────────────────────────────────┘
```

### Component Diagram

```
┌─────────────────────┐
│  Endpoint Monitor   │
│     Daemon          │
│                     │
│  ┌───────────────┐  │
│  │ Health Check  │──┼──> Async Workers (asyncio)
│  │   Scheduler   │  │    │
│  └───────────────┘  │    ├─> Worker 1 (endpoint 1)
│                     │    ├─> Worker 2 (endpoint 2)
│  ┌───────────────┐  │    └─> Worker N (endpoint N)
│  │  Auto-Wake    │  │
│  │    Engine     │  │
│  └───────────────┘  │
│                     │
│  ┌───────────────┐  │
│  │   Fallback    │  │
│  │   Executor    │  │
│  └───────────────┘  │
└─────────────────────┘
         │
         ├──> Prometheus Metrics (:9090/metrics)
         ├──> Health API (:8080/health)
         └──> Config File (endpoints.yaml)
```

## Domain Model

### Entities

#### 1. Endpoint

```python
@dataclass(frozen=True)
class Endpoint:
    """Represents a monitored inference endpoint."""

    id: str                      # Unique identifier (e.g., "qwen3-primary")
    provider: str                # "huggingface", "replicate", "modal"
    url: str                     # Base URL for health checks
    priority: EndpointPriority   # CRITICAL, HIGH, MEDIUM, LOW
    wake_strategy: WakeStrategy  # ALWAYS_WARM, PRIORITY_BASED, REACTIVE
    health_check_interval: int   # Seconds between checks (default 60)
    wake_timeout: int            # Max seconds to wait for wake (default 90)

    # Optional fallback chain
    fallback_endpoint_id: Optional[str] = None
```

#### 2. HealthStatus

```python
@dataclass
class HealthStatus:
    """Current health state of an endpoint."""

    endpoint_id: str
    state: EndpointState        # HEALTHY, SLEEPING, DEGRADED, FAILED
    last_check_time: datetime
    last_wake_time: Optional[datetime]
    response_time_ms: Optional[float]
    consecutive_failures: int
    error_message: Optional[str]

    def is_healthy(self) -> bool:
        return self.state == EndpointState.HEALTHY

    def is_sleeping(self) -> bool:
        return self.state == EndpointState.SLEEPING

    def needs_wake(self) -> bool:
        """Determine if endpoint needs wake-up based on state and strategy."""
        return self.is_sleeping() or self.state == EndpointState.FAILED
```

#### 3. FallbackChain

```python
@dataclass(frozen=True)
class FallbackChain:
    """Defines fallback routing for an endpoint."""

    primary_endpoint_id: str
    secondary_endpoint_id: Optional[str] = None
    tertiary_endpoint_id: Optional[str] = None

    def get_next_endpoint(self, current_id: str) -> Optional[str]:
        """Get next endpoint in fallback chain."""
        if current_id == self.primary_endpoint_id:
            return self.secondary_endpoint_id
        if current_id == self.secondary_endpoint_id:
            return self.tertiary_endpoint_id
        return None
```

### Use Cases

#### 1. CheckEndpointHealth

```python
class CheckEndpointHealth:
    """Execute health check for a single endpoint."""

    def __init__(
        self,
        health_checker: IHealthChecker,
        metrics_exporter: IMetricsExporter
    ):
        self._checker = health_checker
        self._metrics = metrics_exporter

    async def execute(self, endpoint: Endpoint) -> HealthStatus:
        """
        Perform health check on endpoint.

        Returns:
            HealthStatus with current state and metrics
        """
        start_time = time.time()

        try:
            # Send health check request (lightweight inference)
            response = await self._checker.check(endpoint)
            response_time_ms = (time.time() - start_time) * 1000

            # Determine state from response
            if response.is_successful():
                state = EndpointState.HEALTHY
            elif response.is_cold_start():
                state = EndpointState.SLEEPING
            else:
                state = EndpointState.FAILED

            status = HealthStatus(
                endpoint_id=endpoint.id,
                state=state,
                last_check_time=datetime.now(),
                response_time_ms=response_time_ms,
                consecutive_failures=0,
                error_message=None
            )

            # Export metrics
            await self._metrics.record_health_check(endpoint, status)

            return status

        except Exception as e:
            # Record failure
            status = HealthStatus(
                endpoint_id=endpoint.id,
                state=EndpointState.FAILED,
                last_check_time=datetime.now(),
                response_time_ms=None,
                consecutive_failures=1,
                error_message=str(e)
            )
            await self._metrics.record_health_check(endpoint, status)
            return status
```

#### 2. WakeEndpoint

```python
class WakeEndpoint:
    """Wake a sleeping endpoint with retry logic."""

    def __init__(self, waker: IWaker):
        self._waker = waker

    async def execute(
        self,
        endpoint: Endpoint,
        max_retries: int = 3
    ) -> WakeResult:
        """
        Send wake request to endpoint and poll until ready.

        Returns:
            WakeResult with success status and wake time
        """
        start_time = time.time()

        for attempt in range(max_retries):
            try:
                # Send minimal inference request to wake endpoint
                await self._waker.wake(endpoint)

                # Poll for readiness (with timeout)
                ready = await self._waker.wait_for_ready(
                    endpoint,
                    timeout=endpoint.wake_timeout
                )

                if ready:
                    wake_time_s = time.time() - start_time
                    return WakeResult(
                        success=True,
                        wake_time_s=wake_time_s,
                        attempts=attempt + 1
                    )

            except Exception as e:
                if attempt == max_retries - 1:
                    return WakeResult(
                        success=False,
                        error=str(e),
                        attempts=max_retries
                    )

        return WakeResult(success=False, error="Max retries exceeded")
```

#### 3. ExecuteFallbackChain

```python
class ExecuteFallbackChain:
    """Execute fallback chain on primary endpoint failure."""

    def __init__(
        self,
        health_checker: CheckEndpointHealth,
        waker: WakeEndpoint
    ):
        self._health_checker = health_checker
        self._waker = waker

    async def execute(
        self,
        chain: FallbackChain,
        endpoints: Dict[str, Endpoint]
    ) -> FallbackResult:
        """
        Try primary, fallback to secondary/tertiary on failure.

        Returns:
            FallbackResult with active endpoint and fallback count
        """
        current_id = chain.primary_endpoint_id
        fallback_count = 0

        while current_id:
            endpoint = endpoints[current_id]

            # Check health
            status = await self._health_checker.execute(endpoint)

            if status.is_healthy():
                return FallbackResult(
                    active_endpoint_id=current_id,
                    fallback_count=fallback_count,
                    success=True
                )

            # Try to wake if sleeping
            if status.is_sleeping():
                wake_result = await self._waker.execute(endpoint)
                if wake_result.success:
                    return FallbackResult(
                        active_endpoint_id=current_id,
                        fallback_count=fallback_count,
                        success=True
                    )

            # Fallback to next in chain
            current_id = chain.get_next_endpoint(current_id)
            fallback_count += 1

        # All endpoints failed
        return FallbackResult(
            active_endpoint_id=None,
            fallback_count=fallback_count,
            success=False,
            error="All endpoints in fallback chain failed"
        )
```

## Adapters

### HFInferenceHealthAdapter

```python
class HFInferenceHealthAdapter(IHealthChecker):
    """Health check implementation for Hugging Face Inference API."""

    async def check(self, endpoint: Endpoint) -> HealthCheckResponse:
        """
        Send minimal inference request to check endpoint health.

        Health check payload (minimal for cost efficiency):
        - Input: Single token ("hi")
        - Max tokens: 1
        - Expected response time: < 2s (healthy), 30-60s (cold start)
        """
        payload = {
            "inputs": "hi",
            "parameters": {"max_new_tokens": 1}
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                endpoint.url,
                json=payload,
                headers={"Authorization": f"Bearer {HF_TOKEN}"},
                timeout=aiohttp.ClientTimeout(total=90)
            ) as response:
                response_time = response.headers.get("X-Compute-Time")

                if response.status == 200:
                    # Fast response = healthy
                    if response_time and float(response_time) < 2.0:
                        return HealthCheckResponse(
                            status=EndpointState.HEALTHY,
                            response_time_ms=float(response_time) * 1000
                        )
                    # Slow response = was sleeping (cold start)
                    else:
                        return HealthCheckResponse(
                            status=EndpointState.SLEEPING,
                            response_time_ms=float(response_time) * 1000 if response_time else None
                        )

                elif response.status == 503:
                    # Service temporarily unavailable (loading model)
                    return HealthCheckResponse(
                        status=EndpointState.SLEEPING,
                        response_time_ms=None
                    )

                else:
                    return HealthCheckResponse(
                        status=EndpointState.FAILED,
                        error=f"HTTP {response.status}"
                    )
```

### PrometheusMetricsAdapter

```python
class PrometheusMetricsAdapter(IMetricsExporter):
    """Export health metrics to Prometheus."""

    def __init__(self):
        # Prometheus metric definitions
        self.endpoint_health = Gauge(
            'endpoint_health_status',
            'Current health status of endpoint (1=healthy, 0=failed)',
            ['endpoint_id', 'provider', 'priority']
        )

        self.response_time = Histogram(
            'endpoint_response_time_seconds',
            'Health check response time',
            ['endpoint_id', 'provider']
        )

        self.wake_duration = Histogram(
            'endpoint_wake_duration_seconds',
            'Time to wake sleeping endpoint',
            ['endpoint_id', 'provider']
        )

        self.consecutive_failures = Counter(
            'endpoint_consecutive_failures_total',
            'Number of consecutive health check failures',
            ['endpoint_id', 'provider']
        )

        self.fallback_count = Counter(
            'endpoint_fallback_total',
            'Number of times fallback was triggered',
            ['primary_id', 'fallback_id']
        )

    async def record_health_check(
        self,
        endpoint: Endpoint,
        status: HealthStatus
    ):
        """Record health check metrics."""
        # Health status (1=healthy, 0=failed)
        health_value = 1.0 if status.is_healthy() else 0.0
        self.endpoint_health.labels(
            endpoint_id=endpoint.id,
            provider=endpoint.provider,
            priority=endpoint.priority.value
        ).set(health_value)

        # Response time
        if status.response_time_ms:
            self.response_time.labels(
                endpoint_id=endpoint.id,
                provider=endpoint.provider
            ).observe(status.response_time_ms / 1000.0)

        # Consecutive failures
        if status.consecutive_failures > 0:
            self.consecutive_failures.labels(
                endpoint_id=endpoint.id,
                provider=endpoint.provider
            ).inc()
```

## Configuration

### endpoints.yaml

```yaml
# Endpoint Monitoring Configuration
version: "1.0"

# Default settings (overridable per endpoint)
defaults:
  health_check_interval: 60       # Seconds between health checks
  wake_timeout: 90                # Max seconds to wait for wake
  wake_strategy: "priority_based" # always_warm | priority_based | reactive
  max_consecutive_failures: 3     # Failures before alerting

# Monitored endpoints
endpoints:
  - id: "qwen3-primary"
    provider: "huggingface"
    url: "https://api-inference.huggingface.co/models/Qwen/Qwen3-80B"
    priority: "critical"
    wake_strategy: "always_warm"  # Keep always warm
    health_check_interval: 30     # More frequent for critical
    fallback_endpoint_id: "qwen3-secondary"

  - id: "qwen3-secondary"
    provider: "huggingface"
    url: "https://api-inference.huggingface.co/models/Qwen/Qwen3-40B"
    priority: "high"
    wake_strategy: "priority_based"
    fallback_endpoint_id: "qwen3-tertiary"

  - id: "qwen3-tertiary"
    provider: "replicate"
    url: "https://api.replicate.com/v1/models/qwen/qwen3-80b"
    priority: "medium"
    wake_strategy: "reactive"  # Only wake on-demand

# Fallback chains
fallback_chains:
  - name: "qwen3-production"
    primary: "qwen3-primary"
    secondary: "qwen3-secondary"
    tertiary: "qwen3-tertiary"

# Alerting rules
alerts:
  - name: "endpoint_down"
    condition: "consecutive_failures > 3"
    severity: "critical"
    notify: ["email", "slack"]

  - name: "high_latency"
    condition: "response_time_ms > 5000"
    severity: "warning"
    notify: ["slack"]
```

## Deployment

### Docker Container

```dockerfile
# Dockerfile.endpoint-monitor
FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY requirements-monitor.txt .
RUN pip install --no-cache-dir -r requirements-monitor.txt

# Copy monitoring service
COPY src/monitoring/ ./src/monitoring/
COPY config/endpoints.yaml ./config/

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Expose metrics and health endpoints
EXPOSE 9090 8080

# Run as non-root
RUN useradd -m -u 1000 monitor
USER monitor

CMD ["python", "-m", "src.monitoring.daemon"]
```

### Kubernetes Deployment

```yaml
# k8s/endpoint-monitor-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: endpoint-monitor
  namespace: monitoring
spec:
  replicas: 1  # Single instance (no need for HA)
  selector:
    matchLabels:
      app: endpoint-monitor
  template:
    metadata:
      labels:
        app: endpoint-monitor
    spec:
      containers:
      - name: monitor
        image: endpoint-monitor:latest
        ports:
        - containerPort: 9090
          name: metrics
        - containerPort: 8080
          name: health
        env:
        - name: HF_TOKEN
          valueFrom:
            secretKeyRef:
              name: hf-secrets
              key: token
        resources:
          requests:
            cpu: 100m
            memory: 128Mi
          limits:
            cpu: 200m
            memory: 256Mi
        livenessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 30
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 10
          periodSeconds: 10
---
apiVersion: v1
kind: Service
metadata:
  name: endpoint-monitor
  namespace: monitoring
spec:
  selector:
    app: endpoint-monitor
  ports:
  - name: metrics
    port: 9090
    targetPort: 9090
  - name: health
    port: 8080
    targetPort: 8080
```

## Testing Strategy

### 1. Unit Tests

- **Entities**: Test health status logic, fallback chain routing
- **Use Cases**: Mock adapters, test business logic in isolation
- **Adapters**: Test with mock HTTP responses

### 2. Integration Tests

```python
# tests/integration/test_health_monitoring.py
async def test_health_check_sleeping_endpoint():
    """Test detection of sleeping endpoint and wake-up."""
    # Mock endpoint that returns 503 (sleeping)
    mock_endpoint = create_mock_endpoint(
        response_status=503,
        response_time=None
    )

    # Execute health check
    checker = CheckEndpointHealth(
        health_checker=HFInferenceHealthAdapter(),
        metrics_exporter=MockMetricsExporter()
    )
    status = await checker.execute(mock_endpoint)

    # Assert sleeping state detected
    assert status.state == EndpointState.SLEEPING
    assert status.needs_wake() is True

async def test_fallback_chain_execution():
    """Test fallback from primary to secondary on failure."""
    # Setup: primary fails, secondary succeeds
    endpoints = {
        "primary": create_mock_endpoint(id="primary", status=500),
        "secondary": create_mock_endpoint(id="secondary", status=200)
    }
    chain = FallbackChain(
        primary_endpoint_id="primary",
        secondary_endpoint_id="secondary"
    )

    # Execute fallback
    executor = ExecuteFallbackChain(...)
    result = await executor.execute(chain, endpoints)

    # Assert fallback to secondary
    assert result.success is True
    assert result.active_endpoint_id == "secondary"
    assert result.fallback_count == 1
```

### 3. End-to-End Tests

- Deploy monitor + mock endpoint server
- Verify health checks occur at correct intervals
- Verify metrics exported to Prometheus
- Verify alerts triggered on failures

## Metrics & Alerting

### Prometheus Metrics

```
# Health status (1=healthy, 0=failed)
endpoint_health_status{endpoint_id="qwen3-primary",provider="huggingface",priority="critical"} 1

# Response time histogram
endpoint_response_time_seconds{endpoint_id="qwen3-primary",provider="huggingface"} 0.345

# Wake duration histogram
endpoint_wake_duration_seconds{endpoint_id="qwen3-primary",provider="huggingface"} 45.2

# Consecutive failures counter
endpoint_consecutive_failures_total{endpoint_id="qwen3-primary",provider="huggingface"} 0

# Fallback counter
endpoint_fallback_total{primary_id="qwen3-primary",fallback_id="qwen3-secondary"} 3
```

### Alerting Rules

```yaml
# config/prometheus/alerts.yml
groups:
  - name: endpoint_monitoring
    interval: 30s
    rules:
      - alert: EndpointDown
        expr: endpoint_health_status == 0
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Endpoint {{ $labels.endpoint_id }} is down"
          description: "Endpoint has been unhealthy for 5 minutes"

      - alert: HighLatency
        expr: endpoint_response_time_seconds > 5
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "High latency on {{ $labels.endpoint_id }}"
          description: "Response time exceeds 5 seconds"

      - alert: FrequentFallbacks
        expr: rate(endpoint_fallback_total[1h]) > 0.1
        for: 30m
        labels:
          severity: warning
        annotations:
          summary: "Frequent fallbacks from {{ $labels.primary_id }}"
          description: "Fallback rate exceeds threshold"
```

### Grafana Dashboard

```json
{
  "dashboard": {
    "title": "Endpoint Health Monitoring",
    "panels": [
      {
        "title": "Endpoint Health Status",
        "type": "stat",
        "targets": [{
          "expr": "endpoint_health_status"
        }]
      },
      {
        "title": "Response Time (p95)",
        "type": "graph",
        "targets": [{
          "expr": "histogram_quantile(0.95, endpoint_response_time_seconds)"
        }]
      },
      {
        "title": "Wake Duration",
        "type": "graph",
        "targets": [{
          "expr": "endpoint_wake_duration_seconds"
        }]
      },
      {
        "title": "Fallback Events",
        "type": "graph",
        "targets": [{
          "expr": "rate(endpoint_fallback_total[5m])"
        }]
      }
    ]
  }
}
```

## Next Steps

### Implementation Order

1. ✅ **Architecture Design** (this document)
2. ⏳ **Entities & Domain Logic** (src/monitoring/entities/)
3. ⏳ **Use Cases** (src/monitoring/use_cases/)
4. ⏳ **Adapters** (src/monitoring/adapters/)
5. ⏳ **Daemon Service** (src/monitoring/daemon.py)
6. ⏳ **Configuration** (config/endpoints.yaml)
7. ⏳ **Tests** (tests/monitoring/)
8. ⏳ **Deployment** (Dockerfile, K8s manifests)
9. ⏳ **Documentation** (runbook, troubleshooting)

### Estimated Timeline

- **Phase 1 (Entities + Use Cases)**: 4 hours
- **Phase 2 (Adapters + Integration)**: 6 hours
- **Phase 3 (Testing + Debugging)**: 4 hours
- **Phase 4 (Deployment + Docs)**: 2 hours
- **Total**: 16 hours ✅ (matches estimate)

## References

- HF Inference API: https://huggingface.co/docs/api-inference/index
- Prometheus Python Client: https://github.com/prometheus/client_python
- AsyncIO Best Practices: https://docs.python.org/3/library/asyncio.html
- Clean Architecture (Robert C. Martin): Entities → Use Cases → Adapters
