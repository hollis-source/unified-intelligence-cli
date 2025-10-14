"""KubernetesWorkerPool Adapter.

Kubernetes-based worker pool using MCP "agentspace" server.
Scales to N parallel workers (ephemeral containers).

Clean Architecture: Adapter layer (implements IWorkerPool interface)
SOLID: LSP - substitutable for IWorkerPool
"""

import time
from typing import List, Dict, Optional
from datetime import datetime

from src.claude_orchestrator.interfaces.worker_pool import (
    IWorkerPool,
    TaskOutput,
    TaskExecutionStatus,
    WorkerPoolExhausted,
    WorkerExecutionError,
    WorkerNotFound,
    TaskTimeoutError,
    CancellationFailed,
)
from src.claude_orchestrator.entities.worker import (
    Worker,
    WorkerStatus,
    WorkerType,
    WorkerPoolConfig,
)
from src.claude_orchestrator.entities.generated_task import GeneratedTask


class KubernetesWorkerPool(IWorkerPool):
    """
    Kubernetes-based worker pool using MCP tools.

    Characteristics:
    - Parallel execution (N tasks simultaneously)
    - Ephemeral workers (1 container = 1 task)
    - MCP-based (uses agentspace_* tools)
    - Auto-scaling within resource limits

    MCP Tools Used:
    - agentspace_create_task(task_id, instruction) → creates K8s pod
    - agentspace_get_status(task_id) → checks pod status
    - agentspace_get_output(task_id) → retrieves logs/PR
    - agentspace_cancel_task(task_id) → terminates pod
    - agentspace_list_active() → lists running pods

    Usage:
        config = WorkerPoolConfig(
            pool_type="kubernetes",
            max_workers=10,
            namespace="agentspace",
            image_name="unified-intelligence-worker:latest",
            model_name="meta-llama/Llama-3-8b",
        )

        pool = KubernetesWorkerPool(config)
        worker = pool.assign_task(task)  # Creates K8s pod
        output = pool.wait_for_completion(worker.id, timeout_minutes=30)
    """

    def __init__(self, config: WorkerPoolConfig):
        """
        Initialize Kubernetes worker pool.

        Args:
            config: Worker pool configuration (must be kubernetes type)
        """
        if config.pool_type != "kubernetes":
            raise ValueError(f"KubernetesWorkerPool requires kubernetes pool_type, got {config.pool_type}")

        self.config = config
        self.workers: Dict[str, Worker] = {}  # worker_id -> Worker
        self.active_count = 0

    def assign_task(self, task: GeneratedTask) -> Worker:
        """
        Assign task to new Kubernetes worker (creates pod).

        Args:
            task: Generated task to assign

        Returns:
            Worker instance representing K8s pod

        Raises:
            WorkerPoolExhausted: If max_workers limit reached
            WorkerExecutionError: If pod creation fails
        """
        # Check capacity
        if self.active_count >= self.config.max_workers:
            raise WorkerPoolExhausted(
                f"Worker pool at max capacity ({self.config.max_workers}). "
                "Wait for tasks to complete or increase max_workers."
            )

        # Create worker (ephemeral - tied to task)
        worker_id = f"task-{task.id}"
        worker = Worker.create(
            id=worker_id,
            worker_type=WorkerType.KUBERNETES,
            status=WorkerStatus.IDLE,
            capabilities={
                "namespace": self.config.namespace,
                "model": self.config.model_name,
                "image": self.config.image_name,
            },
            resource_limits=self.config.resources_per_worker,
        )

        # Create K8s pod via MCP
        try:
            self._create_pod_mcp(task)
            worker = worker.assign_task(task.id)
            self.workers[worker_id] = worker
            self.active_count += 1
        except Exception as e:
            raise WorkerExecutionError(f"Failed to create pod for task {task.id}: {e}")

        return worker

    def get_available_workers(self) -> List[Worker]:
        """
        Get list of idle workers.

        For K8s pool, this is based on capacity (max_workers - active).

        Returns:
            Empty list (K8s creates workers on-demand)
        """
        # K8s pool creates workers on-demand, doesn't maintain idle workers
        return []

    def get_worker_status(self, worker_id: str) -> Worker:
        """
        Get current status of worker (K8s pod).

        Args:
            worker_id: Worker ID (format: task-{id})

        Returns:
            Worker instance with updated status

        Raises:
            WorkerNotFound: If worker not found
        """
        if worker_id not in self.workers:
            raise WorkerNotFound(f"Worker {worker_id} not found")

        worker = self.workers[worker_id]

        # Check pod status via MCP
        if worker.status == WorkerStatus.BUSY:
            status = self._check_pod_status_mcp(worker.current_task_id)

            if status == TaskExecutionStatus.COMPLETED:
                worker = worker.complete_task(success=True)
                self.workers[worker_id] = worker
                self.active_count -= 1
            elif status == TaskExecutionStatus.FAILED:
                worker = worker.complete_task(success=False, error="Pod failed")
                self.workers[worker_id] = worker
                self.active_count -= 1

        return worker

    def wait_for_completion(
        self, worker_id: str, timeout_minutes: int = 30, poll_interval_seconds: int = 10
    ) -> TaskOutput:
        """
        Wait for worker (K8s pod) to complete task.

        Args:
            worker_id: Worker ID
            timeout_minutes: Maximum time to wait
            poll_interval_seconds: How often to check status

        Returns:
            TaskOutput with results

        Raises:
            TaskTimeoutError: If timeout exceeded
            WorkerNotFound: If worker not found
        """
        if worker_id not in self.workers:
            raise WorkerNotFound(f"Worker {worker_id} not found")

        start_time = time.time()
        timeout_seconds = timeout_minutes * 60

        while True:
            # Update worker status
            worker = self.get_worker_status(worker_id)

            # Check if completed
            if worker.status in [WorkerStatus.COMPLETED, WorkerStatus.FAILED, WorkerStatus.CANCELLED]:
                # Retrieve output via MCP
                output = self._retrieve_pod_output_mcp(worker.current_task_id)

                # Cleanup pod
                self._cleanup_pod_mcp(worker.current_task_id)
                del self.workers[worker_id]

                return output

            # Check timeout
            elapsed = time.time() - start_time
            if elapsed > timeout_seconds:
                # Cancel pod on timeout
                self.cancel_task(worker_id)
                raise TaskTimeoutError(
                    f"Task {worker.current_task_id} exceeded timeout of {timeout_minutes} minutes"
                )

            # Wait before next poll
            time.sleep(poll_interval_seconds)

    def cancel_task(self, worker_id: str) -> Worker:
        """
        Cancel worker's task (terminates K8s pod).

        Args:
            worker_id: Worker ID

        Returns:
            Worker instance with status=CANCELLED

        Raises:
            WorkerNotFound: If worker not found
            CancellationFailed: If cancellation fails
        """
        if worker_id not in self.workers:
            raise WorkerNotFound(f"Worker {worker_id} not found")

        worker = self.workers[worker_id]

        if worker.status != WorkerStatus.BUSY:
            raise CancellationFailed(f"Worker {worker_id} is not busy (status={worker.status})")

        # Cancel pod via MCP
        try:
            self._cancel_pod_mcp(worker.current_task_id)
            worker = worker.cancel_task()
            self.workers[worker_id] = worker
            self.active_count -= 1
        except Exception as e:
            raise CancellationFailed(f"Failed to cancel pod: {e}")

        return worker

    def list_active_tasks(self) -> List[Worker]:
        """List all workers with active tasks."""
        return [w for w in self.workers.values() if w.status == WorkerStatus.BUSY]

    def shutdown(self) -> None:
        """Shutdown worker pool (cancel all active tasks)."""
        active_workers = list(self.workers.keys())
        for worker_id in active_workers:
            try:
                self.cancel_task(worker_id)
            except Exception:
                pass  # Best effort

        self.workers.clear()
        self.active_count = 0

    # MCP interaction methods (private)

    def _create_pod_mcp(self, task: GeneratedTask) -> None:
        """
        Create Kubernetes pod via MCP agentspace_create_task.

        Args:
            task: Task to create pod for

        NOTE: This is a placeholder for MCP tool call.
        Actual implementation would be:

        result = agentspace_create_task(
            task_id=task.id,
            instruction=task.instruction,
            model=self.config.model_name,
            timeout_minutes=task.estimated_minutes,
        )
        """
        pass

    def _check_pod_status_mcp(self, task_id: str) -> TaskExecutionStatus:
        """
        Check pod status via MCP agentspace_get_status.

        Args:
            task_id: Task ID

        Returns:
            TaskExecutionStatus

        NOTE: Placeholder for MCP tool call.
        Actual implementation:

        status = agentspace_get_status(task_id=task_id)
        return status["status"]  # "running", "completed", "failed"
        """
        return TaskExecutionStatus.RUNNING

    def _retrieve_pod_output_mcp(self, task_id: str) -> TaskOutput:
        """
        Retrieve pod output via MCP agentspace_get_output.

        Args:
            task_id: Task ID

        Returns:
            TaskOutput with results

        NOTE: Placeholder for MCP tool call.
        Actual implementation:

        output = agentspace_get_output(task_id=task_id, stream=False)
        return TaskOutput(
            task_id=task_id,
            status=TaskExecutionStatus.COMPLETED,
            pr_url=output.get("pr_url"),
            stdout=output["stdout"],
            stderr=output["stderr"],
        )
        """
        return TaskOutput(
            task_id=task_id,
            status=TaskExecutionStatus.COMPLETED,
            pr_url=None,
            stdout="Task completed (placeholder)",
            stderr="",
        )

    def _cancel_pod_mcp(self, task_id: str) -> None:
        """
        Cancel pod via MCP agentspace_cancel_task.

        Args:
            task_id: Task ID

        NOTE: Placeholder for MCP tool call.
        Actual implementation:

        agentspace_cancel_task(task_id=task_id)
        """
        pass

    def _cleanup_pod_mcp(self, task_id: str) -> None:
        """
        Cleanup pod resources after completion.

        Args:
            task_id: Task ID

        NOTE: K8s pods may auto-delete based on TTL.
        This is optional cleanup.
        """
        pass
