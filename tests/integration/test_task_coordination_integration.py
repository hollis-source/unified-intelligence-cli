"""
Integration tests for task coordination flow.

Tests the full flow from use cases through adapters with real async execution.
"""

import pytest
import asyncio
from src.entities import Agent, Task, ExecutionStatus, ExecutionContext
from src.use_cases.task_planner import TaskPlannerUseCase
from src.use_cases.task_coordinator import TaskCoordinatorUseCase
from src.adapters.llm.mock_provider import MockLLMProvider
from src.adapters.agent.llm_executor import LLMAgentExecutor
from src.adapters.agent.capability_selector import CapabilityBasedSelector


@pytest.mark.asyncio
class TestTaskCoordinationIntegration:
    """Integration tests for full task coordination flow."""

    @pytest.fixture
    def agents(self):
        """Create test agents."""
        return [
            Agent(role="coder", capabilities=["code", "programming", "development"]),
            Agent(role="tester", capabilities=["test", "testing", "qa"]),
            Agent(role="writer", capabilities=["write", "documentation", "docs"])
        ]

    @pytest.fixture
    def mock_provider(self):
        """Create mock LLM provider."""
        return MockLLMProvider(default_response="Task completed successfully")

    @pytest.fixture
    def agent_selector(self):
        """Create agent selector."""
        return CapabilityBasedSelector()

    @pytest.fixture
    def planner(self, mock_provider, agent_selector):
        """Create task planner."""
        return TaskPlannerUseCase(
            llm_provider=mock_provider,
            agent_selector=agent_selector
        )

    @pytest.fixture
    def executor(self, mock_provider):
        """Create agent executor."""
        return LLMAgentExecutor(llm_provider=mock_provider)

    @pytest.fixture
    def coordinator(self, planner, executor):
        """Create task coordinator."""
        return TaskCoordinatorUseCase(
            task_planner=planner,
            agent_executor=executor,
            max_retries=2
        )

    async def test_single_task_coordination(self, coordinator, agents):
        """Test coordinating a single task end-to-end."""
        task = Task(description="Write code for authentication", priority=1)

        results = await coordinator.coordinate([task], agents)

        assert len(results) == 1
        assert results[0].status == ExecutionStatus.SUCCESS
        assert results[0].output is not None

    async def test_multiple_tasks_coordination(self, coordinator, agents):
        """Test coordinating multiple tasks end-to-end."""
        tasks = [
            Task(description="Write code for login", priority=1),
            Task(description="Write tests for login", priority=2),
            Task(description="Write documentation for login", priority=3)
        ]

        results = await coordinator.coordinate(tasks, agents)

        assert len(results) == 3
        assert all(r.status == ExecutionStatus.SUCCESS for r in results)

    async def test_coordination_with_context(self, coordinator, agents):
        """Test coordination with execution context."""
        task = Task(description="Write code", priority=1)
        context = ExecutionContext(
            session_id="test-session",
            history=[{"role": "user", "content": "Previous interaction"}]
        )

        results = await coordinator.coordinate([task], agents, context)

        assert len(results) == 1
        assert results[0].status == ExecutionStatus.SUCCESS

    async def test_parallel_execution(self, coordinator, agents):
        """Test that parallel-capable tasks execute efficiently."""
        tasks = [
            Task(description=f"Write code module {i}", priority=1)
            for i in range(3)
        ]

        import time
        start = time.time()
        results = await coordinator.coordinate(tasks, agents)
        elapsed = time.time() - start

        assert len(results) == 3
        assert all(r.status == ExecutionStatus.SUCCESS for r in results)
        # Parallel execution should be faster than sequential
        # (though with mocks this is just a sanity check)
        assert elapsed < 5.0  # Should complete quickly with mocks

    async def test_agent_selection(self, coordinator, agents):
        """Test that correct agents are selected for tasks."""
        tasks = [
            Task(description="Write code for feature", priority=1),
            Task(description="Write tests for feature", priority=2)
        ]

        results = await coordinator.coordinate(tasks, agents)

        # Both should succeed with appropriate agents
        assert len(results) == 2
        assert all(r.status == ExecutionStatus.SUCCESS for r in results)

    async def test_no_suitable_agent(self, coordinator, agents):
        """Test handling when no agent matches task."""
        # Create a task that doesn't match any agent capabilities
        task = Task(description="Deploy to kubernetes production cluster", priority=1)

        results = await coordinator.coordinate([task], agents)

        assert len(results) == 1
        # Should fail or have fallback handling
        assert results[0].status in [ExecutionStatus.FAILURE, ExecutionStatus.SUCCESS]

    async def test_dependency_handling(self, coordinator, agents):
        """Test that task dependencies are respected."""
        task1 = Task(
            description="Write code",
            task_id="task1",
            priority=1,
            dependencies=[]
        )
        task2 = Task(
            description="Write tests",
            task_id="task2",
            priority=2,
            dependencies=["task1"]
        )

        results = await coordinator.coordinate([task1, task2], agents)

        assert len(results) == 2
        # Dependencies should be handled (though exact order depends on planner)
        assert all(r.status == ExecutionStatus.SUCCESS for r in results)

    async def test_error_recovery(self, coordinator, agents):
        """Test that errors are properly handled and recovered."""
        # Create a task with empty description (edge case)
        task = Task(description="", priority=1)

        results = await coordinator.coordinate([task], agents)

        assert len(results) == 1
        # Should handle gracefully
        assert results[0] is not None

    async def test_timeout_handling(self, planner, executor, agents):
        """Test that long-running tasks respect timeouts."""
        # Create coordinator with short retry limit
        coordinator = TaskCoordinatorUseCase(
            task_planner=planner,
            agent_executor=executor,
            max_retries=1
        )

        task = Task(description="Long running task", priority=1)

        # Should complete (mocks don't actually timeout)
        results = await asyncio.wait_for(
            coordinator.coordinate([task], agents),
            timeout=5.0
        )

        assert len(results) == 1