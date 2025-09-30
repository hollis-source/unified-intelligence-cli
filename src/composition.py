"""Dependency composition module - Clean Architecture composition root."""

import logging
from typing import Optional, List
from src.entities import Agent
from src.use_cases.task_planner import TaskPlannerUseCase
from src.use_cases.task_coordinator import TaskCoordinatorUseCase
from src.adapters.agent.capability_selector import CapabilityBasedSelector
from src.adapters.agent.llm_executor import LLMAgentExecutor
from src.interfaces import ITextGenerator, IAgentCoordinator


def compose_dependencies(
    llm_provider: ITextGenerator,
    agents: List[Agent],
    logger: Optional[logging.Logger] = None
) -> IAgentCoordinator:
    """
    Compose dependencies for the coordinator use case.

    Clean Architecture: Composition root pattern.
    SRP: Single responsibility - dependency wiring.
    DIP: Returns interface, injects abstractions.

    Args:
        llm_provider: LLM provider implementation
        agents: Available agents
        logger: Optional logger

    Returns:
        Configured IAgentCoordinator (TaskCoordinatorUseCase)
    """
    # Create adapters
    agent_executor = LLMAgentExecutor(llm_provider)
    agent_selector = CapabilityBasedSelector()

    # Create planner use case (SRP: planning)
    task_planner = TaskPlannerUseCase(
        llm_provider=llm_provider,
        agent_selector=agent_selector,
        logger=logger
    )

    # Create coordinator use case (SRP: execution)
    task_coordinator = TaskCoordinatorUseCase(
        task_planner=task_planner,
        agent_executor=agent_executor,
        logger=logger
    )

    return task_coordinator