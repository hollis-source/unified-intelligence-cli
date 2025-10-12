"""Wake endpoint use case.

Orchestrates endpoint waking with optional readiness polling.
"""

import asyncio
import time
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from ..entities import Endpoint, WakeResult, HealthStatus
    from ..interfaces import IWaker, IMetricsExporter

from ..interfaces import IReadinessPoller


class WakeEndpoint:
    """Use case for waking sleeping endpoints.

    Responsibilities:
    - Send wake request via IWaker
    - Poll for readiness if IReadinessPoller available (ISP-compliant)
    - Record wake metrics via IMetricsExporter
    - Update HealthStatus with wake time
    - Return WakeResult

    ISP Compliance:
    - Gracefully handles wakers that don't support readiness polling
    - Uses isinstance() check to determine if polling available
    - Falls back to simple wake if polling not supported

    Clean Architecture:
    - Depends on interfaces (IWaker, optional IReadinessPoller)
    - No knowledge of provider-specific wake mechanisms
    - Pure orchestration of domain logic
    """

    def __init__(
        self,
        waker: "IWaker",
        metrics_exporter: "IMetricsExporter"
    ):
        """Initialize use case with dependencies.

        Args:
            waker: Waker adapter (may also implement IReadinessPoller)
            metrics_exporter: Metrics exporter (Prometheus, etc.)
        """
        self._waker = waker
        self._metrics_exporter = metrics_exporter

    async def execute(
        self,
        endpoint: "Endpoint",
        health_status: "HealthStatus",
        wait_for_ready: bool = True
    ) -> "WakeResult":
        """Wake endpoint and optionally wait for readiness.

        Args:
            endpoint: Endpoint to wake
            health_status: Mutable status object to update
            wait_for_ready: Whether to poll for readiness (requires IReadinessPoller)

        Returns:
            WakeResult with wake outcome

        Side Effects:
            - Updates health_status.last_wake_time
            - Records wake metrics (async, non-blocking)

        Contract:
            - MUST return WakeResult (never None)
            - MUST update health_status.last_wake_time
            - SHOULD poll for readiness if wait_for_ready=True and adapter supports it
        """
        from ..entities import WakeResult
        from datetime import datetime

        start_time = time.time()

        # Send wake request (minimal inference to trigger cold start)
        wake_result = await self._waker.wake(endpoint)

        # Poll for readiness if requested and adapter supports it (ISP-compliant)
        polling_error = None
        if wait_for_ready and isinstance(self._waker, IReadinessPoller):
            try:
                is_ready = await asyncio.wait_for(
                    self._waker.poll_until_ready(endpoint, endpoint.wake_timeout),
                    timeout=endpoint.wake_timeout
                )
                if not is_ready:
                    polling_error = f"Endpoint not ready after {endpoint.wake_timeout}s"
            except asyncio.TimeoutError:
                polling_error = f"Readiness polling timed out after {endpoint.wake_timeout}s"

        # Calculate total wake time
        wake_time_s = time.time() - start_time

        # Create final result with wake time (WakeResult is frozen, so create new instance)
        final_result = WakeResult(
            success=wake_result.success,
            wake_time_s=wake_time_s,
            attempts=wake_result.attempts,
            error=wake_result.error if wake_result.error else polling_error,
            warning=wake_result.warning
        )

        # Update health status with wake time
        health_status.last_wake_time = datetime.now()

        # Record wake metrics (fire-and-forget, failures logged internally)
        await self._metrics_exporter.record_wake_attempt(
            endpoint,
            wake_time_s,
            final_result.success
        )

        return final_result
