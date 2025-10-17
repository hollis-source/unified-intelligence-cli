"""Feedback coordinator use case - Feedback-driven replanning.

Migrated from: src/project_builder/feedback/handler.py
Enhanced with: Better failure classification, adaptive strategies, history tracking

Clean Architecture: Use case layer (business logic)
SOLID: SRP (single responsibility), DIP (depends on abstractions)
"""

import logging
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List, Any, Optional
from datetime import datetime

from src.interface.feedback_handler import IFeedbackHandler
from src.entity.execution import ExecutionResult, ExecutionStatus


class FailureType(Enum):
    """Classification of task failures."""
    TIMEOUT = auto()
    DEPENDENCY_MISSING = auto()
    MODEL_FAILURE = auto()
    PRECONDITION_VIOLATION = auto()
    RESOURCE_UNAVAILABLE = auto()
    VALIDATION_ERROR = auto()
    UNKNOWN = auto()


class ReplanningStrategy(Enum):
    """Strategies for handling failures."""
    RETRY_WITH_SAME_CONFIG = auto()
    RETRY_WITH_DIFFERENT_MODEL = auto()
    REORDER_DEPENDENCIES = auto()
    REFINE_DECOMPOSITION = auto()
    SKIP_TASK = auto()
    FAIL_PROJECT = auto()


@dataclass
class FeedbackCoordinatorUseCase(IFeedbackHandler):
    """Feedback-driven replanning coordinator.
    
    Analyzes task failures and determines appropriate replanning strategies
    with automatic retry logic and circuit breakers.
    
    Attributes:
        max_retries: Maximum retry attempts per task (default: 3)
        max_total_failures: Maximum total failures before aborting (default: 10)
        failure_history: Historical failure tracking
        logger: Optional logger for debugging
    
    Example:
        >>> coordinator = FeedbackCoordinatorUseCase(max_retries=3)
        >>> analysis = coordinator.analyze_failures(failed_tasks)
        >>> if coordinator.should_replan(analysis, attempt=1):
        ...     plan = coordinator.replan(failed_tasks, analysis, context)
    """
    
    max_retries: int = 3
    max_total_failures: int = 10
    failure_history: Dict[str, List[Dict[str, Any]]] = field(default_factory=dict)
    logger: Optional[logging.Logger] = None
    
    def __post_init__(self):
        """Initialize logger if not provided."""
        if self.logger is None:
            self.logger = logging.getLogger(__name__)
    
    def analyze_failures(
        self,
        failed_tasks: List[ExecutionResult]
    ) -> Dict[str, Any]:
        """Analyze failed tasks and classify failure types.
        
        Performs comprehensive failure analysis:
        - Classifies each failure by type
        - Counts failure types
        - Extracts error messages
        - Recommends replanning strategy
        """
        if not failed_tasks:
            return {
                "total_failures": 0,
                "failure_types": {},
                "error_messages": [],
                "task_ids": [],
                "recommended_strategy": None
            }
        
        failure_types: Dict[str, int] = {}
        error_messages: List[str] = []
        task_ids: List[str] = []
        
        for result in failed_tasks:
            # Classify failure
            failure_type = self._classify_failure(result)
            failure_type_name = failure_type.name
            failure_types[failure_type_name] = failure_types.get(failure_type_name, 0) + 1
            
            # Collect error messages
            if result.error:
                error_messages.append(result.error)
            
            # Collect task IDs
            task_ids.append(result.task_id)
        
        # Recommend strategy based on failure analysis
        recommended_strategy = self._recommend_strategy(failure_types, len(failed_tasks))
        
        analysis = {
            "total_failures": len(failed_tasks),
            "failure_types": failure_types,
            "error_messages": error_messages,
            "task_ids": task_ids,
            "recommended_strategy": recommended_strategy.name
        }
        
        self.logger.info(f"Failure analysis: {analysis['total_failures']} failures, "
                        f"recommended strategy: {recommended_strategy.name}")
        
        return analysis
    
    def should_replan(
        self,
        analysis: Dict[str, Any],
        attempt_count: int
    ) -> bool:
        """Determine if replanning should occur.
        
        Checks:
        - Attempt count within max_retries
        - Total failures within max_total_failures
        - Recommended strategy is not FAIL_PROJECT
        """
        # Check retry limit
        if attempt_count >= self.max_retries:
            self.logger.warning(f"Max retries ({self.max_retries}) reached")
            return False
        
        # Check total failure limit
        if analysis["total_failures"] >= self.max_total_failures:
            self.logger.warning(f"Max total failures ({self.max_total_failures}) reached")
            return False
        
        # Check recommended strategy
        strategy = ReplanningStrategy[analysis["recommended_strategy"]]
        if strategy == ReplanningStrategy.FAIL_PROJECT:
            self.logger.warning("Recommended strategy is FAIL_PROJECT")
            return False
        
        self.logger.info(f"Replanning approved: attempt {attempt_count}/{self.max_retries}")
        return True
    
    def replan(
        self,
        failed_tasks: List[ExecutionResult],
        analysis: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create replanning strategy based on failure analysis."""
        
        strategy = ReplanningStrategy[analysis["recommended_strategy"]]
        
        self.logger.info(f"Replanning with strategy: {strategy.name}")
        
        if strategy == ReplanningStrategy.RETRY_WITH_SAME_CONFIG:
            return self._plan_retry_same_config(failed_tasks, analysis, context)
        
        elif strategy == ReplanningStrategy.RETRY_WITH_DIFFERENT_MODEL:
            return self._plan_retry_different_model(failed_tasks, analysis, context)
        
        elif strategy == ReplanningStrategy.REORDER_DEPENDENCIES:
            return self._plan_reorder_dependencies(failed_tasks, analysis, context)
        
        elif strategy == ReplanningStrategy.REFINE_DECOMPOSITION:
            return self._plan_refine_decomposition(failed_tasks, analysis, context)
        
        elif strategy == ReplanningStrategy.SKIP_TASK:
            return self._plan_skip_task(failed_tasks, analysis, context)
        
        elif strategy == ReplanningStrategy.FAIL_PROJECT:
            raise ValueError(f"Project failed: {analysis['total_failures']} failures")
        
        else:
            raise ValueError(f"Unknown strategy: {strategy}")
    
    def record_failure(
        self,
        task_id: str,
        failure_type: str,
        error_message: str
    ) -> None:
        """Record failure for historical analysis."""
        
        if task_id not in self.failure_history:
            self.failure_history[task_id] = []
        
        failure_record = {
            "timestamp": datetime.now().isoformat(),
            "failure_type": failure_type,
            "error_message": error_message
        }
        
        self.failure_history[task_id].append(failure_record)
        
        self.logger.debug(f"Recorded failure for {task_id}: {failure_type}")
    
    def get_failure_history(self, task_id: str) -> List[Dict[str, Any]]:
        """Get failure history for a task."""
        return self.failure_history.get(task_id, [])
    
    # Private helper methods
    
    def _classify_failure(self, result: ExecutionResult) -> FailureType:
        """Classify failure type from execution result."""
        
        if not result.error:
            return FailureType.UNKNOWN
        
        error_lower = result.error.lower()
        
        # Pattern matching for failure classification
        if "timeout" in error_lower or "timed out" in error_lower:
            return FailureType.TIMEOUT
        
        elif "dependency" in error_lower or "precondition" in error_lower:
            return FailureType.DEPENDENCY_MISSING
        
        elif "model" in error_lower or "llm" in error_lower or "provider" in error_lower:
            return FailureType.MODEL_FAILURE
        
        elif "validation" in error_lower or "invalid" in error_lower:
            return FailureType.VALIDATION_ERROR
        
        elif "resource" in error_lower or "unavailable" in error_lower:
            return FailureType.RESOURCE_UNAVAILABLE
        
        else:
            return FailureType.UNKNOWN
    
    def _recommend_strategy(
        self,
        failure_types: Dict[str, int],
        total_failures: int
    ) -> ReplanningStrategy:
        """Recommend replanning strategy based on failure analysis."""
        
        # If too many failures, abort
        if total_failures >= self.max_total_failures:
            return ReplanningStrategy.FAIL_PROJECT
        
        # Dependency issues → reorder
        if failure_types.get("DEPENDENCY_MISSING", 0) >= max(1, total_failures // 2):
            return ReplanningStrategy.REORDER_DEPENDENCIES
        
        # Validation issues → refine
        if failure_types.get("VALIDATION_ERROR", 0) >= max(1, total_failures // 2):
            return ReplanningStrategy.REFINE_DECOMPOSITION
        
        # Model/timeout issues → retry with different model
        model_timeout_count = (
            failure_types.get("MODEL_FAILURE", 0) +
            failure_types.get("TIMEOUT", 0)
        )
        if model_timeout_count >= max(1, total_failures // 2):
            return ReplanningStrategy.RETRY_WITH_DIFFERENT_MODEL
        
        # Resource issues → skip or retry
        if failure_types.get("RESOURCE_UNAVAILABLE", 0) >= max(1, total_failures // 2):
            return ReplanningStrategy.SKIP_TASK
        
        # Default: retry with same config
        return ReplanningStrategy.RETRY_WITH_SAME_CONFIG
    
    def _plan_retry_same_config(
        self,
        failed_tasks: List[ExecutionResult],
        analysis: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Plan retry with same configuration."""
        
        actions = [
            {
                "type": "retry",
                "task_id": result.task_id,
                "config": "same"
            }
            for result in failed_tasks
        ]
        
        return {
            "strategy": "RETRY_WITH_SAME_CONFIG",
            "actions": actions,
            "modified_tasks": [result.task_id for result in failed_tasks],
            "reason": "Transient failure, retry with same configuration"
        }
    
    def _plan_retry_different_model(
        self,
        failed_tasks: List[ExecutionResult],
        analysis: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Plan retry with different model."""
        
        # Cycle through available models
        available_models = context.get("available_models", ["grok", "granite", "tongyi"])
        current_model = context.get("current_model", "auto")
        
        # Select next model
        if current_model in available_models:
            current_index = available_models.index(current_model)
            next_model = available_models[(current_index + 1) % len(available_models)]
        else:
            next_model = available_models[0]
        
        actions = [
            {
                "type": "retry",
                "task_id": result.task_id,
                "config": "different_model",
                "model": next_model
            }
            for result in failed_tasks
        ]
        
        return {
            "strategy": "RETRY_WITH_DIFFERENT_MODEL",
            "actions": actions,
            "modified_tasks": [result.task_id for result in failed_tasks],
            "reason": f"Model/timeout failure, retry with {next_model}"
        }
    
    def _plan_reorder_dependencies(
        self,
        failed_tasks: List[ExecutionResult],
        analysis: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Plan dependency reordering."""
        
        actions = [
            {
                "type": "reorder",
                "task_id": result.task_id,
                "action": "move_to_end"
            }
            for result in failed_tasks
        ]
        
        return {
            "strategy": "REORDER_DEPENDENCIES",
            "actions": actions,
            "modified_tasks": [result.task_id for result in failed_tasks],
            "reason": "Dependency failure, reorder tasks"
        }
    
    def _plan_refine_decomposition(
        self,
        failed_tasks: List[ExecutionResult],
        analysis: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Plan decomposition refinement."""
        
        raise ValueError(
            "Refinement requires re-decomposition (not yet implemented). "
            f"Failed tasks: {[r.task_id for r in failed_tasks]}"
        )
    
    def _plan_skip_task(
        self,
        failed_tasks: List[ExecutionResult],
        analysis: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Plan to skip failed tasks."""
        
        actions = [
            {
                "type": "skip",
                "task_id": result.task_id,
                "reason": "Resource unavailable"
            }
            for result in failed_tasks
        ]
        
        return {
            "strategy": "SKIP_TASK",
            "actions": actions,
            "modified_tasks": [],  # No tasks to retry
            "reason": "Resource unavailable, skip tasks"
        }

