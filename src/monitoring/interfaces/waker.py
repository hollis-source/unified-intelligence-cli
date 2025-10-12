"""Waker interfaces (ISP-compliant - split into minimal interfaces).

IWaker: Wake sleeping endpoint (basic capability)
IReadinessPoller: Poll endpoint readiness (optional capability)

These interfaces are separate to avoid forcing implementations to
provide capabilities they don't support (Interface Segregation Principle).
"""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..entities import Endpoint, WakeResult


class IWaker(ABC):
    """Abstract interface for waking sleeping endpoints (basic capability).

    All providers must support wake, so this is the base interface.
    Wake operation sends a minimal request to endpoint to trigger loading.

    ISP Compliance: This interface contains only wake() - implementations
    that don't support readiness polling aren't forced to implement it.
    """

    @abstractmethod
    async def wake(self, endpoint: "Endpoint") -> "WakeResult":
        """Send wake request to endpoint.

        Sends minimal inference request to trigger endpoint loading.
        Does NOT wait for readiness - that's IReadinessPoller's job.

        Args:
            endpoint: Endpoint to wake

        Returns:
            WakeResult with success status and optional error

        Contract:
        - MUST send wake request (minimal inference)
        - MUST return WakeResult (never None)
        - MUST NOT wait for readiness (just trigger wake)
        - SHOULD complete quickly (< 10s)
        """
        pass


class IReadinessPoller(ABC):
    """Abstract interface for polling endpoint readiness (optional capability).

    Not all providers support readiness polling (e.g., Replicate has no status API).
    This is a separate interface so implementations aren't forced to provide it.

    ISP Compliance: Clients that only need wake can depend on IWaker alone.
    Clients that need polling can require both IWaker and IReadinessPoller.

    Example:
        # HF supports both
        class HFInferenceWaker(IWaker, IReadinessPoller):
            pass

        # Replicate only supports wake
        class ReplicateWaker(IWaker):
            pass  # Not forced to implement poll_until_ready
    """

    @abstractmethod
    async def poll_until_ready(self, endpoint: "Endpoint", timeout: int) -> bool:
        """Poll endpoint until ready or timeout.

        Repeatedly checks endpoint status until it's ready to accept requests,
        or timeout is reached.

        Args:
            endpoint: Endpoint to poll
            timeout: Max seconds to wait

        Returns:
            True if endpoint became ready, False if timeout

        Contract:
        - MUST poll endpoint status (not full inference)
        - MUST return within timeout seconds
        - MUST return bool (True = ready, False = timeout)
        - SHOULD use reasonable poll interval (5-10s)
        """
        pass
