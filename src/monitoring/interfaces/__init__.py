"""Abstract interfaces for endpoint monitoring.

Interfaces define contracts between layers following Dependency Inversion Principle.
Use cases depend on these abstractions, adapters implement them.

Key interfaces:
- IHealthChecker: Check endpoint health (abstract, provider-agnostic)
- IWaker: Wake sleeping endpoint (basic capability)
- IReadinessPoller: Poll endpoint readiness (optional capability, ISP-compliant)
- IMetricsExporter: Export health metrics (Prometheus, etc.)
"""

from .health_checker import IHealthChecker, BaseHealthChecker
from .waker import IWaker, IReadinessPoller
from .metrics import IMetricsExporter

__all__ = [
    "IHealthChecker",
    "BaseHealthChecker",
    "IWaker",
    "IReadinessPoller",
    "IMetricsExporter",
]
