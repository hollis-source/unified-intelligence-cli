"""Worker Entity.

Represents a compute resource that executes tasks autonomously.
Workers can be: SSH-based (SYD2), Kubernetes pods, local processes, Docker containers.

Clean Architecture: Core entity (immutable, no dependencies)
SOLID: SRP - single responsibility for worker representation
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Optional, Any
from datetime import datetime


class WorkerStatus(str, Enum):
    """Status of a worker in its execution lifecycle."""

    IDLE = "idle"  # Available for task assignment
    BUSY = "busy"  # Currently executing a task
    COMPLETED = "completed"  # Task finished successfully
    FAILED = "failed"  # Task failed with error
    CANCELLED = "cancelled"  # Task cancelled by orchestrator
    TERMINATED = "terminated"  # Worker shut down permanently


class WorkerType(str, Enum):
    """Type of worker execution environment."""

    SSH = "ssh"  # SSH-based worker (e.g., SYD2)
    KUBERNETES = "kubernetes"  # Kubernetes pod worker
    LOCAL = "local"  # Local process worker (dev/testing)
    DOCKER = "docker"  # Docker container worker


@dataclass(frozen=True)
class ResourceLimits:
    """
    Resource constraints for worker execution.

    Defines CPU, memory, disk, and time limits for task execution.
    Used by worker pools to provision appropriate resources.

    Example:
        limits = ResourceLimits(
            cpu_cores=2.0,
            memory_gb=8.0,
            disk_gb=50.0,
            timeout_minutes=30
        )
    """

    cpu_cores: float = 1.0  # CPU cores allocated
    memory_gb: float = 2.0  # RAM in GB
    disk_gb: float = 10.0  # Disk space in GB
    timeout_minutes: int = 30  # Max execution time

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "cpu_cores": self.cpu_cores,
            "memory_gb": self.memory_gb,
            "disk_gb": self.disk_gb,
            "timeout_minutes": self.timeout_minutes,
        }


@dataclass(frozen=True)
class WorkerPoolConfig:
    """
    Configuration for worker pool.

    Defines how workers are provisioned, managed, and scaled.
    Different pool types (SSH, Kubernetes, Local) require different config.

    Example - Kubernetes:
        config = WorkerPoolConfig(
            pool_type="kubernetes",
            max_workers=10,
            namespace="agentspace",
            model_name="meta-llama/Llama-3-8b",
            resources_per_worker=ResourceLimits(cpu_cores=2.0, memory_gb=8.0)
        )

    Example - SSH:
        config = WorkerPoolConfig(
            pool_type="ssh",
            max_workers=1,
            ssh_host="user@syd2.example.com",
            working_dir="/home/user/project"
        )
    """

    pool_type: str  # "ssh", "kubernetes", "local", "docker"
    max_workers: int  # Maximum concurrent workers

    # Kubernetes-specific
    namespace: Optional[str] = None
    image_name: Optional[str] = None

    # SSH-specific
    ssh_host: Optional[str] = None
    working_dir: Optional[str] = None

    # Common
    model_name: Optional[str] = None
    resources_per_worker: Optional[ResourceLimits] = None

    def __post_init__(self):
        """Validate configuration."""
        if self.max_workers <= 0:
            raise ValueError("max_workers must be > 0")

        if self.pool_type == "kubernetes" and not self.namespace:
            raise ValueError("namespace required for kubernetes pool")

        if self.pool_type == "ssh" and not self.ssh_host:
            raise ValueError("ssh_host required for ssh pool")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "pool_type": self.pool_type,
            "max_workers": self.max_workers,
            "namespace": self.namespace,
            "image_name": self.image_name,
            "ssh_host": self.ssh_host,
            "working_dir": self.working_dir,
            "model_name": self.model_name,
            "resources_per_worker": self.resources_per_worker.to_dict() if self.resources_per_worker else None,
        }


@dataclass(frozen=True)
class Worker:
    """
    Represents a compute resource executing tasks.

    Immutable entity representing a worker (SSH process, K8s pod, local process).
    Workers have lifecycle: IDLE → BUSY → COMPLETED/FAILED/CANCELLED → TERMINATED.

    For ephemeral workers (Kubernetes), worker ID = task ID.
    For persistent workers (SSH), worker ID is static.

    Example:
        worker = Worker.create(
            id="task-abc123",
            worker_type=WorkerType.KUBERNETES,
            status=WorkerStatus.IDLE,
            capabilities={"model": "llama-3-8b", "provider": "huggingface"},
            resource_limits=ResourceLimits(cpu_cores=2.0, memory_gb=8.0)
        )

        # Assign task (returns new instance - immutable)
        busy_worker = worker.assign_task("task-abc123")

        # Complete task
        completed_worker = busy_worker.complete_task(success=True)
    """

    # Identity
    id: str  # Unique worker ID (for K8s: task-{id}, for SSH: worker-{name})
    worker_type: WorkerType

    # State
    status: WorkerStatus
    current_task_id: Optional[str] = None
    error_message: Optional[str] = None

    # Capabilities
    capabilities: Dict[str, Any] = field(default_factory=dict)
    resource_limits: Optional[ResourceLimits] = None

    # Lifecycle timestamps
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    @staticmethod
    def create(
        id: str,
        worker_type: WorkerType,
        status: WorkerStatus,
        current_task_id: Optional[str] = None,
        capabilities: Optional[Dict[str, Any]] = None,
        resource_limits: Optional[ResourceLimits] = None,
        started_at: Optional[datetime] = None,
        completed_at: Optional[datetime] = None,
    ) -> "Worker":
        """
        Factory method to create Worker with validation.

        Args:
            id: Unique worker identifier
            worker_type: Type of worker (SSH, Kubernetes, etc.)
            status: Current worker status
            current_task_id: ID of task being executed (if any)
            capabilities: Worker capabilities (model, provider, etc.)
            resource_limits: Resource constraints
            started_at: When worker started current task
            completed_at: When worker completed current task

        Returns:
            Worker instance
        """
        return Worker(
            id=id,
            worker_type=worker_type,
            status=status,
            current_task_id=current_task_id,
            capabilities=capabilities or {},
            resource_limits=resource_limits,
            started_at=started_at,
            completed_at=completed_at,
        )

    def assign_task(self, task_id: str) -> "Worker":
        """
        Assign task to worker (returns new worker instance).

        Transitions: IDLE → BUSY

        Args:
            task_id: ID of task to assign

        Returns:
            New Worker instance with task assigned
        """
        return Worker(
            id=self.id,
            worker_type=self.worker_type,
            status=WorkerStatus.BUSY,
            current_task_id=task_id,
            capabilities=self.capabilities,
            resource_limits=self.resource_limits,
            created_at=self.created_at,
            started_at=datetime.now(),
            completed_at=None,
            error_message=None,
        )

    def complete_task(self, success: bool, error: Optional[str] = None) -> "Worker":
        """
        Mark task as completed (returns new worker instance).

        Transitions: BUSY → COMPLETED (success) or FAILED (failure)

        Args:
            success: Whether task completed successfully
            error: Error message if failed

        Returns:
            New Worker instance with completion recorded
        """
        return Worker(
            id=self.id,
            worker_type=self.worker_type,
            status=WorkerStatus.COMPLETED if success else WorkerStatus.FAILED,
            current_task_id=self.current_task_id,
            capabilities=self.capabilities,
            resource_limits=self.resource_limits,
            created_at=self.created_at,
            started_at=self.started_at,
            completed_at=datetime.now(),
            error_message=error,
        )

    def cancel_task(self) -> "Worker":
        """
        Cancel current task (returns new worker instance).

        Transitions: BUSY → CANCELLED

        Returns:
            New Worker instance with cancellation recorded
        """
        return Worker(
            id=self.id,
            worker_type=self.worker_type,
            status=WorkerStatus.CANCELLED,
            current_task_id=self.current_task_id,
            capabilities=self.capabilities,
            resource_limits=self.resource_limits,
            created_at=self.created_at,
            started_at=self.started_at,
            completed_at=datetime.now(),
            error_message="Task cancelled by orchestrator",
        )

    def is_available(self) -> bool:
        """
        Check if worker is available for new task assignment.

        Returns:
            True if worker is IDLE, False otherwise
        """
        return self.status == WorkerStatus.IDLE

    def elapsed_seconds(self) -> float:
        """
        Calculate elapsed execution time in seconds.

        Returns:
            Seconds elapsed since task started (0 if not started)
        """
        if self.started_at is None:
            return 0.0

        end_time = self.completed_at or datetime.now()
        elapsed = (end_time - self.started_at).total_seconds()
        return elapsed

    def to_dict(self) -> Dict[str, Any]:
        """Convert worker to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "worker_type": self.worker_type.value,
            "status": self.status.value,
            "current_task_id": self.current_task_id,
            "error_message": self.error_message,
            "capabilities": self.capabilities,
            "resource_limits": self.resource_limits.to_dict() if self.resource_limits else None,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "elapsed_seconds": self.elapsed_seconds(),
        }
