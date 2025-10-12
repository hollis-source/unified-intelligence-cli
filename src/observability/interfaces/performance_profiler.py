"""Performance profiler interface for performance monitoring.

Defines the contract for performance profiler implementations following
Dependency Inversion Principle. Use cases depend on this
interface, not concrete implementations.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional

from ..entities import PerformanceMetric, ProfileSummary, OperationProfile, MetricType


class IPerformanceProfiler(ABC):
    """Interface for performance profiling and monitoring.

    Abstracts performance metric storage and analysis implementation details.
    Implementations can use SQLite, PostgreSQL, in-memory, etc.

    Contract:
    - record_metric() stores a performance metric
    - get_metrics() retrieves metrics with filters
    - get_summary() generates performance summary for operation
    - get_operation_profile() gets detailed profile for operation
    - get_slow_operations() identifies slow operations
    - delete_metrics() removes old metrics
    """

    @abstractmethod
    def record_metric(self, metric: PerformanceMetric) -> None:
        """Record a performance metric.

        Args:
            metric: PerformanceMetric to store

        Raises:
            ValueError: If metric validation fails
            RuntimeError: If storage fails
        """
        pass

    @abstractmethod
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
        """Get performance metrics matching filters.

        Args:
            operation_name: Filter by operation name
            metric_type: Filter by metric type
            project_id: Filter by project
            agent_name: Filter by agent
            start_time: Filter by start time (inclusive)
            end_time: Filter by end time (exclusive)
            limit: Maximum number of metrics to return

        Returns:
            List of PerformanceMetric objects matching filters

        Note:
            Metrics are returned in reverse chronological order (newest first).
        """
        pass

    @abstractmethod
    def get_summary(
        self,
        operation_name: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> ProfileSummary:
        """Get performance summary for an operation.

        Args:
            operation_name: Operation to summarize
            start_time: Filter by start time (inclusive)
            end_time: Filter by end time (exclusive)

        Returns:
            ProfileSummary with aggregated statistics

        Note:
            Calculates statistics like avg/min/max duration, resource usage, etc.
        """
        pass

    @abstractmethod
    def get_operation_profile(
        self,
        operation_name: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> OperationProfile:
        """Get detailed profile for an operation.

        Args:
            operation_name: Operation to profile
            start_time: Filter by start time (inclusive)
            end_time: Filter by end time (excessive)

        Returns:
            OperationProfile with comprehensive performance data
        """
        pass

    @abstractmethod
    def get_slow_operations(
        self,
        threshold_ms: float = 1000.0,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: Optional[int] = None,
    ) -> List[OperationProfile]:
        """Identify slow operations.

        Args:
            threshold_ms: Duration threshold in milliseconds
            start_time: Filter by start time
            end_time: Filter by end time
            limit: Maximum number of operations to return

        Returns:
            List of OperationProfile objects for slow operations

        Note:
            Returns operations sorted by average duration (slowest first).
        """
        pass

    @abstractmethod
    def delete_metrics(
        self,
        operation_name: Optional[str] = None,
        before: Optional[datetime] = None,
    ) -> int:
        """Delete performance metrics matching filters.

        Args:
            operation_name: Filter by operation name
            before: Delete metrics before this time

        Returns:
            Number of metrics deleted

        Note:
            At least one filter must be specified (safety check).

        Raises:
            ValueError: If no filters specified
        """
        pass

    def get_metric_count(
        self,
        operation_name: Optional[str] = None,
        metric_type: Optional[MetricType] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> int:
        """Get count of performance metrics matching filters.

        Args:
            operation_name: Filter by operation name
            metric_type: Filter by metric type
            start_time: Filter by start time
            end_time: Filter by end time

        Returns:
            Number of metrics matching filters

        Note:
            This is an optional method with default implementation.
            Implementations can override with optimized counting logic.
        """
        metrics = self.get_metrics(
            operation_name=operation_name,
            metric_type=metric_type,
            start_time=start_time,
            end_time=end_time,
        )
        return len(metrics)
