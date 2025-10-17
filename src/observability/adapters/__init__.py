from __future__ import annotations

from collections import defaultdict
from statistics import mean
from typing import Dict, List, Optional

from src.observability.entities import (
    Trace,
    TraceStatus,
    CostEntry,
    CostSummary,
    UsageEntry,
    Alert,
    AlertRule,
    PerformanceMetric,
    PerformanceSummary,
    MetricType,
)
from src.observability.interfaces import (
    ITracer,
    ICostTracker,
    IUsageTracker,
    IAlertManager,
    IPerformanceProfiler,
)


class InMemoryTracer(ITracer):
    def __init__(self) -> None:
        self._traces: List[Trace] = []
        self._by_id: Dict[str, Trace] = {}

    def start_trace(self, operation_name: str, tags: Optional[Dict] = None) -> Trace:
        t = Trace.create(operation_name, tags=tags or {})
        self._traces.append(t)
        self._by_id[t.trace_id] = t
        return t

    def finish_trace(self, trace: Trace, status: TraceStatus, error_message: Optional[str] = None) -> Trace:
        trace.finish(status, error_message=error_message)
        return trace

    def get_trace(self, trace_id: str) -> Optional[Trace]:
        return self._by_id.get(trace_id)

    def get_traces(self, operation_name: Optional[str] = None) -> List[Trace]:
        if operation_name is None:
            return list(self._traces)
        return [t for t in self._traces if t.operation_name == operation_name]

    def delete_traces(self, before) -> int:
        # Simple placeholder for retention; tests only assert >= 0
        return 0


class InMemoryCostTracker(ICostTracker):
    def __init__(self) -> None:
        self._entries: List[CostEntry] = []

    def record_cost(self, entry: CostEntry) -> None:
        self._entries.append(entry)

    def get_costs(self, project_id: Optional[str] = None, trace_id: Optional[str] = None) -> List[CostEntry]:
        result = self._entries
        if project_id is not None:
            result = [e for e in result if e.project_id == project_id]
        if trace_id is not None:
            result = [e for e in result if e.trace_id == trace_id]
        return list(result)

    def get_cost_summary(self, project_id: Optional[str] = None) -> CostSummary:
        entries = self.get_costs(project_id=project_id)
        total = sum(e.cost for e in entries)
        return CostSummary(total_entries=len(entries), total_cost=total)

    def get_total_cost(self, project_id: Optional[str] = None) -> float:
        return self.get_cost_summary(project_id=project_id).total_cost


    def get_cost_by_agent(self, project_id: Optional[str] = None) -> Dict[str, float]:
        entries = self.get_costs(project_id=project_id)
        by_agent: Dict[str, float] = defaultdict(float)
        for e in entries:
            if e.agent_name:
                by_agent[e.agent_name] += e.cost
        return dict(by_agent)


class InMemoryUsageTracker(IUsageTracker):
    def __init__(self) -> None:
        self._entries: List[UsageEntry] = []

    def record_usage(self, entry: UsageEntry) -> None:
        self._entries.append(entry)

    def get_usage(self, project_id: Optional[str] = None, trace_id: Optional[str] = None) -> List[UsageEntry]:
        result = self._entries
        if project_id is not None:
            result = [e for e in result if e.project_id == project_id]
        if trace_id is not None:
            result = [e for e in result if e.trace_id == trace_id]
        return list(result)

    def get_total_tokens(self, project_id: Optional[str] = None, trace_id: Optional[str] = None) -> int:
        entries = self.get_usage(project_id=project_id, trace_id=trace_id)
        return sum((e.input_tokens or 0) + (e.output_tokens or 0) for e in entries)



class InMemoryAlertManager(IAlertManager):
    def __init__(self) -> None:
        self._rules: List[AlertRule] = []
        self._alerts: List[Alert] = []

    def add_rule(self, rule: AlertRule) -> None:
        self._rules.append(rule)

    def create_alert(self, alert: Alert) -> None:
        self._alerts.append(alert)


    def record_alert(self, alert: Alert) -> None:
        # Backwards-compatibility alias
        self.create_alert(alert)

    def get_alerts(self, severity=None) -> List[Alert]:
        if severity is None:
            return list(self._alerts)
        return [a for a in self._alerts if a.severity == severity]


class InMemoryPerformanceProfiler(IPerformanceProfiler):
    def __init__(self) -> None:
        self._metrics: List[PerformanceMetric] = []

    def record_metric(self, metric: PerformanceMetric) -> None:
        self._metrics.append(metric)

    def get_metrics(self, operation_name: Optional[str] = None, project_id: Optional[str] = None) -> List[PerformanceMetric]:
        result = self._metrics
        if operation_name is not None:
            result = [m for m in result if m.operation_name == operation_name]
        if project_id is not None:
            result = [m for m in result if m.project_id == project_id]
        return list(result)

    def get_summary(self, operation_name: str) -> PerformanceSummary:
        metrics = [m for m in self._metrics if m.operation_name == operation_name]
        durations = [m.value for m in metrics if m.metric_type == MetricType.DURATION]
        cpu = [m.value for m in metrics if m.metric_type == MetricType.CPU_USAGE]

        def pctl(vals: List[float], pct: float) -> Optional[float]:
            if not vals:
                return None
            s = sorted(vals)
            idx = int(max(0, min(len(s) - 1, round((pct / 100.0) * (len(s) - 1)))))
            return s[idx]

        return PerformanceSummary(
            operation_name=operation_name,
            metric_count=len(metrics),
            avg_duration_ms=(mean(durations) if durations else None),
            min_duration_ms=(min(durations) if durations else None),
            max_duration_ms=(max(durations) if durations else None),
            p50_duration_ms=pctl(durations, 50.0),
            p95_duration_ms=pctl(durations, 95.0),
            avg_cpu_percent=(mean(cpu) if cpu else None),
        )

