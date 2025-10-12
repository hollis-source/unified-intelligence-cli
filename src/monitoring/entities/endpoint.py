"""Endpoint entity - represents a monitored inference endpoint."""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional
from .enums import EndpointPriority, WakeStrategy


@dataclass(frozen=True)
class Endpoint:
    """Represents a monitored inference endpoint.

    Immutable entity containing all configuration for monitoring a single endpoint.
    Uses frozen dataclass for thread-safety and value semantics.

    Attributes:
        id: Unique identifier (e.g., "qwen3-primary")
        provider: Provider name ("huggingface", "replicate", "modal", etc.)
        url: Base URL for API requests (no auth embedded)
        priority: Priority level (affects wake strategy and check frequency)
        wake_strategy: Strategy for waking sleeping endpoints
        auth_config: Provider-specific authentication configuration
        health_check_interval: Seconds between health checks (default from priority)
        wake_timeout: Max seconds to wait for wake (default 90)
        fallback_endpoint_id: Optional ID of fallback endpoint on failure

    Example auth_config formats:
        HuggingFace: {"type": "bearer", "token_env": "HF_TOKEN"}
        Replicate: {"type": "query_param", "param_name": "token", "token_env": "REPLICATE_TOKEN"}
        Modal: {"type": "header", "header_name": "X-Modal-Key", "token_env": "MODAL_KEY"}
    """

    # Core identification
    id: str
    provider: str
    url: str

    # Monitoring configuration
    priority: EndpointPriority
    wake_strategy: WakeStrategy

    # Authentication (provider-specific)
    auth_config: Dict[str, Any] = field(default_factory=dict)

    # Timing configuration
    health_check_interval: Optional[int] = None  # None = use priority default
    wake_timeout: int = 90  # Seconds to wait for wake

    # Fallback configuration
    fallback_endpoint_id: Optional[str] = None

    def __post_init__(self):
        """Validate endpoint configuration at creation time (fail fast)."""
        # Validate ID
        if not self.id or not self.id.strip():
            raise ValueError("Endpoint ID cannot be empty")

        # Validate provider
        if not self.provider or not self.provider.strip():
            raise ValueError("Endpoint provider cannot be empty")

        # Validate URL
        if not self.url or not self.url.strip():
            raise ValueError("Endpoint URL cannot be empty")
        if not (self.url.startswith("http://") or self.url.startswith("https://")):
            raise ValueError(f"Endpoint URL must start with http:// or https://: {self.url}")

        # Validate wake timeout
        if self.wake_timeout <= 0:
            raise ValueError(f"Wake timeout must be positive: {self.wake_timeout}")

        # Validate health check interval (if provided)
        if self.health_check_interval is not None and self.health_check_interval <= 0:
            raise ValueError(f"Health check interval must be positive: {self.health_check_interval}")

    def get_health_check_interval(self) -> int:
        """Get effective health check interval (custom or priority default)."""
        if self.health_check_interval is not None:
            return self.health_check_interval
        return self.priority.get_health_check_interval()

    def should_auto_wake(self) -> bool:
        """Check if endpoint should be automatically woken when sleeping."""
        return self.wake_strategy.should_wake_immediately(self.priority)

    def get_auth_header(self, token: str) -> Dict[str, str]:
        """Get HTTP headers for authentication (helper method).

        Args:
            token: Authentication token value

        Returns:
            Dict of HTTP headers for authentication

        Raises:
            ValueError: If auth_config type is unsupported
        """
        auth_type = self.auth_config.get("type", "bearer")

        if auth_type == "bearer":
            return {"Authorization": f"Bearer {token}"}
        elif auth_type == "header":
            header_name = self.auth_config.get("header_name", "Authorization")
            return {header_name: token}
        else:
            raise ValueError(f"Unsupported auth type: {auth_type}")

    def get_auth_url(self, token: str) -> str:
        """Get URL with embedded authentication (for query param auth).

        Args:
            token: Authentication token value

        Returns:
            URL with authentication embedded

        Raises:
            ValueError: If auth_config type is not query_param
        """
        auth_type = self.auth_config.get("type", "bearer")

        if auth_type == "query_param":
            param_name = self.auth_config.get("param_name", "token")
            separator = "&" if "?" in self.url else "?"
            return f"{self.url}{separator}{param_name}={token}"
        else:
            raise ValueError(f"get_auth_url only supports query_param auth, got: {auth_type}")

    def __str__(self) -> str:
        """Human-readable string representation."""
        return f"Endpoint(id={self.id}, provider={self.provider}, priority={self.priority.value})"

    def __repr__(self) -> str:
        """Developer-friendly representation."""
        return (
            f"Endpoint(id={self.id!r}, provider={self.provider!r}, url={self.url!r}, "
            f"priority={self.priority}, wake_strategy={self.wake_strategy})"
        )
