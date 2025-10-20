"""Unit tests for Worker entity.

Tests the immutable Worker entity which represents a compute resource
executing tasks (SYD2 SSH worker, Kubernetes pod, local process, etc.).

TDD: Test-first approach for Worker entity.
"""

import pytest
from datetime import datetime, timedelta
from src.claude_orchestrator.entities.worker import (
    Worker,
    WorkerStatus,
    ResourceLimits,
    WorkerPoolConfig,
    WorkerType,
)


class TestWorkerEntity:
    """Test suite for Worker entity."""

    def test_worker_creation_with_all_fields(self):
        """Test creating Worker with all fields specified."""
        resources = ResourceLimits(
            cpu_cores=2.0,
            memory_gb=8.0,
            disk_gb=50.0,
            timeout_minutes=30,
        )

        worker = Worker.create(
            id="task-abc123",
            worker_type=WorkerType.KUBERNETES,
            status=WorkerStatus.IDLE,
            current_task_id=None,
            capabilities={"model": "llama-3-8b", "provider": "huggingface"},
            resource_limits=resources,
        )

        assert worker.id == "task-abc123"
        assert worker.worker_type == WorkerType.KUBERNETES
        assert worker.status == WorkerStatus.IDLE
        assert worker.current_task_id is None
        assert worker.capabilities["model"] == "llama-3-8b"
        assert worker.resource_limits.cpu_cores == 2.0
        assert isinstance(worker.created_at, datetime)

    def test_worker_immutability(self):
        """Test that Worker is immutable (frozen dataclass)."""
        worker = Worker.create(
            id="test-worker",
            worker_type=WorkerType.SSH,
            status=WorkerStatus.IDLE,
        )

        with pytest.raises(AttributeError):
            worker.status = WorkerStatus.BUSY

    def test_worker_default_values(self):
        """Test Worker creation with minimal fields (defaults applied)."""
        worker = Worker.create(
            id="minimal-worker",
            worker_type=WorkerType.LOCAL,
            status=WorkerStatus.IDLE,
        )

        assert worker.status == WorkerStatus.IDLE
        assert worker.current_task_id is None
        assert worker.capabilities == {}
        assert worker.resource_limits is None
        assert worker.started_at is None
        assert worker.completed_at is None
        assert isinstance(worker.created_at, datetime)

    def test_worker_assign_task(self):
        """Test assigning task to worker (returns new worker instance)."""
        worker = Worker.create(
            id="worker-1",
            worker_type=WorkerType.SSH,
            status=WorkerStatus.IDLE,
        )

        busy_worker = worker.assign_task("task-123")

        # Original unchanged (immutable)
        assert worker.status == WorkerStatus.IDLE
        assert worker.current_task_id is None

        # New instance has task assigned
        assert busy_worker.status == WorkerStatus.BUSY
        assert busy_worker.current_task_id == "task-123"
        assert isinstance(busy_worker.started_at, datetime)

    def test_worker_complete_task_success(self):
        """Test completing task successfully."""
        worker = Worker.create(
            id="worker-1",
            worker_type=WorkerType.KUBERNETES,
            status=WorkerStatus.BUSY,
            current_task_id="task-123",
        )

        completed_worker = worker.complete_task(success=True)

        assert completed_worker.status == WorkerStatus.COMPLETED
        assert completed_worker.current_task_id == "task-123"  # Still tracked
        assert isinstance(completed_worker.completed_at, datetime)

    def test_worker_complete_task_failure(self):
        """Test completing task with failure."""
        worker = Worker.create(
            id="worker-1",
            worker_type=WorkerType.SSH,
            status=WorkerStatus.BUSY,
            current_task_id="task-456",
        )

        failed_worker = worker.complete_task(success=False, error="Timeout exceeded")

        assert failed_worker.status == WorkerStatus.FAILED
        assert failed_worker.current_task_id == "task-456"
        assert failed_worker.error_message == "Timeout exceeded"
        assert isinstance(failed_worker.completed_at, datetime)

    def test_worker_cancel_task(self):
        """Test cancelling active task."""
        worker = Worker.create(
            id="worker-1",
            worker_type=WorkerType.KUBERNETES,
            status=WorkerStatus.BUSY,
            current_task_id="task-789",
        )

        cancelled_worker = worker.cancel_task()

        assert cancelled_worker.status == WorkerStatus.CANCELLED
        assert cancelled_worker.current_task_id == "task-789"
        assert isinstance(cancelled_worker.completed_at, datetime)

    def test_worker_is_available(self):
        """Test checking if worker is available for new tasks."""
        idle_worker = Worker.create(
            id="worker-idle",
            worker_type=WorkerType.SSH,
            status=WorkerStatus.IDLE,
        )

        busy_worker = Worker.create(
            id="worker-busy",
            worker_type=WorkerType.SSH,
            status=WorkerStatus.BUSY,
            current_task_id="task-1",
        )

        assert idle_worker.is_available() is True
        assert busy_worker.is_available() is False

    def test_worker_elapsed_time(self):
        """Test calculating elapsed execution time."""
        started = datetime.now() - timedelta(minutes=5)
        worker = Worker.create(
            id="worker-1",
            worker_type=WorkerType.KUBERNETES,
            status=WorkerStatus.BUSY,
            current_task_id="task-1",
            started_at=started,
        )

        elapsed = worker.elapsed_seconds()

        # Should be approximately 300 seconds (5 minutes)
        assert 295 <= elapsed <= 305

    def test_worker_elapsed_time_not_started(self):
        """Test elapsed time for worker that hasn't started."""
        worker = Worker.create(
            id="worker-1",
            worker_type=WorkerType.SSH,
            status=WorkerStatus.IDLE,
        )

        assert worker.elapsed_seconds() == 0

    def test_worker_to_dict_serialization(self):
        """Test Worker serialization to dictionary."""
        resources = ResourceLimits(
            cpu_cores=4.0,
            memory_gb=16.0,
            disk_gb=100.0,
            timeout_minutes=60,
        )

        worker = Worker.create(
            id="worker-serialize",
            worker_type=WorkerType.KUBERNETES,
            status=WorkerStatus.BUSY,
            current_task_id="task-serialize",
            capabilities={"model": "llama-3-70b"},
            resource_limits=resources,
        )

        worker_dict = worker.to_dict()

        assert worker_dict["id"] == "worker-serialize"
        assert worker_dict["worker_type"] == "kubernetes"
        assert worker_dict["status"] == "busy"
        assert worker_dict["current_task_id"] == "task-serialize"
        assert worker_dict["capabilities"]["model"] == "llama-3-70b"
        assert worker_dict["resource_limits"]["cpu_cores"] == 4.0
        assert "created_at" in worker_dict


class TestResourceLimits:
    """Test suite for ResourceLimits entity."""

    def test_resource_limits_creation(self):
        """Test creating ResourceLimits with all fields."""
        limits = ResourceLimits(
            cpu_cores=2.0,
            memory_gb=8.0,
            disk_gb=50.0,
            timeout_minutes=30,
        )

        assert limits.cpu_cores == 2.0
        assert limits.memory_gb == 8.0
        assert limits.disk_gb == 50.0
        assert limits.timeout_minutes == 30

    def test_resource_limits_defaults(self):
        """Test ResourceLimits with default values."""
        limits = ResourceLimits()

        assert limits.cpu_cores == 1.0
        assert limits.memory_gb == 2.0
        assert limits.disk_gb == 10.0
        assert limits.timeout_minutes == 30

    def test_resource_limits_to_dict(self):
        """Test ResourceLimits serialization."""
        limits = ResourceLimits(cpu_cores=4.0, memory_gb=16.0)

        limits_dict = limits.to_dict()

        assert limits_dict["cpu_cores"] == 4.0
        assert limits_dict["memory_gb"] == 16.0


class TestWorkerPoolConfig:
    """Test suite for WorkerPoolConfig entity."""

    def test_worker_pool_config_creation(self):
        """Test creating WorkerPoolConfig with all fields."""
        resources = ResourceLimits(cpu_cores=2.0, memory_gb=8.0)

        config = WorkerPoolConfig(
            pool_type="kubernetes",
            max_workers=10,
            namespace="agentspace",
            model_name="meta-llama/Llama-3-8b",
            resources_per_worker=resources,
        )

        assert config.pool_type == "kubernetes"
        assert config.max_workers == 10
        assert config.namespace == "agentspace"
        assert config.model_name == "meta-llama/Llama-3-8b"
        assert config.resources_per_worker.cpu_cores == 2.0

    def test_worker_pool_config_ssh_type(self):
        """Test SSH worker pool configuration."""
        config = WorkerPoolConfig(
            pool_type="ssh",
            max_workers=1,
            ssh_host="ui-cli_jake@syd2.jacobhollis.com",
            working_dir="/home/ui-cli_jake/autonomous-task-agent-dev-orchestration",
        )

        assert config.pool_type == "ssh"
        assert config.max_workers == 1
        assert config.ssh_host == "ui-cli_jake@syd2.jacobhollis.com"

    def test_worker_pool_config_validation(self):
        """Test config validation (max_workers > 0)."""
        with pytest.raises(ValueError, match="max_workers must be > 0"):
            WorkerPoolConfig(
                pool_type="kubernetes",
                max_workers=0,
            )


class TestWorkerStatusEnum:
    """Test suite for WorkerStatus enum."""

    def test_worker_status_values(self):
        """Test WorkerStatus enum has expected values."""
        assert WorkerStatus.IDLE.value == "idle"
        assert WorkerStatus.BUSY.value == "busy"
        assert WorkerStatus.COMPLETED.value == "completed"
        assert WorkerStatus.FAILED.value == "failed"
        assert WorkerStatus.CANCELLED.value == "cancelled"
        assert WorkerStatus.TERMINATED.value == "terminated"


class TestWorkerTypeEnum:
    """Test suite for WorkerType enum."""

    def test_worker_type_values(self):
        """Test WorkerType enum has expected values."""
        assert WorkerType.SSH.value == "ssh"
        assert WorkerType.KUBERNETES.value == "kubernetes"
        assert WorkerType.LOCAL.value == "local"
        assert WorkerType.DOCKER.value == "docker"
