"""Tests for LLM executor DSPy integration.

Sprint 1, US-1.3: Integration tests for DSPy prompt mode.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from src.adapters.agent.llm_executor import LLMAgentExecutor
from src.entities import Task, Agent, ExecutionContext
from src.interfaces import ITextGenerator


def test_llm_executor_accepts_prompt_mode_parameter():
    """Test that LLMAgentExecutor accepts prompt_mode parameter."""
    mock_provider = Mock(spec=ITextGenerator)
    mock_provider.model = "test"
    mock_provider.api_base = "https://test"
    mock_provider.api_key = "key"

    # Should not raise with manual mode
    executor_manual = LLMAgentExecutor(
        llm_provider=mock_provider,
        prompt_mode="manual"
    )
    assert executor_manual.prompt_mode == "manual"
    assert executor_manual.dspy_adapter is None

    # Should not raise with dspy mode
    with patch('src.adapters.agent.llm_executor.DSPyPromptAdapter'):
        executor_dspy = LLMAgentExecutor(
            llm_provider=mock_provider,
            prompt_mode="dspy"
        )
        assert executor_dspy.prompt_mode == "dspy"
        assert executor_dspy.dspy_adapter is not None


def test_llm_executor_defaults_to_manual_mode():
    """Test that prompt_mode defaults to 'manual'."""
    mock_provider = Mock(spec=ITextGenerator)
    mock_provider.model = "test"

    executor = LLMAgentExecutor(llm_provider=mock_provider)

    assert executor.prompt_mode == "manual"
    assert executor.dspy_adapter is None


def test_llm_executor_creates_dspy_adapter_when_enabled():
    """Test that DSPy adapter is created when prompt_mode='dspy'."""
    mock_provider = Mock(spec=ITextGenerator)
    mock_provider.model = "test"
    mock_provider.api_base = "https://test"
    mock_provider.api_key = "key"

    with patch('src.adapters.agent.llm_executor.DSPyPromptAdapter') as mock_dspy_class:
        mock_adapter = Mock()
        mock_dspy_class.return_value = mock_adapter

        executor = LLMAgentExecutor(
            llm_provider=mock_provider,
            prompt_mode="dspy"
        )

        # Verify DSPy adapter was created
        mock_dspy_class.assert_called_once_with(mock_provider, use_chain_of_thought=True)
        assert executor.dspy_adapter == mock_adapter


@pytest.mark.asyncio
async def test_llm_executor_routes_to_dspy_adapter_when_enabled():
    """Test that tasks are routed to DSPy adapter in DSPy mode."""
    mock_provider = Mock(spec=ITextGenerator)
    mock_provider.model = "test"
    mock_provider.api_base = "https://test"
    mock_provider.api_key = "key"

    with patch('src.adapters.agent.llm_executor.DSPyPromptAdapter') as mock_dspy_class:
        mock_adapter = Mock()
        mock_adapter.generate_for_task.return_value = "def multiply(a, b):\n    return a * b"
        mock_dspy_class.return_value = mock_adapter

        executor = LLMAgentExecutor(
            llm_provider=mock_provider,
            prompt_mode="dspy"
        )

        agent = Agent(role="backend-engineer", capabilities=["python"])
        task = Task(
            task_id="test_1",
            description="Write multiply function",
            task_type="implementation"
        )
        context = ExecutionContext(session_id="test", llm_state={})

        result = await executor.execute(agent, task, context)

        # Verify DSPy adapter was called
        mock_adapter.generate_for_task.assert_called_once_with(task, context)

        # Verify result contains DSPy-generated code
        assert result.output == "def multiply(a, b):\n    return a * b"


@pytest.mark.asyncio
async def test_llm_executor_uses_manual_prompts_when_disabled():
    """Test that manual prompts are used when prompt_mode='manual'."""
    mock_provider = Mock(spec=ITextGenerator)
    mock_provider.model = "test"
    mock_provider.generate.return_value = "def multiply(a, b):\n    return a * b"

    executor = LLMAgentExecutor(
        llm_provider=mock_provider,
        prompt_mode="manual"
    )

    agent = Agent(role="backend-engineer", capabilities=["python"])
    task = Task(
        description="Write multiply function",
        task_id="test_1",
        task_type="implementation"
    )
    context = ExecutionContext(session_id="test", llm_state={})

    result = await executor.execute(agent, task, context)

    # Verify manual provider was called (not DSPy adapter)
    mock_provider.generate.assert_called_once()
    assert result.output == "def multiply(a, b):\n    return a * b"


@pytest.mark.asyncio
async def test_llm_executor_fallback_on_dspy_error():
    """Test that executor falls back to manual prompts if DSPy fails."""
    mock_provider = Mock(spec=ITextGenerator)
    mock_provider.model = "test"
    mock_provider.api_base = "https://test"
    mock_provider.api_key = "key"
    mock_provider.generate.return_value = "def multiply(a, b):\n    return a * b"

    with patch('src.adapters.agent.llm_executor.DSPyPromptAdapter') as mock_dspy_class:
        mock_adapter = Mock()
        # DSPy raises exception
        mock_adapter.generate_for_task.side_effect = Exception("DSPy error")
        mock_dspy_class.return_value = mock_adapter

        executor = LLMAgentExecutor(
            llm_provider=mock_provider,
            prompt_mode="dspy"
        )

        agent = Agent(role="backend-engineer", capabilities=["python"])
        task = Task(
            task_id="test_1",
            description="Write multiply function",
            task_type="implementation"
        )
        context = ExecutionContext(session_id="test", llm_state={})

        result = await executor.execute(agent, task, context)

        # Should fall back to manual prompts
        mock_provider.generate.assert_called_once()
        assert result.output == "def multiply(a, b):\n    return a * b"
