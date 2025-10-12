"""In-memory usage tracker adapter for testing and development.

Stores usage entries in memory without requiring external database.
Useful for unit tests and local development.
"""

from datetime import datetime
from typing import Dict, List, Optional
from collections import defaultdict
import logging

from ..interfaces import IUsageTracker
from ..entities import UsageEntry, UsageSummary, UsagePattern, OperationType

logger = logging.getLogger(__name__)


class InMemoryUsageTracker(IUsageTracker):
    """In-memory usage tracker implementation for testing.

    Stores usage entries in a list with in-memory filtering and aggregation.
    Provides simple implementation of IUsageTracker contract without
    requiring external dependencies (SQLite, PostgreSQL, etc.).

    Thread-safe for single-threaded test environments.
    For production, use SQLiteUsageTracker or PostgreSQLUsageTracker.
    """

    def __init__(self):
        """Initialize empty usage storage."""
        self._entries: List[UsageEntry] = []

    def record_usage(self, entry: UsageEntry) -> None:
        """Record a usage entry.

        Args:
            entry: UsageEntry to store

        Raises:
            ValueError: If entry is invalid
        """
        if not isinstance(entry, UsageEntry):
            raise ValueError(f"Expected UsageEntry, got {type(entry)}")

        self._entries.append(entry)
        status = "success" if entry.success else f"failure ({entry.error_type})"
        logger.debug(
            f"Recorded usage: {entry.model_name} ({entry.provider}) "
            f"{entry.total_tokens} tokens [{status}] "
            f"[{entry.input_tokens}→{entry.output_tokens}]"
        )

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
        """Get total tokens for specified filters."""
        filtered = self._filter_entries(
            project_id, task_id, agent_name, model_name, provider,
            operation_type, success_only, start_time, end_time
        )
        return sum(entry.total_tokens for entry in filtered)

    def get_usage_breakdown(
        self,
        group_by: str,
        project_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> Dict[str, int]:
        """Get usage breakdown grouped by specified dimension."""
        valid_groups = {"model", "provider", "agent", "project", "task", "operation"}
        if group_by not in valid_groups:
            raise ValueError(f"Invalid group_by: {group_by}. Must be one of {valid_groups}")

        filtered = self._filter_entries(
            project_id=project_id,
            start_time=start_time,
            end_time=end_time,
        )

        breakdown: Dict[str, int] = defaultdict(int)
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
            elif group_by == "operation":
                key = entry.operation_type.value
            else:
                continue

            breakdown[key] += entry.total_tokens

        return dict(breakdown)

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
        """Get usage entries matching filters."""
        filtered = self._filter_entries(
            project_id, task_id, agent_name, model_name, provider,
            operation_type, success_only, start_time, end_time
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
        agent_name: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> UsageSummary:
        """Get usage summary statistics for specified filters."""
        filtered = self._filter_entries(
            project_id=project_id,
            task_id=task_id,
            agent_name=agent_name,
            start_time=start_time,
            end_time=end_time,
        )

        if not filtered:
            # No entries, return empty summary
            now = datetime.now()
            return UsageSummary(
                total_tokens=0,
                total_input_tokens=0,
                total_output_tokens=0,
                entry_count=0,
                success_count=0,
                failure_count=0,
                start_time=start_time or now,
                end_time=end_time or now,
            )

        # Calculate totals
        total_tokens = sum(e.total_tokens for e in filtered)
        total_input = sum(e.input_tokens for e in filtered)
        total_output = sum(e.output_tokens for e in filtered)
        success_count = sum(1 for e in filtered if e.success)
        failure_count = sum(1 for e in filtered if not e.success)

        # Calculate breakdowns
        tokens_by_model = self.get_usage_breakdown("model", project_id, start_time, end_time)
        tokens_by_provider = self.get_usage_breakdown("provider", project_id, start_time, end_time)
        tokens_by_agent = self.get_usage_breakdown("agent", project_id, start_time, end_time)
        tokens_by_operation = self.get_usage_breakdown("operation", project_id, start_time, end_time)

        # Count unique entities
        unique_models = len(set(e.model_name for e in filtered))
        unique_agents = len(set(e.agent_name for e in filtered if e.agent_name))
        unique_projects = len(set(e.project_id for e in filtered if e.project_id))

        # Determine time range
        actual_start = min(e.timestamp for e in filtered)
        actual_end = max(e.timestamp for e in filtered)

        return UsageSummary(
            total_tokens=total_tokens,
            total_input_tokens=total_input,
            total_output_tokens=total_output,
            entry_count=len(filtered),
            success_count=success_count,
            failure_count=failure_count,
            start_time=start_time or actual_start,
            end_time=end_time or actual_end,
            tokens_by_model=tokens_by_model,
            tokens_by_provider=tokens_by_provider,
            tokens_by_agent=tokens_by_agent,
            tokens_by_operation=tokens_by_operation,
            unique_models=unique_models,
            unique_agents=unique_agents,
            unique_projects=unique_projects,
        )

    def get_entry_count(
        self,
        project_id: Optional[str] = None,
        success_only: bool = False,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> int:
        """Get count of usage entries matching filters."""
        filtered = self._filter_entries(
            project_id=project_id,
            success_only=success_only,
            start_time=start_time,
            end_time=end_time,
        )
        return len(filtered)

    def get_success_rate(
        self,
        project_id: Optional[str] = None,
        agent_name: Optional[str] = None,
        model_name: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> float:
        """Get success rate for specified filters."""
        filtered = self._filter_entries(
            project_id=project_id,
            agent_name=agent_name,
            model_name=model_name,
            start_time=start_time,
            end_time=end_time,
        )

        if not filtered:
            return 0.0

        success_count = sum(1 for e in filtered if e.success)
        return (success_count / len(filtered)) * 100.0

    def delete_entries(
        self,
        project_id: Optional[str] = None,
        before: Optional[datetime] = None,
    ) -> int:
        """Delete usage entries matching filters."""
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
        logger.info(f"Deleted {deleted_count} usage entries")
        return deleted_count

    def _filter_entries(
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
    ) -> List[UsageEntry]:
        """Filter entries by specified criteria.

        Args:
            project_id: Filter by project
            task_id: Filter by task
            agent_name: Filter by agent
            model_name: Filter by model
            provider: Filter by provider
            operation_type: Filter by operation type
            success_only: Only include successful operations
            start_time: Filter by start time (inclusive)
            end_time: Filter by end time (exclusive)

        Returns:
            List of UsageEntry objects matching all filters
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

        if operation_type is not None:
            filtered = [e for e in filtered if e.operation_type == operation_type]

        if success_only:
            filtered = [e for e in filtered if e.success]

        if start_time is not None:
            filtered = [e for e in filtered if e.timestamp >= start_time]

        if end_time is not None:
            filtered = [e for e in filtered if e.timestamp < end_time]

        return filtered

    def get_all_entries(self) -> List[UsageEntry]:
        """Get all usage entries (no filtering).

        Returns:
            List of all UsageEntry objects

        Note:
            Not part of IUsageTracker interface. Useful for testing.
        """
        return self._entries.copy()

    def clear(self) -> None:
        """Clear all usage entries.

        Note:
            Not part of IUsageTracker interface. Useful for test cleanup.
        """
        count = len(self._entries)
        self._entries.clear()
        logger.debug(f"Cleared {count} usage entries")
