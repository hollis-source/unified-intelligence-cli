"""Feedback handler interface - DIP: Core depends on abstraction.

This interface defines the contract for feedback-driven replanning when
tasks fail during execution.

Clean Architecture: Interface layer (abstraction for use cases)
SOLID: ISP (narrow interface), DIP (depend on abstraction)
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any
from src.entity.execution import ExecutionResult


class IFeedbackHandler(ABC):
    """Interface for feedback-driven replanning.
    
    Implementations analyze task failures and determine appropriate
    replanning strategies (retry, reorder, refine, or fail).
    
    Example:
        >>> handler = FeedbackCoordinatorUseCase(max_retries=3)
        >>> failed_tasks = [result1, result2]
        >>> strategy = handler.analyze_failures(failed_tasks)
        >>> new_plan = handler.replan(current_plan, failed_tasks, strategy)
    """
    
    @abstractmethod
    def analyze_failures(
        self,
        failed_tasks: List[ExecutionResult]
    ) -> Dict[str, Any]:
        """Analyze failed tasks and classify failure types.
        
        Args:
            failed_tasks: List of failed task execution results
        
        Returns:
            Dict containing:
                - failure_types: Dict[str, int] - Count of each failure type
                - total_failures: int - Total number of failures
                - error_messages: List[str] - All error messages
                - task_ids: List[str] - IDs of failed tasks
                - recommended_strategy: str - Recommended replanning strategy
        
        Example:
            >>> analysis = handler.analyze_failures(failed_tasks)
            >>> print(analysis['recommended_strategy'])
            'RETRY_WITH_DIFFERENT_MODEL'
        """
        pass
    
    @abstractmethod
    def should_replan(
        self,
        analysis: Dict[str, Any],
        attempt_count: int
    ) -> bool:
        """Determine if replanning should occur.
        
        Args:
            analysis: Failure analysis from analyze_failures()
            attempt_count: Current attempt number
        
        Returns:
            bool: True if replanning should occur, False to abort
        
        Example:
            >>> if handler.should_replan(analysis, attempt=2):
            ...     new_plan = handler.replan(...)
        """
        pass
    
    @abstractmethod
    def replan(
        self,
        failed_tasks: List[ExecutionResult],
        analysis: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create replanning strategy based on failure analysis.
        
        Args:
            failed_tasks: List of failed task results
            analysis: Failure analysis from analyze_failures()
            context: Execution context (state, history, etc.)
        
        Returns:
            Dict containing:
                - strategy: str - Replanning strategy name
                - actions: List[Dict] - Actions to take
                - modified_tasks: List[Task] - Tasks to retry/modify
                - reason: str - Explanation of replanning decision
        
        Raises:
            ValueError: If replanning fails or project should abort
        
        Example:
            >>> plan = handler.replan(failed_tasks, analysis, context)
            >>> print(plan['strategy'])
            'RETRY_WITH_DIFFERENT_MODEL'
            >>> print(plan['actions'])
            [{'type': 'retry', 'task_id': 'task1', 'model': 'grok'}]
        """
        pass
    
    @abstractmethod
    def record_failure(
        self,
        task_id: str,
        failure_type: str,
        error_message: str
    ) -> None:
        """Record failure for historical analysis.
        
        Args:
            task_id: ID of failed task
            failure_type: Type of failure (timeout, dependency, model, etc.)
            error_message: Error message from failure
        
        Example:
            >>> handler.record_failure('task1', 'TIMEOUT', 'Task timed out after 60s')
        """
        pass
    
    @abstractmethod
    def get_failure_history(self, task_id: str) -> List[Dict[str, Any]]:
        """Get failure history for a task.
        
        Args:
            task_id: ID of task
        
        Returns:
            List of failure records with timestamps and details
        
        Example:
            >>> history = handler.get_failure_history('task1')
            >>> print(f"Task failed {len(history)} times")
        """
        pass

