"""In-memory cost tracker adapter for testing and development.

Stores cost entries in memory without requiring external database.
Useful for unit tests and local development.
"""

from datetime import datetime
from typing import Dict, List, Optional
from collections import defaultdict
import logging

from ..interfaces import ICostTracker
from ..entities import CostEntry, CostSummary

logger = logging.getLogger(__name__)


class InMemoryCostTracker(ICostTracker):
    """In-memory cost tracker implementation for testing.

    Stores cost entries in a list with in-memory filtering and aggregation.
    Provides simple implementation of ICostTracker contract without
    requiring external dependencies (SQLite, PostgreSQL, etc.).

    Thread-safe for single-threaded test environments.
    For production, use SQLiteCostTracker or PostgreSQLCostTracker.
    """

    def __init__(self):
        """Initialize empty cost storage."""
        self._entries: List[CostEntry] = []

    def record_cost(self, entry: CostEntry) -> None:
        """Record a cost entry.

        Args:
            entry: CostEntry to store

        Raises:
            ValueError: If entry is invalid
        """
        if not isinstance(entry, CostEntry):
            raise ValueError(f"Expected CostEntry, got {type(entry)}")

        self._entries.append(entry)
        logger.debug(
            f"Recorded cost: {entry.model_name} ({entry.provider}) "
            f"${entry.calculate_cost():.4f} "
            f"[{entry.input_tokens}→{entry.output_tokens} tokens]"
        )

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
        """Get total cost for specified filters."""
        filtered = self._filter_entries(
            project_id, task_id, agent_name, model_name, provider, start_time, end_time
        )
        return sum(entry.calculate_cost() for entry in filtered)

    def get_cost_breakdown(
        self,
        group_by: str,
        project_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> Dict[str, float]:
        """Get cost breakdown grouped by specified dimension."""
        valid_groups = {"model", "provider", "agent", "project", "task"}
        if group_by not in valid_groups:
            raise ValueError(f"Invalid group_by: {group_by}. Must be one of {valid_groups}")

        filtered = self._filter_entries(
            project_id=project_id,
            start_time=start_time,
            end_time=end_time,
        )

        breakdown: Dict[str, float] = defaultdict(float)
        for entry in filtered:
            # Get group key
            if group_by == "model":
                key = entry.model_name
            elif group_by == "provider":
                key = entry.provider
            elif group_by == "agent":
                key = entry.agent_name or "unknown"
            elif group_by == "project":
                key = entry.project_id or "unknown"
            elif group_by == "task":
                key = entry.task_id or "unknown"
            else:
                continue

            breakdown[key] += entry.calculate_cost()

        return dict(breakdown)

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
        """Get cost entries matching filters."""
        filtered = self._filter_entries(
            project_id, task_id, agent_name, model_name, provider, start_time, end_time
        )

        # Sort by timestamp (newest first)
        sorted_entries = sorted(filtered, key=lambda e: e.timestamp, reverse=True)

        # Apply limit
        if limit is not None:
            sorted_entries = sorted_entries[:limit]

        return sorted_entries

    def get_summary(
        self,
        project_id: Optional[str] = None,
        task_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> CostSummary:
        """Get cost summary statistics for specified filters."""
        filtered = self._filter_entries(
            project_id=project_id,
            task_id=task_id,
            start_time=start_time,
            end_time=end_time,
        )

        if not filtered:
            # No entries, return empty summary
            now = datetime.now()
            return CostSummary(
                total_cost_usd=0.0,
                total_input_tokens=0,
                total_output_tokens=0,
                total_tokens=0,
                entry_count=0,
                start_time=start_time or now,
                end_time=end_time or now,
            )

        # Calculate totals
        total_cost = sum(e.calculate_cost() for e in filtered)
        total_input = sum(e.input_tokens for e in filtered)
        total_output = sum(e.output_tokens for e in filtered)
        total_tokens = sum(e.total_tokens for e in filtered)

        # Calculate breakdowns
        cost_by_model = self.get_cost_breakdown("model", project_id, start_time, end_time)
        cost_by_provider = self.get_cost_breakdown("provider", project_id, start_time, end_time)
        cost_by_agent = self.get_cost_breakdown("agent", project_id, start_time, end_time)

        # Determine time range
        actual_start = min(e.timestamp for e in filtered)
        actual_end = max(e.timestamp for e in filtered)

        return CostSummary(
            total_cost_usd=total_cost,
            total_input_tokens=total_input,
            total_output_tokens=total_output,
            total_tokens=total_tokens,
            entry_count=len(filtered),
            start_time=start_time or actual_start,
            end_time=end_time or actual_end,
            cost_by_model=cost_by_model,
            cost_by_provider=cost_by_provider,
            cost_by_agent=cost_by_agent,
        )

    def get_entry_count(
        self,
        project_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> int:
        """Get count of cost entries matching filters."""
        filtered = self._filter_entries(
            project_id=project_id,
            start_time=start_time,
            end_time=end_time,
        )
        return len(filtered)

    def delete_entries(
        self,
        project_id: Optional[str] = None,
        before: Optional[datetime] = None,
    ) -> int:
        """Delete cost entries matching filters."""
        if project_id is None and before is None:
            raise ValueError("At least one filter must be specified for safety")

        # Find entries to delete
        to_delete = self._filter_entries(
            project_id=project_id,
            end_time=before,  # before = end_time filter
        )

        # Remove from storage
        for entry in to_delete:
            self._entries.remove(entry)

        deleted_count = len(to_delete)
        logger.info(f"Deleted {deleted_count} cost entries")
        return deleted_count

    def _filter_entries(
        self,
        project_id: Optional[str] = None,
        task_id: Optional[str] = None,
        agent_name: Optional[str] = None,
        model_name: Optional[str] = None,
        provider: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> List[CostEntry]:
        """Filter entries by specified criteria.

        Args:
            project_id: Filter by project
            task_id: Filter by task
            agent_name: Filter by agent
            model_name: Filter by model
            provider: Filter by provider
            start_time: Filter by start time (inclusive)
            end_time: Filter by end time (exclusive)

        Returns:
            List of CostEntry objects matching all filters
        """
        filtered = self._entries

        if project_id is not None:
            filtered = [e for e in filtered if e.project_id == project_id]

        if task_id is not None:
            filtered = [e for e in filtered if e.task_id == task_id]

        if agent_name is not None:
            filtered = [e for e in filtered if e.agent_name == agent_name]

        if model_name is not None:
            filtered = [e for e in filtered if e.model_name == model_name]

        if provider is not None:
            filtered = [e for e in filtered if e.provider == provider]

        if start_time is not None:
            filtered = [e for e in filtered if e.timestamp >= start_time]

        if end_time is not None:
            filtered = [e for e in filtered if e.timestamp < end_time]

        return filtered

    def get_all_entries(self) -> List[CostEntry]:
        """Get all cost entries (no filtering).

        Returns:
            List of all CostEntry objects

        Note:
            Not part of ICostTracker interface. Useful for testing.
        """
        return self._entries.copy()

    def clear(self) -> None:
        """Clear all cost entries.

        Note:
            Not part of ICostTracker interface. Useful for test cleanup.
        """
        count = len(self._entries)
        self._entries.clear()
        logger.debug(f"Cleared {count} cost entries")
