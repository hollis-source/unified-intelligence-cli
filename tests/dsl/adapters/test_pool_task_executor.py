"""Tests for PoolTaskExecutor - Dynamic task routing via executor pool.

Tests cover:
- AgentExecutor capability matching
- AgentExecutor execution
- PoolTaskExecutor initialization
- Task routing to capable agents
- Error handling
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from src.dsl.adapters.pool_task_executor import AgentExecutor, PoolTaskExecutor
from src.entities import Agent, Task, ExecutionResult as AgentExecutionResult, ExecutionStatus
from src.entities.executor import ExecutionResult, ExecutorStatus
from src.factories.agent_factory import AgentFactory


@pytest.fixture
def mock_llm_executor():
    """Create mock LLM executor."""
    executor = Mock()
    executor.execute = AsyncMock(return_value=AgentExecutionResult(
        status=ExecutionStatus.SUCCESS,
        output="Task completed successfully",
        metadata={"agent_role": "test_agent", "task_id": "task_1"}
    ))
    return executor


@pytest.fixture
def mock_llm_provider():
    """Create mock LLM provider."""
    provider = Mock()
    provider.generate_text = AsyncMock(return_value="Mock response")
    return provider


@pytest.fixture
def test_agent():
    """Create test agent."""
    return Agent(
        role="test_coder",
        capabilities=["code", "python", "test", "debug"],
        tier=3,
        parent_agent=None,
        specialization="backend"
    )


@pytest.fixture
def agent_executor(test_agent, mock_llm_executor):
    """Create AgentExecutor with test agent."""
    return AgentExecutor(test_agent, mock_llm_executor)


class TestAgentExecutor:
    """Tests for AgentExecutor wrapper."""

    def test_initialization(self, agent_executor, test_agent):
        """Test AgentExecutor initializes correctly."""
        assert agent_executor.executor_id == "agent_test_coder"
        assert agent_executor.name == "Agent: test_coder"
        assert agent_executor.agent == test_agent
        assert agent_executor.metadata["agent_role"] == "test_coder"
        assert agent_executor.metadata["capabilities"] == ["code", "python", "test", "debug"]
        assert agent_executor.metadata["tier"] == 3

    def test_can_execute_with_string_task(self, agent_executor):
        """Test can_execute with string task description."""
        # Should match capability
        assert agent_executor.can_execute("Write some python code") == True
        assert agent_executor.can_execute("Debug the test") == True

        # Should not match
        assert agent_executor.can_execute("Review the document") == False

    def test_can_execute_with_dict_task(self, agent_executor):
        """Test can_execute with dict task."""
        task = {"description": "Write code for feature"}
        assert agent_executor.can_execute(task) == True

        task = {"description": "Design the architecture"}
        assert agent_executor.can_execute(task) == False

    def test_can_execute_case_insensitive(self, agent_executor):
        """Test capability matching is case insensitive."""
        assert agent_executor.can_execute("Write PYTHON CODE") == True
        assert agent_executor.can_execute("DEBUG the app") == True

    def test_execute_success(self, agent_executor, mock_llm_executor):
        """Test successful task execution."""
        result = agent_executor.execute("Write python code")

        assert result.success == True
        assert result.output == "Task completed successfully"
        assert result.metadata["agent"] == "test_coder"
        assert agent_executor.status == ExecutorStatus.IDLE
        assert agent_executor.execution_count == 1

    def test_execute_increments_count(self, agent_executor):
        """Test execution count increments."""
        initial_count = agent_executor.execution_count

        agent_executor.execute("Write code")
        assert agent_executor.execution_count == initial_count + 1

        agent_executor.execute("Debug code")
        assert agent_executor.execution_count == initial_count + 2

    def test_execute_failure_handling(self, test_agent):
        """Test execution handles failures gracefully."""
        # Create executor with failing LLM
        failing_executor = Mock()
        failing_executor.execute = AsyncMock(side_effect=Exception("LLM error"))

        agent_executor = AgentExecutor(test_agent, failing_executor)
        result = agent_executor.execute("Write code")

        assert result.success == False
        assert "LLM error" in result.error
        assert agent_executor.status == ExecutorStatus.FAILED

    def test_execute_with_dict_task(self, agent_executor):
        """Test execute with dict task."""
        task = {"description": "Write python code", "priority": "high"}
        result = agent_executor.execute(task)

        assert result.success == True
        assert "Write python code" in result.metadata["task"]


class TestPoolTaskExecutor:
    """Tests for PoolTaskExecutor."""

    @pytest.fixture
    def pool_executor(self, mock_llm_provider):
        """Create PoolTaskExecutor with mock provider."""
        factory = AgentFactory()
        config = {"agent_mode": "default", "provider": "mock"}
        return PoolTaskExecutor(factory, mock_llm_provider, config)

    def test_initialization(self, pool_executor):
        """Test PoolTaskExecutor initializes with agents."""
        # Should register default agents (5)
        assert len(pool_executor.pool.executors) == 5

        # Check some expected agents are registered
        executor_ids = list(pool_executor.pool.executors.keys())
        assert "agent_coder" in executor_ids
        assert "agent_tester" in executor_ids
        assert "agent_coordinator" in executor_ids

    def test_initialization_with_extended_agents(self, mock_llm_provider):
        """Test initialization with extended agent mode."""
        factory = AgentFactory()
        config = {"agent_mode": "extended"}
        pool = PoolTaskExecutor(factory, mock_llm_provider, config)

        # Extended mode has 8 agents
        assert len(pool.pool.executors) == 8

    @pytest.mark.asyncio
    async def test_execute_task_routes_to_capable_agent(self, pool_executor):
        """Test task routing to capable agent."""
        # Mock the execute method to avoid actual LLM calls
        for executor in pool_executor.pool.executors.values():
            executor.execute = Mock(return_value=ExecutionResult(
                success=True,
                output="Task completed",
                metadata={"agent": executor.agent.role}
            ))

        # Execute coding task
        result = await pool_executor.execute_task("Write python code")

        # Should route to coder agent
        assert result == "Task completed"

        # Check that coder agent was called
        coder_executor = pool_executor.pool.executors.get("agent_coder")
        assert coder_executor is not None
        assert coder_executor.execute.called

    @pytest.mark.asyncio
    async def test_execute_task_fails_when_no_capable_agent(self, pool_executor):
        """Test execution fails when no agent can handle task."""
        # Task that doesn't match any capabilities
        with pytest.raises(ValueError, match="No executor available"):
            await pool_executor.execute_task("Perform quantum computing analysis")

    @pytest.mark.asyncio
    async def test_execute_task_propagates_execution_errors(self, pool_executor):
        """Test execution errors are propagated."""
        # Mock executor to fail
        for executor in pool_executor.pool.executors.values():
            executor.execute = Mock(return_value=ExecutionResult(
                success=False,
                error="Execution failed",
                metadata={}
            ))

        with pytest.raises(ValueError, match="Task execution failed"):
            await pool_executor.execute_task("Write code")

    def test_get_all_capabilities(self, pool_executor):
        """Test getting all capabilities from pool."""
        capabilities = pool_executor._get_all_capabilities()

        # Should include capabilities from all agents
        assert "code" in capabilities
        assert "test" in capabilities
        assert "review" in capabilities
        assert "plan" in capabilities
        assert "research" in capabilities

    def test_get_executor_stats(self, pool_executor):
        """Test getting executor statistics."""
        stats = pool_executor.get_executor_stats()

        assert stats["total_executors"] == 5
        assert "executors_by_status" in stats
        assert "executors_by_tier" in stats
        assert "total_executions" in stats

        # Initially all should be IDLE
        assert stats["executors_by_status"]["IDLE"] == 5

    def test_get_executor_stats_tracks_executions(self, pool_executor):
        """Test stats track execution counts."""
        # Execute some tasks (mock the executor)
        for executor in pool_executor.pool.executors.values():
            executor.execute = Mock(return_value=ExecutionResult(success=True, output="done"))
            executor.execute("test task")
            executor.execution_count += 1

        stats = pool_executor.get_executor_stats()
        assert stats["total_executions"] == 5  # One execution per executor


class TestIntegration:
    """Integration tests combining components."""

    @pytest.mark.asyncio
    async def test_end_to_end_task_execution(self, mock_llm_provider):
        """Test complete flow from task to execution."""
        # Setup
        factory = AgentFactory()
        pool_executor = PoolTaskExecutor(factory, mock_llm_provider, {"agent_mode": "default"})

        # Mock executors
        for executor in pool_executor.pool.executors.values():
            executor.execute = Mock(return_value=ExecutionResult(
                success=True,
                output=f"Completed by {executor.agent.role}",
                metadata={"agent": executor.agent.role}
            ))

        # Execute different task types
        code_result = await pool_executor.execute_task("Write python function")
        test_result = await pool_executor.execute_task("Run unit tests")
        plan_result = await pool_executor.execute_task("Plan the sprint")

        # Verify routing
        assert "coder" in code_result
        assert "tester" in test_result
        assert "coordinator" in plan_result

    def test_multiple_agents_can_handle_overlapping_capabilities(self, mock_llm_provider):
        """Test pool handles agents with overlapping capabilities."""
        factory = AgentFactory()
        pool = PoolTaskExecutor(factory, mock_llm_provider, {"agent_mode": "default"})

        # Task "analyze" could match reviewer or researcher
        task = "analyze the codebase"

        # Get available executor
        executor = pool.pool.get_available_executor(task)

        # Should get one that can handle it
        assert executor is not None
        assert executor.can_execute(task) == True
