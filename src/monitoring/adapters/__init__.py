from __future__ import annotations

import asyncio
import time
from typing import Optional

from prometheus_client import Counter, Gauge, Histogram  # type: ignore

from src.monitoring.entities import (
    Endpoint,
    EndpointState,
    HealthStatus,
    HealthCheckResponse,
    HealthCheckErrorCode,
    WakeResult,
)
from src.monitoring.interfaces import IMetricsExporter, IWaker, IReadinessPoller


class PrometheusMetricsAdapter(IMetricsExporter):
    def __init__(self) -> None:
        # Minimal metrics (module-level registry)
        self._health_state = Gauge(
            "endpoint_health_state",
            "Numeric health state (0=UNKNOWN,1=HEALTHY,2=DEGRADED,3=SLEEPING,4=FAILED)",
            ["endpoint_id"],
        )
        self._response_time = Histogram(
            "endpoint_response_time_ms",
            "Endpoint response time in ms",
            ["endpoint_id"],
            buckets=(10, 50, 100, 200, 500, 1000, 2000),
        )
        self._wake_attempts = Counter(
            "endpoint_wake_attempts_total",
            "Wake attempts",
            ["endpoint_id", "success"],
        )
        self._fallbacks = Counter(
            "endpoint_fallback_total",
            "Fallback occurrences",
            ["primary", "fallback"],
        )
        self._consecutive_failures = Gauge(
            "endpoint_consecutive_failures",
            "Consecutive failure count",
            ["endpoint_id"],
        )

    def _state_to_numeric(self, state: EndpointState) -> int:
        mapping = {
            EndpointState.UNKNOWN: 0,
            EndpointState.HEALTHY: 1,
            EndpointState.DEGRADED: 2,
            EndpointState.SLEEPING: 3,
            EndpointState.FAILED: 4,
        }
        return mapping.get(state, 0)

    async def record_health_check(self, endpoint: Endpoint, status: HealthStatus) -> None:
        try:
            self._health_state.labels(endpoint_id=endpoint.id).set(self._state_to_numeric(status.state))
            if status.response_time_ms is not None:
                self._response_time.labels(endpoint_id=endpoint.id).observe(status.response_time_ms)
        except Exception:
            # Contract: never raise
            pass

    async def record_wake_attempt(self, endpoint: Endpoint, wake_time_s: float, success: bool) -> None:
        try:
            self._wake_attempts.labels(endpoint_id=endpoint.id, success=str(success).lower()).inc()
        except Exception:
            pass

    async def record_fallback(self, primary_endpoint_id: str, fallback_endpoint_id: str, fallback_count: int) -> None:
        try:
            self._fallbacks.labels(primary=primary_endpoint_id, fallback=fallback_endpoint_id).inc()
        except Exception:
            pass

    async def increment_consecutive_failures(self, endpoint: Endpoint, failure_count: int) -> None:
        try:
            self._consecutive_failures.labels(endpoint_id=endpoint.id).set(failure_count)
        except Exception:
            pass


class HFInferenceHealthAdapter:
    async def _request(self, url: str, headers: dict, json_payload: dict):
        import aiohttp  # local import for test environment
        async with aiohttp.ClientSession() as session:
            start = time.perf_counter()
            try:
                async with session.post(url, headers=headers, json=json_payload) as resp:
                    text = await resp.text()
                    elapsed_ms = (time.perf_counter() - start) * 1000.0
                    return resp.status, text, elapsed_ms
            except Exception as e:
                elapsed_ms = (time.perf_counter() - start) * 1000.0
                raise e

    def _headers_from_auth(self, endpoint: Endpoint) -> dict:
        headers = {"Content-Type": "application/json"}
        cfg = endpoint.auth_config or {}
        if cfg.get("type") == "bearer":
            import os
            token_env = cfg.get("token_env")
            token = os.environ.get(token_env or "")
            if not token:
                raise RuntimeError("missing_token")
            headers["Authorization"] = f"Bearer {token}"
        return headers

    def _payload(self) -> dict:
        return {"inputs": "wake", "parameters": {"max_new_tokens": 1}}

    async def check(self, endpoint: Endpoint) -> HealthCheckResponse:
        try:
            headers = self._headers_from_auth(endpoint)
        except Exception:
            return HealthCheckResponse(status=EndpointState.FAILED, response_time_ms=None, error_code=HealthCheckErrorCode.UNKNOWN)
        try:
            status, text, elapsed_ms = await self._request(endpoint.url, headers, self._payload())
            body_lower = (text or "").lower()
            if status == 200:
                return HealthCheckResponse(status=EndpointState.HEALTHY, response_time_ms=elapsed_ms)
            if status == 429:
                return HealthCheckResponse(status=EndpointState.DEGRADED, response_time_ms=elapsed_ms, error_code=HealthCheckErrorCode.RATE_LIMITED)
            if status in (401, 403):
                return HealthCheckResponse(status=EndpointState.FAILED, response_time_ms=elapsed_ms, error_code=HealthCheckErrorCode.AUTH_FAILED)
            if status == 503:
                if "loading" in body_lower:
                    return HealthCheckResponse(status=EndpointState.SLEEPING, response_time_ms=elapsed_ms, error_code=HealthCheckErrorCode.MODEL_LOADING)
                return HealthCheckResponse(status=EndpointState.FAILED, response_time_ms=elapsed_ms, error_code=HealthCheckErrorCode.INTERNAL_ERROR)
            if status >= 500:
                return HealthCheckResponse(status=EndpointState.FAILED, response_time_ms=elapsed_ms, error_code=HealthCheckErrorCode.INTERNAL_ERROR)
            return HealthCheckResponse(status=EndpointState.FAILED, response_time_ms=elapsed_ms, error_code=HealthCheckErrorCode.UNKNOWN)
        except Exception as e:
            # Map network errors
            return HealthCheckResponse(status=EndpointState.FAILED, response_time_ms=None, error_code=HealthCheckErrorCode.NETWORK_ERROR)


class HFInferenceWaker(IWaker, IReadinessPoller):
    def _headers(self, endpoint: Endpoint) -> dict:
        return HFInferenceHealthAdapter()._headers_from_auth(endpoint)

    def _payload(self) -> dict:
        return {"inputs": "wake", "parameters": {"max_new_tokens": 1}}

    async def wake(self, endpoint: Endpoint) -> WakeResult:
        import aiohttp
        try:
            headers = self._headers(endpoint)
        except Exception as e:
            return WakeResult(success=False, error=str(e))
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(endpoint.url, headers=headers, json=self._payload()) as resp:
                    text = await resp.text()
                    if resp.status == 200:
                        return WakeResult(success=True)
                    if resp.status == 503 and "loading" in (text or "").lower():
                        return WakeResult(success=True)
                    if 400 <= resp.status < 500:
                        return WakeResult(success=False, error=f"HTTP {resp.status}")
                    if resp.status >= 500:
                        return WakeResult(success=False, error=f"HTTP {resp.status}")
                    return WakeResult(success=False, error=f"HTTP {resp.status}")
        except Exception as e:
            return WakeResult(success=False, error=f"Network error: {e}")

    async def poll_until_ready(self, endpoint: Endpoint, timeout: int = 30) -> bool:
        import aiohttp
        deadline = time.time() + timeout
        interval = 2.0
        headers = {}
        try:
            headers = self._headers(endpoint)
        except Exception:
            return False
        async with aiohttp.ClientSession() as session:
            while time.time() < deadline:
                try:
                    async with session.post(endpoint.url, headers=headers, json=self._payload()) as resp:
                        text = await resp.text()
                        if resp.status == 200:
                            return True
                        if resp.status == 503 and "loading" in (text or "").lower():
                            await asyncio.sleep(interval)
                            interval = min(interval * 2, 8.0)
                            continue
                        # stop on other errors
                        return False
                except Exception:
                    return False
            return False

