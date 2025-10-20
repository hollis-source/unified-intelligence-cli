from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional
from uuid import uuid4
from datetime import datetime


# Phase 1: Tracing
class TraceStatus(Enum):
    RUNNING = auto()
    SUCCESS = auto()
    ERROR = auto()


@dataclass
class Trace:
    trace_id: str
    operation_name: str
    start_time: datetime
    end_time: Optional[datetime] = None
    status: TraceStatus = TraceStatus.RUNNING
    error_message: Optional[str] = None
    tags: Dict[str, Any] = field(default_factory=dict)

    @staticmethod
    def create(operation_name: str, tags: Optional[Dict[str, Any]] = None) -> "Trace":
        return Trace(trace_id=str(uuid4()), operation_name=operation_name, start_time=datetime.now(), tags=tags or {})

    def with_start_time(self, when: datetime) -> "Trace":
        self.start_time = when
        return self

    def finish(self, status: TraceStatus, when: Optional[datetime] = None, error_message: Optional[str] = None) -> "Trace":
        self.end_time = when or datetime.now()
        self.status = status
        self.error_message = error_message
        return self


# Phase 2: Cost tracking
@dataclass
class CostEntry:
    model_name: str
    provider: str
    input_tokens: int
    output_tokens: int
    input_cost_per_1k: float
    output_cost_per_1k: float
    project_id: Optional[str] = None
    agent_name: Optional[str] = None
    trace_id: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)

    @property
    def cost(self) -> float:
        return (self.input_tokens / 1000.0) * self.input_cost_per_1k + (self.output_tokens / 1000.0) * self.output_cost_per_1k

    @staticmethod
    def create(
        model_name: str,
        provider: str,
        input_tokens: int,
        output_tokens: int,
        input_cost_per_1k: float,
        output_cost_per_1k: float,
        project_id: Optional[str] = None,
        agent_name: Optional[str] = None,
        trace_id: Optional[str] = None,
    ) -> "CostEntry":
        return CostEntry(
            model_name=model_name,
            provider=provider,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            input_cost_per_1k=input_cost_per_1k,
            output_cost_per_1k=output_cost_per_1k,
            project_id=project_id,
            agent_name=agent_name,
            trace_id=trace_id,
        )


@dataclass
class CostSummary:
    total_entries: int
    total_cost: float


# Phase 3: Usage analytics
class OperationType(Enum):
    CHAT = auto()
    EMBEDDING = auto()
    IMAGE = auto()


@dataclass
class UsageEntry:
    model_name: str
    provider: str
    input_tokens: int
    output_tokens: int
    operation_type: OperationType
    project_id: Optional[str] = None
    agent_name: Optional[str] = None
    trace_id: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)

    @staticmethod
    def create(
        model_name: str,
        provider: str,
        input_tokens: int,
        output_tokens: int,
        operation_type: OperationType,
        project_id: Optional[str] = None,
        agent_name: Optional[str] = None,
        trace_id: Optional[str] = None,
    ) -> "UsageEntry":
        return UsageEntry(
            model_name=model_name,
            provider=provider,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            operation_type=operation_type,
            project_id=project_id,
            agent_name=agent_name,
            trace_id=trace_id,
        )


# Phase 4: Alerts
class AlertSeverity(Enum):
    INFO = auto()
    WARNING = auto()
    ERROR = auto()
    CRITICAL = auto()


@dataclass
class AlertRule:
    id: str
    name: str
    description: str
    condition: Callable[[], bool]
    severity: AlertSeverity
    cooldown_minutes: int = 0

    @staticmethod
    def create(
        name: str,
        description: str,
        condition: Callable[[], bool],
        severity: AlertSeverity,
        cooldown_minutes: int = 0,
    ) -> "AlertRule":
        return AlertRule(id=str(uuid4()), name=name, description=description, condition=condition, severity=severity, cooldown_minutes=cooldown_minutes)


@dataclass
class Alert:
    id: str
    severity: AlertSeverity
    message: str
    source: str
    created_at: datetime = field(default_factory=datetime.now)
    rule_id: Optional[str] = None

    @staticmethod
    def create(
        severity: AlertSeverity,
        message: str,
        source: str,
        rule_id: Optional[str] = None,
    ) -> "Alert":
        return Alert(id=str(uuid4()), severity=severity, message=message, source=source, rule_id=rule_id)


# Phase 5: Performance profiling
class MetricType(Enum):
    DURATION = auto()
    CPU_USAGE = auto()
    MEMORY_USAGE = auto()


@dataclass
class PerformanceMetric:
    operation_name: str
    metric_type: MetricType
    value: float
    unit: str
    timestamp: datetime = field(default_factory=datetime.now)
    trace_id: Optional[str] = None
    project_id: Optional[str] = None
    agent_name: Optional[str] = None

    @staticmethod
    def create(
        operation_name: str,
        metric_type: MetricType,
        value: float,
        unit: str,
        trace_id: Optional[str] = None,
        project_id: Optional[str] = None,
        agent_name: Optional[str] = None,
    ) -> "PerformanceMetric":
        return PerformanceMetric(
            operation_name=operation_name,
            metric_type=metric_type,
            value=value,
            unit=unit,
            trace_id=trace_id,
            project_id=project_id,
            agent_name=agent_name,
        )


@dataclass
class PerformanceSummary:
    operation_name: str
    metric_count: int
    avg_duration_ms: Optional[float]
    min_duration_ms: Optional[float]
    max_duration_ms: Optional[float]
    p50_duration_ms: Optional[float]
    p95_duration_ms: Optional[float]
    avg_cpu_percent: Optional[float]

