"""Endpoint monitoring daemon service.

Main orchestration logic for periodic health checking and auto-wake.
"""

import asyncio
import logging
import signal
from typing import Dict, Set
from prometheus_client import start_http_server

from .config import MonitoringConfig
from .entities import Endpoint, HealthStatus
from .use_cases import CheckEndpointHealth, WakeEndpoint
from .adapters import (
    HFInferenceHealthAdapter,
    HFInferenceWaker,
    PrometheusMetricsAdapter,
)

logger = logging.getLogger(__name__)


class EndpointMonitoringDaemon:
    """Daemon service for endpoint health monitoring and auto-wake.

    Responsibilities:
    - Schedule periodic health checks for all configured endpoints
    - Auto-wake sleeping endpoints based on wake strategy
    - Expose Prometheus metrics
    - Handle graceful shutdown

    Clean Architecture:
    - Uses domain entities (Endpoint, HealthStatus)
    - Depends on use cases (CheckEndpointHealth, WakeEndpoint)
    - Adapters injected (health checker, waker, metrics)
    """

    def __init__(
        self,
        config: MonitoringConfig,
        metrics_port: int = 9090,
        check_health_use_case: CheckEndpointHealth = None,
        wake_endpoint_use_case: WakeEndpoint = None,
        execute_fallback_chain_use_case = None,
    ):
        """Initialize daemon with configuration.

        Args:
            config: Parsed monitoring configuration
            metrics_port: Port for Prometheus metrics endpoint
            check_health_use_case: Optional CheckEndpointHealth use case (for testing)
            wake_endpoint_use_case: Optional WakeEndpoint use case (for testing)
            execute_fallback_chain_use_case: Optional ExecuteFallbackChain use case (for testing)
        """
        self.config = config
        self.metrics_port = metrics_port

        # Initialize use cases (or use injected ones for testing)
        if check_health_use_case is None:
            # Production: Create real adapters and use cases
            self.metrics_adapter = PrometheusMetricsAdapter()
            self.health_adapter = HFInferenceHealthAdapter()
            self.waker = HFInferenceWaker()

            self.check_health_use_case = CheckEndpointHealth(
                health_checker=self.health_adapter,
                metrics_exporter=self.metrics_adapter,
            )
            self.wake_use_case = WakeEndpoint(
                waker=self.waker, metrics_exporter=self.metrics_adapter
            )
        else:
            # Testing: Use injected mocks
            self.check_health_use_case = check_health_use_case
            self.wake_use_case = wake_endpoint_use_case

        # Track running tasks for graceful shutdown
        self.tasks: Set[asyncio.Task] = set()
        self.shutdown_event = asyncio.Event()

    async def start(self):
        """Start daemon service.

        - Starts Prometheus metrics server
        - Schedules health checks for all endpoints
        - Waits for shutdown signal
        """
        logger.info(f"Starting endpoint monitoring daemon (metrics port: {self.metrics_port})")

        # Start Prometheus metrics server (runs in separate thread)
        start_http_server(self.metrics_port)
        logger.info(f"Prometheus metrics available at http://localhost:{self.metrics_port}/metrics")

        # Setup signal handlers for graceful shutdown
        self._setup_signal_handlers()

        # Start health check tasks for all endpoints
        for endpoint_id, endpoint in self.config.endpoints.items():
            health_status = self.config.health_statuses[endpoint_id]
            task = asyncio.create_task(
                self._health_check_loop(endpoint, health_status),
                name=f"health_check_{endpoint_id}",
            )
            self.tasks.add(task)
            logger.info(
                f"Started health check for {endpoint_id} "
                f"(interval: {endpoint.get_health_check_interval()}s)"
            )

        logger.info(f"Daemon started with {len(self.tasks)} endpoint monitors")

        # Wait for shutdown signal
        await self.shutdown_event.wait()

        # Graceful shutdown
        await self._shutdown()

    async def _health_check_loop(self, endpoint: Endpoint, health_status: HealthStatus):
        """Continuously monitor endpoint health.

        Args:
            endpoint: Endpoint to monitor
            health_status: Mutable health status to update
        """
        interval = endpoint.get_health_check_interval()

        while not self.shutdown_event.is_set():
            try:
                # Execute health check
                response = await self.check_health_use_case.execute(
                    endpoint, health_status
                )

                logger.debug(
                    f"[{endpoint.id}] Health check: {response.status.value} "
                    f"(response_time: {response.response_time_ms}ms)"
                )

                # Auto-wake if sleeping and strategy allows
                if response.is_cold_start() and endpoint.should_auto_wake():
                    logger.info(
                        f"[{endpoint.id}] Endpoint is sleeping, auto-waking "
                        f"(strategy: {endpoint.wake_strategy.value})"
                    )
                    wake_result = await self.wake_use_case.execute(
                        endpoint, health_status, wait_for_ready=True
                    )

                    if wake_result.success and wake_result.is_ready:
                        logger.info(
                            f"[{endpoint.id}] Wake successful "
                            f"(wake_time: {wake_result.wake_time_s:.1f}s)"
                        )
                    else:
                        logger.warning(
                            f"[{endpoint.id}] Wake failed: {wake_result.error_message}"
                        )

            except Exception as e:
                logger.error(
                    f"[{endpoint.id}] Unexpected error in health check loop: {e}",
                    exc_info=True,
                )

            # Sleep until next check (or shutdown)
            try:
                await asyncio.wait_for(
                    self.shutdown_event.wait(), timeout=interval
                )
                # If we get here, shutdown was signaled
                break
            except asyncio.TimeoutError:
                # Normal case: timeout means continue to next health check
                continue

    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown."""
        loop = asyncio.get_running_loop()

        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(
                sig, lambda s=sig: asyncio.create_task(self._handle_signal(s))
            )

    async def _handle_signal(self, sig: signal.Signals):
        """Handle shutdown signal.

        Args:
            sig: Signal received (SIGTERM or SIGINT)
        """
        logger.info(f"Received {sig.name}, initiating graceful shutdown...")
        self.shutdown_event.set()

    async def _shutdown(self):
        """Perform graceful shutdown.

        - Cancel all health check tasks
        - Wait for tasks to complete
        - Log shutdown status
        """
        logger.info("Shutting down daemon...")

        # Cancel all tasks
        for task in self.tasks:
            task.cancel()

        # Wait for all tasks to complete (or be cancelled)
        results = await asyncio.gather(*self.tasks, return_exceptions=True)

        # Log any unexpected errors (ignore CancelledError)
        for i, result in enumerate(results):
            if isinstance(result, Exception) and not isinstance(
                result, asyncio.CancelledError
            ):
                logger.error(f"Task {i} failed during shutdown: {result}")

        logger.info("Daemon shutdown complete")
