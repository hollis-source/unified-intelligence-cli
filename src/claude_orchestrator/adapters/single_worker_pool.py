"""SingleWorkerPool Adapter.

SSH-based worker pool with single worker (SYD2).
MVP implementation for testing orchestrator logic.

Clean Architecture: Adapter layer (implements IWorkerPool interface)
SOLID: LSP - substitutable for IWorkerPool
"""

import time
import subprocess
import json
import re
from typing import List, Optional, Dict
from datetime import datetime
from pathlib import Path

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


class SingleWorkerPool(IWorkerPool):
    """
    Single-worker pool using SSH to remote server (SYD2).

    Characteristics:
    - Serial execution (1 task at a time)
    - Persistent worker (reuses between tasks)
    - SSH-based (uses MCP SSH tools)
    - Simple status tracking

    Usage:
        config = WorkerPoolConfig(
            pool_type="ssh",
            max_workers=1,
            ssh_host="ui-cli_jake@syd2.jacobhollis.com",
            working_dir="/home/ui-cli_jake/unified-intelligence-cli",
        )

        pool = SingleWorkerPool(config)
        worker = pool.assign_task(task)
        output = pool.wait_for_completion(worker.id, timeout_minutes=30)
    """

    def __init__(self, config: WorkerPoolConfig):
        """
        Initialize single worker pool.

        Args:
            config: Worker pool configuration (must be ssh type)
        """
        if config.pool_type != "ssh":
            raise ValueError(f"SingleWorkerPool requires ssh pool_type, got {config.pool_type}")

        self.config = config
        self.worker: Optional[Worker] = None
        self.task_outputs: Dict[str, TaskOutput] = {}  # task_id -> output

        # Create persistent worker
        self.worker = Worker.create(
            id="syd2-worker-1",
            worker_type=WorkerType.SSH,
            status=WorkerStatus.IDLE,
            capabilities={
                "host": config.ssh_host,
                "working_dir": config.working_dir,
                "model": config.model_name or "gpt5",
            },
        )

    def assign_task(self, task: GeneratedTask) -> Worker:
        """
        Assign task to the single worker.

        Blocks if worker is busy (waits for completion).

        Args:
            task: Generated task to assign

        Returns:
            Worker instance with task assigned

        Raises:
            WorkerPoolExhausted: Should never happen (waits for worker)
        """
        # Wait for worker to be available
        while self.worker.status == WorkerStatus.BUSY:
            time.sleep(1)  # Poll every second

        # Assign task
        self.worker = self.worker.assign_task(task.id)

        # Submit task via SSH (async, non-blocking)
        self._submit_task_ssh(task)

        return self.worker

    def get_available_workers(self) -> List[Worker]:
        """Get list of idle workers (0 or 1)."""
        if self.worker and self.worker.is_available():
            return [self.worker]
        return []

    def get_worker_status(self, worker_id: str) -> Worker:
        """
        Get current status of worker.

        Args:
            worker_id: Worker ID (must be "syd2-worker-1")

        Returns:
            Worker instance with updated status

        Raises:
            WorkerNotFound: If worker ID doesn't match
        """
        if worker_id != self.worker.id:
            raise WorkerNotFound(f"Worker {worker_id} not found")

        # Check task status via SSH
        if self.worker.status == WorkerStatus.BUSY:
            status = self._check_task_status_ssh(self.worker.current_task_id)

            if status == TaskExecutionStatus.COMPLETED:
                self.worker = self.worker.complete_task(success=True)
            elif status == TaskExecutionStatus.FAILED:
                self.worker = self.worker.complete_task(success=False, error="Task failed")

        return self.worker

    def wait_for_completion(
        self, worker_id: str, timeout_minutes: int = 30, poll_interval_seconds: int = 10
    ) -> TaskOutput:
        """
        Wait for worker to complete task (blocking).

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
        if worker_id != self.worker.id:
            raise WorkerNotFound(f"Worker {worker_id} not found")

        start_time = time.time()
        timeout_seconds = timeout_minutes * 60

        while True:
            # Update worker status
            self.worker = self.get_worker_status(worker_id)

            # Check if completed
            if self.worker.status in [
                WorkerStatus.COMPLETED,
                WorkerStatus.FAILED,
                WorkerStatus.CANCELLED,
            ]:
                # Retrieve output
                output = self._retrieve_task_output_ssh(self.worker.current_task_id)
                self.task_outputs[self.worker.current_task_id] = output

                # Cleanup remote task files
                self._cleanup_task_files_ssh(self.worker.current_task_id)

                # Reset worker to IDLE
                self.worker = Worker.create(
                    id=self.worker.id,
                    worker_type=self.worker.worker_type,
                    status=WorkerStatus.IDLE,
                    capabilities=self.worker.capabilities,
                    resource_limits=self.worker.resource_limits,
                )

                return output

            # Check timeout
            elapsed = time.time() - start_time
            if elapsed > timeout_seconds:
                raise TaskTimeoutError(
                    f"Task {self.worker.current_task_id} exceeded timeout of {timeout_minutes} minutes"
                )

            # Wait before next poll
            time.sleep(poll_interval_seconds)

    def cancel_task(self, worker_id: str) -> Worker:
        """
        Cancel worker's current task.

        Args:
            worker_id: Worker ID

        Returns:
            Worker instance with status=CANCELLED

        Raises:
            WorkerNotFound: If worker not found
            CancellationFailed: If cancellation fails
        """
        if worker_id != self.worker.id:
            raise WorkerNotFound(f"Worker {worker_id} not found")

        if self.worker.status != WorkerStatus.BUSY:
            raise CancellationFailed(f"Worker {worker_id} is not busy (status={self.worker.status})")

        # Cancel via SSH (kill process)
        try:
            self._cancel_task_ssh(self.worker.current_task_id)
            self.worker = self.worker.cancel_task()
        except Exception as e:
            raise CancellationFailed(f"Failed to cancel task: {e}")

        return self.worker

    def list_active_tasks(self) -> List[Worker]:
        """List all workers with active tasks (0 or 1)."""
        if self.worker and self.worker.status == WorkerStatus.BUSY:
            return [self.worker]
        return []

    def shutdown(self) -> None:
        """Shutdown worker pool (cancel active task if any)."""
        if self.worker and self.worker.status == WorkerStatus.BUSY:
            try:
                self.cancel_task(self.worker.id)
            except Exception:
                pass  # Best effort

        self.worker = None

    # SSH interaction methods (private)

    def _ssh_exec(self, command: str) -> subprocess.CompletedProcess:
        """
        Execute command on remote host via SSH.

        Args:
            command: Command to execute

        Returns:
            CompletedProcess with stdout/stderr

        Raises:
            WorkerExecutionError: If SSH command fails
        """
        ssh_cmd = ["ssh", self.config.ssh_host, command]
        try:
            result = subprocess.run(
                ssh_cmd,
                capture_output=True,
                text=True,
                timeout=60,  # 60s timeout for SSH commands (increased for reliability)
            )
            return result
        except subprocess.TimeoutExpired as e:
            raise WorkerExecutionError(f"SSH command timed out: {command}")
        except Exception as e:
            raise WorkerExecutionError(f"SSH command failed: {e}")

    def _submit_task_ssh(self, task: GeneratedTask) -> None:
        """
        Submit task to SYD2 via SSH (non-blocking).

        Creates instruction file and executes auggie in background.

        Task files on remote:
        - /tmp/orchestrator-task-{id}.txt - instruction file
        - /tmp/orchestrator-task-{id}.status - status file (running/completed/failed)
        - /tmp/orchestrator-task-{id}.log - stdout/stderr
        - /tmp/orchestrator-task-{id}.pid - process ID

        Args:
            task: Task to submit

        Raises:
            WorkerExecutionError: If task submission fails
        """
        task_id = task.id
        working_dir = self.config.working_dir
        model = self.config.model_name or "sonnet4"

        # Create instruction file content
        instruction = f"""{task.instruction}

# Task Metadata
Task ID: {task_id}
Goal: {task.goal_id}
Priority: {task.priority}
Estimated Time: {task.estimated_minutes} minutes

# Rationale
{task.rationale}
"""

        # Write instruction file
        # Use echo with base64 encoding to avoid heredoc issues over SSH
        instruction_path = f"/tmp/orchestrator-task-{task_id}.txt"
        import base64
        instruction_b64 = base64.b64encode(instruction.encode('utf-8')).decode('ascii')
        self._ssh_exec(f"echo '{instruction_b64}' | base64 -d > {instruction_path}")

        # Initialize status file
        self._ssh_exec(f"echo 'running' > /tmp/orchestrator-task-{task_id}.status")

        # Start auggie in background
        # Use subshell with stdin redirect to avoid SSH hanging
        # This ensures SSH returns immediately without waiting for process
        auggie_cmd = (
            f"cd {working_dir} && "
            f"(auggie "
            f"--instruction-file {instruction_path} "
            f"--model {model} "
            f"--quiet "
            f"> /tmp/orchestrator-task-{task_id}.log 2>&1 </dev/null & "
            f"echo $! > /tmp/orchestrator-task-{task_id}.pid)"
        )

        result = self._ssh_exec(auggie_cmd)

        if result.returncode != 0:
            raise WorkerExecutionError(
                f"Failed to start auggie: {result.stderr}"
            )

        # Mark task as submitted
        # Status will be updated by auggie completion or checked via polling

    def _check_task_status_ssh(self, task_id: str) -> TaskExecutionStatus:
        """
        Check task status via SSH.

        Checks if process is still running and reads status file.

        Args:
            task_id: Task ID

        Returns:
            TaskExecutionStatus (RUNNING, COMPLETED, FAILED)
        """
        # Check if process is still running
        pid_file = f"/tmp/orchestrator-task-{task_id}.pid"
        result = self._ssh_exec(f"[ -f {pid_file} ] && kill -0 $(cat {pid_file}) 2>/dev/null && echo 'running' || echo 'stopped'")

        process_status = result.stdout.strip()

        if process_status == "running":
            return TaskExecutionStatus.RUNNING

        # Process stopped - check status file for success/failure
        status_file = f"/tmp/orchestrator-task-{task_id}.status"
        result = self._ssh_exec(f"cat {status_file} 2>/dev/null || echo 'unknown'")

        status = result.stdout.strip()

        if status == "completed":
            return TaskExecutionStatus.COMPLETED
        elif status == "failed":
            return TaskExecutionStatus.FAILED
        else:
            # Process stopped but status not updated - assume completed
            # (auggie may have finished without updating status file)
            return TaskExecutionStatus.COMPLETED

    def _retrieve_task_output_ssh(self, task_id: str) -> TaskOutput:
        """
        Retrieve task output from SYD2 via SSH.

        Reads log file and extracts:
        - stdout/stderr
        - PR URL (if present)
        - Exit status

        Args:
            task_id: Task ID

        Returns:
            TaskOutput with results
        """
        log_file = f"/tmp/orchestrator-task-{task_id}.log"

        # Read log file
        result = self._ssh_exec(f"cat {log_file} 2>/dev/null || echo ''")
        log_content = result.stdout

        # Extract PR URL from log (auggie typically outputs PR URL)
        pr_url = None
        pr_patterns = [
            r'https://github\.com/[^/]+/[^/]+/pull/\d+',
            r'PR:\s*(https://[^\s]+)',
            r'Pull Request:\s*(https://[^\s]+)',
        ]

        for pattern in pr_patterns:
            match = re.search(pattern, log_content)
            if match:
                pr_url = match.group(0) if 'github.com' in match.group(0) else match.group(1)
                break

        # Determine final status
        status_result = self._check_task_status_ssh(task_id)

        # Determine exit code (0 = success, 1 = failure)
        exit_code = 0 if status_result == TaskExecutionStatus.COMPLETED else 1

        return TaskOutput(
            task_id=task_id,
            status=status_result,
            pr_url=pr_url,
            stdout=log_content,
            stderr="",  # Combined in log file
            exit_code=exit_code,
            execution_time_seconds=0.0,  # Not tracked in MVP
        )

    def _cancel_task_ssh(self, task_id: str) -> None:
        """
        Cancel task via SSH (kill process).

        Args:
            task_id: Task ID

        Raises:
            CancellationFailed: If cancellation fails
        """
        pid_file = f"/tmp/orchestrator-task-{task_id}.pid"

        # Read PID and kill process
        result = self._ssh_exec(
            f"[ -f {pid_file} ] && kill -9 $(cat {pid_file}) 2>/dev/null || true"
        )

        # Update status file
        status_file = f"/tmp/orchestrator-task-{task_id}.status"
        self._ssh_exec(f"echo 'cancelled' > {status_file}")

        # Cleanup task files
        self._cleanup_task_files_ssh(task_id)

    def _cleanup_task_files_ssh(self, task_id: str) -> None:
        """
        Cleanup temporary task files on remote server.

        Args:
            task_id: Task ID
        """
        # Remove task files from /tmp
        files_to_remove = [
            f"/tmp/orchestrator-task-{task_id}.txt",
            f"/tmp/orchestrator-task-{task_id}.status",
            f"/tmp/orchestrator-task-{task_id}.log",
            f"/tmp/orchestrator-task-{task_id}.pid",
        ]

        for file_path in files_to_remove:
            self._ssh_exec(f"rm -f {file_path}")
