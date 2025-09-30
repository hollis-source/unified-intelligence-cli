"""Unit tests for TaskCoordinatorUseCase - TDD approach."""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, MagicMock
from src.entities import Agent, Task, ExecutionResult, ExecutionStatus, ExecutionContext
from src.interfaces import ITaskPlanner, IAgentExecutor, ExecutionPlan


class TestCoordinateAgentsUseCase:
    """Test the agent coordination use case."""

    @pytest.fixture
    def mock_task_planner(self):
        """Create a mock task planner."""
        planner = AsyncMock(spec=ITaskPlanner)
        # Default plan - will be overridden in tests
        planner.create_plan.return_value = ExecutionPlan(
            task_order=["0"],
            task_assignments={"0": "coder"},
            parallel_groups=[["0"]]
        )
        return planner

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
        mock_task_planner,
        mock_agent_executor,
        sample_agents,
        sample_tasks
    ):
        """Test coordinating a single task."""
        from src.use_cases.task_coordinator import TaskCoordinatorUseCase

        # Setup
        task = sample_tasks[0]
        agent = sample_agents[0]

        # Configure planner to return execution plan
        mock_task_planner.create_plan.return_value = ExecutionPlan(
            task_order=["0"],
            task_assignments={"0": "coder"},
            parallel_groups=[["0"]]
        )

        # Create use case
        use_case = TaskCoordinatorUseCase(
            task_planner=mock_task_planner,
            agent_executor=mock_agent_executor
        )

        # Execute
        results = await use_case.coordinate(
            tasks=[task],
            agents=sample_agents
        )

        # Verify
        assert len(results) == 1
        assert results[0].status == ExecutionStatus.SUCCESS
        mock_task_planner.create_plan.assert_called_once()
        mock_agent_executor.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_coordinate_multiple_tasks(
        self,
        mock_task_planner,
        mock_agent_executor,
        sample_agents,
        sample_tasks
    ):
        """Test coordinating multiple tasks with different agents."""
        from src.use_cases.task_coordinator import TaskCoordinatorUseCase

        # Configure planner for multiple tasks
        mock_task_planner.create_plan.return_value = ExecutionPlan(
            task_order=["0", "1", "2"],
            task_assignments={"0": "coder", "1": "tester", "2": "reviewer"},
            parallel_groups=[["0"], ["1"], ["2"]]
        )

        use_case = TaskCoordinatorUseCase(
            task_planner=mock_task_planner,
            agent_executor=mock_agent_executor
        )

        # Execute
        results = await use_case.coordinate(
            tasks=sample_tasks,
            agents=sample_agents
        )

        # Verify
        assert len(results) == 3
        assert all(r.status == ExecutionStatus.SUCCESS for r in results)
        mock_task_planner.create_plan.assert_called_once()
        assert mock_agent_executor.execute.call_count == 3

    @pytest.mark.asyncio
    async def test_coordinate_with_no_suitable_agent(
        self,
        mock_task_planner,
        mock_agent_executor,
        sample_agents
    ):
        """Test handling when no suitable agent is found."""
        from src.use_cases.task_coordinator import TaskCoordinatorUseCase

        # Setup - configure planner to return empty assignment (no agent found)
        task = Task(description="Deploy to production", priority=1)
        mock_task_planner.create_plan.return_value = ExecutionPlan(
            task_order=["0"],
            task_assignments={},  # Empty - no agent assigned
            parallel_groups=[["0"]]
        )

        use_case = TaskCoordinatorUseCase(
            task_planner=mock_task_planner,
            agent_executor=mock_agent_executor
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
        mock_task_planner,
        mock_agent_executor,
        sample_agents,
        sample_tasks
    ):
        """Test coordination with execution context."""
        from src.use_cases.task_coordinator import TaskCoordinatorUseCase

        # Setup
        context = ExecutionContext(
            session_id="test-session",
            history=[{"role": "user", "content": "Start coding"}]
        )

        mock_task_planner.create_plan.return_value = ExecutionPlan(
            task_order=["0"],
            task_assignments={"0": "coder"},
            parallel_groups=[["0"]]
        )

        use_case = TaskCoordinatorUseCase(
            task_planner=mock_task_planner,
            agent_executor=mock_agent_executor
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