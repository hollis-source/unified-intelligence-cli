"""Coordinate agents use case - Backward-compatible wrapper."""

import logging
from typing import List, Optional

from src.entities import Agent, Task, ExecutionResult, ExecutionContext
from src.interfaces import IAgentCoordinator, IAgentExecutor, IAgentSelector, ITextGenerator
from src.use_cases.task_planner import TaskPlannerUseCase
from src.use_cases.task_coordinator import TaskCoordinatorUseCase


class CoordinateAgentsUseCase(IAgentCoordinator):
    """
    Backward-compatible wrapper around split use cases.

    OCP: Extends by composition, doesn't modify new use cases.
    SRP: Delegates to specialized use cases (planner + coordinator).

    DEPRECATED: Use TaskCoordinatorUseCase directly for new code.
    """

    def __init__(
        self,
        llm_provider: ITextGenerator,
        agent_executor: IAgentExecutor,
        agent_selector: IAgentSelector,
        max_retries: int = 3,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize with injected dependencies.

        Creates internal planner and coordinator following SRP.
        """
        self.logger = logger or logging.getLogger(__name__)

        # Create planner (SRP: planning responsibility)
        self.planner = TaskPlannerUseCase(
            llm_provider=llm_provider,
            agent_selector=agent_selector,
            logger=logger
        )

        # Create coordinator (SRP: execution responsibility)
        self.coordinator = TaskCoordinatorUseCase(
            task_planner=self.planner,
            agent_executor=agent_executor,
            max_retries=max_retries,
            logger=logger
        )

    async def coordinate(
        self,
        tasks: List[Task],
        agents: List[Agent],
        context: Optional[ExecutionContext] = None
    ) -> List[ExecutionResult]:
        """
        Coordinate agents - delegates to new split use cases.

        Clean Code: Simple delegation, no complex logic.
        """
        self.logger.info(f"Starting coordination for {len(tasks)} tasks (via wrapper)")

        # Delegate to new coordinator
        results = await self.coordinator.coordinate(tasks, agents, context)

        self.logger.info(f"Coordination complete: {len(results)} results")
        return results