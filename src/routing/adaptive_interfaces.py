"""
Adaptive Model Selection - Core Interfaces and Entities.

Clean Architecture: Core layer interfaces for adaptive learning system.
DIP Compliance: Infrastructure depends on these abstractions, not vice versa.

Based on Qwen3-Next-80B-Thinking architectural design.
"""

from typing import List, Optional, Protocol
from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class SelectionStrategy(Enum):
    """Strategy for model selection optimization."""
    MINIMIZE_COST = "minimize_cost"
    MINIMIZE_LATENCY = "minimize_latency"
    MAXIMIZE_QUALITY = "maximize_quality"
    BALANCED = "balanced"


@dataclass
class SelectionRequirements:
    """
    Requirements for model selection.

    Entity representing constraints and optimization goals.
    All fields are optional - None means "no constraint".
    """
    max_latency_ms: Optional[float] = None
    min_success_rate: Optional[float] = None
    max_cost_per_task: Optional[float] = None
    strategy: SelectionStrategy = SelectionStrategy.BALANCED


@dataclass
class PerformanceLog:
    """
    Raw performance log for a single task execution.

    Entity stored in PerformanceDataRepository for learning.
    """
    model_id: str
    task_type: str
    latency_ms: float
    success: bool
    cost_usd: float
    timestamp: datetime
    task_description: Optional[str] = None  # For future similarity matching


@dataclass
class ModelSummary:
    """
    Aggregated performance summary for a model.

    Entity computed by LearningService from raw PerformanceLog data.
    Used by AdaptiveModelSelector for selection decisions.
    """
    model_id: str
    task_type: str
    avg_latency_ms: float
    success_rate: float
    avg_cost_per_task: float
    sample_size: int  # Number of tasks used to compute this summary
    last_updated: datetime


class IPerformanceDataRepository(Protocol):
    """
    Interface for raw performance log storage.

    DIP: Infrastructure layer implements this, core layer depends on abstraction.
    Stores raw logs for learning and historical analysis.
    """

    async def save_performance_log(self, log: PerformanceLog) -> None:
        """
        Save raw performance log asynchronously.

        Args:
            log: Performance log to save

        Note: Should be non-blocking to avoid impacting task execution.
        """
        ...

    def get_raw_logs_for_time_range(
        self,
        start_time: datetime,
        end_time: datetime,
        model_id: Optional[str] = None,
        task_type: Optional[str] = None
    ) -> List[PerformanceLog]:
        """
        Retrieve raw logs for analysis.

        Args:
            start_time: Start of time range
            end_time: End of time range
            model_id: Optional filter by model
            task_type: Optional filter by task type

        Returns:
            List of performance logs matching criteria
        """
        ...

    def get_recent_logs(self, limit: int = 1000) -> List[PerformanceLog]:
        """
        Get most recent logs for quick analysis.

        Args:
            limit: Maximum number of logs to retrieve

        Returns:
            List of recent performance logs
        """
        ...


class IModelSummaryRepository(Protocol):
    """
    Interface for aggregated model performance summaries.

    DIP: Infrastructure layer implements this, core layer depends on abstraction.
    Stores precomputed summaries for fast selection.
    """

    def get_summary_for_task_type(
        self,
        task_type: str,
        model_id: Optional[str] = None
    ) -> List[ModelSummary]:
        """
        Get summaries for a task type.

        Args:
            task_type: Type of task
            model_id: Optional filter by specific model

        Returns:
            List of summaries matching criteria
        """
        ...

    def get_all_summaries(self) -> List[ModelSummary]:
        """
        Get all summaries for global analysis.

        Returns:
            List of all model summaries
        """
        ...

    def update_summary(self, summary: ModelSummary) -> None:
        """
        Update or insert a summary.

        Args:
            summary: Summary to update/insert

        Note: Upsert semantics - creates if doesn't exist, updates if exists.
        """
        ...

    def get_summary(self, model_id: str, task_type: str) -> Optional[ModelSummary]:
        """
        Get specific summary for model and task type.

        Args:
            model_id: Model identifier
            task_type: Task type

        Returns:
            Summary if exists, None otherwise
        """
        ...


class IAdaptiveModelSelector(Protocol):
    """
    Interface for adaptive model selection.

    Extends IModelSelector concept with learned performance data.
    LSP Compliance: Can substitute static ModelSelector.
    """

    def select_model(
        self,
        task_type: str,
        requirements: SelectionRequirements,
        available_models: Optional[List[str]] = None
    ) -> str:
        """
        Select optimal model based on learned performance and requirements.

        Args:
            task_type: Type of task (e.g., "code_analysis", "translation")
            requirements: Selection requirements and constraints
            available_models: Optional list of available model IDs (None = all)

        Returns:
            Selected model ID

        Raises:
            ValueError: If no models meet requirements
        """
        ...

    def get_selection_rationale(
        self,
        model_id: str,
        task_type: str
    ) -> dict:
        """
        Get explanation for why a model was selected.

        Args:
            model_id: Selected model ID
            task_type: Task type

        Returns:
            Dict with selection rationale (metrics, alternatives considered, etc.)
        """
        ...


class ILearningService(Protocol):
    """
    Interface for learning service that updates summaries.

    Processes raw logs into aggregated summaries.
    """

    def update_summaries(self) -> int:
        """
        Update all summaries from recent logs.

        Returns:
            Number of summaries updated
        """
        ...

    def update_summary_for_model(self, model_id: str, task_type: str) -> bool:
        """
        Update summary for specific model and task type.

        Args:
            model_id: Model identifier
            task_type: Task type

        Returns:
            True if updated, False if no data available
        """
        ...
