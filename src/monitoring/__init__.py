"""Endpoint monitoring and auto-wake service.

This module provides health monitoring and automatic wake-up for scale-to-zero
inference endpoints (Hugging Face Inference API, Replicate, Modal, etc.).

Architecture follows Clean Architecture principles:
- entities/: Domain entities (Endpoint, HealthStatus, FallbackChain)
- interfaces/: Abstract interfaces (IHealthChecker, IWaker, etc.)
- use_cases/: Business logic (CheckHealth, WakeEndpoint, ExecuteFallback)
- adapters/: External integrations (HF, Replicate, Prometheus, etc.)

Key capabilities:
- Health monitoring via periodic polling
- Auto-wake for sleeping endpoints
- Fallback chains for reliability
- Prometheus metrics + Grafana dashboards
- AlertManager integration

See docs/ENDPOINT_MONITOR_ARCHITECTURE.md for detailed design.
"""

__version__ = "1.0.0"
