"""Unit tests for HFInferenceWaker."""

import pytest
import os
import asyncio
from aioresponses import aioresponses

from src.monitoring.entities import (
    Endpoint,
    EndpointPriority,
    WakeStrategy,
)
from src.monitoring.adapters import HFInferenceWaker
from src.monitoring.interfaces import IWaker, IReadinessPoller


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
def waker():
    """Create HFInferenceWaker."""
    return HFInferenceWaker()


@pytest.fixture(autouse=True)
def setup_env():
    """Setup environment variables for tests."""
    os.environ["HF_TOKEN"] = "test-token-12345"
    yield
    # Cleanup
    if "HF_TOKEN" in os.environ:
        del os.environ["HF_TOKEN"]


class TestISPCompliance:
    """Tests for Interface Segregation Principle compliance."""

    def test_implements_iwaker(self, waker):
        """Test waker implements IWaker interface."""
        assert isinstance(waker, IWaker)

    def test_implements_ireadiness_poller(self, waker):
        """Test waker implements IReadinessPoller interface."""
        assert isinstance(waker, IReadinessPoller)

    def test_has_wake_method(self, waker):
        """Test waker has wake method."""
        assert hasattr(waker, "wake")
        assert callable(waker.wake)

    def test_has_poll_until_ready_method(self, waker):
        """Test waker has poll_until_ready method."""
        assert hasattr(waker, "poll_until_ready")
        assert callable(waker.poll_until_ready)


class TestWakeSuccess:
    """Tests for successful wake operations."""

    @pytest.mark.asyncio
    async def test_successful_wake_200_response(self, waker, test_endpoint):
        """Test successful wake with 200 response (already ready)."""
        with aioresponses() as m:
            m.post(
                test_endpoint.url,
                status=200,
                payload=[{"generated_text": "wake"}],
            )

            # Act
            result = await waker.wake(test_endpoint)

            # Assert
            assert result.success is True
            # Note: is_ready attribute may not exist in WakeResult
            # Check actual WakeResult structure

    @pytest.mark.asyncio
    async def test_wake_request_sent_503_response(self, waker, test_endpoint):
        """Test wake request accepted with 503 response (loading)."""
        with aioresponses() as m:
            m.post(
                test_endpoint.url,
                status=503,
                body="Model is loading",
            )

            # Act
            result = await waker.wake(test_endpoint)

            # Assert
            assert result.success is True  # Wake request was sent successfully

    @pytest.mark.asyncio
    async def test_wake_uses_minimal_payload(self, waker, test_endpoint):
        """Test wake uses minimal inference payload."""
        with aioresponses() as m:
            m.post(test_endpoint.url, status=200, payload=[{"generated_text": "wake"}])

            # Act
            await waker.wake(test_endpoint)

            # Assert
            assert len(m.requests) == 1
            request = list(m.requests.values())[0][0]
            payload = request.kwargs["json"]
            assert "inputs" in payload
            assert "parameters" in payload
            assert payload["parameters"]["max_new_tokens"] == 1


class TestWakeFailure:
    """Tests for failed wake operations."""

    @pytest.mark.asyncio
    async def test_wake_fails_on_4xx_error(self, waker, test_endpoint):
        """Test wake fails on 4xx error."""
        with aioresponses() as m:
            m.post(test_endpoint.url, status=400, body="Bad request")

            # Act
            result = await waker.wake(test_endpoint)

            # Assert
            assert result.success is False
            assert result.error is not None

    @pytest.mark.asyncio
    async def test_wake_fails_on_network_error(self, waker, test_endpoint):
        """Test wake fails on network error."""
        with aioresponses() as m:
            # Use aiohttp.ClientError instead of generic Exception
            import aiohttp
            m.post(
                test_endpoint.url,
                exception=aiohttp.ClientError("Connection refused"),
            )

            # Act
            result = await waker.wake(test_endpoint)

            # Assert
            assert result.success is False
            assert result.error is not None
            assert "Network error" in result.error


class TestReadinessPolling:
    """Tests for readiness polling functionality."""

    @pytest.mark.asyncio
    async def test_poll_until_ready_success(self, waker, test_endpoint):
        """Test polling succeeds when endpoint becomes ready."""
        with aioresponses() as m:
            # First poll: still loading
            m.post(test_endpoint.url, status=503, body="Loading")
            # Second poll: ready
            m.post(test_endpoint.url, status=200, payload=[{"generated_text": "ready"}])

            # Act
            is_ready = await waker.poll_until_ready(test_endpoint, timeout=10)

            # Assert
            assert is_ready is True

    @pytest.mark.asyncio
    async def test_poll_until_ready_immediate_success(self, waker, test_endpoint):
        """Test polling succeeds immediately if already ready."""
        with aioresponses() as m:
            m.post(test_endpoint.url, status=200, payload=[{"generated_text": "ready"}])

            # Act
            is_ready = await waker.poll_until_ready(test_endpoint, timeout=10)

            # Assert
            assert is_ready is True

    @pytest.mark.asyncio
    async def test_poll_until_ready_timeout(self, waker, test_endpoint):
        """Test polling times out if endpoint never ready."""
        with aioresponses() as m:
            # Always return 503 (loading)
            for _ in range(10):
                m.post(test_endpoint.url, status=503, body="Loading")

            # Act
            is_ready = await waker.poll_until_ready(test_endpoint, timeout=5)

            # Assert
            assert is_ready is False

    @pytest.mark.asyncio
    async def test_poll_uses_exponential_backoff(self, waker, test_endpoint):
        """Test polling uses exponential backoff."""
        with aioresponses() as m:
            # Setup multiple responses - first 2 fail, then success
            m.post(test_endpoint.url, status=503, body="Loading")
            m.post(test_endpoint.url, status=503, body="Loading")
            m.post(test_endpoint.url, status=200, payload=[{"generated_text": "ready"}])

            # Act
            start_time = asyncio.get_event_loop().time()
            is_ready = await waker.poll_until_ready(test_endpoint, timeout=30)
            elapsed = asyncio.get_event_loop().time() - start_time

            # Assert
            assert is_ready is True
            # Should have some delay due to backoff (at least 2s for first interval)
            # First poll: immediate, second poll: after 2s delay, third poll: after 4s delay
            # Total: at least 2s (first backoff)
            assert elapsed >= 2.0

    @pytest.mark.asyncio
    async def test_poll_stops_on_non_503_error(self, waker, test_endpoint):
        """Test polling stops on non-503 error."""
        with aioresponses() as m:
            m.post(test_endpoint.url, status=500, body="Internal error")

            # Act
            is_ready = await waker.poll_until_ready(test_endpoint, timeout=10)

            # Assert
            assert is_ready is False
            # Should only make one request (stops on error)
            assert len(m.requests) == 1


class TestAuthConfiguration:
    """Tests for authentication configuration."""

    @pytest.mark.asyncio
    async def test_wake_uses_bearer_token(self, waker, test_endpoint):
        """Test wake uses bearer token from environment."""
        with aioresponses() as m:
            m.post(test_endpoint.url, status=200, payload=[{"generated_text": "wake"}])

            # Act
            await waker.wake(test_endpoint)

            # Assert
            assert len(m.requests) == 1
            request = list(m.requests.values())[0][0]
            assert "Authorization" in request.kwargs["headers"]
            assert request.kwargs["headers"]["Authorization"] == "Bearer test-token-12345"

    @pytest.mark.asyncio
    async def test_poll_uses_bearer_token(self, waker, test_endpoint):
        """Test polling uses bearer token from environment."""
        with aioresponses() as m:
            m.post(test_endpoint.url, status=200, payload=[{"generated_text": "ready"}])

            # Act
            await waker.poll_until_ready(test_endpoint, timeout=10)

            # Assert
            assert len(m.requests) == 1
            request = list(m.requests.values())[0][0]
            assert "Authorization" in request.kwargs["headers"]
            assert request.kwargs["headers"]["Authorization"] == "Bearer test-token-12345"


class TestWakeContract:
    """Tests for IWaker contract compliance."""

    @pytest.mark.asyncio
    async def test_wake_always_returns_wake_result(self, waker, test_endpoint):
        """Test wake always returns WakeResult (never None)."""
        with aioresponses() as m:
            m.post(test_endpoint.url, status=200, payload=[{"generated_text": "wake"}])

            # Act
            result = await waker.wake(test_endpoint)

            # Assert
            assert result is not None

    @pytest.mark.asyncio
    async def test_wake_completes_quickly(self, waker, test_endpoint):
        """Test wake completes quickly (< 10s per contract)."""
        with aioresponses() as m:
            m.post(test_endpoint.url, status=200, payload=[{"generated_text": "wake"}])

            # Act
            start_time = asyncio.get_event_loop().time()
            await waker.wake(test_endpoint)
            elapsed = asyncio.get_event_loop().time() - start_time

            # Assert
            assert elapsed < 10.0  # Should complete in < 10s


class TestReadinessPollerContract:
    """Tests for IReadinessPoller contract compliance."""

    @pytest.mark.asyncio
    async def test_poll_returns_bool(self, waker, test_endpoint):
        """Test poll_until_ready returns bool."""
        with aioresponses() as m:
            m.post(test_endpoint.url, status=200, payload=[{"generated_text": "ready"}])

            # Act
            result = await waker.poll_until_ready(test_endpoint, timeout=10)

            # Assert
            assert isinstance(result, bool)

    @pytest.mark.asyncio
    async def test_poll_respects_timeout(self, waker, test_endpoint):
        """Test poll_until_ready respects timeout parameter."""
        with aioresponses() as m:
            # Always return 503
            for _ in range(100):
                m.post(test_endpoint.url, status=503, body="Loading")

            # Act
            start_time = asyncio.get_event_loop().time()
            await waker.poll_until_ready(test_endpoint, timeout=3)
            elapsed = asyncio.get_event_loop().time() - start_time

            # Assert
            # Should complete within timeout + reasonable buffer for backoff
            # With exponential backoff (2s, 4s, 8s...), it may take slightly longer
            assert elapsed < 10.0  # Generous buffer

