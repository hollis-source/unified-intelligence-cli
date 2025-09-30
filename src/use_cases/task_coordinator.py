"""Task coordinator use case - SRP: Focused on executing planned tasks."""

import asyncio
import logging
from typing import List, Optional, Dict
from src.entities import Agent, Task, ExecutionResult, ExecutionStatus, ExecutionContext
from src.interfaces import (
    IAgentCoordinator,
    IAgentExecutor,
    ITaskPlanner,
    ExecutionPlan
)
from src.validators import TaskValidator, ValidationError


class TaskCoordinatorUseCase(IAgentCoordinator):
    """
    Execution use case - runs tasks per plan.

    SRP: Single responsibility - execution (not planning).
    Clean Code: Small methods <20 lines each.
    """

    def __init__(
        self,
        task_planner: ITaskPlanner,
        agent_executor: IAgentExecutor,
        max_retries: int = 3,
        logger: Optional[logging.Logger] = None
    ):
        """Initialize with injected dependencies."""
        self.task_planner = task_planner
        self.agent_executor = agent_executor
        self.max_retries = max_retries
        self.logger = logger or logging.getLogger(__name__)

    async def coordinate(
        self,
        tasks: List[Task],
        agents: List[Agent],
        context: Optional[ExecutionContext] = None
    ) -> List[ExecutionResult]:
        """
        Coordinate task execution using injected planner.

        Clean Code: Orchestration - delegates to planner and executor.
        """
        self.logger.info(f"Coordinating {len(tasks)} tasks")
        self.logger.debug(f"Available agents: {[a.role for a in agents]}")

        # Delegate planning to TaskPlannerUseCase
        plan = await self.task_planner.create_plan(tasks, agents, context)
        self.logger.debug(f"Plan created: {len(plan.task_assignments)} task assignments")

        # Execute the plan
        results = await self._execute_plan(plan, tasks, agents, context)

        self.logger.info(f"Coordination complete: {len(results)} results")
        return results

    async def coordinate_task(
        self,
        task: Task,
        context: Optional[ExecutionContext] = None
    ) -> ExecutionResult:
        """
        Convenience method to coordinate a single task.

        User-friendly API discovered via user simulation testing.
        Wraps coordinate() for single-task use case.

        Enhanced with validation (Week 1: Error Infrastructure).

        Args:
            task: Single task to execute
            context: Optional execution context

        Returns:
            Single ExecutionResult

        Raises:
            Same exceptions as coordinate()
        """
        # Validate task early (Week 1: Error Infrastructure)
        is_valid, validation_error = TaskValidator.validate(task)
        if not is_valid:
            self.logger.warning(f"Task validation failed: {validation_error.message}")
            return ExecutionResult(
                status=ExecutionStatus.FAILURE,
                output=None,
                errors=[validation_error.message],
                error_details={
                    "error_type": "ValidationError",
                    "component": "TaskValidator",
                    "input": {
                        "description": task.description,
                        "priority": task.priority,
                        "task_id": task.task_id
                    },
                    "root_cause": f"Field '{validation_error.field}' failed validation",
                    "user_message": validation_error.message,
                    "suggestion": validation_error.suggestion,
                    "context": {
                        "field": validation_error.field,
                        "validator": "TaskValidator"
                    }
                }
            )

        # Get default agents from task planner
        from src.factories.agent_factory import AgentFactory
        agent_factory = AgentFactory()
        agents = agent_factory.create_default_agents()

        # Execute as single-item list
        results = await self.coordinate(
            tasks=[task],
            agents=agents,
            context=context
        )

        # Return first (and only) result
        return results[0] if results else ExecutionResult(
            status=ExecutionStatus.FAILURE,
            output=None,
            errors=["Coordination returned empty results"],
            error_details={
                "error_type": "ExecutionError",
                "component": "TaskCoordinator",
                "input": {"task_id": task.task_id},
                "root_cause": "coordinate() returned empty result list",
                "user_message": "Task coordination failed to produce a result",
                "suggestion": "This is likely a bug. Please report with task details.",
                "context": {"task_count": 1, "results_count": 0}
            }
        )

    async def _execute_plan(
        self,
        plan: ExecutionPlan,
        tasks: List[Task],
        agents: List[Agent],
        context: Optional[ExecutionContext]
    ) -> List[ExecutionResult]:
        """
        Execute plan with parallel groups.

        Clean Code: Focused on execution flow.
        """
        results = {}
        task_map = {t.task_id or str(i): t for i, t in enumerate(tasks)}
        agent_map = {a.role: a for a in agents}

        # Execute each parallel group sequentially
        for group in plan.parallel_groups:
            group_results = await self._execute_parallel_group(
                group, plan, task_map, agent_map, context
            )
            results.update(group_results)

        # Return results in original task order
        return self._order_results(results, tasks)

    async def _execute_parallel_group(
        self,
        group: List[str],
        plan: ExecutionPlan,
        task_map: Dict[str, Task],
        agent_map: Dict[str, Agent],
        context: Optional[ExecutionContext]
    ) -> Dict[str, ExecutionResult]:
        """
        Execute tasks in parallel group.

        Clean Code: Single responsibility - parallel execution.
        """
        group_tasks = []

        for task_id in group:
            coroutine = self._create_task_coroutine(
                task_id, plan, task_map, agent_map, context
            )
            if coroutine:
                group_tasks.append((task_id, coroutine))

        # Run in parallel
        if group_tasks:
            task_ids, coroutines = zip(*group_tasks)
            results_list = await asyncio.gather(*coroutines)
            return dict(zip(task_ids, results_list))

        return {}

    def _create_task_coroutine(
        self,
        task_id: str,
        plan: ExecutionPlan,
        task_map: Dict[str, Task],
        agent_map: Dict[str, Agent],
        context: Optional[ExecutionContext]
    ):
        """
        Create coroutine for task execution.

        Clean Code: Extract method for clarity.
        """
        if task_id not in task_map:
            return self._create_failure_coroutine("Task not found")

        if task_id not in plan.task_assignments:
            return self._create_failure_coroutine("No suitable agent found for task")

        task = task_map[task_id]
        agent_role = plan.task_assignments[task_id]
        agent = agent_map.get(agent_role)

        # Week 4: Debug logging for agent selection
        self.logger.debug(f"Task '{task.description[:50]}...' assigned to agent: {agent_role}")

        if agent:
            self.logger.debug(f"Agent '{agent_role}' found, executing task {task_id}")
            return self._execute_with_retry(task, agent, context, task_id)
        else:
            self.logger.debug(f"Agent '{agent_role}' not available for task {task_id}")
            return self._create_failure_coroutine(
                f"No suitable agent ({agent_role}) available for task {task_id}"
            )

    async def _execute_with_retry(
        self,
        task: Task,
        agent: Agent,
        context: Optional[ExecutionContext],
        task_id: str
    ) -> ExecutionResult:
        """
        Execute task with exponential backoff retry.

        Clean Code: Focused retry logic.
        """
        for attempt in range(self.max_retries):
            try:
                result = await self._attempt_execution(
                    task, agent, context, task_id, attempt
                )

                if result.status == ExecutionStatus.SUCCESS:
                    return result

                if attempt < self.max_retries - 1:
                    await asyncio.sleep(2 ** attempt)

            except Exception as e:
                if attempt == self.max_retries - 1:
                    return self._create_failure_result(
                        f"Execution failed: {str(e)}"
                    )

        return self._create_failure_result(
            f"Max retries exceeded for task {task_id}"
        )

    async def _attempt_execution(
        self,
        task: Task,
        agent: Agent,
        context: Optional[ExecutionContext],
        task_id: str,
        attempt: int
    ) -> ExecutionResult:
        """
        Single execution attempt.

        Clean Code: Extract for testability.
        """
        self.logger.info(
            f"Executing task {task_id} with {agent.role} (attempt {attempt + 1})"
        )

        result = await self.agent_executor.execute(
            agent=agent,
            task=task,
            context=context
        )

        if result.status != ExecutionStatus.SUCCESS:
            self.logger.warning(f"Task {task_id} failed: {result.errors}")
        else:
            self.logger.info(f"Task {task_id} completed successfully")

        return result

    async def _create_failure_coroutine(self, error_message: str) -> ExecutionResult:
        """Create async failure result."""
        return self._create_failure_result(error_message)

    def _create_failure_result(
        self,
        error_message: str,
        error_type: str = "ExecutionError",
        component: str = "TaskCoordinator"
    ) -> ExecutionResult:
        """
        Create failure result with error tracking.

        Enhanced with error_details (Week 1: Error Infrastructure).
        """
        return ExecutionResult(
            status=ExecutionStatus.FAILURE,
            output=None,
            errors=[error_message],
            error_details={
                "error_type": error_type,
                "component": component,
                "root_cause": error_message,
                "user_message": f"Task execution failed: {error_message}",
                "suggestion": "Check task description and try again. Use --verbose flag for more details.",
                "context": {}
            },
            metadata={"error_type": "execution_failure"}
        )

    def _order_results(
        self,
        results: Dict[str, ExecutionResult],
        tasks: List[Task]
    ) -> List[ExecutionResult]:
        """
        Order results to match original task order.

        Clean Code: Single ordering responsibility.
        """
        ordered = []
        for i, task in enumerate(tasks):
            task_id = task.task_id or str(i)
            result = results.get(
                task_id,
                self._create_failure_result("Not executed")
            )
            ordered.append(result)

        return ordered