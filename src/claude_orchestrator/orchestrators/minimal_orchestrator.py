"""MinimalOrchestrator - MVP Orchestrator for Task Execution.

Simple orchestrator that coordinates task execution end-to-end.
MVP version: Single task execution, no context analysis, no PR review.

Clean Architecture: Orchestrator coordinates use cases and adapters
SOLID: DIP - depends on IWorkerPool abstraction
"""

from typing import Optional, List
from datetime import datetime

from src.claude_orchestrator.interfaces.worker_pool import (
    IWorkerPool,
    TaskOutput,
    TaskExecutionStatus,
)
from src.claude_orchestrator.entities.generated_task import GeneratedTask
from src.claude_orchestrator.entities.worker import Worker


class MinimalOrchestrator:
    """
    MVP orchestrator for autonomous task execution.

    Coordinates:
    1. Task assignment to worker pool
    2. Waiting for completion
    3. Basic result reporting

    Future versions will add:
    - Context analysis (git, tests, coverage)
    - Dynamic task generation
    - PR review and integration
    - Learning from execution patterns

    Usage:
        config = WorkerPoolConfig(...)
        pool = SingleWorkerPool(config)
        orchestrator = MinimalOrchestrator(pool)

        task = GeneratedTask.create(...)
        result = orchestrator.execute_task(task)

        print(f"Task completed: {result.pr_url}")
    """

    def __init__(self, pool: IWorkerPool):
        """
        Initialize orchestrator with worker pool.

        Args:
            pool: Worker pool implementation (SSH, K8s, local)
        """
        self.pool = pool
        self.execution_history: List[TaskOutput] = []

    def execute_task(
        self,
        task: GeneratedTask,
        timeout_minutes: int = 30,
        poll_interval_seconds: int = 10,
    ) -> TaskOutput:
        """
        Execute single task end-to-end.

        Flow:
        1. Assign task to worker pool
        2. Wait for completion (blocking with polling)
        3. Retrieve output
        4. Store in execution history
        5. Return result

        Args:
            task: Generated task to execute
            timeout_minutes: Maximum wait time
            poll_interval_seconds: Status check interval

        Returns:
            TaskOutput with execution results

        Raises:
            TaskTimeoutError: If task exceeds timeout
            WorkerExecutionError: If execution fails
        """
        print(f"[Orchestrator] Executing task: {task.id}")
        print(f"[Orchestrator] Instruction: {task.instruction[:100]}...")

        # 1. Assign task
        worker = self.pool.assign_task(task)
        print(f"[Orchestrator] Task assigned to worker: {worker.id}")
        print(f"[Orchestrator] Worker status: {worker.status}")

        # 2. Wait for completion
        print(f"[Orchestrator] Waiting for completion (timeout={timeout_minutes}min)...")
        output = self.pool.wait_for_completion(
            worker.id,
            timeout_minutes=timeout_minutes,
            poll_interval_seconds=poll_interval_seconds,
        )

        # 3. Report results
        print(f"[Orchestrator] Task completed: {output.status}")
        print(f"[Orchestrator] Exit code: {output.exit_code}")

        if output.pr_url:
            print(f"[Orchestrator] PR URL: {output.pr_url}")

        # 4. Store in history
        self.execution_history.append(output)

        return output

    def execute_tasks_sequential(
        self,
        tasks: List[GeneratedTask],
        timeout_minutes: int = 30,
    ) -> List[TaskOutput]:
        """
        Execute multiple tasks sequentially.

        Args:
            tasks: List of tasks to execute
            timeout_minutes: Timeout per task

        Returns:
            List of TaskOutput results
        """
        results = []

        for i, task in enumerate(tasks, 1):
            print(f"\n[Orchestrator] === Task {i}/{len(tasks)} ===")
            result = self.execute_task(task, timeout_minutes=timeout_minutes)
            results.append(result)

        print(f"\n[Orchestrator] === All {len(tasks)} tasks completed ===")
        return results

    def get_execution_summary(self) -> dict:
        """
        Get summary of all executed tasks.

        Returns:
            dict with execution statistics
        """
        total = len(self.execution_history)
        completed = sum(1 for o in self.execution_history if o.status == TaskExecutionStatus.COMPLETED)
        failed = sum(1 for o in self.execution_history if o.status == TaskExecutionStatus.FAILED)
        with_pr = sum(1 for o in self.execution_history if o.pr_url is not None)

        return {
            "total_tasks": total,
            "completed": completed,
            "failed": failed,
            "success_rate": completed / total if total > 0 else 0.0,
            "prs_created": with_pr,
        }

    def shutdown(self) -> None:
        """Shutdown orchestrator and worker pool."""
        print("[Orchestrator] Shutting down...")
        self.pool.shutdown()
        print(f"[Orchestrator] Executed {len(self.execution_history)} tasks total")
