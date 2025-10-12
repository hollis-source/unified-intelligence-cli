"""Metrics exporter interface for health monitoring data.

IMetricsExporter: Abstract interface for exporting metrics (Prometheus, etc.)
"""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..entities import Endpoint, HealthStatus


class IMetricsExporter(ABC):
    """Abstract interface for exporting health metrics.

    Implementations export metrics to various backends (Prometheus, OpenTelemetry, etc.).
    Use cases call this after health checks to record metrics.

    Contract:
    - Metrics recording should be non-blocking (async)
    - Failures should not affect health check operation
    - Should support multiple metric types (gauges, histograms, counters)
    """

    @abstractmethod
    async def record_health_check(
        self,
        endpoint: "Endpoint",
        status: "HealthStatus"
    ) -> None:
        """Record health check result.

        Args:
            endpoint: Endpoint that was checked
            status: Health status result

        Contract:
        - MUST NOT raise exceptions (log errors instead)
        - SHOULD complete quickly (< 1s)
        - MAY batch metrics for performance
        """
        pass

    @abstractmethod
    async def record_wake_attempt(
        self,
        endpoint: "Endpoint",
        wake_time_s: float,
        success: bool
    ) -> None:
        """Record wake attempt result.

        Args:
            endpoint: Endpoint that was woken
            wake_time_s: Time taken to wake endpoint
            success: Whether wake succeeded

        Contract:
        - MUST NOT raise exceptions (log errors instead)
        - SHOULD complete quickly (< 1s)
        """
        pass

    @abstractmethod
    async def record_fallback(
        self,
        primary_endpoint_id: str,
        fallback_endpoint_id: str,
        fallback_count: int
    ) -> None:
        """Record fallback event.

        Args:
            primary_endpoint_id: ID of primary endpoint that failed
            fallback_endpoint_id: ID of fallback endpoint used
            fallback_count: Number of fallbacks in chain (1 = first fallback)

        Contract:
        - MUST NOT raise exceptions (log errors instead)
        - SHOULD complete quickly (< 1s)
        """
        pass

    @abstractmethod
    async def increment_consecutive_failures(
        self,
        endpoint: "Endpoint",
        failure_count: int
    ) -> None:
        """Increment consecutive failure counter.

        Args:
            endpoint: Endpoint with failures
            failure_count: Current consecutive failure count

        Contract:
        - MUST NOT raise exceptions (log errors instead)
        - SHOULD complete quickly (< 1s)
        """
        pass
