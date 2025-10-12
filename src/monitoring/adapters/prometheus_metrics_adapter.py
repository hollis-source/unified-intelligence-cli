"""Prometheus metrics exporter adapter.

Implements metrics export to Prometheus for health monitoring data.
"""

import logging
from typing import TYPE_CHECKING

from prometheus_client import Gauge, Histogram, Counter

if TYPE_CHECKING:
    from ..entities import Endpoint, HealthStatus

from ..entities import EndpointState
from ..interfaces import IMetricsExporter

logger = logging.getLogger(__name__)


class PrometheusMetricsAdapter(IMetricsExporter):
    """Metrics exporter for Prometheus.

    Exports health monitoring metrics to Prometheus format.

    Metrics exported:
    - endpoint_health_status: Current health state (0-4)
    - endpoint_response_time_ms: Response time distribution
    - endpoint_wake_time_seconds: Wake time distribution
    - endpoint_consecutive_failures: Consecutive failure count
    - endpoint_fallback_total: Fallback event counter

    Contract Compliance:
    - MUST NOT raise exceptions (logs errors instead)
    - SHOULD complete quickly (< 1s)
    - MAY batch metrics for performance
    """

    def __init__(self):
        """Initialize Prometheus metrics."""
        # Gauge: Current health status (0=UNKNOWN, 1=HEALTHY, 2=DEGRADED, 3=SLEEPING, 4=FAILED)
        self.health_status_gauge = Gauge(
            "endpoint_health_status",
            "Current health status of endpoint (0=UNKNOWN, 1=HEALTHY, 2=DEGRADED, 3=SLEEPING, 4=FAILED)",
            ["endpoint_id", "provider", "priority"]
        )

        # Histogram: Response time distribution
        self.response_time_histogram = Histogram(
            "endpoint_response_time_ms",
            "Health check response time in milliseconds",
            ["endpoint_id", "provider", "state"],
            buckets=[10, 50, 100, 500, 1000, 5000, 10000, 30000, 60000, 90000]  # 10ms to 90s
        )

        # Histogram: Wake time distribution
        self.wake_time_histogram = Histogram(
            "endpoint_wake_time_seconds",
            "Endpoint wake time in seconds",
            ["endpoint_id", "provider", "success"],
            buckets=[1, 5, 10, 30, 60, 90, 120, 180, 300]  # 1s to 5min
        )

        # Gauge: Consecutive failures
        self.consecutive_failures_gauge = Gauge(
            "endpoint_consecutive_failures",
            "Number of consecutive health check failures",
            ["endpoint_id", "provider"]
        )

        # Counter: Fallback events
        self.fallback_counter = Counter(
            "endpoint_fallback_total",
            "Total number of fallback events",
            ["primary_endpoint_id", "fallback_endpoint_id", "fallback_count"]
        )

    async def record_health_check(
        self,
        endpoint: "Endpoint",
        status: "HealthStatus"
    ) -> None:
        """Record health check result.

        Contract:
        - MUST NOT raise exceptions (log errors instead)
        - SHOULD complete quickly (< 1s)

        Args:
            endpoint: Endpoint that was checked
            status: Health status result
        """
        try:
            # Map state to numeric value for gauge
            state_value = self._state_to_numeric(status.state)

            # Update health status gauge
            self.health_status_gauge.labels(
                endpoint_id=endpoint.id,
                provider=endpoint.provider,
                priority=endpoint.priority.value
            ).set(state_value)

            # Record response time if available
            if status.response_time_ms is not None:
                self.response_time_histogram.labels(
                    endpoint_id=endpoint.id,
                    provider=endpoint.provider,
                    state=status.state.value
                ).observe(status.response_time_ms)

            # Update consecutive failures gauge
            self.consecutive_failures_gauge.labels(
                endpoint_id=endpoint.id,
                provider=endpoint.provider
            ).set(status.consecutive_failures)

        except Exception as e:
            # Contract: MUST NOT raise exceptions
            logger.error(
                f"Failed to record health check metrics for {endpoint.id}: {e}",
                exc_info=True
            )

    async def record_wake_attempt(
        self,
        endpoint: "Endpoint",
        wake_time_s: float,
        success: bool
    ) -> None:
        """Record wake attempt result.

        Contract:
        - MUST NOT raise exceptions (log errors instead)
        - SHOULD complete quickly (< 1s)

        Args:
            endpoint: Endpoint that was woken
            wake_time_s: Time taken to wake endpoint
            success: Whether wake succeeded
        """
        try:
            self.wake_time_histogram.labels(
                endpoint_id=endpoint.id,
                provider=endpoint.provider,
                success=str(success)
            ).observe(wake_time_s)

        except Exception as e:
            # Contract: MUST NOT raise exceptions
            logger.error(
                f"Failed to record wake metrics for {endpoint.id}: {e}",
                exc_info=True
            )

    async def record_fallback(
        self,
        primary_endpoint_id: str,
        fallback_endpoint_id: str,
        fallback_count: int
    ) -> None:
        """Record fallback event.

        Contract:
        - MUST NOT raise exceptions (log errors instead)
        - SHOULD complete quickly (< 1s)

        Args:
            primary_endpoint_id: ID of primary endpoint that failed
            fallback_endpoint_id: ID of fallback endpoint used
            fallback_count: Number of fallbacks in chain (1 = first fallback)
        """
        try:
            self.fallback_counter.labels(
                primary_endpoint_id=primary_endpoint_id,
                fallback_endpoint_id=fallback_endpoint_id,
                fallback_count=str(fallback_count)
            ).inc()

        except Exception as e:
            # Contract: MUST NOT raise exceptions
            logger.error(
                f"Failed to record fallback metrics: primary={primary_endpoint_id}, "
                f"fallback={fallback_endpoint_id}, error={e}",
                exc_info=True
            )

    async def increment_consecutive_failures(
        self,
        endpoint: "Endpoint",
        failure_count: int
    ) -> None:
        """Increment consecutive failure counter.

        Contract:
        - MUST NOT raise exceptions (log errors instead)
        - SHOULD complete quickly (< 1s)

        Args:
            endpoint: Endpoint with failures
            failure_count: Current consecutive failure count
        """
        try:
            self.consecutive_failures_gauge.labels(
                endpoint_id=endpoint.id,
                provider=endpoint.provider
            ).set(failure_count)

        except Exception as e:
            # Contract: MUST NOT raise exceptions
            logger.error(
                f"Failed to update consecutive failures for {endpoint.id}: {e}",
                exc_info=True
            )

    @staticmethod
    def _state_to_numeric(state: EndpointState) -> int:
        """Convert EndpointState to numeric value for Prometheus gauge.

        Args:
            state: EndpointState enum

        Returns:
            Numeric value (0=UNKNOWN, 1=HEALTHY, 2=DEGRADED, 3=SLEEPING, 4=FAILED)
        """
        mapping = {
            EndpointState.UNKNOWN: 0,
            EndpointState.HEALTHY: 1,
            EndpointState.DEGRADED: 2,
            EndpointState.SLEEPING: 3,
            EndpointState.FAILED: 4,
        }
        return mapping.get(state, 0)
