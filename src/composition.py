"""Dependency composition module - Clean Architecture composition root."""

import logging
from typing import Optional, List
from src.entities import Agent
from src.use_cases.coordinator import CoordinateAgentsUseCase
from src.adapters.agent.capability_selector import CapabilityBasedSelector
from src.adapters.agent.llm_executor import LLMAgentExecutor
from src.adapters.llm.mock_provider import MockLLMProvider
from src.interfaces import ITextGenerator


def compose_dependencies(
    llm_provider: ITextGenerator,
    agents: List[Agent],
    logger: Optional[logging.Logger] = None
) -> CoordinateAgentsUseCase:
    """
    Compose dependencies for the coordinator use case.

    Clean Architecture: Composition root pattern.
    SRP: Single responsibility - dependency wiring.

    Args:
        llm_provider: LLM provider implementation
        agents: Available agents
        logger: Optional logger

    Returns:
        Configured CoordinateAgentsUseCase
    """
    # Create adapters
    agent_executor = LLMAgentExecutor(llm_provider)
    agent_selector = CapabilityBasedSelector()

    # Create and return use case
    return CoordinateAgentsUseCase(
        llm_provider=llm_provider,
        agent_executor=agent_executor,
        agent_selector=agent_selector,
        logger=logger
    )