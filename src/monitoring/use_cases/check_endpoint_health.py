"""Check endpoint health use case.

Orchestrates health checking with metrics recording.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..entities import Endpoint, HealthCheckResponse, HealthStatus
    from ..interfaces import IHealthChecker, IMetricsExporter


class CheckEndpointHealth:
    """Use case for checking endpoint health.

    Responsibilities:
    - Execute health check via IHealthChecker
    - Record metrics via IMetricsExporter (non-blocking)
    - Update HealthStatus (mutates state)
    - Return HealthCheckResponse

    Clean Architecture:
    - Depends on interfaces (IHealthChecker, IMetricsExporter)
    - No knowledge of HTTP, database, or other external concerns
    - Pure orchestration of domain logic
    """

    def __init__(
        self,
        health_checker: "IHealthChecker",
        metrics_exporter: "IMetricsExporter"
    ):
        """Initialize use case with dependencies.

        Args:
            health_checker: Health checker adapter (HF, Replicate, etc.)
            metrics_exporter: Metrics exporter (Prometheus, etc.)
        """
        self._health_checker = health_checker
        self._metrics_exporter = metrics_exporter

    async def execute(
        self,
        endpoint: "Endpoint",
        health_status: "HealthStatus"
    ) -> "HealthCheckResponse":
        """Execute health check and update status.

        Args:
            endpoint: Endpoint to check
            health_status: Mutable status object to update

        Returns:
            HealthCheckResponse with check results

        Side Effects:
            - Updates health_status (mutates state)
            - Records metrics (async, non-blocking)

        Contract:
            - MUST return HealthCheckResponse (never None)
            - MUST update health_status from response
            - SHOULD record metrics (but failures don't affect health check)
        """
        # Execute health check (may take 1-90s depending on endpoint state)
        response = await self._health_checker.check(endpoint)

        # Update mutable health status from response
        health_status.update_from_response(response)

        # Record metrics asynchronously (fire-and-forget, failures logged internally)
        # Note: IMetricsExporter contract ensures this doesn't raise exceptions
        await self._metrics_exporter.record_health_check(endpoint, health_status)

        return response
