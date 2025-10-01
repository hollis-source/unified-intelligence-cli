"""Dependency composition module - Clean Architecture composition root."""

import logging
from typing import Optional, List
from src.entities import Agent
from src.use_cases.task_planner import TaskPlannerUseCase
from src.use_cases.task_coordinator import TaskCoordinatorUseCase
from src.adapters.agent.capability_selector import CapabilityBasedSelector
from src.adapters.agent.llm_executor import LLMAgentExecutor
from src.interfaces import ITextGenerator, IAgentCoordinator
from src.factories.provider_factory import ProviderFactory
from src.factories.agent_factory import AgentFactory
from src.factories.orchestration_factory import OrchestrationFactory
from src.utils.data_collector import DataCollector


def compose_dependencies(
    llm_provider: ITextGenerator,
    agents: List[Agent],
    logger: Optional[logging.Logger] = None,
    orchestrator_mode: str = "simple",
    collect_data: bool = False,
    data_dir: str = "data/training",
    provider_name: str = "unknown"
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
        orchestrator_mode: Orchestration mode ("simple" or "openai-agents")
        collect_data: Enable data collection for training (Week 9)
        data_dir: Directory to store collected data (Week 9)
        provider_name: LLM provider name (Week 9)

    Returns:
        Configured IAgentCoordinator (implementation depends on orchestrator_mode)
    """
    # Week 9: Create data collector if enabled
    data_collector = None
    if collect_data:
        data_collector = DataCollector(data_dir=data_dir, enabled=True)
        if logger:
            logger.info(f"Data collection enabled: {data_dir}")

    # Create adapters
    agent_executor = LLMAgentExecutor(
        llm_provider,
        data_collector=data_collector,
        provider_name=provider_name,
        orchestrator=orchestrator_mode
    )
    agent_selector = CapabilityBasedSelector()

    # Create planner use case (SRP: planning)
    task_planner = TaskPlannerUseCase(
        llm_provider=llm_provider,
        agent_selector=agent_selector,
        logger=logger
    )

    # Create coordinator via factory (Week 7: supports multiple orchestration modes)
    coordinator = OrchestrationFactory.create_orchestrator(
        mode=orchestrator_mode,
        llm_provider=llm_provider,
        task_planner=task_planner,
        agent_executor=agent_executor,
        agents=agents,
        logger_instance=logger
    )

    return coordinator


def create_coordinator(
    provider_type: str = "mock",
    verbose: bool = False
) -> IAgentCoordinator:
    """
    Convenience function to create coordinator with defaults.

    Uses factory pattern to create dependencies from provider type string.
    Useful for testing and simple use cases.

    Args:
        provider_type: LLM provider type ("mock", "grok", etc.)
        verbose: Enable verbose logging

    Returns:
        Configured IAgentCoordinator
    """
    # Create factories
    agent_factory = AgentFactory()
    provider_factory = ProviderFactory()

    # Create dependencies via factories
    agents = agent_factory.create_default_agents()
    llm_provider = provider_factory.create_provider(provider_type)

    # Setup logging if verbose
    logger = None
    if verbose:
        logging.basicConfig(level=logging.INFO)
        logger = logging.getLogger(__name__)

    # Compose and return
    return compose_dependencies(
        llm_provider=llm_provider,
        agents=agents,
        logger=logger
    )