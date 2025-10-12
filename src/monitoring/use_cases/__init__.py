"""Use cases for endpoint monitoring service.

Use cases orchestrate domain logic without knowledge of external systems.
They depend on interfaces (IHealthChecker, IWaker, etc.) not implementations.
"""

from .check_endpoint_health import CheckEndpointHealth
from .wake_endpoint import WakeEndpoint
from .execute_fallback_chain import ExecuteFallbackChain

__all__ = [
    "CheckEndpointHealth",
    "WakeEndpoint",
    "ExecuteFallbackChain",
]
