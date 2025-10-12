"""Unit tests for PrometheusMetricsAdapter."""

import pytest
from datetime import datetime
import asyncio

from src.monitoring.entities import (
    Endpoint,
    EndpointPriority,
    WakeStrategy,
    HealthStatus,
    EndpointState,
)
from src.monitoring.adapters import PrometheusMetricsAdapter


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
        state=EndpointState.HEALTHY,
        last_check_time=datetime.now(),
        response_time_ms=150.0,
        consecutive_failures=0,
    )


@pytest.fixture
def adapter():
    """Create PrometheusMetricsAdapter."""
    return PrometheusMetricsAdapter()


class TestRecordHealthCheck:
    """Tests for record_health_check method."""

    @pytest.mark.asyncio
    async def test_record_health_check_does_not_raise(
        self, adapter, test_endpoint, health_status
    ):
        """Test record_health_check doesn't raise exceptions (contract)."""
        # Act - Should not raise
        await adapter.record_health_check(test_endpoint, health_status)

        # Assert - No exception raised
        assert True

    @pytest.mark.asyncio
    async def test_record_health_check_with_healthy_status(
        self, adapter, test_endpoint, health_status
    ):
        """Test recording healthy status."""
        health_status.state = EndpointState.HEALTHY
        health_status.response_time_ms = 100.0

        # Act
        await adapter.record_health_check(test_endpoint, health_status)

        # Assert - Verify metrics were set (check internal state)
        # Note: Prometheus metrics are global, so we can't easily verify values
        # But we can verify no exception was raised
        assert True

    @pytest.mark.asyncio
    async def test_record_health_check_with_failed_status(
        self, adapter, test_endpoint, health_status
    ):
        """Test recording failed status."""
        health_status.state = EndpointState.FAILED
        health_status.consecutive_failures = 3
        health_status.response_time_ms = None

        # Act
        await adapter.record_health_check(test_endpoint, health_status)

        # Assert
        assert True

    @pytest.mark.asyncio
    async def test_record_health_check_completes_quickly(
        self, adapter, test_endpoint, health_status
    ):
        """Test record_health_check completes quickly (< 1s per contract)."""
        # Act
        start_time = asyncio.get_event_loop().time()
        await adapter.record_health_check(test_endpoint, health_status)
        elapsed = asyncio.get_event_loop().time() - start_time

        # Assert
        assert elapsed < 1.0


class TestRecordWakeAttempt:
    """Tests for record_wake_attempt method."""

    @pytest.mark.asyncio
    async def test_record_wake_attempt_does_not_raise(self, adapter, test_endpoint):
        """Test record_wake_attempt doesn't raise exceptions (contract)."""
        # Act - Should not raise
        await adapter.record_wake_attempt(test_endpoint, wake_time_s=5.0, success=True)

        # Assert
        assert True

    @pytest.mark.asyncio
    async def test_record_successful_wake(self, adapter, test_endpoint):
        """Test recording successful wake attempt."""
        # Act
        await adapter.record_wake_attempt(test_endpoint, wake_time_s=3.5, success=True)

        # Assert
        assert True

    @pytest.mark.asyncio
    async def test_record_failed_wake(self, adapter, test_endpoint):
        """Test recording failed wake attempt."""
        # Act
        await adapter.record_wake_attempt(test_endpoint, wake_time_s=10.0, success=False)

        # Assert
        assert True

    @pytest.mark.asyncio
    async def test_record_wake_attempt_completes_quickly(self, adapter, test_endpoint):
        """Test record_wake_attempt completes quickly (< 1s per contract)."""
        # Act
        start_time = asyncio.get_event_loop().time()
        await adapter.record_wake_attempt(test_endpoint, wake_time_s=5.0, success=True)
        elapsed = asyncio.get_event_loop().time() - start_time

        # Assert
        assert elapsed < 1.0


class TestRecordFallback:
    """Tests for record_fallback method."""

    @pytest.mark.asyncio
    async def test_record_fallback_does_not_raise(self, adapter):
        """Test record_fallback doesn't raise exceptions (contract)."""
        # Act - Should not raise
        await adapter.record_fallback(
            primary_endpoint_id="primary",
            fallback_endpoint_id="secondary",
            fallback_count=1,
        )

        # Assert
        assert True

    @pytest.mark.asyncio
    async def test_record_first_fallback(self, adapter):
        """Test recording first fallback (to secondary)."""
        # Act
        await adapter.record_fallback(
            primary_endpoint_id="primary",
            fallback_endpoint_id="secondary",
            fallback_count=1,
        )

        # Assert
        assert True

    @pytest.mark.asyncio
    async def test_record_second_fallback(self, adapter):
        """Test recording second fallback (to tertiary)."""
        # Act
        await adapter.record_fallback(
            primary_endpoint_id="primary",
            fallback_endpoint_id="tertiary",
            fallback_count=2,
        )

        # Assert
        assert True

    @pytest.mark.asyncio
    async def test_record_fallback_completes_quickly(self, adapter):
        """Test record_fallback completes quickly (< 1s per contract)."""
        # Act
        start_time = asyncio.get_event_loop().time()
        await adapter.record_fallback(
            primary_endpoint_id="primary",
            fallback_endpoint_id="secondary",
            fallback_count=1,
        )
        elapsed = asyncio.get_event_loop().time() - start_time

        # Assert
        assert elapsed < 1.0


class TestStateToNumeric:
    """Tests for _state_to_numeric mapping."""

    def test_unknown_maps_to_zero(self, adapter):
        """Test UNKNOWN state maps to 0."""
        result = adapter._state_to_numeric(EndpointState.UNKNOWN)
        assert result == 0

    def test_healthy_maps_to_one(self, adapter):
        """Test HEALTHY state maps to 1."""
        result = adapter._state_to_numeric(EndpointState.HEALTHY)
        assert result == 1

    def test_degraded_maps_to_two(self, adapter):
        """Test DEGRADED state maps to 2."""
        result = adapter._state_to_numeric(EndpointState.DEGRADED)
        assert result == 2

    def test_sleeping_maps_to_three(self, adapter):
        """Test SLEEPING state maps to 3."""
        result = adapter._state_to_numeric(EndpointState.SLEEPING)
        assert result == 3

    def test_failed_maps_to_four(self, adapter):
        """Test FAILED state maps to 4."""
        result = adapter._state_to_numeric(EndpointState.FAILED)
        assert result == 4


class TestContractCompliance:
    """Tests for IMetricsExporter contract compliance."""

    @pytest.mark.asyncio
    async def test_all_methods_never_raise_exceptions(
        self, adapter, test_endpoint, health_status
    ):
        """Test all methods never raise exceptions (contract requirement)."""
        # Act - None of these should raise
        await adapter.record_health_check(test_endpoint, health_status)
        await adapter.record_wake_attempt(test_endpoint, 5.0, True)
        await adapter.record_fallback("primary", "secondary", 1)
        await adapter.increment_consecutive_failures(test_endpoint, 3)

        # Assert
        assert True

    @pytest.mark.asyncio
    async def test_methods_complete_quickly(
        self, adapter, test_endpoint, health_status
    ):
        """Test all methods complete quickly (< 1s per contract)."""
        # Act
        start_time = asyncio.get_event_loop().time()
        
        await adapter.record_health_check(test_endpoint, health_status)
        await adapter.record_wake_attempt(test_endpoint, 5.0, True)
        await adapter.record_fallback("primary", "secondary", 1)
        await adapter.increment_consecutive_failures(test_endpoint, 3)
        
        elapsed = asyncio.get_event_loop().time() - start_time

        # Assert - All 4 operations should complete in < 1s total
        assert elapsed < 1.0

    @pytest.mark.asyncio
    async def test_handles_none_response_time(
        self, adapter, test_endpoint, health_status
    ):
        """Test handles None response_time_ms gracefully."""
        health_status.response_time_ms = None

        # Act - Should not raise
        await adapter.record_health_check(test_endpoint, health_status)

        # Assert
        assert True


class TestIncrementConsecutiveFailures:
    """Tests for increment_consecutive_failures method."""

    @pytest.mark.asyncio
    async def test_increment_consecutive_failures_does_not_raise(
        self, adapter, test_endpoint
    ):
        """Test increment_consecutive_failures doesn't raise exceptions."""
        # Act - Should not raise
        await adapter.increment_consecutive_failures(test_endpoint, failure_count=5)

        # Assert
        assert True

    @pytest.mark.asyncio
    async def test_increment_with_zero_failures(self, adapter, test_endpoint):
        """Test incrementing with zero failures."""
        # Act
        await adapter.increment_consecutive_failures(test_endpoint, failure_count=0)

        # Assert
        assert True

    @pytest.mark.asyncio
    async def test_increment_with_high_failure_count(self, adapter, test_endpoint):
        """Test incrementing with high failure count."""
        # Act
        await adapter.increment_consecutive_failures(test_endpoint, failure_count=100)

        # Assert
        assert True

