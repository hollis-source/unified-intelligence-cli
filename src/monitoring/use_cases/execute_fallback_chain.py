"""Execute fallback chain use case.

Orchestrates fallback routing when primary endpoint fails.
"""

from typing import TYPE_CHECKING, Dict, Optional

if TYPE_CHECKING:
    from ..entities import FallbackChain, FallbackResult, Endpoint, HealthStatus
    from ..interfaces import IMetricsExporter


class ExecuteFallbackChain:
    """Use case for executing fallback chain.

    Responsibilities:
    - Attempt endpoints in chain order (primary → secondary → tertiary)
    - Record fallback metrics for each attempt
    - Return FallbackResult with successful endpoint (or failure)

    Clean Architecture:
    - Coordinates with CheckEndpointHealth for each attempt
    - Depends on IMetricsExporter for fallback tracking
    - No knowledge of specific providers or failure reasons
    - Pure orchestration of domain logic
    """

    def __init__(
        self,
        check_endpoint_health: "CheckEndpointHealth",
        metrics_exporter: "IMetricsExporter"
    ):
        """Initialize use case with dependencies.

        Args:
            check_endpoint_health: Use case for checking endpoint health
            metrics_exporter: Metrics exporter (Prometheus, etc.)
        """
        from .check_endpoint_health import CheckEndpointHealth
        self._check_health = check_endpoint_health
        self._metrics_exporter = metrics_exporter

    async def execute(
        self,
        fallback_chain: "FallbackChain",
        endpoints: Dict[str, "Endpoint"],
        health_statuses: Dict[str, "HealthStatus"]
    ) -> "FallbackResult":
        """Execute fallback chain until success or exhaustion.

        Args:
            fallback_chain: Fallback chain configuration
            endpoints: Map of endpoint_id -> Endpoint
            health_statuses: Map of endpoint_id -> HealthStatus (mutable)

        Returns:
            FallbackResult with outcome

        Side Effects:
            - Updates health_statuses for all attempted endpoints
            - Records fallback metrics for each fallback

        Contract:
            - MUST try endpoints in order: primary → secondary → tertiary
            - MUST stop on first successful health check
            - MUST record fallback metric for each non-primary attempt
            - MUST return FallbackResult (never None)
        """
        from ..entities import FallbackResult

        # Get all endpoints in chain order
        endpoint_ids = fallback_chain.get_endpoints()

        attempted_count = 0
        last_error = None

        # Try each endpoint in chain order
        for endpoint_id in endpoint_ids:
            attempted_count += 1

            # Get endpoint and status
            endpoint = endpoints.get(endpoint_id)
            health_status = health_statuses.get(endpoint_id)

            if not endpoint or not health_status:
                last_error = f"Endpoint {endpoint_id} not found in configuration"
                continue

            # Check endpoint health
            response = await self._check_health.execute(endpoint, health_status)

            # If successful, record fallback metric (if not primary) and return
            if response.is_successful():
                # Record fallback metric if this wasn't the primary endpoint
                if endpoint_id != fallback_chain.primary_endpoint_id:
                    fallback_count = attempted_count - 1  # How many fallbacks occurred
                    await self._metrics_exporter.record_fallback(
                        fallback_chain.primary_endpoint_id,
                        endpoint_id,
                        fallback_count
                    )

                return FallbackResult(
                    success=True,
                    active_endpoint_id=endpoint_id,
                    fallback_count=attempted_count - 1  # 0 = primary, 1 = first fallback, etc.
                )

            # Track error for final result
            last_error = response.error_code.value if response.error_code else "Unknown error"

        # All endpoints failed - return failure result
        return FallbackResult(
            success=False,
            active_endpoint_id=None,
            fallback_count=attempted_count - 1,  # How many fallbacks were attempted
            error=f"All endpoints in chain failed. Last error: {last_error}"
        )
