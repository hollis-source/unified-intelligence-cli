"""Unit tests for CheckEndpointHealth use case."""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

from src.monitoring.entities import (
    Endpoint,
    EndpointPriority,
    WakeStrategy,
    HealthCheckResponse,
    HealthStatus,
    EndpointState,
    HealthCheckErrorCode,
)
from src.monitoring.use_cases import CheckEndpointHealth


@pytest.fixture
def mock_health_checker():
    """Create mock health checker."""
    return AsyncMock()


@pytest.fixture
def mock_metrics_exporter():
    """Create mock metrics exporter."""
    return AsyncMock()


@pytest.fixture
def test_endpoint():
    """Create test endpoint."""
    return Endpoint(
        id="test-endpoint",
        provider="huggingface",
        url="https://api.example.com",
        priority=EndpointPriority.HIGH,
        wake_strategy=WakeStrategy.PRIORITY_BASED,
    )


@pytest.fixture
def health_status(test_endpoint):
    """Create health status."""
    return HealthStatus(
        endpoint_id=test_endpoint.id,
        state=EndpointState.UNKNOWN,
        last_check_time=datetime.now(),
    )


@pytest.fixture
def use_case(mock_health_checker, mock_metrics_exporter):
    """Create CheckEndpointHealth use case."""
    return CheckEndpointHealth(mock_health_checker, mock_metrics_exporter)


class TestCheckEndpointHealthSuccess:
    """Tests for successful health checks."""

    @pytest.mark.asyncio
    async def test_successful_health_check_updates_status(
        self, use_case, test_endpoint, health_status, mock_health_checker
    ):
        """Test successful health check updates health status to HEALTHY."""
        # Arrange
        response = HealthCheckResponse(
            status=EndpointState.HEALTHY,
            response_time_ms=150.0,
        )
        mock_health_checker.check.return_value = response

        # Act
        result = await use_case.execute(test_endpoint, health_status)

        # Assert
        assert result.status == EndpointState.HEALTHY
        assert result.response_time_ms == 150.0
        assert health_status.state == EndpointState.HEALTHY
        assert health_status.response_time_ms == 150.0
        assert health_status.consecutive_failures == 0
        assert health_status.error_message is None

    @pytest.mark.asyncio
    async def test_successful_check_resets_failure_counter(
        self, use_case, test_endpoint, health_status, mock_health_checker
    ):
        """Test successful check resets consecutive failures counter."""
        # Arrange
        health_status.consecutive_failures = 5  # Previous failures
        response = HealthCheckResponse(
            status=EndpointState.HEALTHY,
            response_time_ms=200.0,
        )
        mock_health_checker.check.return_value = response

        # Act
        result = await use_case.execute(test_endpoint, health_status)

        # Assert
        assert result.status == EndpointState.HEALTHY
        assert health_status.consecutive_failures == 0

    @pytest.mark.asyncio
    async def test_degraded_status_is_operational(
        self, use_case, test_endpoint, health_status, mock_health_checker
    ):
        """Test DEGRADED status is considered operational (resets failures)."""
        # Arrange
        health_status.consecutive_failures = 3
        response = HealthCheckResponse(
            status=EndpointState.DEGRADED,
            response_time_ms=5000.0,
        )
        mock_health_checker.check.return_value = response

        # Act
        result = await use_case.execute(test_endpoint, health_status)

        # Assert
        assert result.status == EndpointState.DEGRADED
        assert health_status.state == EndpointState.DEGRADED
        assert health_status.consecutive_failures == 0  # Reset on operational state


class TestCheckEndpointHealthFailure:
    """Tests for failed health checks."""

    @pytest.mark.asyncio
    async def test_failed_check_increments_consecutive_failures(
        self, use_case, test_endpoint, health_status, mock_health_checker
    ):
        """Test failed health check increments consecutive failures."""
        # Arrange
        response = HealthCheckResponse(
            status=EndpointState.FAILED,
            error_code=HealthCheckErrorCode.TIMEOUT,
        )
        mock_health_checker.check.return_value = response

        # Act
        result = await use_case.execute(test_endpoint, health_status)

        # Assert
        assert result.status == EndpointState.FAILED
        assert health_status.state == EndpointState.FAILED
        assert health_status.consecutive_failures == 1

    @pytest.mark.asyncio
    async def test_multiple_failures_increment_counter(
        self, use_case, test_endpoint, health_status, mock_health_checker
    ):
        """Test multiple consecutive failures increment counter."""
        # Arrange
        response = HealthCheckResponse(
            status=EndpointState.FAILED,
            error_code=HealthCheckErrorCode.NETWORK_ERROR,
        )
        mock_health_checker.check.return_value = response

        # Act - Execute 3 times
        await use_case.execute(test_endpoint, health_status)
        await use_case.execute(test_endpoint, health_status)
        await use_case.execute(test_endpoint, health_status)

        # Assert
        assert health_status.consecutive_failures == 3

    @pytest.mark.asyncio
    async def test_sleeping_status_increments_failures(
        self, use_case, test_endpoint, health_status, mock_health_checker
    ):
        """Test SLEEPING status increments failures (not operational)."""
        # Arrange
        response = HealthCheckResponse(
            status=EndpointState.SLEEPING,
            error_code=HealthCheckErrorCode.MODEL_LOADING,
        )
        mock_health_checker.check.return_value = response

        # Act
        result = await use_case.execute(test_endpoint, health_status)

        # Assert
        assert result.status == EndpointState.SLEEPING
        assert health_status.consecutive_failures == 1


class TestCheckEndpointHealthMetrics:
    """Tests for metrics recording."""

    @pytest.mark.asyncio
    async def test_metrics_recorded_on_success(
        self, use_case, test_endpoint, health_status, mock_health_checker, mock_metrics_exporter
    ):
        """Test metrics are recorded for successful health check."""
        # Arrange
        response = HealthCheckResponse(
            status=EndpointState.HEALTHY,
            response_time_ms=100.0,
        )
        mock_health_checker.check.return_value = response

        # Act
        await use_case.execute(test_endpoint, health_status)

        # Assert
        mock_metrics_exporter.record_health_check.assert_called_once_with(
            test_endpoint, health_status
        )

    @pytest.mark.asyncio
    async def test_metrics_recorded_on_failure(
        self, use_case, test_endpoint, health_status, mock_health_checker, mock_metrics_exporter
    ):
        """Test metrics are recorded for failed health check."""
        # Arrange
        response = HealthCheckResponse(
            status=EndpointState.FAILED,
            error_code=HealthCheckErrorCode.TIMEOUT,
        )
        mock_health_checker.check.return_value = response

        # Act
        await use_case.execute(test_endpoint, health_status)

        # Assert
        mock_metrics_exporter.record_health_check.assert_called_once_with(
            test_endpoint, health_status
        )

    @pytest.mark.asyncio
    async def test_metrics_exporter_called_with_correct_args(
        self, use_case, test_endpoint, health_status, mock_health_checker, mock_metrics_exporter
    ):
        """Test metrics exporter is called with correct arguments."""
        # Arrange
        response = HealthCheckResponse(
            status=EndpointState.HEALTHY,
            response_time_ms=100.0,
        )
        mock_health_checker.check.return_value = response

        # Act
        result = await use_case.execute(test_endpoint, health_status)

        # Assert
        mock_metrics_exporter.record_health_check.assert_called_once()
        call_args = mock_metrics_exporter.record_health_check.call_args
        assert call_args[0][0] == test_endpoint
        assert call_args[0][1] == health_status


class TestCheckEndpointHealthContract:
    """Tests for use case contract compliance."""

    @pytest.mark.asyncio
    async def test_always_returns_health_check_response(
        self, use_case, test_endpoint, health_status, mock_health_checker
    ):
        """Test use case always returns HealthCheckResponse (never None)."""
        # Arrange
        response = HealthCheckResponse(
            status=EndpointState.HEALTHY,
            response_time_ms=100.0,
        )
        mock_health_checker.check.return_value = response

        # Act
        result = await use_case.execute(test_endpoint, health_status)

        # Assert
        assert result is not None
        assert isinstance(result, HealthCheckResponse)

    @pytest.mark.asyncio
    async def test_always_updates_health_status(
        self, use_case, test_endpoint, health_status, mock_health_checker
    ):
        """Test use case always updates health status."""
        # Arrange
        initial_check_time = health_status.last_check_time
        response = HealthCheckResponse(
            status=EndpointState.HEALTHY,
            response_time_ms=100.0,
        )
        mock_health_checker.check.return_value = response

        # Act
        await use_case.execute(test_endpoint, health_status)

        # Assert
        assert health_status.last_check_time > initial_check_time
        assert health_status.state == response.status

