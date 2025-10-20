from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, Optional
from datetime import datetime


class EndpointPriority(Enum):
    LOW = auto()
    MEDIUM = auto()
    HIGH = auto()


class WakeStrategy(Enum):
    PRIORITY_BASED = auto()


class EndpointState(Enum):
    UNKNOWN = auto()
    HEALTHY = auto()
    DEGRADED = auto()
    SLEEPING = auto()
    FAILED = auto()


class HealthCheckErrorCode(Enum):
    UNKNOWN = auto()
    AUTH_FAILED = auto()
    RATE_LIMITED = auto()
    INTERNAL_ERROR = auto()
    MODEL_LOADING = auto()
    NETWORK_ERROR = auto()


@dataclass
class Endpoint:
    id: str
    provider: str
    url: str
    priority: EndpointPriority
    wake_strategy: WakeStrategy
    auth_config: Optional[Dict[str, Any]] = None
    wake_timeout: int = 30


@dataclass
class HealthStatus:
    endpoint_id: str
    state: EndpointState
    last_check_time: datetime
    response_time_ms: Optional[float] = None
    consecutive_failures: int = 0


@dataclass
class HealthCheckResponse:
    status: EndpointState
    response_time_ms: Optional[float]
    error_code: Optional[HealthCheckErrorCode] = None


@dataclass
class WakeResult:
    success: bool
    error: Optional[str] = None

