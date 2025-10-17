from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Protocol

from src.monitoring.entities import Endpoint, HealthStatus


class IWaker(ABC):
    @abstractmethod
    async def wake(self, endpoint: Endpoint): ...


class IReadinessPoller(ABC):
    @abstractmethod
    async def poll_until_ready(self, endpoint: Endpoint, timeout: int = 30) -> bool: ...


class IMetricsExporter(ABC):
    @abstractmethod
    async def record_health_check(self, endpoint: Endpoint, status: HealthStatus) -> None: ...

    @abstractmethod
    async def record_wake_attempt(self, endpoint: Endpoint, wake_time_s: float, success: bool) -> None: ...

    @abstractmethod
    async def record_fallback(self, primary_endpoint_id: str, fallback_endpoint_id: str, fallback_count: int) -> None: ...

    @abstractmethod
    async def increment_consecutive_failures(self, endpoint: Endpoint, failure_count: int) -> None: ...

