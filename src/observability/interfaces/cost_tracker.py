"""Cost tracker interface for API cost tracking.

Defines the contract for cost tracker implementations following
Dependency Inversion Principle. Use cases depend on this
interface, not concrete implementations.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Optional

from ..entities import CostEntry, CostSummary


class ICostTracker(ABC):
    """Interface for API cost tracking.

    Abstracts cost storage and aggregation implementation details.
    Implementations can use SQLite, PostgreSQL, in-memory, etc.

    Contract:
    - record_cost() stores a cost entry
    - get_total_cost() returns total cost for filters
    - get_cost_breakdown() returns cost by model/provider/agent
    - get_entries() retrieves cost entries with filters
    - get_summary() generates cost summary statistics
    """

    @abstractmethod
    def record_cost(self, entry: CostEntry) -> None:
        """Record a cost entry.

        Args:
            entry: CostEntry to store

        Raises:
            ValueError: If entry validation fails
            RuntimeError: If storage fails
        """
        pass

    @abstractmethod
    def get_total_cost(
        self,
        project_id: Optional[str] = None,
        task_id: Optional[str] = None,
        agent_name: Optional[str] = None,
        model_name: Optional[str] = None,
        provider: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> float:
        """Get total cost for specified filters.

        Args:
            project_id: Filter by project
            task_id: Filter by task
            agent_name: Filter by agent
            model_name: Filter by model
            provider: Filter by provider
            start_time: Filter by start time (inclusive)
            end_time: Filter by end time (exclusive)

        Returns:
            Total cost in USD

        Note:
            All filters are optional and ANDed together.
            No filters = total cost across all entries.
        """
        pass

    @abstractmethod
    def get_cost_breakdown(
        self,
        group_by: str,  # "model", "provider", "agent", "project", "task"
        project_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> Dict[str, float]:
        """Get cost breakdown grouped by specified dimension.

        Args:
            group_by: Dimension to group by ("model", "provider", "agent", "project", "task")
            project_id: Optional filter by project
            start_time: Optional filter by start time
            end_time: Optional filter by end time

        Returns:
            Dictionary mapping group key to total cost (USD)

        Raises:
            ValueError: If group_by is invalid

        Example:
            >>> tracker.get_cost_breakdown("model")
            {"grok-1": 0.50, "qwen3-next-80b": 0.30}
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
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: Optional[int] = None,
    ) -> List[CostEntry]:
        """Get cost entries matching filters.

        Args:
            project_id: Filter by project
            task_id: Filter by task
            agent_name: Filter by agent
            model_name: Filter by model
            provider: Filter by provider
            start_time: Filter by start time (inclusive)
            end_time: Filter by end time (exclusive)
            limit: Maximum number of entries to return

        Returns:
            List of CostEntry objects matching filters

        Note:
            Entries are returned in reverse chronological order (newest first).
        """
        pass

    @abstractmethod
    def get_summary(
        self,
        project_id: Optional[str] = None,
        task_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> CostSummary:
        """Get cost summary statistics for specified filters.

        Args:
            project_id: Filter by project
            task_id: Filter by task
            start_time: Filter by start time (inclusive)
            end_time: Filter by end time (exclusive)

        Returns:
            CostSummary with aggregated statistics

        Note:
            Summary includes total cost, token counts, breakdowns by model/provider/agent.
        """
        pass

    @abstractmethod
    def get_entry_count(
        self,
        project_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> int:
        """Get count of cost entries matching filters.

        Args:
            project_id: Filter by project
            start_time: Filter by start time
            end_time: Filter by end time

        Returns:
            Number of entries matching filters
        """
        pass

    @abstractmethod
    def delete_entries(
        self,
        project_id: Optional[str] = None,
        before: Optional[datetime] = None,
    ) -> int:
        """Delete cost entries matching filters.

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
