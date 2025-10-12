"""Enums for endpoint monitoring domain.

All enums are string-based for better serialization and debugging.
"""

from enum import Enum


class EndpointState(str, Enum):
    """Current state of an endpoint."""

    HEALTHY = "healthy"         # Endpoint responding normally (< 2s response time)
    SLEEPING = "sleeping"       # Endpoint scaled to zero (cold start detected)
    DEGRADED = "degraded"       # Endpoint responding slowly (2-10s response time)
    FAILED = "failed"           # Endpoint not responding or error state
    UNKNOWN = "unknown"         # State not yet determined (initial state)

    def is_operational(self) -> bool:
        """Check if endpoint is operational (healthy or degraded)."""
        return self in (EndpointState.HEALTHY, EndpointState.DEGRADED)

    def needs_attention(self) -> bool:
        """Check if endpoint needs attention (sleeping or failed)."""
        return self in (EndpointState.SLEEPING, EndpointState.FAILED)


class EndpointPriority(str, Enum):
    """Priority level of an endpoint (affects wake strategy)."""

    CRITICAL = "critical"   # Always keep warm, immediate wake on sleep
    HIGH = "high"          # Wake on sleep, tolerate brief cold starts
    MEDIUM = "medium"      # Wake on demand (first request)
    LOW = "low"            # No auto-wake (manual wake only)

    def should_auto_wake(self) -> bool:
        """Check if endpoint should be automatically woken."""
        return self in (EndpointPriority.CRITICAL, EndpointPriority.HIGH)

    def get_health_check_interval(self) -> int:
        """Get recommended health check interval in seconds."""
        intervals = {
            EndpointPriority.CRITICAL: 30,   # More frequent for critical
            EndpointPriority.HIGH: 60,       # Standard interval
            EndpointPriority.MEDIUM: 120,    # Less frequent
            EndpointPriority.LOW: 300,       # Minimal monitoring
        }
        return intervals[self]


class WakeStrategy(str, Enum):
    """Strategy for waking sleeping endpoints."""

    ALWAYS_WARM = "always_warm"         # Keep always warm (wake immediately on sleep)
    PRIORITY_BASED = "priority_based"   # Wake based on priority (critical/high only)
    REACTIVE = "reactive"               # Wake only on-demand (user request)
    SCHEDULED = "scheduled"             # Wake on schedule (e.g., business hours only)

    def should_wake_immediately(self, priority: EndpointPriority) -> bool:
        """Determine if endpoint should be woken immediately."""
        if self == WakeStrategy.ALWAYS_WARM:
            return True
        elif self == WakeStrategy.PRIORITY_BASED:
            return priority.should_auto_wake()
        elif self == WakeStrategy.REACTIVE:
            return False
        elif self == WakeStrategy.SCHEDULED:
            # TODO: Implement schedule logic (check if within wake hours)
            return False
        return False


class HealthCheckErrorCode(str, Enum):
    """Standardized error codes for health check failures (provider-agnostic).

    These codes abstract away provider-specific errors to maintain LSP compliance.
    Provider-specific details should go in error_details dict.
    """

    MODEL_LOADING = "model_loading"       # Model is loading (cold start)
    TIMEOUT = "timeout"                   # Request timeout exceeded
    RATE_LIMITED = "rate_limited"         # API rate limit hit
    AUTH_FAILED = "auth_failed"           # Authentication/authorization failure
    INVALID_REQUEST = "invalid_request"   # Malformed request
    INTERNAL_ERROR = "internal_error"     # Provider internal error (5xx)
    NETWORK_ERROR = "network_error"       # Network connectivity issue
    UNKNOWN = "unknown"                   # Unknown/unclassified error

    def is_recoverable(self) -> bool:
        """Check if error is recoverable (retry may succeed)."""
        recoverable = {
            HealthCheckErrorCode.MODEL_LOADING,  # Will eventually load
            HealthCheckErrorCode.TIMEOUT,        # May succeed on retry
            HealthCheckErrorCode.RATE_LIMITED,   # Will succeed after cooldown
            HealthCheckErrorCode.INTERNAL_ERROR, # May be transient
            HealthCheckErrorCode.NETWORK_ERROR,  # May be transient
        }
        return self in recoverable

    def should_wake(self) -> bool:
        """Check if this error indicates endpoint needs waking."""
        return self == HealthCheckErrorCode.MODEL_LOADING
