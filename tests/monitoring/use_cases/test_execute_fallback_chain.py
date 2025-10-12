"""Unit tests for ExecuteFallbackChain use case."""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock
from typing import Dict

from src.monitoring.entities import (
    Endpoint,
    EndpointPriority,
    WakeStrategy,
    FallbackChain,
    FallbackResult,
    HealthCheckResponse,
    HealthStatus,
    EndpointState,
    HealthCheckErrorCode,
)
from src.monitoring.use_cases import ExecuteFallbackChain, CheckEndpointHealth


@pytest.fixture
def mock_check_health():
    """Create mock CheckEndpointHealth use case."""
    return AsyncMock()


@pytest.fixture
def mock_metrics_exporter():
    """Create mock metrics exporter."""
    return AsyncMock()


@pytest.fixture
def primary_endpoint():
    """Create primary endpoint."""
    return Endpoint(
        id="primary",
        provider="huggingface",
        url="https://primary.example.com",
        priority=EndpointPriority.CRITICAL,
        wake_strategy=WakeStrategy.ALWAYS_WARM,
    )


@pytest.fixture
def secondary_endpoint():
    """Create secondary endpoint."""
    return Endpoint(
        id="secondary",
        provider="huggingface",
        url="https://secondary.example.com",
        priority=EndpointPriority.HIGH,
        wake_strategy=WakeStrategy.PRIORITY_BASED,
    )


@pytest.fixture
def tertiary_endpoint():
    """Create tertiary endpoint."""
    return Endpoint(
        id="tertiary",
        provider="replicate",
        url="https://tertiary.example.com",
        priority=EndpointPriority.MEDIUM,
        wake_strategy=WakeStrategy.REACTIVE,
    )


@pytest.fixture
def endpoints(primary_endpoint, secondary_endpoint, tertiary_endpoint):
    """Create endpoints dictionary."""
    return {
        "primary": primary_endpoint,
        "secondary": secondary_endpoint,
        "tertiary": tertiary_endpoint,
    }


@pytest.fixture
def health_statuses():
    """Create health statuses dictionary."""
    return {
        "primary": HealthStatus(
            endpoint_id="primary",
            state=EndpointState.UNKNOWN,
            last_check_time=datetime.now(),
        ),
        "secondary": HealthStatus(
            endpoint_id="secondary",
            state=EndpointState.UNKNOWN,
            last_check_time=datetime.now(),
        ),
        "tertiary": HealthStatus(
            endpoint_id="tertiary",
            state=EndpointState.UNKNOWN,
            last_check_time=datetime.now(),
        ),
    }


@pytest.fixture
def fallback_chain():
    """Create fallback chain."""
    return FallbackChain(
        name="test-chain",
        primary_endpoint_id="primary",
        secondary_endpoint_id="secondary",
        tertiary_endpoint_id="tertiary",
    )


@pytest.fixture
def use_case(mock_check_health, mock_metrics_exporter):
    """Create ExecuteFallbackChain use case."""
    return ExecuteFallbackChain(mock_check_health, mock_metrics_exporter)


class TestPrimaryEndpointSuccess:
    """Tests for successful primary endpoint (no fallback)."""

    @pytest.mark.asyncio
    async def test_primary_succeeds_no_fallback(
        self, use_case, fallback_chain, endpoints, health_statuses, mock_check_health
    ):
        """Test primary endpoint succeeds, no fallback needed."""
        # Arrange
        response = HealthCheckResponse(
            status=EndpointState.HEALTHY,
            response_time_ms=100.0,
        )
        mock_check_health.execute.return_value = response

        # Act
        result = await use_case.execute(fallback_chain, endpoints, health_statuses)

        # Assert
        assert result.success is True
        # Note: The actual implementation uses different field names
        # We need to check what fields are actually returned
        mock_check_health.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_primary_success_no_fallback_metrics(
        self, use_case, fallback_chain, endpoints, health_statuses, 
        mock_check_health, mock_metrics_exporter
    ):
        """Test no fallback metrics recorded when primary succeeds."""
        # Arrange
        response = HealthCheckResponse(
            status=EndpointState.HEALTHY,
            response_time_ms=100.0,
        )
        mock_check_health.execute.return_value = response

        # Act
        result = await use_case.execute(fallback_chain, endpoints, health_statuses)

        # Assert
        assert result.success is True
        # No fallback metrics should be recorded
        mock_metrics_exporter.record_fallback.assert_not_called()


class TestFallbackToSecondary:
    """Tests for fallback to secondary endpoint."""

    @pytest.mark.asyncio
    async def test_fallback_to_secondary_after_primary_fails(
        self, use_case, fallback_chain, endpoints, health_statuses, mock_check_health
    ):
        """Test fallback to secondary when primary fails."""
        # Arrange
        primary_response = HealthCheckResponse(
            status=EndpointState.FAILED,
            error_code=HealthCheckErrorCode.TIMEOUT,
        )
        secondary_response = HealthCheckResponse(
            status=EndpointState.HEALTHY,
            response_time_ms=200.0,
        )
        mock_check_health.execute.side_effect = [primary_response, secondary_response]

        # Act
        result = await use_case.execute(fallback_chain, endpoints, health_statuses)

        # Assert
        assert result.success is True
        assert mock_check_health.execute.call_count == 2

    @pytest.mark.asyncio
    async def test_fallback_metrics_recorded_for_secondary(
        self, use_case, fallback_chain, endpoints, health_statuses,
        mock_check_health, mock_metrics_exporter
    ):
        """Test fallback metrics recorded when using secondary."""
        # Arrange
        primary_response = HealthCheckResponse(
            status=EndpointState.FAILED,
            error_code=HealthCheckErrorCode.NETWORK_ERROR,
        )
        secondary_response = HealthCheckResponse(
            status=EndpointState.HEALTHY,
            response_time_ms=150.0,
        )
        mock_check_health.execute.side_effect = [primary_response, secondary_response]

        # Act
        result = await use_case.execute(fallback_chain, endpoints, health_statuses)

        # Assert
        assert result.success is True
        mock_metrics_exporter.record_fallback.assert_called_once()
        call_args = mock_metrics_exporter.record_fallback.call_args[0]
        assert call_args[0] == "primary"  # primary_endpoint_id
        assert call_args[1] == "secondary"  # fallback_endpoint_id
        assert call_args[2] == 1  # fallback_count


class TestFallbackToTertiary:
    """Tests for fallback to tertiary endpoint."""

    @pytest.mark.asyncio
    async def test_fallback_to_tertiary_after_secondary_fails(
        self, use_case, fallback_chain, endpoints, health_statuses, mock_check_health
    ):
        """Test fallback to tertiary when both primary and secondary fail."""
        # Arrange
        primary_response = HealthCheckResponse(
            status=EndpointState.FAILED,
            error_code=HealthCheckErrorCode.TIMEOUT,
        )
        secondary_response = HealthCheckResponse(
            status=EndpointState.SLEEPING,
            error_code=HealthCheckErrorCode.MODEL_LOADING,
        )
        tertiary_response = HealthCheckResponse(
            status=EndpointState.HEALTHY,
            response_time_ms=300.0,
        )
        mock_check_health.execute.side_effect = [
            primary_response,
            secondary_response,
            tertiary_response,
        ]

        # Act
        result = await use_case.execute(fallback_chain, endpoints, health_statuses)

        # Assert
        assert result.success is True
        assert mock_check_health.execute.call_count == 3

    @pytest.mark.asyncio
    async def test_fallback_metrics_recorded_for_tertiary(
        self, use_case, fallback_chain, endpoints, health_statuses,
        mock_check_health, mock_metrics_exporter
    ):
        """Test fallback metrics recorded when using tertiary."""
        # Arrange
        primary_response = HealthCheckResponse(
            status=EndpointState.FAILED,
            error_code=HealthCheckErrorCode.AUTH_FAILED,
        )
        secondary_response = HealthCheckResponse(
            status=EndpointState.FAILED,
            error_code=HealthCheckErrorCode.RATE_LIMITED,
        )
        tertiary_response = HealthCheckResponse(
            status=EndpointState.HEALTHY,
            response_time_ms=250.0,
        )
        mock_check_health.execute.side_effect = [
            primary_response,
            secondary_response,
            tertiary_response,
        ]

        # Act
        result = await use_case.execute(fallback_chain, endpoints, health_statuses)

        # Assert
        assert result.success is True
        mock_metrics_exporter.record_fallback.assert_called_once()
        call_args = mock_metrics_exporter.record_fallback.call_args[0]
        assert call_args[0] == "primary"  # primary_endpoint_id
        assert call_args[1] == "tertiary"  # fallback_endpoint_id
        assert call_args[2] == 2  # fallback_count (2 fallbacks occurred)


class TestAllEndpointsFail:
    """Tests for scenario where all endpoints fail."""

    @pytest.mark.asyncio
    async def test_all_endpoints_fail(
        self, use_case, fallback_chain, endpoints, health_statuses, mock_check_health
    ):
        """Test all endpoints in chain fail."""
        # Arrange
        failed_response = HealthCheckResponse(
            status=EndpointState.FAILED,
            error_code=HealthCheckErrorCode.INTERNAL_ERROR,
        )
        mock_check_health.execute.return_value = failed_response

        # Act
        result = await use_case.execute(fallback_chain, endpoints, health_statuses)

        # Assert
        assert result.success is False
        assert mock_check_health.execute.call_count == 3  # All 3 endpoints tried

    @pytest.mark.asyncio
    async def test_all_fail_no_fallback_metrics(
        self, use_case, fallback_chain, endpoints, health_statuses,
        mock_check_health, mock_metrics_exporter
    ):
        """Test no fallback metrics recorded when all endpoints fail."""
        # Arrange
        failed_response = HealthCheckResponse(
            status=EndpointState.FAILED,
            error_code=HealthCheckErrorCode.NETWORK_ERROR,
        )
        mock_check_health.execute.return_value = failed_response

        # Act
        result = await use_case.execute(fallback_chain, endpoints, health_statuses)

        # Assert
        assert result.success is False
        # No successful fallback, so no metrics recorded
        mock_metrics_exporter.record_fallback.assert_not_called()


class TestFallbackChainContract:
    """Tests for use case contract compliance."""

    @pytest.mark.asyncio
    async def test_always_returns_fallback_result(
        self, use_case, fallback_chain, endpoints, health_statuses, mock_check_health
    ):
        """Test use case always returns FallbackResult (never None)."""
        # Arrange
        response = HealthCheckResponse(
            status=EndpointState.HEALTHY,
            response_time_ms=100.0,
        )
        mock_check_health.execute.return_value = response

        # Act
        result = await use_case.execute(fallback_chain, endpoints, health_statuses)

        # Assert
        assert result is not None
        assert isinstance(result, FallbackResult)

    @pytest.mark.asyncio
    async def test_tries_endpoints_in_order(
        self, use_case, fallback_chain, endpoints, health_statuses, mock_check_health
    ):
        """Test endpoints are tried in correct order: primary → secondary → tertiary."""
        # Arrange
        failed_response = HealthCheckResponse(
            status=EndpointState.FAILED,
            error_code=HealthCheckErrorCode.TIMEOUT,
        )
        mock_check_health.execute.return_value = failed_response

        # Act
        await use_case.execute(fallback_chain, endpoints, health_statuses)

        # Assert
        assert mock_check_health.execute.call_count == 3
        # Check order of calls
        calls = mock_check_health.execute.call_args_list
        assert calls[0][0][0].id == "primary"
        assert calls[1][0][0].id == "secondary"
        assert calls[2][0][0].id == "tertiary"

    @pytest.mark.asyncio
    async def test_stops_on_first_success(
        self, use_case, fallback_chain, endpoints, health_statuses, mock_check_health
    ):
        """Test execution stops on first successful endpoint."""
        # Arrange
        primary_response = HealthCheckResponse(
            status=EndpointState.FAILED,
            error_code=HealthCheckErrorCode.TIMEOUT,
        )
        secondary_response = HealthCheckResponse(
            status=EndpointState.HEALTHY,
            response_time_ms=150.0,
        )
        mock_check_health.execute.side_effect = [primary_response, secondary_response]

        # Act
        result = await use_case.execute(fallback_chain, endpoints, health_statuses)

        # Assert
        assert result.success is True
        # Should only call 2 times (primary + secondary), not tertiary
        assert mock_check_health.execute.call_count == 2

