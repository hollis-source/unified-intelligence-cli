"""
Learning Service - Aggregates performance logs into summaries.

Clean Architecture: Application layer service for learning logic.
Processes raw logs from PerformanceDataRepository into ModelSummaryRepository.

Based on Qwen3-Next-80B-Thinking design: Batch processing every 5 minutes.
"""

import logging
from typing import List, Optional
from datetime import datetime, timedelta
from collections import defaultdict

from src.routing.adaptive_interfaces import (
    PerformanceLog,
    ModelSummary,
    IPerformanceDataRepository,
    IModelSummaryRepository
)
from src.routing.performance_repository import PerformanceDataRepository
from src.routing.summary_repository import ModelSummaryRepository


logger = logging.getLogger(__name__)


class LearningService:
    """
    Service for learning from performance logs.

    SRP: Single responsibility - aggregate logs into summaries.
    Batch processing: Runs periodically (e.g., every 5 minutes) to update summaries.
    """

    def __init__(
        self,
        performance_repo: IPerformanceDataRepository,
        summary_repo: IModelSummaryRepository,
        min_sample_size: int = 3
    ):
        """
        Initialize learning service.

        Args:
            performance_repo: Repository for raw performance logs
            summary_repo: Repository for aggregated summaries
            min_sample_size: Minimum samples required to create/update summary
        """
        self.performance_repo = performance_repo
        self.summary_repo = summary_repo
        self.min_sample_size = min_sample_size
        self.last_update_time: Optional[datetime] = None

    def update_summaries(self, time_window_minutes: int = 60) -> int:
        """
        Update all summaries from recent logs.

        Args:
            time_window_minutes: How many minutes back to process logs

        Returns:
            Number of summaries updated
        """
        # Get recent logs
        end_time = datetime.now()
        start_time = end_time - timedelta(minutes=time_window_minutes)

        logger.info(f"Learning: Processing logs from {start_time} to {end_time}")

        logs = self.performance_repo.get_raw_logs_for_time_range(start_time, end_time)

        if not logs:
            logger.info("Learning: No logs found in time window")
            return 0

        logger.info(f"Learning: Found {len(logs)} logs to process")

        # Group logs by (model_id, task_type)
        grouped_logs = defaultdict(list)
        for log in logs:
            key = (log.model_id, log.task_type)
            grouped_logs[key].append(log)

        # Update summaries for each group
        updated_count = 0
        for (model_id, task_type), group_logs in grouped_logs.items():
            if len(group_logs) >= self.min_sample_size:
                self._update_summary_for_group(model_id, task_type, group_logs)
                updated_count += 1
            else:
                logger.debug(
                    f"Learning: Skipping {model_id}/{task_type} "
                    f"(only {len(group_logs)} samples, need {self.min_sample_size})"
                )

        self.last_update_time = end_time
        logger.info(f"Learning: Updated {updated_count} summaries")

        return updated_count

    def update_summary_for_model(
        self,
        model_id: str,
        task_type: str,
        time_window_minutes: int = 1440  # 24 hours default
    ) -> bool:
        """
        Update summary for specific model and task type.

        Args:
            model_id: Model identifier
            task_type: Task type
            time_window_minutes: How many minutes back to process

        Returns:
            True if updated, False if insufficient data
        """
        end_time = datetime.now()
        start_time = end_time - timedelta(minutes=time_window_minutes)

        logs = self.performance_repo.get_raw_logs_for_time_range(
            start_time,
            end_time,
            model_id=model_id,
            task_type=task_type
        )

        if len(logs) < self.min_sample_size:
            logger.debug(
                f"Learning: Insufficient data for {model_id}/{task_type} "
                f"({len(logs)} samples, need {self.min_sample_size})"
            )
            return False

        self._update_summary_for_group(model_id, task_type, logs)
        return True

    def _update_summary_for_group(
        self,
        model_id: str,
        task_type: str,
        logs: List[PerformanceLog]
    ) -> None:
        """
        Update summary for a group of logs.

        Args:
            model_id: Model identifier
            task_type: Task type
            logs: List of performance logs for this model/task combination
        """
        if not logs:
            return

        # Get existing summary for incremental update (optional enhancement)
        existing = self.summary_repo.get_summary(model_id, task_type)

        # Compute metrics
        total_logs = len(logs)
        successful_logs = [log for log in logs if log.success]
        success_count = len(successful_logs)

        avg_latency = sum(log.latency_ms for log in logs) / total_logs
        success_rate = success_count / total_logs
        avg_cost = sum(log.cost_usd for log in logs) / total_logs

        # If existing summary exists, blend with new data (weighted average)
        if existing and existing.sample_size >= self.min_sample_size:
            # Weighted average: Give more weight to recent data but don't discard history
            old_weight = min(existing.sample_size, 100)  # Cap old weight to avoid stale data dominance
            new_weight = total_logs

            total_weight = old_weight + new_weight

            avg_latency = (
                (existing.avg_latency_ms * old_weight + avg_latency * new_weight)
                / total_weight
            )
            success_rate = (
                (existing.success_rate * old_weight + success_rate * new_weight)
                / total_weight
            )
            avg_cost = (
                (existing.avg_cost_per_task * old_weight + avg_cost * new_weight)
                / total_weight
            )

            # Update sample size (total observations used)
            sample_size = existing.sample_size + total_logs
        else:
            # New summary
            sample_size = total_logs

        # Create/update summary
        summary = ModelSummary(
            model_id=model_id,
            task_type=task_type,
            avg_latency_ms=avg_latency,
            success_rate=success_rate,
            avg_cost_per_task=avg_cost,
            sample_size=sample_size,
            last_updated=datetime.now()
        )

        self.summary_repo.update_summary(summary)

        logger.debug(
            f"Learning: Updated {model_id}/{task_type} - "
            f"latency={avg_latency:.1f}ms, success={success_rate:.2%}, "
            f"cost=${avg_cost:.4f}, samples={sample_size}"
        )

    def bootstrap_from_static_capabilities(
        self,
        static_capabilities: dict,
        task_type: str = "general"
    ) -> int:
        """
        Bootstrap summaries from static ModelCapabilities (cold-start mitigation).

        Args:
            static_capabilities: Dict of model_id -> ModelCapabilities from ModelSelector
            task_type: Default task type for static data

        Returns:
            Number of summaries bootstrapped

        Note: Used to initialize system with default values until real data is collected.
        """
        count = 0
        for model_id, capabilities in static_capabilities.items():
            # Check if summary already exists with sufficient data
            existing = self.summary_repo.get_summary(model_id, task_type)
            if existing and existing.sample_size >= 10:
                logger.debug(f"Learning: Skipping bootstrap for {model_id} (has {existing.sample_size} samples)")
                continue

            # Create bootstrap summary from static capabilities
            summary = ModelSummary(
                model_id=model_id,
                task_type=task_type,
                avg_latency_ms=capabilities.avg_latency * 1000,  # Convert seconds to ms
                success_rate=capabilities.success_rate,
                avg_cost_per_task=capabilities.cost_per_month / 1000,  # Rough estimate
                sample_size=0,  # Mark as bootstrap (no real samples)
                last_updated=datetime.now()
            )

            self.summary_repo.update_summary(summary)
            count += 1

            logger.info(
                f"Learning: Bootstrapped {model_id} from static capabilities - "
                f"latency={summary.avg_latency_ms:.1f}ms, success={summary.success_rate:.2%}"
            )

        return count

    def get_learning_stats(self) -> dict:
        """
        Get learning service statistics.

        Returns:
            Dict with stats (last_update, summaries_count, etc.)
        """
        summary_stats = self.summary_repo.get_stats()
        perf_stats = self.performance_repo.get_stats()

        return {
            "last_update_time": self.last_update_time.isoformat() if self.last_update_time else None,
            "total_summaries": summary_stats["total_summaries"],
            "total_logs": perf_stats["total_logs"],
            "num_models_tracked": summary_stats["num_models"],
            "num_task_types": summary_stats["num_task_types"],
            "avg_sample_size": summary_stats["avg_sample_size"]
        }
