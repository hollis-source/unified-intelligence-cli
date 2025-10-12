"""Feedback loop handler for failure detection and intelligent replanning.

Analyzes task execution failures and generates replanning strategies using
historical performance data and adaptive learning.
"""

import logging
from typing import List, Dict, Any, Optional
from enum import Enum

from src.interfaces import (
    IFeedbackHandler,
    ProjectState,
    ExecutionResult,
    TaskStatus
)
from src.entities.htn.htn_node import HTNNode


logger = logging.getLogger(__name__)


class FailureType(Enum):
    """Types of task execution failures."""
    TIMEOUT = "timeout"
    DEPENDENCY_MISSING = "dependency_missing"
    MODEL_FAILURE = "model_failure"
    PRECONDITION_VIOLATION = "precondition_violation"
    RESOURCE_UNAVAILABLE = "resource_unavailable"
    UNKNOWN = "unknown"


class ReplanningStrategy(Enum):
    """Strategies for replanning after failures."""
    RETRY_WITH_DIFFERENT_MODEL = "retry_different_model"
    REORDER_DEPENDENCIES = "reorder_dependencies"
    REFINE_DECOMPOSITION = "refine_decomposition"
    SKIP_AND_CONTINUE = "skip_and_continue"
    FAIL_PROJECT = "fail_project"


class FeedbackLoopHandler(IFeedbackHandler):
    """Handler for execution failures and intelligent replanning.

    Analyzes failure patterns, classifies failure types, and generates
    appropriate replanning strategies to recover from errors.

    Phase 2: Basic failure classification and simple replanning
    Phase 3: Will add ML-based failure prediction and advanced strategies

    Attributes:
        max_retries: Maximum retries per task before giving up
        failure_history: Historical failure data for learning
    """

    def __init__(self, max_retries: int = 3):
        """Initialize feedback loop handler.

        Args:
            max_retries: Maximum retry attempts per task
        """
        self.max_retries = max_retries
        self.failure_history: Dict[str, List[Dict[str, Any]]] = {}

    def replan(
        self,
        state: ProjectState,
        failed_tasks: List[ExecutionResult]
    ) -> ProjectState:
        """Generate new plan based on execution failures.

        Analyzes failures, selects appropriate strategy, and updates
        project state with new plan.

        Args:
            state: Current project state
            failed_tasks: List of tasks that failed

        Returns:
            Updated project state with new plan

        Raises:
            ValueError: If replanning fails or max retries exceeded
        """
        if not failed_tasks:
            return state

        logger.info(f"Analyzing {len(failed_tasks)} failed tasks for replanning")

        # Analyze failure reasons
        failure_analysis = self._analyze_failures(failed_tasks)
        logger.debug(f"Failure analysis: {failure_analysis}")

        # Select replanning strategy
        strategy = self._select_replanning_strategy(failure_analysis, state)
        logger.info(f"Selected replanning strategy: {strategy.value}")

        # Apply strategy to state
        new_state = self._apply_strategy(strategy, state, failed_tasks, failure_analysis)

        # Record failures for learning
        self._record_failures(failed_tasks, failure_analysis)

        return new_state

    def _analyze_failures(self, failed_tasks: List[ExecutionResult]) -> Dict[str, Any]:
        """Analyze failure reasons and patterns.

        Args:
            failed_tasks: List of failed task results

        Returns:
            Dict with failure analysis
        """
        analysis = {
            "total_failures": len(failed_tasks),
            "failure_types": {},
            "affected_models": set(),
            "affected_agents": set(),
            "error_messages": []
        }

        for result in failed_tasks:
            # Classify failure type
            failure_type = self._classify_failure(result)
            analysis["failure_types"][failure_type.value] = \
                analysis["failure_types"].get(failure_type.value, 0) + 1

            # Track affected resources
            if "model" in result.metadata:
                analysis["affected_models"].add(result.metadata["model"])
            if "agent" in result.metadata:
                analysis["affected_agents"].add(result.metadata["agent"])

            # Collect error messages
            if result.error:
                analysis["error_messages"].append({
                    "task_id": result.task_id,
                    "error": result.error
                })

        # Convert sets to lists for JSON serialization
        analysis["affected_models"] = list(analysis["affected_models"])
        analysis["affected_agents"] = list(analysis["affected_agents"])

        return analysis

    def _classify_failure(self, result: ExecutionResult) -> FailureType:
        """Classify failure type from execution result.

        Args:
            result: Failed execution result

        Returns:
            Failure type classification
        """
        error = result.error.lower() if result.error else ""

        # Check for common failure patterns
        if "timeout" in error or "timed out" in error:
            return FailureType.TIMEOUT

        if "dependency" in error or "missing" in error or "not found" in error:
            return FailureType.DEPENDENCY_MISSING

        if "precondition" in error or "not satisfied" in error:
            return FailureType.PRECONDITION_VIOLATION

        if "model" in error or "llm" in error or "generation" in error:
            return FailureType.MODEL_FAILURE

        if "resource" in error or "unavailable" in error:
            return FailureType.RESOURCE_UNAVAILABLE

        return FailureType.UNKNOWN

    def _select_replanning_strategy(
        self,
        failure_analysis: Dict[str, Any],
        state: ProjectState
    ) -> ReplanningStrategy:
        """Select optimal replanning strategy based on failure analysis.

        Args:
            failure_analysis: Analysis of failures
            state: Current project state

        Returns:
            Selected replanning strategy
        """
        failure_types = failure_analysis["failure_types"]
        total_failures = failure_analysis["total_failures"]

        # Priority order for strategy selection

        # 1. If mostly dependency issues, reorder dependencies
        if failure_types.get(FailureType.DEPENDENCY_MISSING.value, 0) / total_failures > 0.5:
            return ReplanningStrategy.REORDER_DEPENDENCIES

        # 2. If mostly precondition violations, refine decomposition
        if failure_types.get(FailureType.PRECONDITION_VIOLATION.value, 0) / total_failures > 0.5:
            return ReplanningStrategy.REFINE_DECOMPOSITION

        # 3. If model failures, try different model
        if failure_types.get(FailureType.MODEL_FAILURE.value, 0) / total_failures > 0.3:
            return ReplanningStrategy.RETRY_WITH_DIFFERENT_MODEL

        # 4. If timeout issues, try different model (faster one)
        if failure_types.get(FailureType.TIMEOUT.value, 0) / total_failures > 0.3:
            return ReplanningStrategy.RETRY_WITH_DIFFERENT_MODEL

        # 5. If too many failures, fail project
        failed_tasks = sum(1 for status in state.task_status.values() if status == TaskStatus.FAILED)
        if failed_tasks > len(state.task_status) * 0.5:
            return ReplanningStrategy.FAIL_PROJECT

        # Default: Retry with different model
        return ReplanningStrategy.RETRY_WITH_DIFFERENT_MODEL

    def _apply_strategy(
        self,
        strategy: ReplanningStrategy,
        state: ProjectState,
        failed_tasks: List[ExecutionResult],
        failure_analysis: Dict[str, Any]
    ) -> ProjectState:
        """Apply replanning strategy to state.

        Args:
            strategy: Selected replanning strategy
            state: Current project state
            failed_tasks: Failed task results
            failure_analysis: Failure analysis data

        Returns:
            Updated project state

        Raises:
            ValueError: If strategy cannot be applied
        """
        new_state = state.copy()

        if strategy == ReplanningStrategy.RETRY_WITH_DIFFERENT_MODEL:
            # Reset failed tasks to PENDING for retry
            for result in failed_tasks:
                if result.task_id in new_state.task_status:
                    new_state.task_status[result.task_id] = TaskStatus.PENDING
                    logger.debug(f"Reset task {result.task_id} to PENDING for retry")

        elif strategy == ReplanningStrategy.REORDER_DEPENDENCIES:
            # Phase 2: Simple implementation - just reset tasks
            # Phase 3: Will implement intelligent dependency reordering
            for result in failed_tasks:
                if result.task_id in new_state.task_status:
                    new_state.task_status[result.task_id] = TaskStatus.PENDING

            logger.warning("Dependency reordering not fully implemented (Phase 2)")

        elif strategy == ReplanningStrategy.REFINE_DECOMPOSITION:
            # Phase 2: Not implemented
            # Phase 3: Will use thinking model to refine HTN decomposition
            logger.warning("Decomposition refinement not implemented (Phase 2)")
            raise ValueError("Cannot refine decomposition in Phase 2")

        elif strategy == ReplanningStrategy.SKIP_AND_CONTINUE:
            # Mark failed tasks as skipped, continue with rest
            for result in failed_tasks:
                if result.task_id in new_state.task_status:
                    new_state.task_status[result.task_id] = TaskStatus.FAILED
                    logger.info(f"Skipping failed task: {result.task_id}")

        elif strategy == ReplanningStrategy.FAIL_PROJECT:
            # Mark all pending tasks as failed
            for task_id, status in new_state.task_status.items():
                if status == TaskStatus.PENDING:
                    new_state.task_status[task_id] = TaskStatus.FAILED

            raise ValueError("Project failed: too many task failures")

        return new_state

    def _record_failures(
        self,
        failed_tasks: List[ExecutionResult],
        failure_analysis: Dict[str, Any]
    ) -> None:
        """Record failures for future learning.

        Args:
            failed_tasks: Failed task results
            failure_analysis: Analysis of failures
        """
        for result in failed_tasks:
            task_id = result.task_id

            if task_id not in self.failure_history:
                self.failure_history[task_id] = []

            self.failure_history[task_id].append({
                "error": result.error,
                "metadata": result.metadata,
                "failure_type": self._classify_failure(result).value
            })

        logger.debug(f"Recorded {len(failed_tasks)} failures in history")

    def get_failure_statistics(self) -> Dict[str, Any]:
        """Get failure statistics for analysis.

        Returns:
            Dict with failure statistics
        """
        total_failures = sum(len(failures) for failures in self.failure_history.values())

        failure_type_counts = {}
        for failures in self.failure_history.values():
            for failure in failures:
                failure_type = failure.get("failure_type", "unknown")
                failure_type_counts[failure_type] = failure_type_counts.get(failure_type, 0) + 1

        return {
            "total_failures": total_failures,
            "unique_failed_tasks": len(self.failure_history),
            "failure_types": failure_type_counts,
            "most_common_failure": max(failure_type_counts.items(), key=lambda x: x[1])[0] if failure_type_counts else None
        }
