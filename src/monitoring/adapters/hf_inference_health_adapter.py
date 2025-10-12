"""HuggingFace Inference API health checker adapter.

Implements health checking for HuggingFace Inference API endpoints.
"""

import time
from typing import TYPE_CHECKING
import aiohttp

if TYPE_CHECKING:
    from ..entities import Endpoint, HealthCheckResponse

from ..entities import EndpointState, HealthCheckErrorCode, HealthCheckResponse
from ..interfaces import BaseHealthChecker


class HFInferenceHealthAdapter(BaseHealthChecker):
    """Health checker for HuggingFace Inference API.

    Extends BaseHealthChecker for LSP compliance:
    - Timeout enforcement handled by base class
    - Exception handling handled by base class
    - Only implements provider-specific health check logic

    HuggingFace Inference API behavior:
    - 200: Model loaded and ready (HEALTHY)
    - 503 + "loading": Model is loading (SLEEPING)
    - 503 + other: Service unavailable (FAILED)
    - 429: Rate limited (RATE_LIMITED)
    - 401/403: Auth failed (AUTH_FAILED)
    - 500: Internal error (INTERNAL_ERROR)
    - Network errors: NETWORK_ERROR
    """

    async def _check_impl(self, endpoint: "Endpoint") -> "HealthCheckResponse":
        """Implementation of HF Inference API health check.

        Note: BaseHealthChecker enforces timeout and exception handling,
        so this method can focus on provider-specific logic.

        Args:
            endpoint: Endpoint to check

        Returns:
            HealthCheckResponse with standardized state and error codes
        """
        start_time = time.time()

        # Get auth headers using standardized endpoint.get_auth_header()
        # This ensures LSP compliance - all providers use same auth_config structure
        auth_headers = endpoint.get_auth_header(
            self._get_token_from_config(endpoint)
        )

        # Minimal health check payload (single token inference)
        # This triggers model loading if sleeping without heavy computation
        payload = {
            "inputs": "health check",
            "parameters": {"max_new_tokens": 1}
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    endpoint.url,
                    headers={**auth_headers, "Content-Type": "application/json"},
                    json=payload
                ) as response:
                    response_time_ms = (time.time() - start_time) * 1000

                    # Map HF status codes to standardized states and error codes
                    if response.status == 200:
                        return HealthCheckResponse(
                            status=EndpointState.HEALTHY,
                            response_time_ms=response_time_ms
                        )

                    elif response.status == 503:
                        # Check if model is loading (cold start)
                        body = await response.text()
                        if "loading" in body.lower() or "model is currently loading" in body.lower():
                            return HealthCheckResponse(
                                status=EndpointState.SLEEPING,
                                response_time_ms=response_time_ms,
                                error_code=HealthCheckErrorCode.MODEL_LOADING,
                                error_details={"message": "Model is loading"}
                            )
                        else:
                            return HealthCheckResponse(
                                status=EndpointState.FAILED,
                                response_time_ms=response_time_ms,
                                error_code=HealthCheckErrorCode.INTERNAL_ERROR,
                                error_details={"status_code": 503, "body": body[:200]}
                            )

                    elif response.status == 429:
                        return HealthCheckResponse(
                            status=EndpointState.DEGRADED,
                            response_time_ms=response_time_ms,
                            error_code=HealthCheckErrorCode.RATE_LIMITED,
                            error_details={"status_code": 429}
                        )

                    elif response.status in (401, 403):
                        return HealthCheckResponse(
                            status=EndpointState.FAILED,
                            error_code=HealthCheckErrorCode.AUTH_FAILED,
                            error_details={"status_code": response.status}
                        )

                    elif response.status >= 500:
                        return HealthCheckResponse(
                            status=EndpointState.FAILED,
                            error_code=HealthCheckErrorCode.INTERNAL_ERROR,
                            error_details={"status_code": response.status}
                        )

                    else:
                        # Unexpected status code
                        return HealthCheckResponse(
                            status=EndpointState.FAILED,
                            error_code=HealthCheckErrorCode.UNKNOWN,
                            error_details={"status_code": response.status}
                        )

        except aiohttp.ClientError as e:
            # Network errors (connection refused, DNS failure, etc.)
            return HealthCheckResponse(
                status=EndpointState.FAILED,
                error_code=HealthCheckErrorCode.NETWORK_ERROR,
                error_details={"exception": type(e).__name__, "message": str(e)}
            )

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
