"""Health status entities - represent health check results and wake outcomes."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any
from .enums import EndpointState, HealthCheckErrorCode


@dataclass
class HealthCheckResponse:
    """Response from a health check operation (provider-agnostic).

    This is the contract returned by all IHealthChecker implementations.
    Ensures LSP compliance by standardizing error codes and response format.

    Attributes:
        status: Current endpoint state (HEALTHY, SLEEPING, DEGRADED, FAILED)
        response_time_ms: Response time in milliseconds (None if failed)
        error_code: Standardized error code (None if successful)
        error_details: Provider-specific error details (optional, for debugging)
    """

    status: EndpointState
    response_time_ms: Optional[float] = None
    error_code: Optional[HealthCheckErrorCode] = None
    error_details: Optional[Dict[str, Any]] = None

    def is_successful(self) -> bool:
        """Check if health check succeeded (endpoint is healthy or degraded)."""
        return self.status.is_operational()

    def is_cold_start(self) -> bool:
        """Check if health check detected cold start (endpoint sleeping)."""
        return self.status == EndpointState.SLEEPING or (
            self.error_code == HealthCheckErrorCode.MODEL_LOADING
        )

    def needs_wake(self) -> bool:
        """Check if endpoint needs wake-up based on response."""
        return self.is_cold_start() or (
            self.error_code is not None and self.error_code.should_wake()
        )


@dataclass
class HealthStatus:
    """Current health state of an endpoint (mutable - updated by daemon).

    This is the internal state tracked by the monitoring daemon.
    Aggregates multiple health check responses over time.

    Attributes:
        endpoint_id: ID of monitored endpoint
        state: Current endpoint state
        last_check_time: Timestamp of last health check
        last_wake_time: Timestamp of last wake attempt (None if never woken)
        response_time_ms: Latest response time (None if failed)
        consecutive_failures: Number of consecutive health check failures
        error_message: Latest error message (None if healthy)
    """

    endpoint_id: str
    state: EndpointState
    last_check_time: datetime
    last_wake_time: Optional[datetime] = None
    response_time_ms: Optional[float] = None
    consecutive_failures: int = 0
    error_message: Optional[str] = None

    def is_healthy(self) -> bool:
        """Check if endpoint is currently healthy."""
        return self.state == EndpointState.HEALTHY

    def is_sleeping(self) -> bool:
        """Check if endpoint is currently sleeping."""
        return self.state == EndpointState.SLEEPING

    def is_failed(self) -> bool:
        """Check if endpoint is currently failed."""
        return self.state == EndpointState.FAILED

    def needs_wake(self) -> bool:
        """Determine if endpoint needs wake-up based on current state."""
        return self.state in (EndpointState.SLEEPING, EndpointState.FAILED)

    def update_from_response(self, response: HealthCheckResponse) -> None:
        """Update status from health check response (mutates state).

        Args:
            response: HealthCheckResponse from health checker
        """
        self.state = response.status
        self.response_time_ms = response.response_time_ms
        self.last_check_time = datetime.now()

        if response.is_successful():
            # Reset failure counter on success
            self.consecutive_failures = 0
            self.error_message = None
        else:
            # Increment failure counter
            self.consecutive_failures += 1
            if response.error_code:
                self.error_message = f"{response.error_code.value}"
                if response.error_details:
                    self.error_message += f": {response.error_details}"

    def record_wake_attempt(self) -> None:
        """Record that a wake attempt was made (updates timestamp)."""
        self.last_wake_time = datetime.now()

    def __str__(self) -> str:
        """Human-readable string representation."""
        return (
            f"HealthStatus(endpoint={self.endpoint_id}, state={self.state.value}, "
            f"failures={self.consecutive_failures})"
        )


@dataclass(frozen=True)
class WakeResult:
    """Result of a wake endpoint operation.

    Attributes:
        success: Whether wake operation succeeded
        wake_time_s: Time taken to wake endpoint (None if failed)
        attempts: Number of wake attempts made
        error: Error message (None if successful)
        warning: Warning message (None if no warnings)
    """

    success: bool
    wake_time_s: Optional[float] = None
    attempts: int = 1
    error: Optional[str] = None
    warning: Optional[str] = None

    def __str__(self) -> str:
        """Human-readable string representation."""
        if self.success:
            return f"WakeResult(success=True, time={self.wake_time_s:.2f}s, attempts={self.attempts})"
        else:
            return f"WakeResult(success=False, error={self.error})"


@dataclass(frozen=True)
class FallbackResult:
    """Result of executing a fallback chain.

    Attributes:
        active_endpoint_id: ID of endpoint that succeeded (None if all failed)
        fallback_count: Number of fallbacks executed (0 = primary succeeded)
        success: Whether any endpoint in chain succeeded
        error: Error message if all failed (None if successful)
        wake_results: Wake results for each attempted endpoint (optional)
    """

    active_endpoint_id: Optional[str]
    fallback_count: int
    success: bool
    error: Optional[str] = None
    wake_results: Dict[str, WakeResult] = field(default_factory=dict)

    def used_primary(self) -> bool:
        """Check if primary endpoint succeeded (no fallback needed)."""
        return self.success and self.fallback_count == 0

    def used_fallback(self) -> bool:
        """Check if fallback was used."""
        return self.success and self.fallback_count > 0

    def __str__(self) -> str:
        """Human-readable string representation."""
        if self.success:
            if self.used_primary():
                return f"FallbackResult(primary succeeded: {self.active_endpoint_id})"
            else:
                return f"FallbackResult(fallback to {self.active_endpoint_id}, count={self.fallback_count})"
        else:
            return f"FallbackResult(all endpoints failed: {self.error})"
