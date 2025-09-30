"""Unit tests for dependency composition (composition.py)."""

import pytest
import logging
from unittest.mock import Mock

from src.composition import compose_dependencies
from src.entities import Agent
from src.interfaces import ITextGenerator, IAgentCoordinator


class TestComposeDependencies:
    """Test dependency injection composition root."""

    def test_compose_dependencies_returns_coordinator(self):
        """Test that compose_dependencies returns IAgentCoordinator."""
        # Create minimal mocks
        mock_provider = Mock(spec=ITextGenerator)
        mock_agents = [Agent(role="coder", capabilities=["code"])]

        result = compose_dependencies(
            llm_provider=mock_provider,
            agents=mock_agents,
            logger=None
        )

        # Should return coordinator that implements interface
        assert result is not None
        assert hasattr(result, 'coordinate')
        # Check it's the right type
        from src.use_cases.task_coordinator import TaskCoordinatorUseCase
        assert isinstance(result, TaskCoordinatorUseCase)

    def test_compose_dependencies_with_logger(self):
        """Test composition with logger provided."""
        mock_provider = Mock(spec=ITextGenerator)
        mock_agents = [Agent(role="tester", capabilities=["test"])]
        mock_logger = logging.getLogger("test")

        result = compose_dependencies(
            llm_provider=mock_provider,
            agents=mock_agents,
            logger=mock_logger
        )

        assert result is not None
        # Logger should be passed to internal components
        assert hasattr(result, 'logger')

    def test_compose_dependencies_without_logger(self):
        """Test composition without logger (None)."""
        mock_provider = Mock(spec=ITextGenerator)
        mock_agents = [Agent(role="reviewer", capabilities=["review"])]

        result = compose_dependencies(
            llm_provider=mock_provider,
            agents=mock_agents,
            logger=None
        )

        assert result is not None
        # Should work fine without logger

    def test_compose_dependencies_wires_correctly(self):
        """Test that dependencies are wired correctly (DIP)."""
        mock_provider = Mock(spec=ITextGenerator)
        mock_agents = [
            Agent(role="coder", capabilities=["code"]),
            Agent(role="tester", capabilities=["test"])
        ]

        coordinator = compose_dependencies(
            llm_provider=mock_provider,
            agents=mock_agents,
            logger=None
        )

        # Coordinator should have task_planner and agent_executor
        assert hasattr(coordinator, 'task_planner')
        assert hasattr(coordinator, 'agent_executor')

        # Task planner should have llm_provider and agent_selector
        assert hasattr(coordinator.task_planner, 'llm_provider')
        assert hasattr(coordinator.task_planner, 'agent_selector')

        # Agent executor should have llm_provider
        assert hasattr(coordinator.agent_executor, 'llm_provider')

    def test_compose_dependencies_follows_dip(self):
        """Test that composition follows Dependency Inversion Principle."""
        # Mock provider implements interface
        mock_provider = Mock(spec=ITextGenerator)
        mock_provider.generate = Mock(return_value="response")

        mock_agents = [Agent(role="coordinator", capabilities=["coordinate"])]

        coordinator = compose_dependencies(
            llm_provider=mock_provider,
            agents=mock_agents,
            logger=None
        )

        # Coordinator depends on abstractions, not concretions
        # The mock provider should be used by internal components
        assert coordinator.agent_executor.llm_provider == mock_provider
        assert coordinator.task_planner.llm_provider == mock_provider

    def test_compose_dependencies_empty_agents_list(self):
        """Test composition with empty agents list."""
        mock_provider = Mock(spec=ITextGenerator)
        mock_agents = []

        # Should still create coordinator, even with no agents
        result = compose_dependencies(
            llm_provider=mock_provider,
            agents=mock_agents,
            logger=None
        )

        assert result is not None

    def test_compose_dependencies_creates_unique_instances(self):
        """Test that each composition creates fresh instances."""
        mock_provider = Mock(spec=ITextGenerator)
        mock_agents = [Agent(role="researcher", capabilities=["research"])]

        coord1 = compose_dependencies(mock_provider, mock_agents, None)
        coord2 = compose_dependencies(mock_provider, mock_agents, None)

        # Should be different instances
        assert coord1 is not coord2
        assert coord1.task_planner is not coord2.task_planner
        assert coord1.agent_executor is not coord2.agent_executor