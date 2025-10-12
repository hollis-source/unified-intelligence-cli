"""Health checker interface and base implementation.

IHealthChecker: Abstract interface for checking endpoint health
BaseHealthChecker: Base class enforcing LSP invariants (timeout, exception handling)
"""

from abc import ABC, abstractmethod
import asyncio
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..entities import Endpoint, HealthCheckResponse, HealthCheckErrorCode, EndpointState


class IHealthChecker(ABC):
    """Abstract interface for checking endpoint health (provider-agnostic).

    All health check adapters must implement this interface to ensure LSP compliance.
    The contract guarantees:
    - Completes within endpoint.health_check_timeout seconds
    - Returns HealthCheckResponse with standardized error codes
    - Never raises exceptions (returns FAILED status instead)
    - Provider-agnostic response format

    Subclasses should inherit from BaseHealthChecker to get automatic
    timeout and exception handling enforcement.
    """

    @abstractmethod
    async def check(self, endpoint: "Endpoint") -> "HealthCheckResponse":
        """Check endpoint health.

        Args:
            endpoint: Endpoint to check

        Returns:
            HealthCheckResponse with status, response time, and optional error

        Contract:
        - MUST complete within endpoint.health_check_timeout seconds
        - MUST return HealthCheckResponse (never None)
        - MUST use standardized HealthCheckErrorCode for errors
        - MUST NOT raise exceptions (return FAILED status instead)
        """
        pass


class BaseHealthChecker(IHealthChecker):
    """Base health checker enforcing LSP invariants.

    Provides template method pattern to ensure all subclasses comply with contract:
    - Automatic timeout enforcement
    - Exception handling (converts to FAILED status)
    - Consistent error code mapping

    Subclasses should implement _check_impl() instead of check().
    """

    async def check(self, endpoint: "Endpoint") -> "HealthCheckResponse":
        """Check endpoint health with automatic timeout and exception handling.

        Template method that enforces LSP contract. Subclasses implement _check_impl().

        Args:
            endpoint: Endpoint to check

        Returns:
            HealthCheckResponse with guaranteed timeout compliance
        """
        # Import here to avoid circular dependency
        from ..entities import HealthCheckResponse, HealthCheckErrorCode, EndpointState

        try:
            # Enforce timeout at base class level (LSP invariant)
            response = await asyncio.wait_for(
                self._check_impl(endpoint),
                timeout=endpoint.wake_timeout
            )
            return response

        except asyncio.TimeoutError:
            # Timeout handling (enforced by base class)
            return HealthCheckResponse(
                status=EndpointState.FAILED,
                error_code=HealthCheckErrorCode.TIMEOUT,
                response_time_ms=None,
                error_details={
                    "timeout": endpoint.wake_timeout,
                    "message": f"Health check timed out after {endpoint.wake_timeout}s"
                }
            )

        except Exception as e:
            # Exception handling (enforced by base class - never propagate)
            return HealthCheckResponse(
                status=EndpointState.FAILED,
                error_code=HealthCheckErrorCode.UNKNOWN,
                response_time_ms=None,
                error_details={
                    "exception": type(e).__name__,
                    "message": str(e)
                }
            )

    @abstractmethod
    async def _check_impl(self, endpoint: "Endpoint") -> "HealthCheckResponse":
        """Subclass-specific health check implementation.

        This is the method subclasses override (not check()).
        No need to handle timeout or exceptions - base class handles them.

        Args:
            endpoint: Endpoint to check

        Returns:
            HealthCheckResponse with status and metrics

        Note:
            This method may raise exceptions - they'll be caught by base class
            and converted to FAILED status with UNKNOWN error code.
        """
        pass
