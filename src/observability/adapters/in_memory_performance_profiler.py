"""In-memory performance profiler adapter for testing and development.

Stores performance metrics in memory without requiring external database.
Useful for unit tests and local development.
"""

from datetime import datetime
from typing import Dict, List, Optional
from collections import defaultdict
import logging
import statistics

from ..interfaces import IPerformanceProfiler
from ..entities import PerformanceMetric, ProfileSummary, OperationProfile, MetricType

logger = logging.getLogger(__name__)


class InMemoryPerformanceProfiler(IPerformanceProfiler):
    """In-memory performance profiler implementation for testing.

    Stores performance metrics in a list with in-memory aggregation and analysis.
    Provides simple implementation of IPerformanceProfiler contract without
    requiring external dependencies (SQLite, PostgreSQL, etc.).

    Thread-safe for single-threaded test environments.
    For production, use SQLitePerformanceProfiler or PostgreSQLPerformanceProfiler.
    """

    def __init__(self):
        """Initialize empty metric storage."""
        self._metrics: List[PerformanceMetric] = []

    def record_metric(self, metric: PerformanceMetric) -> None:
        """Record a performance metric."""
        if not isinstance(metric, PerformanceMetric):
            raise ValueError(f"Expected PerformanceMetric, got {type(metric)}")

        self._metrics.append(metric)
        # Keep sorted by timestamp (newest first)
        self._metrics.sort(key=lambda m: m.timestamp, reverse=True)

        logger.debug(
            f"Recorded metric: {metric.operation_name} "
            f"[{metric.metric_type.value}] = {metric.value} {metric.unit}"
        )

    def get_metrics(
        self,
        operation_name: Optional[str] = None,
        metric_type: Optional[MetricType] = None,
        project_id: Optional[str] = None,
        agent_name: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: Optional[int] = None,
    ) -> List[PerformanceMetric]:
        """Get performance metrics matching filters."""
        filtered = self._filter_metrics(
            operation_name, metric_type, project_id, agent_name, start_time, end_time
        )

        # Apply limit
        if limit is not None:
            filtered = filtered[:limit]

        return filtered

    def get_summary(
        self,
        operation_name: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> ProfileSummary:
        """Get performance summary for an operation."""
        # Get metrics for this operation
        metrics = self._filter_metrics(
            operation_name=operation_name,
            start_time=start_time,
            end_time=end_time,
        )

        if not metrics:
            # No metrics, return empty summary
            now = datetime.now()
            return ProfileSummary(
                operation_name=operation_name,
                metric_count=0,
                start_time=start_time or now,
                end_time=end_time or now,
            )

        # Calculate time range
        actual_start = min(m.timestamp for m in metrics)
        actual_end = max(m.timestamp for m in metrics)

        # Calculate duration statistics
        duration_metrics = [m for m in metrics if m.metric_type == MetricType.DURATION]
        duration_stats = self._calculate_duration_stats(duration_metrics)

        # Calculate CPU statistics
        cpu_metrics = [m for m in metrics if m.metric_type == MetricType.CPU_USAGE]
        cpu_stats = self._calculate_cpu_stats(cpu_metrics)

        # Calculate memory statistics
        memory_metrics = [m for m in metrics if m.metric_type == MetricType.MEMORY_USAGE]
        memory_stats = self._calculate_memory_stats(memory_metrics)

        # Calculate throughput
        throughput_metrics = [m for m in metrics if m.metric_type == MetricType.THROUGHPUT]
        throughput_stats = self._calculate_throughput_stats(throughput_metrics)

        # Calculate metrics by type
        metrics_by_type = defaultdict(int)
        for metric in metrics:
            metrics_by_type[metric.metric_type.value] += 1

        return ProfileSummary(
            operation_name=operation_name,
            metric_count=len(metrics),
            start_time=start_time or actual_start,
            end_time=end_time or actual_end,
            avg_duration_ms=duration_stats.get("avg"),
            min_duration_ms=duration_stats.get("min"),
            max_duration_ms=duration_stats.get("max"),
            p50_duration_ms=duration_stats.get("p50"),
            p95_duration_ms=duration_stats.get("p95"),
            p99_duration_ms=duration_stats.get("p99"),
            avg_cpu_percent=cpu_stats.get("avg"),
            max_cpu_percent=cpu_stats.get("max"),
            avg_memory_bytes=memory_stats.get("avg"),
            max_memory_bytes=memory_stats.get("max"),
            avg_throughput=throughput_stats.get("avg"),
            total_operations=len(duration_metrics),
            metrics_by_type=dict(metrics_by_type),
        )

    def get_operation_profile(
        self,
        operation_name: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> OperationProfile:
        """Get detailed profile for an operation."""
        # Get metrics
        metrics = self._filter_metrics(
            operation_name=operation_name,
            start_time=start_time,
            end_time=end_time,
        )

        if not metrics:
            # No metrics, return empty profile
            return OperationProfile(
                operation_name=operation_name,
                invocation_count=0,
                total_duration_ms=0.0,
                avg_duration_ms=0.0,
                failure_count=0,
                success_rate=0.0,
            )

        # Get duration metrics
        duration_metrics = [m for m in metrics if m.metric_type == MetricType.DURATION]

        invocation_count = len(duration_metrics)
        total_duration = sum(m.value for m in duration_metrics)
        avg_duration = total_duration / invocation_count if invocation_count > 0 else 0.0

        # Calculate failure count (assume success unless metadata indicates failure)
        failure_count = sum(
            1 for m in duration_metrics
            if m.metadata.get("success", True) is False
        )
        success_count = invocation_count - failure_count
        success_rate = (success_count / invocation_count * 100.0) if invocation_count > 0 else 0.0

        # Get summary
        summary = self.get_summary(operation_name, start_time, end_time)

        return OperationProfile(
            operation_name=operation_name,
            invocation_count=invocation_count,
            total_duration_ms=total_duration,
            avg_duration_ms=avg_duration,
            failure_count=failure_count,
            success_rate=success_rate,
            summary=summary,
        )

    def get_slow_operations(
        self,
        threshold_ms: float = 1000.0,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: Optional[int] = None,
    ) -> List[OperationProfile]:
        """Identify slow operations."""
        # Get all duration metrics
        duration_metrics = [
            m for m in self._filter_metrics(
                metric_type=MetricType.DURATION,
                start_time=start_time,
                end_time=end_time,
            )
        ]

        # Group by operation
        by_operation: Dict[str, List[PerformanceMetric]] = defaultdict(list)
        for metric in duration_metrics:
            by_operation[metric.operation_name].append(metric)

        # Calculate profiles
        profiles = []
        for op_name, op_metrics in by_operation.items():
            avg_duration = statistics.mean(m.value for m in op_metrics)
            if avg_duration > threshold_ms:
                profile = self.get_operation_profile(op_name, start_time, end_time)
                profiles.append(profile)

        # Sort by average duration (slowest first)
        profiles.sort(key=lambda p: p.avg_duration_ms, reverse=True)

        # Apply limit
        if limit is not None:
            profiles = profiles[:limit]

        return profiles

    def delete_metrics(
        self,
        operation_name: Optional[str] = None,
        before: Optional[datetime] = None,
    ) -> int:
        """Delete performance metrics matching filters."""
        if operation_name is None and before is None:
            raise ValueError("At least one filter must be specified for safety")

        # Find metrics to delete
        to_delete = []
        for metric in self._metrics:
            if operation_name is not None and metric.operation_name != operation_name:
                continue
            if before is not None and metric.timestamp >= before:
                continue
            to_delete.append(metric)

        # Remove from storage
        for metric in to_delete:
            self._metrics.remove(metric)

        deleted_count = len(to_delete)
        logger.info(f"Deleted {deleted_count} performance metrics")
        return deleted_count

    def _filter_metrics(
        self,
        operation_name: Optional[str] = None,
        metric_type: Optional[MetricType] = None,
        project_id: Optional[str] = None,
        agent_name: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> List[PerformanceMetric]:
        """Filter metrics by specified criteria."""
        filtered = self._metrics

        if operation_name is not None:
            filtered = [m for m in filtered if m.operation_name == operation_name]

        if metric_type is not None:
            filtered = [m for m in filtered if m.metric_type == metric_type]

        if project_id is not None:
            filtered = [m for m in filtered if m.project_id == project_id]

        if agent_name is not None:
            filtered = [m for m in filtered if m.agent_name == agent_name]

        if start_time is not None:
            filtered = [m for m in filtered if m.timestamp >= start_time]

        if end_time is not None:
            filtered = [m for m in filtered if m.timestamp < end_time]

        return filtered

    def _calculate_duration_stats(self, metrics: List[PerformanceMetric]) -> Dict[str, float]:
        """Calculate duration statistics."""
        if not metrics:
            return {}

        values = [m.value for m in metrics]
        values_sorted = sorted(values)

        stats = {
            "avg": statistics.mean(values),
            "min": min(values),
            "max": max(values),
        }

        # Percentiles
        if len(values_sorted) >= 2:
            stats["p50"] = statistics.median(values)
            stats["p95"] = values_sorted[int(len(values_sorted) * 0.95)]
            stats["p99"] = values_sorted[int(len(values_sorted) * 0.99)]

        return stats

    def _calculate_cpu_stats(self, metrics: List[PerformanceMetric]) -> Dict[str, float]:
        """Calculate CPU usage statistics."""
        if not metrics:
            return {}

        values = [m.value for m in metrics]
        return {
            "avg": statistics.mean(values),
            "max": max(values),
        }

    def _calculate_memory_stats(self, metrics: List[PerformanceMetric]) -> Dict[str, float]:
        """Calculate memory usage statistics."""
        if not metrics:
            return {}

        values = [m.value for m in metrics]
        return {
            "avg": statistics.mean(values),
            "max": max(values),
        }

    def _calculate_throughput_stats(self, metrics: List[PerformanceMetric]) -> Dict[str, float]:
        """Calculate throughput statistics."""
        if not metrics:
            return {}

        values = [m.value for m in metrics]
        return {
            "avg": statistics.mean(values),
        }

    def get_all_metrics(self) -> List[PerformanceMetric]:
        """Get all performance metrics (no filtering).

        Returns:
            List of all PerformanceMetric objects

        Note:
            Not part of IPerformanceProfiler interface. Useful for testing.
        """
        return self._metrics.copy()

    def clear(self) -> None:
        """Clear all performance metrics.

        Note:
            Not part of IPerformanceProfiler interface. Useful for test cleanup.
        """
        count = len(self._metrics)
        self._metrics.clear()
        logger.debug(f"Cleared {count} performance metrics")
