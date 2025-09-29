"""Unit tests for CoordinateAgentsUseCase - TDD approach."""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, MagicMock
from src.entities import Agent, Task, ExecutionResult, ExecutionStatus, ExecutionContext
from src.interfaces import ITextGenerator, IAgentExecutor, IAgentSelector, LLMConfig


class TestCoordinateAgentsUseCase:
    """Test the agent coordination use case."""

    @pytest.fixture
    def mock_llm_provider(self):
        """Create a mock LLM provider."""
        provider = Mock(spec=ITextGenerator)
        provider.generate = Mock(return_value="Task completed successfully")
        return provider

    @pytest.fixture
    def mock_agent_executor(self):
        """Create a mock agent executor."""
        executor = AsyncMock(spec=IAgentExecutor)
        executor.execute.return_value = ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            output="Task executed",
            errors=[],
            metadata={"duration": 1.5}
        )
        return executor

    @pytest.fixture
    def mock_agent_selector(self):
        """Create a mock agent selector."""
        selector = Mock(spec=IAgentSelector)
        selector.select_agent = Mock()
        return selector

    @pytest.fixture
    def sample_agents(self):
        """Create sample agents for testing."""
        return [
            Agent(role="coder", capabilities=["code_gen", "refactor"]),
            Agent(role="tester", capabilities=["test", "validate"]),
            Agent(role="reviewer", capabilities=["review", "analyze"])
        ]

    @pytest.fixture
    def sample_tasks(self):
        """Create sample tasks for testing."""
        return [
            Task(description="Generate code for user authentication", priority=1),
            Task(description="Write test cases for auth module", priority=2),
            Task(description="Review and analyze code quality", priority=3)
        ]

    @pytest.mark.asyncio
    async def test_coordinate_single_task(
        self,
        mock_llm_provider,
        mock_agent_executor,
        mock_agent_selector,
        sample_agents,
        sample_tasks
    ):
        """Test coordinating a single task."""
        # Import here to avoid import errors before implementation
        from src.use_cases.coordinator import CoordinateAgentsUseCase

        # Setup
        task = sample_tasks[0]
        agent = sample_agents[0]
        mock_agent_selector.select_agent.return_value = agent

        # Create use case
        use_case = CoordinateAgentsUseCase(
            llm_provider=mock_llm_provider,
            agent_executor=mock_agent_executor,
            agent_selector=mock_agent_selector
        )

        # Execute
        results = await use_case.coordinate(
            tasks=[task],
            agents=sample_agents
        )

        # Verify
        assert len(results) == 1
        assert results[0].status == ExecutionStatus.SUCCESS
        mock_agent_selector.select_agent.assert_called_once_with(task, sample_agents)
        mock_agent_executor.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_coordinate_multiple_tasks(
        self,
        mock_llm_provider,
        mock_agent_executor,
        mock_agent_selector,
        sample_agents,
        sample_tasks
    ):
        """Test coordinating multiple tasks with different agents."""
        from src.use_cases.coordinator import CoordinateAgentsUseCase

        # Setup - each task gets appropriate agent
        mock_agent_selector.select_agent.side_effect = [
            sample_agents[0],  # coder for task 1
            sample_agents[1],  # tester for task 2
            sample_agents[2]   # reviewer for task 3
        ]

        use_case = CoordinateAgentsUseCase(
            llm_provider=mock_llm_provider,
            agent_executor=mock_agent_executor,
            agent_selector=mock_agent_selector
        )

        # Execute
        results = await use_case.coordinate(
            tasks=sample_tasks,
            agents=sample_agents
        )

        # Verify
        assert len(results) == 3
        assert all(r.status == ExecutionStatus.SUCCESS for r in results)
        assert mock_agent_selector.select_agent.call_count == 3
        assert mock_agent_executor.execute.call_count == 3

    @pytest.mark.asyncio
    async def test_coordinate_with_no_suitable_agent(
        self,
        mock_llm_provider,
        mock_agent_executor,
        mock_agent_selector,
        sample_agents
    ):
        """Test handling when no suitable agent is found."""
        from src.use_cases.coordinator import CoordinateAgentsUseCase

        # Setup
        task = Task(description="Deploy to production", priority=1)
        mock_agent_selector.select_agent.return_value = None

        use_case = CoordinateAgentsUseCase(
            llm_provider=mock_llm_provider,
            agent_executor=mock_agent_executor,
            agent_selector=mock_agent_selector
        )

        # Execute
        results = await use_case.coordinate(
            tasks=[task],
            agents=sample_agents
        )

        # Verify
        assert len(results) == 1
        assert results[0].status == ExecutionStatus.FAILURE
        assert "No suitable agent" in results[0].errors[0]

    @pytest.mark.asyncio
    async def test_coordinate_with_context(
        self,
        mock_llm_provider,
        mock_agent_executor,
        mock_agent_selector,
        sample_agents,
        sample_tasks
    ):
        """Test coordination with execution context."""
        from src.use_cases.coordinator import CoordinateAgentsUseCase

        # Setup
        context = ExecutionContext(
            session_id="test-session",
            history=[{"role": "user", "content": "Start coding"}]
        )
        mock_agent_selector.select_agent.return_value = sample_agents[0]

        use_case = CoordinateAgentsUseCase(
            llm_provider=mock_llm_provider,
            agent_executor=mock_agent_executor,
            agent_selector=mock_agent_selector
        )

        # Execute
        results = await use_case.coordinate(
            tasks=[sample_tasks[0]],
            agents=sample_agents,
            context=context
        )

        # Verify context was passed
        assert len(results) == 1
        call_args = mock_agent_executor.execute.call_args
        assert call_args[1]["context"] == context