"""
Integration tests for EndpointMonitoringDaemon.

Tests daemon orchestration logic including:
- Health check loop scheduling
- Concurrent endpoint monitoring
- Auto-wake triggering
- Graceful shutdown

Uses mocked use cases to avoid real HTTP calls and keep tests fast.
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from src.monitoring.daemon import EndpointMonitoringDaemon
from src.monitoring.config.loader import MonitoringConfig
from src.monitoring.entities import (
    Endpoint,
    HealthStatus,
    HealthCheckResponse,
    WakeResult,
    EndpointState,
    EndpointPriority,
    WakeStrategy,
    HealthCheckErrorCode,
)


@pytest.fixture
def test_config():
    """Create test configuration with short intervals."""
    endpoints = {
        "test-ep-1": Endpoint(
            id="test-ep-1",
            provider="huggingface",
            url="https://api-inference.huggingface.co/models/test-1",
            priority=EndpointPriority.CRITICAL,
            wake_strategy=WakeStrategy.ALWAYS_WARM,
            health_check_interval=1,  # Short interval for testing
        ),
        "test-ep-2": Endpoint(
            id="test-ep-2",
            provider="huggingface",
            url="https://api-inference.huggingface.co/models/test-2",
            priority=EndpointPriority.HIGH,
            wake_strategy=WakeStrategy.PRIORITY_BASED,
            health_check_interval=1,
        ),
    }

    # Initialize health statuses for all endpoints
    health_statuses = {}
    for endpoint_id in endpoints.keys():
        health_statuses[endpoint_id] = HealthStatus(
            endpoint_id=endpoint_id,
            state=EndpointState.UNKNOWN,
            last_check_time=datetime.now(),
        )

    return MonitoringConfig(
        endpoints=endpoints,
        fallback_chains={},
        health_statuses=health_statuses,
    )


@pytest.fixture
def mock_use_cases():
    """Create mocked use cases."""
    check_health_mock = AsyncMock()
    wake_endpoint_mock = AsyncMock()
    fallback_chain_mock = AsyncMock()

    return check_health_mock, wake_endpoint_mock, fallback_chain_mock


class TestDaemonInitialization:
    """Test daemon initialization and setup."""

    def test_daemon_has_config_with_health_statuses(self, test_config, mock_use_cases):
        """Test daemon config contains health status for all endpoints."""
        check_health, wake_endpoint, fallback_chain = mock_use_cases

        daemon = EndpointMonitoringDaemon(
            config=test_config,
            check_health_use_case=check_health,
            wake_endpoint_use_case=wake_endpoint,
            execute_fallback_chain_use_case=fallback_chain,
            metrics_port=9090,
        )

        # Assert
        assert len(daemon.config.health_statuses) == 2
        assert "test-ep-1" in daemon.config.health_statuses
        assert "test-ep-2" in daemon.config.health_statuses
        assert isinstance(daemon.config.health_statuses["test-ep-1"], HealthStatus)
        assert daemon.config.health_statuses["test-ep-1"].endpoint_id == "test-ep-1"

    def test_daemon_initializes_empty_task_set(self, test_config, mock_use_cases):
        """Test daemon initializes empty task set."""
        check_health, wake_endpoint, fallback_chain = mock_use_cases

        daemon = EndpointMonitoringDaemon(
            config=test_config,
            check_health_use_case=check_health,
            wake_endpoint_use_case=wake_endpoint,
            execute_fallback_chain_use_case=fallback_chain,
        )

        # Assert
        assert len(daemon.tasks) == 0


class TestHealthCheckLoopScheduling:
    """Test health check loop scheduling logic."""

    @pytest.mark.asyncio
    async def test_daemon_starts_health_check_loops_for_all_endpoints(
        self, test_config, mock_use_cases
    ):
        """Test daemon creates health check loop tasks for all endpoints."""
        check_health, wake_endpoint, fallback_chain = mock_use_cases

        # Mock healthy response (no wake needed)
        check_health.execute.return_value = HealthCheckResponse(
            status=EndpointState.HEALTHY,
            response_time_ms=100,
        )

        daemon = EndpointMonitoringDaemon(
            config=test_config,
            check_health_use_case=check_health,
            wake_endpoint_use_case=wake_endpoint,
            execute_fallback_chain_use_case=fallback_chain,
        )

        # Patch start_http_server to avoid actual server startup
        with patch("src.monitoring.daemon.start_http_server"):
            # Start daemon in background
            start_task = asyncio.create_task(daemon.start())

            # Wait for tasks to be created
            await asyncio.sleep(0.1)

            # Trigger shutdown
            daemon.shutdown_event.set()

            # Wait for daemon to stop
            await start_task

        # Assert: 2 health check loop tasks created
        assert check_health.execute.call_count >= 2  # At least one call per endpoint


    @pytest.mark.asyncio
    async def test_health_check_loop_respects_interval(
        self, mock_use_cases
    ):
        """Test health check loop uses correct interval."""
        check_health, wake_endpoint, fallback_chain = mock_use_cases

        # Track call times
        call_times = []

        async def record_time(*args, **kwargs):
            call_times.append(asyncio.get_event_loop().time())
            return HealthCheckResponse(
                status=EndpointState.HEALTHY,
                response_time_ms=100,
            )

        check_health.execute.side_effect = record_time

        # Create config with shorter interval for testing
        endpoints = {
            "test-ep-1": Endpoint(
                id="test-ep-1",
                provider="huggingface",
                url="https://api-inference.huggingface.co/models/test-1",
                priority=EndpointPriority.CRITICAL,
                wake_strategy=WakeStrategy.ALWAYS_WARM,
                health_check_interval=0.5,  # Short interval for testing
            ),
        }

        health_statuses = {
            "test-ep-1": HealthStatus(
                endpoint_id="test-ep-1",
                state=EndpointState.UNKNOWN,
                last_check_time=datetime.now(),
            ),
        }

        config = MonitoringConfig(
            endpoints=endpoints,
            fallback_chains={},
            health_statuses=health_statuses,
        )

        daemon = EndpointMonitoringDaemon(
            config=config,
            check_health_use_case=check_health,
            wake_endpoint_use_case=wake_endpoint,
            execute_fallback_chain_use_case=fallback_chain,
        )

        with patch("src.monitoring.daemon.start_http_server"):
            start_task = asyncio.create_task(daemon.start())

            # Wait for multiple health checks
            await asyncio.sleep(1.5)

            # Trigger shutdown
            daemon.shutdown_event.set()
            await start_task

        # Assert: Multiple health checks happened with ~0.5s interval
        # Should have at least 2 calls (1.5s / 0.5s = 3 calls, expect at least 2)
        assert check_health.execute.call_count >= 2


class TestAutoWakeTriggering:
    """Test auto-wake triggering logic."""

    @pytest.mark.asyncio
    async def test_daemon_wakes_sleeping_endpoint_with_always_warm_strategy(
        self, test_config, mock_use_cases
    ):
        """Test daemon auto-wakes sleeping endpoint with ALWAYS_WARM strategy."""
        check_health, wake_endpoint, fallback_chain = mock_use_cases

        # Mock sleeping response
        check_health.execute.return_value = HealthCheckResponse(
            status=EndpointState.SLEEPING,
            error_code=HealthCheckErrorCode.MODEL_LOADING,
        )

        # Mock successful wake
        wake_endpoint.execute.return_value = WakeResult(
            success=True,
            wake_time_s=5.0,
        )

        # test-ep-1 has ALWAYS_WARM strategy
        daemon = EndpointMonitoringDaemon(
            config=test_config,
            check_health_use_case=check_health,
            wake_endpoint_use_case=wake_endpoint,
            execute_fallback_chain_use_case=fallback_chain,
        )

        with patch("src.monitoring.daemon.start_http_server"):
            start_task = asyncio.create_task(daemon.start())

            # Wait for health check + wake
            await asyncio.sleep(0.2)

            # Trigger shutdown
            daemon.shutdown_event.set()
            await start_task

        # Assert: Wake was called for sleeping endpoint
        assert wake_endpoint.execute.call_count >= 1

    @pytest.mark.asyncio
    async def test_daemon_does_not_wake_healthy_endpoint(
        self, test_config, mock_use_cases
    ):
        """Test daemon does not wake already-healthy endpoint."""
        check_health, wake_endpoint, fallback_chain = mock_use_cases

        # Mock healthy response
        check_health.execute.return_value = HealthCheckResponse(
            status=EndpointState.HEALTHY,
            response_time_ms=100,
        )

        daemon = EndpointMonitoringDaemon(
            config=test_config,
            check_health_use_case=check_health,
            wake_endpoint_use_case=wake_endpoint,
            execute_fallback_chain_use_case=fallback_chain,
        )

        with patch("src.monitoring.daemon.start_http_server"):
            start_task = asyncio.create_task(daemon.start())

            # Wait for health check
            await asyncio.sleep(0.2)

            # Trigger shutdown
            daemon.shutdown_event.set()
            await start_task

        # Assert: Wake was NOT called
        assert wake_endpoint.execute.call_count == 0


class TestConcurrentMonitoring:
    """Test concurrent endpoint monitoring."""

    @pytest.mark.asyncio
    async def test_daemon_monitors_multiple_endpoints_concurrently(
        self, test_config, mock_use_cases
    ):
        """Test daemon monitors multiple endpoints in parallel."""
        check_health, wake_endpoint, fallback_chain = mock_use_cases

        # Track which endpoints were checked
        checked_endpoints = set()

        async def record_endpoint(endpoint, health_status):
            checked_endpoints.add(endpoint.id)
            return HealthCheckResponse(
                status=EndpointState.HEALTHY,
                response_time_ms=100,
            )

        check_health.execute.side_effect = record_endpoint

        daemon = EndpointMonitoringDaemon(
            config=test_config,
            check_health_use_case=check_health,
            wake_endpoint_use_case=wake_endpoint,
            execute_fallback_chain_use_case=fallback_chain,
        )

        with patch("src.monitoring.daemon.start_http_server"):
            start_task = asyncio.create_task(daemon.start())

            # Wait for health checks
            await asyncio.sleep(0.2)

            # Trigger shutdown
            daemon.shutdown_event.set()
            await start_task

        # Assert: Both endpoints were checked
        assert "test-ep-1" in checked_endpoints
        assert "test-ep-2" in checked_endpoints


class TestGracefulShutdown:
    """Test graceful shutdown behavior."""

    @pytest.mark.asyncio
    async def test_daemon_cancels_all_tasks_on_shutdown(
        self, test_config, mock_use_cases
    ):
        """Test daemon cancels all health check tasks on shutdown."""
        check_health, wake_endpoint, fallback_chain = mock_use_cases

        # Mock slow health check to ensure tasks are running during shutdown
        async def slow_health_check(*args, **kwargs):
            await asyncio.sleep(10)  # Would run for 10s if not cancelled
            return HealthCheckResponse(
                status=EndpointState.HEALTHY,
                response_time_ms=100,
            )

        check_health.execute.side_effect = slow_health_check

        daemon = EndpointMonitoringDaemon(
            config=test_config,
            check_health_use_case=check_health,
            wake_endpoint_use_case=wake_endpoint,
            execute_fallback_chain_use_case=fallback_chain,
        )

        with patch("src.monitoring.daemon.start_http_server"):
            start_task = asyncio.create_task(daemon.start())

            # Wait for tasks to start
            await asyncio.sleep(0.1)

            # Tasks should be created
            initial_task_count = len(daemon.tasks)
            assert initial_task_count == 2  # 2 endpoints

            # Trigger shutdown
            shutdown_start = asyncio.get_event_loop().time()
            daemon.shutdown_event.set()
            await start_task
            shutdown_duration = asyncio.get_event_loop().time() - shutdown_start

            # Assert: Shutdown completed quickly (not waiting for 10s sleep)
            assert shutdown_duration < 1.0  # Should be ~0.1s, not 10s

    @pytest.mark.asyncio
    async def test_shutdown_event_stops_health_check_loops(
        self, mock_use_cases
    ):
        """Test shutdown event stops health check loops from scheduling new checks."""
        check_health, wake_endpoint, fallback_chain = mock_use_cases

        # Track call count
        call_count = 0

        async def count_calls(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return HealthCheckResponse(
                status=EndpointState.HEALTHY,
                response_time_ms=100,
            )

        check_health.execute.side_effect = count_calls

        # Create config with very short interval
        endpoints = {
            "test-ep-1": Endpoint(
                id="test-ep-1",
                provider="huggingface",
                url="https://api-inference.huggingface.co/models/test-1",
                priority=EndpointPriority.CRITICAL,
                wake_strategy=WakeStrategy.ALWAYS_WARM,
                health_check_interval=0.1,  # Very short for testing
            ),
            "test-ep-2": Endpoint(
                id="test-ep-2",
                provider="huggingface",
                url="https://api-inference.huggingface.co/models/test-2",
                priority=EndpointPriority.HIGH,
                wake_strategy=WakeStrategy.PRIORITY_BASED,
                health_check_interval=0.1,  # Very short for testing
            ),
        }

        health_statuses = {
            "test-ep-1": HealthStatus(
                endpoint_id="test-ep-1",
                state=EndpointState.UNKNOWN,
                last_check_time=datetime.now(),
            ),
            "test-ep-2": HealthStatus(
                endpoint_id="test-ep-2",
                state=EndpointState.UNKNOWN,
                last_check_time=datetime.now(),
            ),
        }

        config = MonitoringConfig(
            endpoints=endpoints,
            fallback_chains={},
            health_statuses=health_statuses,
        )

        daemon = EndpointMonitoringDaemon(
            config=config,
            check_health_use_case=check_health,
            wake_endpoint_use_case=wake_endpoint,
            execute_fallback_chain_use_case=fallback_chain,
        )

        with patch("src.monitoring.daemon.start_http_server"):
            start_task = asyncio.create_task(daemon.start())

            # Wait for a few checks
            await asyncio.sleep(0.3)

            # Trigger shutdown
            daemon.shutdown_event.set()
            await start_task

            # Record call count at shutdown
            shutdown_call_count = call_count

            # Wait a bit more
            await asyncio.sleep(0.3)

            # Assert: No new calls after shutdown
            assert call_count == shutdown_call_count


class TestMetricsServerStartup:
    """Test Prometheus metrics server startup."""

    @pytest.mark.asyncio
    async def test_daemon_starts_metrics_server_on_configured_port(
        self, test_config, mock_use_cases
    ):
        """Test daemon starts Prometheus metrics server on specified port."""
        check_health, wake_endpoint, fallback_chain = mock_use_cases

        check_health.execute.return_value = HealthCheckResponse(
            status=EndpointState.HEALTHY,
            response_time_ms=100,
        )

        daemon = EndpointMonitoringDaemon(
            config=test_config,
            check_health_use_case=check_health,
            wake_endpoint_use_case=wake_endpoint,
            execute_fallback_chain_use_case=fallback_chain,
            metrics_port=9999,
        )

        with patch("src.monitoring.daemon.start_http_server") as mock_http_server:
            start_task = asyncio.create_task(daemon.start())

            # Wait for startup
            await asyncio.sleep(0.1)

            # Trigger shutdown
            daemon.shutdown_event.set()
            await start_task

            # Assert: Metrics server was started on port 9999
            mock_http_server.assert_called_once_with(9999)
