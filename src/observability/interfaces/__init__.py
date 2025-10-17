from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, List, Optional

from src.observability.entities import (
    Trace,
    TraceStatus,
    CostEntry,
    UsageEntry,
    Alert,
    AlertRule,
    PerformanceMetric,
    PerformanceSummary,
)


class ITracer(ABC):
    @abstractmethod
    def start_trace(self, operation_name: str, tags: Optional[Dict] = None) -> Trace: ...

    @abstractmethod
    def finish_trace(self, trace: Trace, status: TraceStatus, error_message: Optional[str] = None) -> Trace: ...

    @abstractmethod
    def get_trace(self, trace_id: str) -> Optional[Trace]: ...

    @abstractmethod
    def get_traces(self, operation_name: Optional[str] = None) -> List[Trace]: ...

    @abstractmethod
    def delete_traces(self, before) -> int: ...


class ICostTracker(ABC):
    @abstractmethod
    def record_cost(self, entry: CostEntry) -> None: ...

    @abstractmethod
    def get_costs(self, project_id: Optional[str] = None, trace_id: Optional[str] = None) -> List[CostEntry]: ...

    @abstractmethod
    def get_cost_summary(self, project_id: Optional[str] = None) -> any: ...

    @abstractmethod
    def get_cost_by_agent(self, project_id: Optional[str] = None) -> Dict[str, float]: ...


class IUsageTracker(ABC):
    @abstractmethod
    def record_usage(self, entry: UsageEntry) -> None: ...

    @abstractmethod
    def get_usage(self, project_id: Optional[str] = None, trace_id: Optional[str] = None) -> List[UsageEntry]: ...


class IAlertManager(ABC):
    @abstractmethod
    def add_rule(self, rule: AlertRule) -> None: ...

    @abstractmethod
    def create_alert(self, alert: Alert) -> None: ...

    @abstractmethod
    def get_alerts(self, severity=None) -> List[Alert]: ...


class IPerformanceProfiler(ABC):
    @abstractmethod
    def record_metric(self, metric: PerformanceMetric) -> None: ...

    @abstractmethod
    def get_metrics(self, operation_name: Optional[str] = None, project_id: Optional[str] = None) -> List[PerformanceMetric]: ...

    @abstractmethod
    def get_summary(self, operation_name: str) -> PerformanceSummary: ...

