"""Domain entities for endpoint monitoring.

Entities are the core business objects that define the domain model.
They have no external dependencies and contain the business rules.

Key entities:
- Endpoint: Represents a monitored inference endpoint
- HealthStatus: Current health state of an endpoint
- FallbackChain: Defines fallback routing between endpoints
- Enums: EndpointState, EndpointPriority, WakeStrategy, etc.
"""

from .enums import (
    EndpointState,
    EndpointPriority,
    WakeStrategy,
    HealthCheckErrorCode,
)
from .endpoint import Endpoint
from .health_status import HealthStatus, HealthCheckResponse, WakeResult, FallbackResult
from .fallback_chain import FallbackChain

__all__ = [
    # Enums
    "EndpointState",
    "EndpointPriority",
    "WakeStrategy",
    "HealthCheckErrorCode",
    # Entities
    "Endpoint",
    "HealthStatus",
    "HealthCheckResponse",
    "WakeResult",
    "FallbackResult",
    "FallbackChain",
]
