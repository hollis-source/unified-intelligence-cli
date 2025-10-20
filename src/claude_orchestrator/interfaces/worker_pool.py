"""IWorkerPool Interface.

Abstract interface for worker pool implementations.
Allows swapping between SSH (SYD2), Kubernetes, local process pools.

Clean Architecture: Interface/Port layer (dependency inversion)
SOLID: DIP - orchestrator depends on abstraction, not concretions
"""

from abc import ABC, abstractmethod
from typing import List, Optional
from dataclasses import dataclass
from enum import Enum

from src.claude_orchestrator.entities.worker import Worker, WorkerPoolConfig
from src.claude_orchestrator.entities.generated_task import GeneratedTask


class TaskExecutionStatus(str, Enum):
    """Status of task execution by worker."""

    SUBMITTED = "submitted"  # Task submitted to worker
    RUNNING = "running"  # Worker executing task
    COMPLETED = "completed"  # Task completed successfully
    FAILED = "failed"  # Task failed with error
    CANCELLED = "cancelled"  # Task cancelled by orchestrator


@dataclass
class TaskOutput:
    """
    Output from worker task execution.

    Contains:
    - PR URL (if created)
    - Logs (stdout/stderr)
    - Modified files
    - Artifacts
    """

    task_id: str
    status: TaskExecutionStatus

    # Output
    pr_url: Optional[str] = None
    stdout: str = ""
    stderr: str = ""
    modified_files: List[str] = None
    artifacts: dict = None

    # Metadata
    exit_code: int = 0
    execution_time_seconds: float = 0.0

    def __post_init__(self):
        """Initialize defaults."""
        if self.modified_files is None:
            object.__setattr__(self, "modified_files", [])
        if self.artifacts is None:
            object.__setattr__(self, "artifacts", {})


class IWorkerPool(ABC):
    """
    Abstract interface for worker pools.

    Implementations:
    - SingleWorkerPool: SSH-based, 1 worker (SYD2)
    - KubernetesWorkerPool: MCP-based, N workers (K8s pods)
    - LocalProcessWorkerPool: Local processes (dev/testing)

    Usage:
        config = WorkerPoolConfig(pool_type="ssh", max_workers=1, ssh_host="syd2...")
        pool = SingleWorkerPool(config)

        # Assign task to available worker
        task = GeneratedTask.create(...)
        worker = pool.assign_task(task)

        # Wait for completion
        output = pool.wait_for_completion(worker.id, timeout_minutes=30)

        # Check status
        updated_worker = pool.get_worker_status(worker.id)
    """

    @abstractmethod
    def __init__(self, config: WorkerPoolConfig):
        """
        Initialize worker pool with configuration.

        Args:
            config: Worker pool configuration
        """
        pass

    @abstractmethod
    def assign_task(self, task: GeneratedTask) -> Worker:
        """
        Assign task to available worker.

        Blocks until worker is available if pool is at capacity.
        Creates new worker (for K8s) or reuses existing (for SSH).

        Args:
            task: Generated task to assign

        Returns:
            Worker instance with task assigned (status=BUSY)

        Raises:
            WorkerPoolExhausted: If no workers available and can't create more
            WorkerExecutionError: If worker creation/assignment fails
        """
        pass

    @abstractmethod
    def get_available_workers(self) -> List[Worker]:
        """
        Get list of idle workers ready for task assignment.

        Returns:
            List of workers with status=IDLE
        """
        pass

    @abstractmethod
    def get_worker_status(self, worker_id: str) -> Worker:
        """
        Get current status of worker.

        Args:
            worker_id: Worker ID

        Returns:
            Worker instance with updated status

        Raises:
            WorkerNotFound: If worker ID not found
        """
        pass

    @abstractmethod
    def wait_for_completion(
        self, worker_id: str, timeout_minutes: int = 30, poll_interval_seconds: int = 10
    ) -> TaskOutput:
        """
        Wait for worker to complete task (blocking).

        Polls worker status until completion or timeout.

        Args:
            worker_id: Worker ID
            timeout_minutes: Maximum time to wait
            poll_interval_seconds: How often to check status

        Returns:
            TaskOutput with results

        Raises:
            TaskTimeoutError: If timeout exceeded
            WorkerExecutionError: If worker execution fails
        """
        pass

    @abstractmethod
    def cancel_task(self, worker_id: str) -> Worker:
        """
        Cancel worker's current task.

        Terminates worker (K8s) or stops execution (SSH/local).

        Args:
            worker_id: Worker ID

        Returns:
            Worker instance with status=CANCELLED

        Raises:
            WorkerNotFound: If worker ID not found
            CancellationFailed: If cancellation fails
        """
        pass

    @abstractmethod
    def list_active_tasks(self) -> List[Worker]:
        """
        List all workers with active tasks.

        Returns:
            List of workers with status=BUSY
        """
        pass

    @abstractmethod
    def shutdown(self) -> None:
        """
        Shutdown worker pool.

        Cancels all active tasks, terminates all workers, cleanup resources.
        """
        pass


# Custom exceptions

class WorkerPoolError(Exception):
    """Base exception for worker pool errors."""

    pass


class WorkerPoolExhausted(WorkerPoolError):
    """No workers available and pool at max capacity."""

    pass


class WorkerExecutionError(WorkerPoolError):
    """Worker execution failed."""

    pass


class WorkerNotFound(WorkerPoolError):
    """Worker ID not found in pool."""

    pass


class TaskTimeoutError(WorkerPoolError):
    """Task execution exceeded timeout."""

    pass


class CancellationFailed(WorkerPoolError):
    """Failed to cancel task."""

    pass
