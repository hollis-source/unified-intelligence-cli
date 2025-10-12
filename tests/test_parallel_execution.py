import time
import asyncio
import pytest

from typing import List, Optional

from src.interfaces import IAgentExecutor, ITaskPlanner, ExecutionPlan
from src.entities import Agent, Task, ExecutionResult, ExecutionStatus, ExecutionContext
from src.use_cases.task_coordinator import TaskCoordinatorUseCase
from src.adapters.orchestration.parallel_executor import ParallelAgentExecutor


class BlockingFakeExecutor(IAgentExecutor):
    def __init__(self, delay: float = 0.2):
        self.delay = delay

    async def execute(
        self,
        agent: Agent,
        task: Task,
        context: Optional[ExecutionContext] = None
    ) -> ExecutionResult:
        # Intentionally block the event loop (simulate sync I/O)
        time.sleep(self.delay)
        return ExecutionResult(status=ExecutionStatus.SUCCESS, output=f"done:{task.description}", errors=[])


class AllParallelPlanner(ITaskPlanner):
    async def create_plan(
        self,
        tasks: List[Task],
        agents: List[Agent],
        context: Optional[ExecutionContext] = None
    ) -> ExecutionPlan:
        ids = [t.task_id or str(i) for i, t in enumerate(tasks)]
        # Assign all to the single agent role provided
        role = agents[0].role if agents else "worker"
        return ExecutionPlan(
            task_order=ids,
            task_assignments={tid: role for tid in ids},
            parallel_groups=[ids],
        )


@pytest.mark.asyncio
async def test_parallel_executor_speedup():
    tasks = [Task(description=f"t{i}") for i in range(8)]
    agent = Agent(role="worker", capabilities=["any"], tier=1)

    planner = AllParallelPlanner()
    base_exec = BlockingFakeExecutor(delay=0.2)

    # Baseline (sequential due to blocking)
    start = time.time()
    simple = TaskCoordinatorUseCase(task_planner=planner, agent_executor=base_exec)
    _ = await simple.coordinate(tasks=tasks, agents=[agent], context=None)
    baseline = time.time() - start

    # Parallel wrapped
    parallel = TaskCoordinatorUseCase(
        task_planner=planner,
        agent_executor=ParallelAgentExecutor(base_exec, max_workers=4),
    )
    start = time.time()
    _ = await parallel.coordinate(tasks=tasks, agents=[agent], context=None)
    parallel_time = time.time() - start

    # Expect 3x+ speedup when parallelized (8 tasks * 0.2s = ~1.6s baseline)
    # With 4 workers, expect ~0.4-0.6s
    assert baseline / parallel_time >= 3.0, f"Expected >=3x speedup, got {baseline:.2f}s vs {parallel_time:.2f}s"

