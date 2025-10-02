"""
Hybrid Orchestrator - Intelligent routing between orchestration strategies.

Clean Architecture: Adapter pattern wrapping multiple orchestration strategies.
Strategy Pattern: Selects strategy at runtime based on task characteristics.
"""

import logging
from typing import List, Optional

from src.entities import Agent, Task, ExecutionResult, ExecutionContext
from src.interfaces import IAgentCoordinator, ITextGenerator, ITaskPlanner, IAgentExecutor
from src.routing.orchestrator_router import OrchestratorRouter
from src.use_cases.task_coordinator import TaskCoordinatorUseCase


logger = logging.getLogger(__name__)


class HybridOrchestrator(IAgentCoordinator):
    """
    Hybrid orchestrator using intelligent routing.

    Strategy Pattern: Routes tasks to best orchestration strategy.
    - Simple tasks → OpenAI Agents SDK (cleaner, faster initialization)
    - Complex multi-agent tasks → TaskCoordinatorUseCase (proven, reliable)

    DIP: Implements IAgentCoordinator interface.
    Clean Code: Delegates to specialized orchestrators.
    """

    def __init__(
        self,
        llm_provider: ITextGenerator,
        task_planner: ITaskPlanner,
        agent_executor: IAgentExecutor,
        agents: List[Agent],
        logger_instance: Optional[logging.Logger] = None,
        enable_sdk: bool = True
    ):
        """
        Initialize hybrid orchestrator.

        Args:
            llm_provider: LLM provider
            task_planner: Task planning strategy
            agent_executor: Agent execution strategy
            agents: Available agents
            logger_instance: Optional logger
            enable_sdk: Whether SDK mode is available
        """
        self.llm_provider = llm_provider
        self.task_planner = task_planner
        self.agent_executor = agent_executor
        self.agents = agents
        self.logger = logger_instance or logging.getLogger(__name__)
        self.enable_sdk = enable_sdk

        # Create router for task classification
        self.router = OrchestratorRouter(enable_sdk=enable_sdk)

        # Create simple mode orchestrator (always available)
        self.simple_orchestrator = TaskCoordinatorUseCase(
            task_planner=task_planner,
            agent_executor=agent_executor,
            max_retries=3,
            logger=logger_instance
        )

        # Create SDK orchestrator (if available)
        self.sdk_orchestrator = None
        if enable_sdk:
            try:
                from src.adapters.orchestration.openai_agents_sdk_adapter import OpenAIAgentsSDKAdapter
                self.sdk_orchestrator = OpenAIAgentsSDKAdapter(
                    llm_provider=llm_provider,
                    agents=agents,
                    max_turns=10
                )
                self.logger.info("Hybrid orchestrator initialized with SDK support")
            except ImportError as e:
                self.logger.warning(f"SDK not available, using simple mode only: {e}")
                self.enable_sdk = False
                self.router.enable_sdk = False
        else:
            self.logger.info("Hybrid orchestrator initialized without SDK (disabled)")

        # Statistics tracking
        self.stats = {
            "sdk_mode": 0,
            "simple_mode": 0,
            "total_tasks": 0
        }

    async def coordinate(
        self,
        tasks: List[Task],
        agents: List[Agent],
        context: Optional[ExecutionContext] = None
    ) -> List[ExecutionResult]:
        """
        Coordinate task execution using hybrid routing.

        Strategy:
        1. Route each task to appropriate orchestrator
        2. Execute tasks in batches by orchestrator type
        3. Merge and return results in original order

        Args:
            tasks: Tasks to execute
            agents: Available agents
            context: Optional execution context

        Returns:
            List of ExecutionResult (one per task)
        """
        if not tasks:
            return []

        self.logger.info(f"Hybrid orchestrator coordinating {len(tasks)} tasks")

        # Route tasks
        routes = self.router.route_batch(tasks)

        # Group by orchestrator
        sdk_tasks = [(idx, task) for idx, (task, mode) in enumerate(routes) if mode == "openai-agents"]
        simple_tasks = [(idx, task) for idx, (task, mode) in enumerate(routes) if mode == "simple"]

        # Update statistics
        self.stats["sdk_mode"] += len(sdk_tasks)
        self.stats["simple_mode"] += len(simple_tasks)
        self.stats["total_tasks"] += len(tasks)

        self.logger.info(
            f"Routing: {len(sdk_tasks)} tasks to SDK, "
            f"{len(simple_tasks)} tasks to simple mode"
        )

        # Execute tasks by orchestrator
        results_dict = {}

        # Execute SDK tasks
        if sdk_tasks and self.sdk_orchestrator:
            sdk_task_list = [task for _, task in sdk_tasks]
            self.logger.info(f"Executing {len(sdk_task_list)} tasks via SDK")

            sdk_results = await self.sdk_orchestrator.coordinate(
                sdk_task_list,
                agents,
                context
            )

            for (idx, _), result in zip(sdk_tasks, sdk_results):
                results_dict[idx] = result

        # Execute simple mode tasks
        if simple_tasks:
            simple_task_list = [task for _, task in simple_tasks]
            self.logger.info(f"Executing {len(simple_task_list)} tasks via simple mode")

            simple_results = await self.simple_orchestrator.coordinate(
                simple_task_list,
                agents,
                context
            )

            for (idx, _), result in zip(simple_tasks, simple_results):
                results_dict[idx] = result

        # Return results in original order
        ordered_results = [results_dict[idx] for idx in range(len(tasks))]

        self.logger.info(
            f"Hybrid coordination complete: {len(ordered_results)} results "
            f"(SDK: {len(sdk_tasks)}, Simple: {len(simple_tasks)})"
        )

        return ordered_results

    def get_stats(self) -> dict:
        """
        Get routing statistics.

        Returns:
            Dict with routing statistics
        """
        total = self.stats["total_tasks"]

        if total == 0:
            return {
                **self.stats,
                "sdk_percentage": 0.0,
                "simple_percentage": 0.0
            }

        return {
            **self.stats,
            "sdk_percentage": (self.stats["sdk_mode"] / total) * 100,
            "simple_percentage": (self.stats["simple_mode"] / total) * 100
        }
