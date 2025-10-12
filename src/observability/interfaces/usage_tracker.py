"""Usage tracker interface for API usage analytics.

Defines the contract for usage tracker implementations following
Dependency Inversion Principle. Use cases depend on this
interface, not concrete implementations.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Optional

from ..entities import UsageEntry, UsageSummary, UsagePattern, OperationType


class IUsageTracker(ABC):
    """Interface for API usage tracking and analytics.

    Abstracts usage storage and aggregation implementation details.
    Implementations can use SQLite, PostgreSQL, in-memory, etc.

    Contract:
    - record_usage() stores a usage entry
    - get_total_tokens() returns total tokens for filters
    - get_usage_breakdown() returns usage by model/provider/agent
    - get_entries() retrieves usage entries with filters
    - get_summary() generates usage summary statistics
    - detect_patterns() identifies usage patterns (optional)
    """

    @abstractmethod
    def record_usage(self, entry: UsageEntry) -> None:
        """Record a usage entry.

        Args:
            entry: UsageEntry to store

        Raises:
            ValueError: If entry validation fails
            RuntimeError: If storage fails
        """
        pass

    @abstractmethod
    def get_total_tokens(
        self,
        project_id: Optional[str] = None,
        task_id: Optional[str] = None,
        agent_name: Optional[str] = None,
        model_name: Optional[str] = None,
        provider: Optional[str] = None,
        operation_type: Optional[OperationType] = None,
        success_only: bool = False,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> int:
        """Get total tokens for specified filters.

        Args:
            project_id: Filter by project
            task_id: Filter by task
            agent_name: Filter by agent
            model_name: Filter by model
            provider: Filter by provider
            operation_type: Filter by operation type
            success_only: Only count successful operations
            start_time: Filter by start time (inclusive)
            end_time: Filter by end time (exclusive)

        Returns:
            Total tokens

        Note:
            All filters are optional and ANDed together.
            No filters = total tokens across all entries.
        """
        pass

    @abstractmethod
    def get_usage_breakdown(
        self,
        group_by: str,  # "model", "provider", "agent", "project", "task", "operation"
        project_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> Dict[str, int]:
        """Get usage breakdown grouped by specified dimension.

        Args:
            group_by: Dimension to group by ("model", "provider", "agent", "project", "task", "operation")
            project_id: Optional filter by project
            start_time: Optional filter by start time
            end_time: Optional filter by end time

        Returns:
            Dictionary mapping group key to total tokens

        Raises:
            ValueError: If group_by is invalid

        Example:
            >>> tracker.get_usage_breakdown("model")
            {"grok-1": 5000, "qwen3-next-80b": 3000}
        """
        pass

    @abstractmethod
    def get_entries(
        self,
        project_id: Optional[str] = None,
        task_id: Optional[str] = None,
        agent_name: Optional[str] = None,
        model_name: Optional[str] = None,
        provider: Optional[str] = None,
        operation_type: Optional[OperationType] = None,
        success_only: bool = False,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: Optional[int] = None,
    ) -> List[UsageEntry]:
        """Get usage entries matching filters.

        Args:
            project_id: Filter by project
            task_id: Filter by task
            agent_name: Filter by agent
            model_name: Filter by model
            provider: Filter by provider
            operation_type: Filter by operation type
            success_only: Only return successful operations
            start_time: Filter by start time (inclusive)
            end_time: Filter by end time (exclusive)
            limit: Maximum number of entries to return

        Returns:
            List of UsageEntry objects matching filters

        Note:
            Entries are returned in reverse chronological order (newest first).
        """
        pass

    @abstractmethod
    def get_summary(
        self,
        project_id: Optional[str] = None,
        task_id: Optional[str] = None,
        agent_name: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> UsageSummary:
        """Get usage summary statistics for specified filters.

        Args:
            project_id: Filter by project
            task_id: Filter by task
            agent_name: Filter by agent
            start_time: Filter by start time (inclusive)
            end_time: Filter by end time (exclusive)

        Returns:
            UsageSummary with aggregated statistics

        Note:
            Summary includes total tokens, call counts, breakdowns by model/provider/agent.
        """
        pass

    @abstractmethod
    def get_entry_count(
        self,
        project_id: Optional[str] = None,
        success_only: bool = False,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> int:
        """Get count of usage entries matching filters.

        Args:
            project_id: Filter by project
            success_only: Only count successful operations
            start_time: Filter by start time
            end_time: Filter by end time

        Returns:
            Number of entries matching filters
        """
        pass

    @abstractmethod
    def get_success_rate(
        self,
        project_id: Optional[str] = None,
        agent_name: Optional[str] = None,
        model_name: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> float:
        """Get success rate for specified filters.

        Args:
            project_id: Filter by project
            agent_name: Filter by agent
            model_name: Filter by model
            start_time: Filter by start time
            end_time: Filter by end time

        Returns:
            Success rate as percentage (0-100)
        """
        pass

    @abstractmethod
    def delete_entries(
        self,
        project_id: Optional[str] = None,
        before: Optional[datetime] = None,
    ) -> int:
        """Delete usage entries matching filters.

        Args:
            project_id: Filter by project
            before: Delete entries before this time

        Returns:
            Number of entries deleted

        Note:
            Use with caution. Primarily for cleanup/testing.
            At least one filter must be specified (safety check).

        Raises:
            ValueError: If no filters specified
        """
        pass

    def detect_patterns(
        self,
        project_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> List[UsagePattern]:
        """Detect usage patterns in data (optional implementation).

        Args:
            project_id: Filter by project
            start_time: Filter by start time
            end_time: Filter by end time

        Returns:
            List of detected UsagePattern objects

        Note:
            This is an optional method for advanced analytics.
            Base implementation can return empty list.
            Implementations can add pattern detection logic:
            - Peak usage times
            - Model preferences
            - Token usage distributions
            - Anomalies
        """
        return []  # Default: no pattern detection
