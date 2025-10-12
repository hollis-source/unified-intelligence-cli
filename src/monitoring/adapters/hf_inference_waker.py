"""HuggingFace Inference API waker adapter.

Implements waking and readiness polling for HuggingFace Inference API endpoints.
"""

import asyncio
import time
from typing import TYPE_CHECKING
import aiohttp

if TYPE_CHECKING:
    from ..entities import Endpoint, WakeResult

from ..entities import WakeResult
from ..interfaces import IWaker, IReadinessPoller


class HFInferenceWaker(IWaker, IReadinessPoller):
    """Waker for HuggingFace Inference API with readiness polling.

    ISP Compliance:
    - Implements both IWaker (basic wake) and IReadinessPoller (optional polling)
    - Clients can depend on IWaker alone if they don't need polling
    - This adapter provides full capabilities for HF Inference API

    Clean Architecture:
    - No knowledge of use cases or business logic
    - Pure adapter for HF Inference API wake protocol
    """

    async def wake(self, endpoint: "Endpoint") -> "WakeResult":
        """Wake sleeping HF Inference API endpoint.

        Sends minimal inference request to trigger model loading.

        Args:
            endpoint: Endpoint to wake

        Returns:
            WakeResult with wake outcome

        Contract:
            - MUST send wake request (minimal inference)
            - MUST return WakeResult (never None)
            - MUST NOT wait for readiness (just trigger wake)
        """
        # Get auth token from endpoint config (LSP-compliant)
        token = self._get_token_from_config(endpoint)
        auth_headers = endpoint.get_auth_header(token)

        # Minimal wake payload (single token inference)
        payload = {
            "inputs": "wake",
            "parameters": {"max_new_tokens": 1}
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    endpoint.url,
                    headers={**auth_headers, "Content-Type": "application/json"},
                    json=payload
                ) as response:
                    # Any response (even 503) means wake request was received
                    if response.status in (200, 503):
                        return WakeResult(
                            success=True,
                            is_ready=(response.status == 200),
                            wake_time_s=0  # Updated by use case
                        )
                    else:
                        body = await response.text()
                        return WakeResult(
                            success=False,
                            is_ready=False,
                            error_message=f"Wake failed with status {response.status}: {body[:100]}"
                        )

        except aiohttp.ClientError as e:
            return WakeResult(
                success=False,
                is_ready=False,
                error_message=f"Network error during wake: {type(e).__name__}: {str(e)}"
            )

    async def poll_until_ready(self, endpoint: "Endpoint", timeout: int) -> bool:
        """Poll HF Inference API until ready or timeout.

        ISP Compliance: This is an optional capability.
        Clients that only need wake can depend on IWaker alone.

        Args:
            endpoint: Endpoint to poll
            timeout: Maximum seconds to poll

        Returns:
            True if ready within timeout, False otherwise

        Contract:
            - MUST poll until ready or timeout
            - SHOULD use exponential backoff to reduce API calls
            - MUST respect timeout parameter
        """
        token = self._get_token_from_config(endpoint)
        auth_headers = endpoint.get_auth_header(token)

        # Minimal health check payload
        payload = {
            "inputs": "ready check",
            "parameters": {"max_new_tokens": 1}
        }

        start_time = time.time()
        poll_interval = 2  # Start with 2s interval
        max_interval = 10  # Cap at 10s

        while (time.time() - start_time) < timeout:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        endpoint.url,
                        headers={**auth_headers, "Content-Type": "application/json"},
                        json=payload
                    ) as response:
                        # 200 = ready
                        if response.status == 200:
                            return True

                        # 503 = still loading, continue polling
                        # Other errors = failed, stop polling
                        if response.status != 503:
                            return False

            except aiohttp.ClientError:
                # Network errors = not ready, continue polling
                pass

            # Exponential backoff (2s → 4s → 8s → 10s → 10s...)
            await asyncio.sleep(poll_interval)
            poll_interval = min(poll_interval * 2, max_interval)

        # Timeout reached
        return False

    def _get_token_from_config(self, endpoint: "Endpoint") -> str:
        """Extract token from endpoint auth_config.

        LSP Compliance: Uses standardized auth_config structure.

        Args:
            endpoint: Endpoint with auth_config

        Returns:
            Auth token string

        Raises:
            ValueError: If token_env not found in config or environment
        """
        import os

        token_env = endpoint.auth_config.get("token_env", "HF_TOKEN")
        token = os.getenv(token_env)

        if not token:
            raise ValueError(
                f"Auth token not found in environment variable: {token_env}"
            )

        return token
