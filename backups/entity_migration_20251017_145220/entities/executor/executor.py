"""Executor abstraction for task execution.

Provides abstract interface for task executors, enabling polymorphic
execution across different backends (local, remote, containerized, etc.).
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, Optional
from datetime import datetime


class ExecutorStatus(Enum):
    """Status of executor."""

    IDLE = auto()
    BUSY = auto()
    FAILED = auto()
    UNAVAILABLE = auto()


@dataclass
class ExecutionResult:
    """Result of task execution.

    Attributes:
        success: Whether execution succeeded
        output: Execution output data
        error: Error message if failed
        duration: Execution duration in seconds
        metadata: Additional execution information
    """

    success: bool
    output: Any = None
    error: Optional[str] = None
    duration: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


class Executor(ABC):
    """Abstract base class for task executors.

    Defines interface for executing tasks across different backends.
    Implementations handle specific execution environments (local shell,
    remote SSH, Docker containers, cloud functions, etc.).

    All executors are resource-agnostic - they adapt to available resources
    automatically without explicit resource management at this abstraction level.
    """

    def __init__(self, executor_id: str, name: str = ""):
        """Initialize executor.

        Args:
            executor_id: Unique identifier for this executor
            name: Human-readable name
        """
        self.executor_id = executor_id
        self.name = name or f"Executor-{executor_id}"
        self.status = ExecutorStatus.IDLE
        self.current_task_id: Optional[str] = None
        self.execution_count = 0
        self.metadata: Dict[str, Any] = {}

    @abstractmethod
    def can_execute(self, task: Any) -> bool:
        """Check if executor can handle given task.

        Args:
            task: Task to check

        Returns:
            True if executor can execute this task
        """
        pass

    @abstractmethod
    def execute(self, task: Any, **kwargs) -> ExecutionResult:
        """Execute a task.

        Args:
            task: Task to execute
            **kwargs: Additional execution parameters

        Returns:
            ExecutionResult containing outcome

        Raises:
            Exception: If execution fails critically
        """
        pass

    def get_status(self) -> ExecutorStatus:
        """Get current executor status.

        Returns:
            Current status
        """
        return self.status

    def is_available(self) -> bool:
        """Check if executor is available for new tasks.

        Returns:
            True if status is IDLE
        """
        return self.status == ExecutorStatus.IDLE

    def is_busy(self) -> bool:
        """Check if executor is currently executing a task.

        Returns:
            True if status is BUSY
        """
        return self.status == ExecutorStatus.BUSY

    @abstractmethod
    def cancel(self, task_id: str) -> bool:
        """Cancel a running task.

        Args:
            task_id: ID of task to cancel

        Returns:
            True if cancellation succeeded
        """
        pass

    def get_current_task(self) -> Optional[str]:
        """Get ID of currently executing task.

        Returns:
            Task ID if executor is busy, None otherwise
        """
        return self.current_task_id

    def get_execution_count(self) -> int:
        """Get total number of executions performed.

        Returns:
            Execution count
        """
        return self.execution_count

    def set_metadata(self, key: str, value: Any) -> None:
        """Set executor metadata.

        Args:
            key: Metadata key
            value: Metadata value
        """
        self.metadata[key] = value

    def get_metadata(self, key: str, default: Any = None) -> Any:
        """Get executor metadata.

        Args:
            key: Metadata key
            default: Default value if key not found

        Returns:
            Metadata value or default
        """
        return self.metadata.get(key, default)

    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"{self.__class__.__name__}(id='{self.executor_id}', "
            f"name='{self.name}', status={self.status.name})"
        )


class LocalExecutor(Executor):
    """Concrete executor for local task execution.

    Executes tasks in the local environment (e.g., subprocess, function call).
    Useful for development, testing, and single-machine deployments.
    """

    def can_execute(self, task: Any) -> bool:
        """Check if task can be executed locally.

        For demonstration, accepts any task with 'command' or 'function' attribute.

        Args:
            task: Task to check

        Returns:
            True if task is executable locally
        """
        return hasattr(task, "command") or callable(task)

    def execute(self, task: Any, **kwargs) -> ExecutionResult:
        """Execute task locally.

        Args:
            task: Task to execute (must be callable or have 'command')
            **kwargs: Additional execution parameters

        Returns:
            ExecutionResult with outcome
        """
        if not self.can_execute(task):
            return ExecutionResult(
                success=False,
                error="Task not executable by LocalExecutor"
            )

        self.status = ExecutorStatus.BUSY
        self.current_task_id = getattr(task, "entity_id", str(id(task)))

        start_time = datetime.utcnow()

        try:
            # Execute callable task
            if callable(task):
                result = task(**kwargs)
                output = result
            # Execute task with command (stub for demonstration)
            elif hasattr(task, "command"):
                # In real implementation, would use subprocess
                output = f"Executed: {task.command}"
            else:
                raise ValueError("Task not executable")

            duration = (datetime.utcnow() - start_time).total_seconds()

            self.execution_count += 1
            self.status = ExecutorStatus.IDLE
            self.current_task_id = None

            return ExecutionResult(
                success=True,
                output=output,
                duration=duration
            )

        except Exception as e:
            duration = (datetime.utcnow() - start_time).total_seconds()

            self.status = ExecutorStatus.FAILED
            self.current_task_id = None

            return ExecutionResult(
                success=False,
                error=str(e),
                duration=duration
            )

    def cancel(self, task_id: str) -> bool:
        """Cancel running task.

        Args:
            task_id: Task ID to cancel

        Returns:
            True if task was cancelled
        """
        if self.current_task_id == task_id:
            self.current_task_id = None
            self.status = ExecutorStatus.IDLE
            return True
        return False


class ExecutorPool:
    """Pool of executors for load balancing and fault tolerance.

    Manages multiple executors, routing tasks to available executors
    and providing fallback on failures.
    """

    def __init__(self):
        """Initialize empty executor pool."""
        self.executors: Dict[str, Executor] = {}

    def register_executor(self, executor: Executor) -> None:
        """Add executor to pool.

        Args:
            executor: Executor to register
        """
        self.executors[executor.executor_id] = executor

    def unregister_executor(self, executor_id: str) -> bool:
        """Remove executor from pool.

        Args:
            executor_id: ID of executor to remove

        Returns:
            True if executor was removed
        """
        if executor_id in self.executors:
            del self.executors[executor_id]
            return True
        return False

    def get_executor(self, executor_id: str) -> Optional[Executor]:
        """Get executor by ID.

        Args:
            executor_id: Executor identifier

        Returns:
            Executor if found, None otherwise
        """
        return self.executors.get(executor_id)

    def get_available_executor(self, task: Any = None) -> Optional[Executor]:
        """Find an available executor for task.

        Args:
            task: Optional task to match against executor capabilities

        Returns:
            Available executor, or None if none available
        """
        for executor in self.executors.values():
            if executor.is_available():
                if task is None or executor.can_execute(task):
                    return executor
        return None

    def execute_task(self, task: Any, **kwargs) -> Optional[ExecutionResult]:
        """Execute task using any available executor.

        Args:
            task: Task to execute
            **kwargs: Additional execution parameters

        Returns:
            ExecutionResult if task executed, None if no executor available
        """
        executor = self.get_available_executor(task)
        if executor:
            return executor.execute(task, **kwargs)
        return None

    def get_pool_status(self) -> Dict[str, int]:
        """Get pool status summary.

        Returns:
            Dictionary with counts by status
        """
        status_counts = {
            "idle": 0,
            "busy": 0,
            "failed": 0,
            "unavailable": 0
        }

        for executor in self.executors.values():
            status = executor.get_status()
            if status == ExecutorStatus.IDLE:
                status_counts["idle"] += 1
            elif status == ExecutorStatus.BUSY:
                status_counts["busy"] += 1
            elif status == ExecutorStatus.FAILED:
                status_counts["failed"] += 1
            elif status == ExecutorStatus.UNAVAILABLE:
                status_counts["unavailable"] += 1

        return status_counts

    def get_executor_count(self) -> int:
        """Get total number of executors in pool.

        Returns:
            Executor count
        """
        return len(self.executors)
