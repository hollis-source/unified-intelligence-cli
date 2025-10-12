"""Unit tests for Endpoint entity."""

import pytest
from src.monitoring.entities import Endpoint, EndpointPriority, WakeStrategy


class TestEndpointCreation:
    """Tests for Endpoint creation and validation."""

    def test_create_valid_endpoint(self):
        """Test creating endpoint with valid configuration."""
        endpoint = Endpoint(
            id="test-endpoint",
            provider="huggingface",
            url="https://api.example.com",
            priority=EndpointPriority.HIGH,
            wake_strategy=WakeStrategy.PRIORITY_BASED,
        )

        assert endpoint.id == "test-endpoint"
        assert endpoint.provider == "huggingface"
        assert endpoint.url == "https://api.example.com"
        assert endpoint.priority == EndpointPriority.HIGH
        assert endpoint.wake_strategy == WakeStrategy.PRIORITY_BASED

    def test_endpoint_immutable(self):
        """Test that endpoint is immutable (frozen dataclass)."""
        endpoint = Endpoint(
            id="test",
            provider="hf",
            url="https://example.com",
            priority=EndpointPriority.HIGH,
            wake_strategy=WakeStrategy.ALWAYS_WARM,
        )

        with pytest.raises(AttributeError):
            endpoint.priority = EndpointPriority.LOW  # Should fail

    def test_empty_id_raises_error(self):
        """Test that empty ID raises ValueError."""
        with pytest.raises(ValueError, match="ID cannot be empty"):
            Endpoint(
                id="",
                provider="hf",
                url="https://example.com",
                priority=EndpointPriority.HIGH,
                wake_strategy=WakeStrategy.ALWAYS_WARM,
            )

    def test_invalid_url_raises_error(self):
        """Test that invalid URL raises ValueError."""
        with pytest.raises(ValueError, match="must start with http"):
            Endpoint(
                id="test",
                provider="hf",
                url="invalid-url",
                priority=EndpointPriority.HIGH,
                wake_strategy=WakeStrategy.ALWAYS_WARM,
            )


class TestEndpointMethods:
    """Tests for Endpoint methods."""

    def test_get_health_check_interval_custom(self):
        """Test get_health_check_interval with custom interval."""
        endpoint = Endpoint(
            id="test",
            provider="hf",
            url="https://example.com",
            priority=EndpointPriority.HIGH,
            wake_strategy=WakeStrategy.ALWAYS_WARM,
            health_check_interval=45,
        )

        assert endpoint.get_health_check_interval() == 45

    def test_get_health_check_interval_default(self):
        """Test get_health_check_interval with priority default."""
        endpoint = Endpoint(
            id="test",
            provider="hf",
            url="https://example.com",
            priority=EndpointPriority.CRITICAL,
            wake_strategy=WakeStrategy.ALWAYS_WARM,
        )

        assert endpoint.get_health_check_interval() == 30  # CRITICAL default

    def test_should_auto_wake_always_warm(self):
        """Test should_auto_wake for ALWAYS_WARM strategy."""
        endpoint = Endpoint(
            id="test",
            provider="hf",
            url="https://example.com",
            priority=EndpointPriority.LOW,
            wake_strategy=WakeStrategy.ALWAYS_WARM,
        )

        assert endpoint.should_auto_wake() is True

    def test_should_auto_wake_reactive(self):
        """Test should_auto_wake for REACTIVE strategy."""
        endpoint = Endpoint(
            id="test",
            provider="hf",
            url="https://example.com",
            priority=EndpointPriority.CRITICAL,
            wake_strategy=WakeStrategy.REACTIVE,
        )

        assert endpoint.should_auto_wake() is False

    def test_get_auth_header_bearer(self):
        """Test get_auth_header with bearer token."""
        endpoint = Endpoint(
            id="test",
            provider="hf",
            url="https://example.com",
            priority=EndpointPriority.HIGH,
            wake_strategy=WakeStrategy.ALWAYS_WARM,
            auth_config={"type": "bearer"},
        )

        headers = endpoint.get_auth_header("test-token-123")
        assert headers == {"Authorization": "Bearer test-token-123"}

    def test_get_auth_url_query_param(self):
        """Test get_auth_url with query parameter."""
        endpoint = Endpoint(
            id="test",
            provider="replicate",
            url="https://example.com/api",
            priority=EndpointPriority.HIGH,
            wake_strategy=WakeStrategy.ALWAYS_WARM,
            auth_config={"type": "query_param", "param_name": "token"},
        )

        url = endpoint.get_auth_url("secret-token")
        assert url == "https://example.com/api?token=secret-token"
