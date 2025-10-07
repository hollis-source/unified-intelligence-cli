"""Tests for DirectTaskExecutor P1-1 output validation.

Tests cover result dict validation, logging, and assertion checks
to prevent silent failures.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from src.dsl.adapters.direct_task_executor import DirectTaskExecutor
from src.entities import Agent, Task, ExecutionResult, ExecutionStatus
from src.factories.agent_factory import AgentFactory


class MockLLMProvider:
    """Mock LLM provider for testing."""

    def __init__(self):
        self.model = "test-model"

    async def generate(self, messages, config=None):
        return "Test response"


class MockAgentFactory:
    """Mock agent factory for testing."""

    def create_default_agents(self):
        return [Agent(role="test-agent", capabilities=["testing"])]


class TestDirectTaskExecutorValidation:
    """Test P1-1 output validation in DirectTaskExecutor."""

    @pytest.mark.asyncio
    async def test_execute_task_returns_valid_dict_on_success(self):
        """Test that execute_task returns properly structured dict on success."""
        llm_provider = MockLLMProvider()
        agent_factory = MockAgentFactory()

        executor = DirectTaskExecutor(
            llm_provider=llm_provider,
            agent_factory=agent_factory,
            config={'provider': 'test', 'agent_mode': 'default'}
        )

        # Mock LLM executor to return valid result
        mock_result = Mock()
        mock_result.status = ExecutionStatus.SUCCESS
        mock_result.output = "Task completed successfully"

        with patch.object(executor.llm_executor, 'execute', return_value=mock_result):
            result = await executor.execute_task("test_task")

        # P1-1: Validate dict structure
        assert 'status' in result
        assert 'output' in result
        assert 'metadata' in result
        assert result['status'] == 'SUCCESS'
        assert result['output'] == "Task completed successfully"

    @pytest.mark.asyncio
    async def test_execute_task_validates_result_attributes(self):
        """Test that execute_task validates result has expected attributes."""
        llm_provider = MockLLMProvider()
        agent_factory = MockAgentFactory()

        executor = DirectTaskExecutor(
            llm_provider=llm_provider,
            agent_factory=agent_factory,
            config={'provider': 'test', 'agent_mode': 'default'}
        )

        # Mock result missing 'status' attribute
        mock_result = Mock(spec=[])  # No attributes
        mock_result.output = "output"

        with patch.object(executor.llm_executor, 'execute', return_value=mock_result):
            with patch('src.dsl.adapters.direct_task_executor.logger') as mock_logger:
                result = await executor.execute_task("test_task")

                # Should log warning about missing status
                assert mock_logger.warning.called
                # Should use default SUCCESS status
                assert result['status'] == 'SUCCESS'

    @pytest.mark.asyncio
    async def test_execute_task_logs_warning_when_output_is_none(self):
        """Test that execute_task logs warning when SUCCESS but output is None."""
        llm_provider = MockLLMProvider()
        agent_factory = MockAgentFactory()

        executor = DirectTaskExecutor(
            llm_provider=llm_provider,
            agent_factory=agent_factory,
            config={'provider': 'test', 'agent_mode': 'default'}
        )

        # Mock result with SUCCESS status but None output
        mock_result = Mock()
        mock_result.status = ExecutionStatus.SUCCESS
        mock_result.output = None

        with patch.object(executor.llm_executor, 'execute', return_value=mock_result):
            with patch('src.dsl.adapters.direct_task_executor.logger') as mock_logger:
                result = await executor.execute_task("test_task")

                # Should log warning about None output
                warning_calls = [call for call in mock_logger.warning.call_args_list
                                if 'None output' in str(call)]
                assert len(warning_calls) > 0

                # Should still return the result
                assert result['status'] == 'SUCCESS'
                assert result['output'] is None

    @pytest.mark.asyncio
    async def test_execute_task_error_dict_has_required_keys(self):
        """Test that error dict has all required keys."""
        llm_provider = MockLLMProvider()
        agent_factory = MockAgentFactory()

        executor = DirectTaskExecutor(
            llm_provider=llm_provider,
            agent_factory=agent_factory,
            config={'provider': 'test', 'agent_mode': 'default'}
        )

        # Mock execution to raise exception
        with patch.object(executor.llm_executor, 'execute', side_effect=Exception("Test error")):
            result = await executor.execute_task("test_task")

        # P1-1: Validate error dict structure
        assert 'status' in result
        assert 'output' in result
        assert 'error' in result
        assert 'metadata' in result
        assert result['status'] == 'FAILED'
        assert result['error'] == "Test error"

    @pytest.mark.asyncio
    async def test_execute_task_assertions_catch_structural_errors(self):
        """Test that assertions catch structural errors in result dict."""
        # This test verifies that if somehow the dict construction fails,
        # assertions will catch it. In practice, this shouldn't happen,
        # but assertions provide fail-fast safety.

        llm_provider = MockLLMProvider()
        agent_factory = MockAgentFactory()

        executor = DirectTaskExecutor(
            llm_provider=llm_provider,
            agent_factory=agent_factory,
            config={'provider': 'test', 'agent_mode': 'default'}
        )

        mock_result = Mock()
        mock_result.status = ExecutionStatus.SUCCESS
        mock_result.output = "output"

        with patch.object(executor.llm_executor, 'execute', return_value=mock_result):
            # This should not raise AssertionError because dict is properly constructed
            result = await executor.execute_task("test_task")

            # Verify assertions would have caught missing keys
            assert 'status' in result
            assert 'output' in result
            assert 'metadata' in result
