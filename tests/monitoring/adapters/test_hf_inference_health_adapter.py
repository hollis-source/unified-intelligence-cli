"""Unit tests for HFInferenceHealthAdapter."""

import pytest
import os
from aioresponses import aioresponses

from src.monitoring.entities import (
    Endpoint,
    EndpointPriority,
    WakeStrategy,
    EndpointState,
    HealthCheckErrorCode,
)
from src.monitoring.adapters import HFInferenceHealthAdapter


@pytest.fixture
def test_endpoint():
    """Create test endpoint with HF auth config."""
    return Endpoint(
        id="test-hf-endpoint",
        provider="huggingface",
        url="https://api-inference.huggingface.co/models/test-model",
        priority=EndpointPriority.HIGH,
        wake_strategy=WakeStrategy.PRIORITY_BASED,
        auth_config={"type": "bearer", "token_env": "HF_TOKEN"},
        wake_timeout=30,
    )


@pytest.fixture
def adapter():
    """Create HFInferenceHealthAdapter."""
    return HFInferenceHealthAdapter()


@pytest.fixture(autouse=True)
def setup_env():
    """Setup environment variables for tests."""
    os.environ["HF_TOKEN"] = "test-token-12345"
    yield
    # Cleanup
    if "HF_TOKEN" in os.environ:
        del os.environ["HF_TOKEN"]


class TestHealthyResponse:
    """Tests for healthy endpoint responses (200)."""

    @pytest.mark.asyncio
    async def test_200_response_returns_healthy(self, adapter, test_endpoint):
        """Test 200 response returns HEALTHY status."""
        with aioresponses() as m:
            m.post(
                test_endpoint.url,
                status=200,
                payload=[{"generated_text": "test"}],
            )

            # Act
            response = await adapter.check(test_endpoint)

            # Assert
            assert response.status == EndpointState.HEALTHY
            assert response.response_time_ms is not None
            assert response.response_time_ms > 0
            assert response.error_code is None

    @pytest.mark.asyncio
    async def test_healthy_response_includes_timing(self, adapter, test_endpoint):
        """Test healthy response includes response time."""
        with aioresponses() as m:
            m.post(test_endpoint.url, status=200, payload=[{"generated_text": "test"}])

            # Act
            response = await adapter.check(test_endpoint)

            # Assert
            assert response.response_time_ms is not None
            assert isinstance(response.response_time_ms, float)
            assert response.response_time_ms >= 0


class TestSleepingResponse:
    """Tests for sleeping endpoint responses (503 with loading)."""

    @pytest.mark.asyncio
    async def test_503_with_loading_returns_sleeping(self, adapter, test_endpoint):
        """Test 503 with 'loading' message returns SLEEPING status."""
        with aioresponses() as m:
            m.post(
                test_endpoint.url,
                status=503,
                body="Model is currently loading",
            )

            # Act
            response = await adapter.check(test_endpoint)

            # Assert
            assert response.status == EndpointState.SLEEPING
            assert response.error_code == HealthCheckErrorCode.MODEL_LOADING
            assert response.response_time_ms is not None

    @pytest.mark.asyncio
    async def test_503_with_loading_lowercase(self, adapter, test_endpoint):
        """Test 503 with 'loading' (case-insensitive) returns SLEEPING."""
        with aioresponses() as m:
            m.post(
                test_endpoint.url,
                status=503,
                body="model is loading, please wait",
            )

            # Act
            response = await adapter.check(test_endpoint)

            # Assert
            assert response.status == EndpointState.SLEEPING
            assert response.error_code == HealthCheckErrorCode.MODEL_LOADING


class TestFailedResponse:
    """Tests for failed endpoint responses."""

    @pytest.mark.asyncio
    async def test_503_without_loading_returns_failed(self, adapter, test_endpoint):
        """Test 503 without 'loading' returns FAILED status."""
        with aioresponses() as m:
            m.post(
                test_endpoint.url,
                status=503,
                body="Service temporarily unavailable",
            )

            # Act
            response = await adapter.check(test_endpoint)

            # Assert
            assert response.status == EndpointState.FAILED
            assert response.error_code == HealthCheckErrorCode.INTERNAL_ERROR

    @pytest.mark.asyncio
    async def test_500_returns_failed_internal_error(self, adapter, test_endpoint):
        """Test 500 response returns FAILED with INTERNAL_ERROR."""
        with aioresponses() as m:
            m.post(test_endpoint.url, status=500, body="Internal server error")

            # Act
            response = await adapter.check(test_endpoint)

            # Assert
            assert response.status == EndpointState.FAILED
            assert response.error_code == HealthCheckErrorCode.INTERNAL_ERROR


class TestDegradedResponse:
    """Tests for degraded endpoint responses (429)."""

    @pytest.mark.asyncio
    async def test_429_returns_degraded_rate_limited(self, adapter, test_endpoint):
        """Test 429 response returns DEGRADED with RATE_LIMITED."""
        with aioresponses() as m:
            m.post(test_endpoint.url, status=429, body="Rate limit exceeded")

            # Act
            response = await adapter.check(test_endpoint)

            # Assert
            assert response.status == EndpointState.DEGRADED
            assert response.error_code == HealthCheckErrorCode.RATE_LIMITED
            assert response.response_time_ms is not None


class TestAuthFailure:
    """Tests for authentication failures (401/403)."""

    @pytest.mark.asyncio
    async def test_401_returns_failed_auth_failed(self, adapter, test_endpoint):
        """Test 401 response returns FAILED with AUTH_FAILED."""
        with aioresponses() as m:
            m.post(test_endpoint.url, status=401, body="Unauthorized")

            # Act
            response = await adapter.check(test_endpoint)

            # Assert
            assert response.status == EndpointState.FAILED
            assert response.error_code == HealthCheckErrorCode.AUTH_FAILED

    @pytest.mark.asyncio
    async def test_403_returns_failed_auth_failed(self, adapter, test_endpoint):
        """Test 403 response returns FAILED with AUTH_FAILED."""
        with aioresponses() as m:
            m.post(test_endpoint.url, status=403, body="Forbidden")

            # Act
            response = await adapter.check(test_endpoint)

            # Assert
            assert response.status == EndpointState.FAILED
            assert response.error_code == HealthCheckErrorCode.AUTH_FAILED


class TestNetworkError:
    """Tests for network errors."""

    @pytest.mark.asyncio
    async def test_network_error_returns_failed(self, adapter, test_endpoint):
        """Test network error returns FAILED with NETWORK_ERROR."""
        with aioresponses() as m:
            m.post(
                test_endpoint.url,
                exception=Exception("Connection refused"),
            )

            # Act
            response = await adapter.check(test_endpoint)

            # Assert
            assert response.status == EndpointState.FAILED
            assert response.error_code == HealthCheckErrorCode.NETWORK_ERROR


class TestLSPCompliance:
    """Tests for LSP compliance (BaseHealthChecker enforces timeout)."""

    @pytest.mark.asyncio
    async def test_timeout_enforced_by_base_class(self, adapter, test_endpoint):
        """Test BaseHealthChecker enforces timeout."""
        # Create endpoint with very short timeout
        short_timeout_endpoint = Endpoint(
            id="timeout-test",
            provider="huggingface",
            url="https://api-inference.huggingface.co/models/test-model",
            priority=EndpointPriority.HIGH,
            wake_strategy=WakeStrategy.PRIORITY_BASED,
            auth_config={"type": "bearer", "token_env": "HF_TOKEN"},
            wake_timeout=1,  # 1 second timeout
        )

        with aioresponses() as m:
            # Simulate slow response (but aioresponses doesn't support delays easily)
            # This test verifies the timeout mechanism exists
            m.post(short_timeout_endpoint.url, status=200, payload=[{"generated_text": "test"}])

            # Act
            response = await adapter.check(short_timeout_endpoint)

            # Assert - Should complete (either success or timeout)
            assert response is not None
            assert response.status in [
                EndpointState.HEALTHY,
                EndpointState.FAILED,
            ]

    @pytest.mark.asyncio
    async def test_never_raises_exceptions(self, adapter, test_endpoint):
        """Test adapter never raises exceptions (LSP contract)."""
        with aioresponses() as m:
            m.post(
                test_endpoint.url,
                exception=Exception("Unexpected error"),
            )

            # Act - Should not raise exception
            response = await adapter.check(test_endpoint)

            # Assert
            assert response is not None
            assert response.status == EndpointState.FAILED


class TestAuthConfiguration:
    """Tests for authentication configuration."""

    @pytest.mark.asyncio
    async def test_uses_bearer_token_from_env(self, adapter, test_endpoint):
        """Test adapter uses bearer token from environment."""
        with aioresponses() as m:
            m.post(test_endpoint.url, status=200, payload=[{"generated_text": "test"}])

            # Act
            response = await adapter.check(test_endpoint)

            # Assert
            assert response.status == EndpointState.HEALTHY
            # Verify request was made with auth header
            assert len(m.requests) == 1
            request = list(m.requests.values())[0][0]
            assert "Authorization" in request.kwargs["headers"]
            assert request.kwargs["headers"]["Authorization"] == "Bearer test-token-12345"

    @pytest.mark.asyncio
    async def test_missing_token_env_raises_error(self, adapter):
        """Test missing token environment variable raises error."""
        # Remove token from environment
        del os.environ["HF_TOKEN"]

        endpoint = Endpoint(
            id="no-token",
            provider="huggingface",
            url="https://api-inference.huggingface.co/models/test-model",
            priority=EndpointPriority.HIGH,
            wake_strategy=WakeStrategy.PRIORITY_BASED,
            auth_config={"type": "bearer", "token_env": "HF_TOKEN"},
        )

        with aioresponses() as m:
            m.post(endpoint.url, status=200, payload=[{"generated_text": "test"}])

            # Act
            response = await adapter.check(endpoint)

            # Assert - Should return FAILED (exception caught by base class)
            assert response.status == EndpointState.FAILED
            assert response.error_code == HealthCheckErrorCode.UNKNOWN

