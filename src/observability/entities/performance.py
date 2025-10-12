"""Performance profiling domain entities.

Entities for performance monitoring and profiling:
- PerformanceMetric: Individual performance measurement
- ProfileSummary: Aggregated performance statistics
- OperationType: Type of operation being profiled

All entities are immutable (frozen dataclasses) following Clean Architecture.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Optional
from enum import Enum
import uuid


class MetricType(str, Enum):
    """Type of performance metric."""

    DURATION = "duration"  # Operation duration
    CPU_USAGE = "cpu_usage"  # CPU utilization percentage
    MEMORY_USAGE = "memory_usage"  # Memory usage in bytes
    THROUGHPUT = "throughput"  # Operations per second
    LATENCY = "latency"  # Response latency in milliseconds
    CUSTOM = "custom"  # Custom metric


@dataclass(frozen=True)
class PerformanceMetric:
    """Individual performance measurement.

    Immutable entity tracking a single performance metric.
    Records metric type, value, and context.
    """

    id: str
    metric_type: MetricType
    value: float
    unit: str  # e.g., "ms", "bytes", "percent", "ops/sec"
    operation_name: str  # e.g., "api_call", "database_query"
    timestamp: datetime

    # Optional context
    project_id: Optional[str] = None
    task_id: Optional[str] = None
    agent_name: Optional[str] = None
    trace_id: Optional[str] = None  # Link to distributed trace

    # Additional metadata
    metadata: Dict[str, any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate performance metric data."""
        # Validate ID
        if not self.id or not self.id.strip():
            raise ValueError("Metric ID cannot be empty")

        # Validate operation name
        if not self.operation_name or not self.operation_name.strip():
            raise ValueError("Operation name cannot be empty")

        # Validate unit
        if not self.unit or not self.unit.strip():
            raise ValueError("Unit cannot be empty")

        # Validate metric type
        if not isinstance(self.metric_type, MetricType):
            raise ValueError(f"Invalid metric type: {self.metric_type}")

        # Validate value (non-negative for most metrics)
        if self.value < 0 and self.metric_type != MetricType.CUSTOM:
            raise ValueError(f"Metric value cannot be negative: {self.value}")

    @staticmethod
    def create(
        metric_type: MetricType,
        value: float,
        unit: str,
        operation_name: str,
        project_id: Optional[str] = None,
        task_id: Optional[str] = None,
        agent_name: Optional[str] = None,
        trace_id: Optional[str] = None,
        metadata: Optional[Dict[str, any]] = None,
    ) -> "PerformanceMetric":
        """Factory method to create a performance metric with generated ID.

        Args:
            metric_type: Type of metric
            value: Metric value
            unit: Measurement unit
            operation_name: Name of operation being measured
            project_id: Optional project identifier
            task_id: Optional task identifier
            agent_name: Optional agent name
            trace_id: Optional trace identifier
            metadata: Optional metadata

        Returns:
            New PerformanceMetric with generated ID
        """
        return PerformanceMetric(
            id=str(uuid.uuid4()),
            metric_type=metric_type,
            value=value,
            unit=unit,
            operation_name=operation_name,
            timestamp=datetime.now(),
            project_id=project_id,
            task_id=task_id,
            agent_name=agent_name,
            trace_id=trace_id,
            metadata=metadata or {},
        )

    def is_slow(self, threshold: float) -> bool:
        """Check if duration/latency exceeds threshold.

        Args:
            threshold: Threshold value

        Returns:
            True if metric indicates slow performance
        """
        if self.metric_type in (MetricType.DURATION, MetricType.LATENCY):
            return self.value > threshold
        return False

    def is_high_resource(self, threshold: float) -> bool:
        """Check if resource usage exceeds threshold.

        Args:
            threshold: Threshold value (percentage for CPU, bytes for memory)

        Returns:
            True if resource usage is high
        """
        if self.metric_type in (MetricType.CPU_USAGE, MetricType.MEMORY_USAGE):
            return self.value > threshold
        return False

    def to_dict(self) -> Dict[str, any]:
        """Serialize metric to dictionary.

        Returns:
            Dictionary representation of metric
        """
        return {
            "id": self.id,
            "metric_type": self.metric_type.value,
            "value": self.value,
            "unit": self.unit,
            "operation_name": self.operation_name,
            "timestamp": self.timestamp.isoformat(),
            "project_id": self.project_id,
            "task_id": self.task_id,
            "agent_name": self.agent_name,
            "trace_id": self.trace_id,
            "metadata": self.metadata,
        }


@dataclass(frozen=True)
class ProfileSummary:
    """Aggregated performance statistics.

    Immutable summary of performance metrics for an operation or time period.
    """

    operation_name: str
    metric_count: int
    start_time: datetime
    end_time: datetime

    # Duration statistics (if applicable)
    avg_duration_ms: Optional[float] = None
    min_duration_ms: Optional[float] = None
    max_duration_ms: Optional[float] = None
    p50_duration_ms: Optional[float] = None  # Median
    p95_duration_ms: Optional[float] = None  # 95th percentile
    p99_duration_ms: Optional[float] = None  # 99th percentile

    # Resource usage statistics (if applicable)
    avg_cpu_percent: Optional[float] = None
    max_cpu_percent: Optional[float] = None
    avg_memory_bytes: Optional[float] = None
    max_memory_bytes: Optional[float] = None

    # Throughput statistics (if applicable)
    avg_throughput: Optional[float] = None
    total_operations: int = 0

    # Breakdown by metric type
    metrics_by_type: Dict[str, int] = field(default_factory=dict)

    def __post_init__(self):
        """Validate profile summary data."""
        if not self.operation_name or not self.operation_name.strip():
            raise ValueError("Operation name cannot be empty")

        if self.metric_count < 0:
            raise ValueError(f"Metric count cannot be negative: {self.metric_count}")

        if self.start_time > self.end_time:
            raise ValueError("Start time cannot be after end time")

    def has_performance_issues(
        self,
        max_duration_ms: float = 1000.0,
        max_cpu_percent: float = 80.0,
        max_memory_mb: float = 512.0,
    ) -> bool:
        """Check if profile indicates performance issues.

        Args:
            max_duration_ms: Maximum acceptable duration
            max_cpu_percent: Maximum acceptable CPU usage
            max_memory_mb: Maximum acceptable memory usage (MB)

        Returns:
            True if any threshold is exceeded
        """
        if self.avg_duration_ms and self.avg_duration_ms > max_duration_ms:
            return True

        if self.avg_cpu_percent and self.avg_cpu_percent > max_cpu_percent:
            return True

        if self.avg_memory_bytes:
            memory_mb = self.avg_memory_bytes / (1024 * 1024)
            if memory_mb > max_memory_mb:
                return True

        return False

    def get_efficiency_score(self) -> float:
        """Calculate efficiency score (0.0 to 1.0).

        Based on duration and resource usage.
        Lower duration and resource usage = higher score.

        Returns:
            Efficiency score between 0 and 1
        """
        # Simple scoring: inverse of normalized metrics
        # This is a placeholder - real implementation would be more sophisticated
        score = 1.0

        # Penalize slow operations
        if self.avg_duration_ms:
            # Normalize to 0-1 (assume 1000ms = 0 score)
            duration_penalty = min(self.avg_duration_ms / 1000.0, 1.0)
            score -= duration_penalty * 0.4

        # Penalize high CPU
        if self.avg_cpu_percent:
            cpu_penalty = self.avg_cpu_percent / 100.0
            score -= cpu_penalty * 0.3

        # Penalize high memory
        if self.avg_memory_bytes:
            # Normalize to 0-1 (assume 512MB = 0 score)
            memory_mb = self.avg_memory_bytes / (1024 * 1024)
            memory_penalty = min(memory_mb / 512.0, 1.0)
            score -= memory_penalty * 0.3

        return max(score, 0.0)


@dataclass(frozen=True)
class OperationProfile:
    """Detailed profile for a specific operation.

    Contains comprehensive performance data for analysis.
    """

    operation_name: str
    invocation_count: int
    total_duration_ms: float
    avg_duration_ms: float
    failure_count: int
    success_rate: float

    # Optional detailed metrics
    summary: Optional[ProfileSummary] = None
    metadata: Dict[str, any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate operation profile data."""
        if not self.operation_name or not self.operation_name.strip():
            raise ValueError("Operation name cannot be empty")

        if self.invocation_count < 0:
            raise ValueError(f"Invocation count cannot be negative: {self.invocation_count}")

        if self.total_duration_ms < 0:
            raise ValueError(f"Total duration cannot be negative: {self.total_duration_ms}")

        if not 0.0 <= self.success_rate <= 100.0:
            raise ValueError(f"Success rate must be 0-100: {self.success_rate}")

    def is_unreliable(self, min_success_rate: float = 95.0) -> bool:
        """Check if operation is unreliable.

        Args:
            min_success_rate: Minimum acceptable success rate (percentage)

        Returns:
            True if success rate is below threshold
        """
        return self.success_rate < min_success_rate

    def is_performance_critical(self, invocation_threshold: int = 1000) -> bool:
        """Check if operation is performance-critical (high usage).

        Args:
            invocation_threshold: Minimum invocations to be considered critical

        Returns:
            True if invocation count exceeds threshold
        """
        return self.invocation_count >= invocation_threshold
