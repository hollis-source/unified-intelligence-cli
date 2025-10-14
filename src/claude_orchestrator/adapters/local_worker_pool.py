"""LocalWorkerPool Adapter.

Local subprocess-based worker pool with single worker.
Enables true local execution without SSH overhead.

Clean Architecture: Adapter layer (implements IWorkerPool interface)
SOLID: LSP - substitutable for IWorkerPool
"""

import time
import subprocess
import os
import signal
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


class LocalWorkerPool(IWorkerPool):
    """
    Single-worker pool using local subprocess execution.

    Characteristics:
    - Serial execution (1 task at a time)
    - Persistent worker (reuses between tasks)
    - Subprocess-based (no SSH overhead)
    - Simple status tracking

    Usage:
        config = WorkerPoolConfig(
            pool_type="local",
            max_workers=1,
            working_dir="/home/ui-cli_jake/unified-intelligence-cli",
            model_name="sonnet4",
        )

        pool = LocalWorkerPool(config)
        worker = pool.assign_task(task)
        output = pool.wait_for_completion(worker.id, timeout_minutes=30)
    """

    def __init__(self, config: WorkerPoolConfig):
        """
        Initialize local worker pool.

        Args:
            config: Worker pool configuration (must be local type)
        """
        if config.pool_type != "local":
            raise ValueError(f"LocalWorkerPool requires local pool_type, got {config.pool_type}")

        self.config = config
        self.worker: Optional[Worker] = None
        self.task_outputs: Dict[str, TaskOutput] = {}  # task_id -> output

        # Create persistent worker
        self.worker = Worker.create(
            id="local-worker-1",
            worker_type=WorkerType.LOCAL,
            status=WorkerStatus.IDLE,
            capabilities={
                "working_dir": config.working_dir,
                "model": config.model_name or "sonnet4",
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

        # Submit task locally (async, non-blocking)
        self._submit_task_local(task)

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
            worker_id: Worker ID (must be "local-worker-1")

        Returns:
            Worker instance with updated status

        Raises:
            WorkerNotFound: If worker ID doesn't match
        """
        if worker_id != self.worker.id:
            raise WorkerNotFound(f"Worker {worker_id} not found")

        # Check task status locally
        if self.worker.status == WorkerStatus.BUSY:
            status = self._check_task_status_local(self.worker.current_task_id)

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
                output = self._retrieve_task_output_local(self.worker.current_task_id)
                self.task_outputs[self.worker.current_task_id] = output

                # Cleanup local task files
                self._cleanup_task_files_local(self.worker.current_task_id)

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

        # Cancel locally (kill process)
        try:
            self._cancel_task_local(self.worker.current_task_id)
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

    # Local subprocess methods (private)

    def _submit_task_local(self, task: GeneratedTask) -> None:
        """
        Submit task locally via subprocess (non-blocking).

        Creates instruction file and executes auggie in background.

        Task files:
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
        instruction_path = Path(f"/tmp/orchestrator-task-{task_id}.txt")
        try:
            instruction_path.write_text(instruction, encoding='utf-8')
        except Exception as e:
            raise WorkerExecutionError(f"Failed to write instruction file: {e}")

        # Initialize status file
        status_path = Path(f"/tmp/orchestrator-task-{task_id}.status")
        status_path.write_text("running")

        # Prepare auggie command
        log_path = f"/tmp/orchestrator-task-{task_id}.log"
        pid_path = f"/tmp/orchestrator-task-{task_id}.pid"

        # Start auggie in background using subprocess.Popen
        auggie_cmd = [
            "auggie",
            "--instruction-file", str(instruction_path),
            "--model", model,
            "--quiet",
        ]

        try:
            # Open log file for stdout/stderr
            log_file = open(log_path, 'w')

            # Start process in background
            process = subprocess.Popen(
                auggie_cmd,
                cwd=working_dir,
                stdout=log_file,
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
                start_new_session=True,  # Detach from parent process
            )

            # Write PID to file
            Path(pid_path).write_text(str(process.pid))

            # Don't wait for process - it runs in background

        except FileNotFoundError:
            raise WorkerExecutionError(
                "auggie command not found. Ensure auggie is installed and in PATH."
            )
        except Exception as e:
            raise WorkerExecutionError(f"Failed to start auggie: {e}")

    def _check_task_status_local(self, task_id: str) -> TaskExecutionStatus:
        """
        Check task status locally.

        Checks if process is still running and reads status file.

        Args:
            task_id: Task ID

        Returns:
            TaskExecutionStatus (RUNNING, COMPLETED, FAILED)
        """
        pid_file = Path(f"/tmp/orchestrator-task-{task_id}.pid")

        # Check if process is still running
        if not pid_file.exists():
            # No PID file - assume completed (or never started)
            return TaskExecutionStatus.COMPLETED

        try:
            pid = int(pid_file.read_text().strip())

            # Check if process exists using os.kill with signal 0
            try:
                os.kill(pid, 0)  # Signal 0 checks existence without killing
                # Process exists - still running
                return TaskExecutionStatus.RUNNING
            except OSError:
                # Process doesn't exist - stopped
                pass

        except (ValueError, FileNotFoundError):
            # Invalid PID or file disappeared
            pass

        # Process stopped - check status file for success/failure
        status_file = Path(f"/tmp/orchestrator-task-{task_id}.status")

        if status_file.exists():
            status = status_file.read_text().strip()
            if status == "completed":
                return TaskExecutionStatus.COMPLETED
            elif status == "failed":
                return TaskExecutionStatus.FAILED

        # Process stopped but status not updated - assume completed
        # (auggie may have finished without updating status file)
        return TaskExecutionStatus.COMPLETED

    def _retrieve_task_output_local(self, task_id: str) -> TaskOutput:
        """
        Retrieve task output locally.

        Reads log file and extracts:
        - stdout/stderr
        - PR URL (if present)
        - Exit status

        Args:
            task_id: Task ID

        Returns:
            TaskOutput with results
        """
        log_file = Path(f"/tmp/orchestrator-task-{task_id}.log")

        # Read log file
        log_content = ""
        if log_file.exists():
            try:
                log_content = log_file.read_text(encoding='utf-8', errors='replace')
            except Exception:
                log_content = "(Failed to read log file)"

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
        status_result = self._check_task_status_local(task_id)

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

    def _cancel_task_local(self, task_id: str) -> None:
        """
        Cancel task locally (kill process).

        Args:
            task_id: Task ID

        Raises:
            CancellationFailed: If cancellation fails
        """
        pid_file = Path(f"/tmp/orchestrator-task-{task_id}.pid")

        if not pid_file.exists():
            # No PID file - nothing to cancel
            return

        try:
            pid = int(pid_file.read_text().strip())

            # Kill process and all children (process group)
            try:
                os.killpg(os.getpgid(pid), signal.SIGTERM)
                time.sleep(1)  # Give it a second to die gracefully
                # If still alive, force kill
                try:
                    os.killpg(os.getpgid(pid), signal.SIGKILL)
                except ProcessLookupError:
                    pass  # Already dead
            except ProcessLookupError:
                pass  # Process already gone

        except (ValueError, FileNotFoundError):
            pass  # Invalid PID or file disappeared

        # Update status file
        status_file = Path(f"/tmp/orchestrator-task-{task_id}.status")
        status_file.write_text("cancelled")

        # Cleanup task files
        self._cleanup_task_files_local(task_id)

    def _cleanup_task_files_local(self, task_id: str) -> None:
        """
        Cleanup temporary task files locally.

        Args:
            task_id: Task ID
        """
        # Remove task files from /tmp
        files_to_remove = [
            Path(f"/tmp/orchestrator-task-{task_id}.txt"),
            Path(f"/tmp/orchestrator-task-{task_id}.status"),
            Path(f"/tmp/orchestrator-task-{task_id}.log"),
            Path(f"/tmp/orchestrator-task-{task_id}.pid"),
        ]

        for file_path in files_to_remove:
            try:
                if file_path.exists():
                    file_path.unlink()
            except Exception:
                pass  # Best effort cleanup
