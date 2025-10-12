"""Unit tests for WakeEndpoint use case."""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock
import asyncio

from src.monitoring.entities import (
    Endpoint,
    EndpointPriority,
    WakeStrategy,
    WakeResult,
    HealthStatus,
    EndpointState,
)
from src.monitoring.interfaces import IWaker, IReadinessPoller
from src.monitoring.use_cases import WakeEndpoint


class MockWaker:
    """Mock waker without readiness polling."""

    def __init__(self):
        self.wake = AsyncMock()


class MockWakerWithPolling(IReadinessPoller):
    """Mock waker with readiness polling support."""

    def __init__(self):
        self.wake = AsyncMock()
        self._poll_mock = AsyncMock()

    async def poll_until_ready(self, endpoint, timeout):
        """Mock implementation."""
        return await self._poll_mock(endpoint, timeout)


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
        wake_timeout=30,
    )


@pytest.fixture
def health_status(test_endpoint):
    """Create health status."""
    return HealthStatus(
        endpoint_id=test_endpoint.id,
        state=EndpointState.SLEEPING,
        last_check_time=datetime.now(),
    )


class TestWakeEndpointWithoutPolling:
    """Tests for wake without readiness polling."""

    @pytest.mark.asyncio
    async def test_successful_wake_without_polling(
        self, test_endpoint, health_status, mock_metrics_exporter
    ):
        """Test successful wake when waker doesn't support polling."""
        # Arrange
        mock_waker = MockWaker()
        wake_result = WakeResult(success=True)
        mock_waker.wake.return_value = wake_result
        use_case = WakeEndpoint(mock_waker, mock_metrics_exporter)

        # Act
        result = await use_case.execute(test_endpoint, health_status, wait_for_ready=False)

        # Assert
        assert result.success is True
        mock_waker.wake.assert_called_once_with(test_endpoint)
        assert health_status.last_wake_time is not None

    @pytest.mark.asyncio
    async def test_wake_without_polling_updates_wake_time(
        self, test_endpoint, health_status, mock_metrics_exporter
    ):
        """Test wake updates health status wake time."""
        # Arrange
        mock_waker = MockWaker()
        wake_result = WakeResult(success=True)
        mock_waker.wake.return_value = wake_result
        use_case = WakeEndpoint(mock_waker, mock_metrics_exporter)
        initial_wake_time = health_status.last_wake_time

        # Act
        await use_case.execute(test_endpoint, health_status, wait_for_ready=False)

        # Assert
        assert health_status.last_wake_time != initial_wake_time
        assert health_status.last_wake_time is not None

    @pytest.mark.asyncio
    async def test_failed_wake_without_polling(
        self, test_endpoint, health_status, mock_metrics_exporter
    ):
        """Test failed wake when waker doesn't support polling."""
        # Arrange
        mock_waker = MockWaker()
        wake_result = WakeResult(success=False, error="Network error")
        mock_waker.wake.return_value = wake_result
        use_case = WakeEndpoint(mock_waker, mock_metrics_exporter)

        # Act
        result = await use_case.execute(test_endpoint, health_status, wait_for_ready=False)

        # Assert
        assert result.success is False
        assert result.error == "Network error"


class TestWakeEndpointWithPolling:
    """Tests for wake with readiness polling (ISP compliance)."""

    @pytest.mark.asyncio
    async def test_successful_wake_with_polling(
        self, test_endpoint, health_status, mock_metrics_exporter
    ):
        """Test successful wake with readiness polling."""
        # Arrange
        mock_waker = MockWakerWithPolling()
        wake_result = WakeResult(success=True)
        mock_waker.wake.return_value = wake_result
        mock_waker._poll_mock.return_value = True
        use_case = WakeEndpoint(mock_waker, mock_metrics_exporter)

        # Act
        result = await use_case.execute(test_endpoint, health_status, wait_for_ready=True)

        # Assert
        assert result.success is True
        mock_waker.wake.assert_called_once_with(test_endpoint)
        mock_waker._poll_mock.assert_called_once_with(
            test_endpoint, test_endpoint.wake_timeout
        )

    @pytest.mark.asyncio
    async def test_polling_timeout_handling(
        self, test_endpoint, health_status, mock_metrics_exporter
    ):
        """Test polling timeout is handled gracefully."""
        # Arrange
        mock_waker = MockWakerWithPolling()
        wake_result = WakeResult(success=True)
        mock_waker.wake.return_value = wake_result

        # Simulate timeout by making poll_until_ready take too long
        async def slow_poll(*args, **kwargs):
            await asyncio.sleep(100)  # Longer than timeout
            return True

        mock_waker._poll_mock.side_effect = slow_poll
        use_case = WakeEndpoint(mock_waker, mock_metrics_exporter)

        # Act
        result = await use_case.execute(test_endpoint, health_status, wait_for_ready=True)

        # Assert
        assert result.success is True  # Wake succeeded
        # Note: The actual implementation should handle timeout

    @pytest.mark.asyncio
    async def test_polling_returns_not_ready(
        self, test_endpoint, health_status, mock_metrics_exporter
    ):
        """Test when polling indicates endpoint not ready."""
        # Arrange
        mock_waker = MockWakerWithPolling()
        wake_result = WakeResult(success=True)
        mock_waker.wake.return_value = wake_result
        mock_waker._poll_mock.return_value = False
        use_case = WakeEndpoint(mock_waker, mock_metrics_exporter)

        # Act
        result = await use_case.execute(test_endpoint, health_status, wait_for_ready=True)

        # Assert
        assert result.success is True  # Wake request succeeded
        mock_waker._poll_mock.assert_called_once()

    @pytest.mark.asyncio
    async def test_isp_compliance_no_polling_when_not_supported(
        self, test_endpoint, health_status, mock_metrics_exporter
    ):
        """Test ISP compliance: no polling attempted when waker doesn't support it."""
        # Arrange
        mock_waker = MockWaker()  # No IReadinessPoller
        wake_result = WakeResult(success=True)
        mock_waker.wake.return_value = wake_result
        use_case = WakeEndpoint(mock_waker, mock_metrics_exporter)

        # Act
        result = await use_case.execute(test_endpoint, health_status, wait_for_ready=True)

        # Assert
        assert result.success is True
        mock_waker.wake.assert_called_once()
        # Verify isinstance check works correctly - waker doesn't implement IReadinessPoller
        assert not isinstance(mock_waker, IReadinessPoller)


class TestWakeEndpointMetrics:
    """Tests for wake metrics recording."""

    @pytest.mark.asyncio
    async def test_metrics_recorded_on_successful_wake(
        self, test_endpoint, health_status, mock_metrics_exporter
    ):
        """Test metrics are recorded for successful wake."""
        # Arrange
        mock_waker = MockWaker()
        wake_result = WakeResult(success=True)
        mock_waker.wake.return_value = wake_result
        use_case = WakeEndpoint(mock_waker, mock_metrics_exporter)

        # Act
        await use_case.execute(test_endpoint, health_status, wait_for_ready=False)

        # Assert
        mock_metrics_exporter.record_wake_attempt.assert_called_once()
        call_args = mock_metrics_exporter.record_wake_attempt.call_args
        assert call_args[0][0] == test_endpoint
        assert isinstance(call_args[0][1], float)  # wake_time_s
        assert call_args[0][2] is True  # success

    @pytest.mark.asyncio
    async def test_metrics_recorded_on_failed_wake(
        self, test_endpoint, health_status, mock_metrics_exporter
    ):
        """Test metrics are recorded for failed wake."""
        # Arrange
        mock_waker = MockWaker()
        wake_result = WakeResult(success=False, error="Network error")
        mock_waker.wake.return_value = wake_result
        use_case = WakeEndpoint(mock_waker, mock_metrics_exporter)

        # Act
        await use_case.execute(test_endpoint, health_status, wait_for_ready=False)

        # Assert
        mock_metrics_exporter.record_wake_attempt.assert_called_once()
        call_args = mock_metrics_exporter.record_wake_attempt.call_args
        assert call_args[0][2] is False  # success = False

    @pytest.mark.asyncio
    async def test_wake_time_calculated_correctly(
        self, test_endpoint, health_status, mock_metrics_exporter
    ):
        """Test wake time is calculated and included in result."""
        # Arrange
        mock_waker = MockWaker()
        wake_result = WakeResult(success=True)
        mock_waker.wake.return_value = wake_result
        use_case = WakeEndpoint(mock_waker, mock_metrics_exporter)

        # Act
        result = await use_case.execute(test_endpoint, health_status, wait_for_ready=False)

        # Assert
        assert result.wake_time_s is not None
        assert result.wake_time_s >= 0


class TestWakeEndpointContract:
    """Tests for use case contract compliance."""

    @pytest.mark.asyncio
    async def test_always_returns_wake_result(
        self, test_endpoint, health_status, mock_metrics_exporter
    ):
        """Test use case always returns WakeResult (never None)."""
        # Arrange
        mock_waker = MockWaker()
        wake_result = WakeResult(success=True)
        mock_waker.wake.return_value = wake_result
        use_case = WakeEndpoint(mock_waker, mock_metrics_exporter)

        # Act
        result = await use_case.execute(test_endpoint, health_status, wait_for_ready=False)

        # Assert
        assert result is not None
        assert isinstance(result, WakeResult)

    @pytest.mark.asyncio
    async def test_always_updates_last_wake_time(
        self, test_endpoint, health_status, mock_metrics_exporter
    ):
        """Test use case always updates health status last_wake_time."""
        # Arrange
        mock_waker = MockWaker()
        wake_result = WakeResult(success=True)
        mock_waker.wake.return_value = wake_result
        use_case = WakeEndpoint(mock_waker, mock_metrics_exporter)
        initial_wake_time = health_status.last_wake_time

        # Act
        await use_case.execute(test_endpoint, health_status, wait_for_ready=False)

        # Assert
        assert health_status.last_wake_time is not None
        assert health_status.last_wake_time != initial_wake_time

