"""Integration tests for Worker Pools.

Tests SingleWorkerPool and KubernetesWorkerPool behavior
using mock SSH/MCP interactions.

Integration Testing: Validates adapter implementations
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch

from src.claude_orchestrator.entities.worker import (
    Worker,
    WorkerStatus,
    WorkerType,
    WorkerPoolConfig,
    ResourceLimits,
)
from src.claude_orchestrator.entities.generated_task import GeneratedTask
from src.claude_orchestrator.adapters.single_worker_pool import SingleWorkerPool
from src.claude_orchestrator.adapters.kubernetes_worker_pool import KubernetesWorkerPool
from src.claude_orchestrator.interfaces.worker_pool import (
    TaskOutput,
    TaskExecutionStatus,
    WorkerPoolExhausted,
    WorkerNotFound,
)


class TestSingleWorkerPool:
    """Integration tests for SingleWorkerPool (SSH-based)."""

    @pytest.fixture
    def ssh_config(self):
        """Create SSH worker pool configuration."""
        return WorkerPoolConfig(
            pool_type="ssh",
            max_workers=1,
            ssh_host="ui-cli_jake@syd2.jacobhollis.com",
            working_dir="/home/ui-cli_jake/autonomous-task-agent-dev-orchestration",
            model_name="gpt5",
        )

    @pytest.fixture
    def task(self):
        """Create sample generated task."""
        return GeneratedTask.create(
            id="test-task-1",
            instruction="Add unit tests for parser.py",
            rationale="Coverage analysis shows parser.py uncovered",
            goal_id="coverage-95",
            estimated_minutes=30,
            priority="P1",
        )

    def test_pool_initialization(self, ssh_config):
        """Test SingleWorkerPool initializes correctly."""
        pool = SingleWorkerPool(ssh_config)

        assert pool.config == ssh_config
        assert pool.worker is not None
        assert pool.worker.status == WorkerStatus.IDLE
        assert pool.worker.worker_type == WorkerType.SSH

    def test_get_available_workers(self, ssh_config):
        """Test getting available workers (1 idle worker)."""
        pool = SingleWorkerPool(ssh_config)

        available = pool.get_available_workers()

        assert len(available) == 1
        assert available[0].status == WorkerStatus.IDLE

    def test_assign_task(self, ssh_config, task):
        """Test assigning task to worker."""
        pool = SingleWorkerPool(ssh_config)

        worker = pool.assign_task(task)

        assert worker.status == WorkerStatus.BUSY
        assert worker.current_task_id == task.id
        assert worker.started_at is not None

    def test_get_worker_status(self, ssh_config, task):
        """Test getting worker status."""
        pool = SingleWorkerPool(ssh_config)
        worker = pool.assign_task(task)

        status_worker = pool.get_worker_status(worker.id)

        assert status_worker.id == worker.id
        assert status_worker.current_task_id == task.id

    def test_get_worker_status_not_found(self, ssh_config):
        """Test getting status for non-existent worker."""
        pool = SingleWorkerPool(ssh_config)

        with pytest.raises(WorkerNotFound):
            pool.get_worker_status("nonexistent-worker")

    def test_list_active_tasks(self, ssh_config, task):
        """Test listing active tasks."""
        pool = SingleWorkerPool(ssh_config)
        pool.assign_task(task)

        active = pool.list_active_tasks()

        assert len(active) == 1
        assert active[0].current_task_id == task.id

    def test_shutdown(self, ssh_config):
        """Test shutting down pool."""
        pool = SingleWorkerPool(ssh_config)
        pool.shutdown()

        assert pool.worker is None


class TestKubernetesWorkerPool:
    """Integration tests for KubernetesWorkerPool (MCP-based)."""

    @pytest.fixture
    def k8s_config(self):
        """Create Kubernetes worker pool configuration."""
        return WorkerPoolConfig(
            pool_type="kubernetes",
            max_workers=10,
            namespace="agentspace",
            image_name="unified-intelligence-worker:latest",
            model_name="meta-llama/Llama-3-8b",
            resources_per_worker=ResourceLimits(
                cpu_cores=2.0,
                memory_gb=8.0,
                disk_gb=50.0,
                timeout_minutes=30,
            ),
        )

    @pytest.fixture
    def tasks(self):
        """Create multiple tasks for parallel testing."""
        return [
            GeneratedTask.create(
                id=f"task-{i}",
                instruction=f"Task {i} instruction",
                rationale=f"Task {i} rationale",
                goal_id="coverage-95",
                estimated_minutes=30,
                priority="P1",
            )
            for i in range(3)
        ]

    def test_pool_initialization(self, k8s_config):
        """Test KubernetesWorkerPool initializes correctly."""
        pool = KubernetesWorkerPool(k8s_config)

        assert pool.config == k8s_config
        assert pool.active_count == 0
        assert len(pool.workers) == 0

    def test_assign_single_task(self, k8s_config, tasks):
        """Test assigning single task (creates pod)."""
        pool = KubernetesWorkerPool(k8s_config)

        worker = pool.assign_task(tasks[0])

        assert worker.status == WorkerStatus.BUSY
        assert worker.worker_type == WorkerType.KUBERNETES
        assert worker.current_task_id == tasks[0].id
        assert pool.active_count == 1

    def test_assign_multiple_tasks_parallel(self, k8s_config, tasks):
        """Test assigning multiple tasks in parallel."""
        pool = KubernetesWorkerPool(k8s_config)

        workers = [pool.assign_task(task) for task in tasks]

        assert len(workers) == 3
        assert pool.active_count == 3
        assert all(w.status == WorkerStatus.BUSY for w in workers)

    def test_pool_exhaustion(self, k8s_config, tasks):
        """Test worker pool exhaustion (max_workers limit)."""
        config = WorkerPoolConfig(
            pool_type="kubernetes",
            max_workers=2,  # Limit to 2 workers
            namespace="agentspace",
        )
        pool = KubernetesWorkerPool(config)

        # Assign 2 tasks (OK)
        pool.assign_task(tasks[0])
        pool.assign_task(tasks[1])

        # Try to assign 3rd task (should fail)
        with pytest.raises(WorkerPoolExhausted):
            pool.assign_task(tasks[2])

    def test_get_worker_status(self, k8s_config, tasks):
        """Test getting worker status."""
        pool = KubernetesWorkerPool(k8s_config)
        worker = pool.assign_task(tasks[0])

        status_worker = pool.get_worker_status(worker.id)

        assert status_worker.id == worker.id
        assert status_worker.current_task_id == tasks[0].id

    def test_get_worker_status_not_found(self, k8s_config):
        """Test getting status for non-existent worker."""
        pool = KubernetesWorkerPool(k8s_config)

        with pytest.raises(WorkerNotFound):
            pool.get_worker_status("task-nonexistent")

    def test_list_active_tasks(self, k8s_config, tasks):
        """Test listing active tasks."""
        pool = KubernetesWorkerPool(k8s_config)

        for task in tasks:
            pool.assign_task(task)

        active = pool.list_active_tasks()

        assert len(active) == 3
        assert all(w.status == WorkerStatus.BUSY for w in active)

    def test_cancel_task(self, k8s_config, tasks):
        """Test cancelling task."""
        pool = KubernetesWorkerPool(k8s_config)
        worker = pool.assign_task(tasks[0])

        cancelled_worker = pool.cancel_task(worker.id)

        assert cancelled_worker.status == WorkerStatus.CANCELLED
        assert pool.active_count == 0

    def test_shutdown(self, k8s_config, tasks):
        """Test shutting down pool with active tasks."""
        pool = KubernetesWorkerPool(k8s_config)

        # Assign multiple tasks
        for task in tasks:
            pool.assign_task(task)

        # Shutdown should cancel all
        pool.shutdown()

        assert len(pool.workers) == 0
        assert pool.active_count == 0


class TestWorkerPoolInterfaces:
    """Test that both pools implement IWorkerPool correctly."""

    @pytest.fixture
    def ssh_pool(self):
        """Create SSH worker pool."""
        config = WorkerPoolConfig(
            pool_type="ssh",
            max_workers=1,
            ssh_host="test@example.com",
            working_dir="/home/test",
        )
        return SingleWorkerPool(config)

    @pytest.fixture
    def k8s_pool(self):
        """Create Kubernetes worker pool."""
        config = WorkerPoolConfig(
            pool_type="kubernetes",
            max_workers=10,
            namespace="agentspace",
        )
        return KubernetesWorkerPool(config)

    @pytest.fixture
    def task(self):
        """Create test task."""
        return GeneratedTask.create(
            id="test-task",
            instruction="Test instruction",
            rationale="Test rationale",
            goal_id="test-goal",
            estimated_minutes=30,
            priority="P1",
        )

    def test_both_pools_implement_assign_task(self, ssh_pool, k8s_pool, task):
        """Test both pools implement assign_task."""
        ssh_worker = ssh_pool.assign_task(task)
        assert ssh_worker.status == WorkerStatus.BUSY

        task2 = GeneratedTask.create(
            id="test-task-2",
            instruction="Test 2",
            rationale="Test 2",
            goal_id="test-goal",
            estimated_minutes=30,
            priority="P1",
        )
        k8s_worker = k8s_pool.assign_task(task2)
        assert k8s_worker.status == WorkerStatus.BUSY

    def test_both_pools_implement_list_active_tasks(self, ssh_pool, k8s_pool, task):
        """Test both pools implement list_active_tasks."""
        ssh_pool.assign_task(task)
        assert len(ssh_pool.list_active_tasks()) == 1

        task2 = GeneratedTask.create(
            id="test-task-2",
            instruction="Test 2",
            rationale="Test 2",
            goal_id="test-goal",
            estimated_minutes=30,
            priority="P1",
        )
        k8s_pool.assign_task(task2)
        assert len(k8s_pool.list_active_tasks()) == 1

    def test_both_pools_implement_shutdown(self, ssh_pool, k8s_pool):
        """Test both pools implement shutdown."""
        ssh_pool.shutdown()
        k8s_pool.shutdown()
        # No exceptions = success
