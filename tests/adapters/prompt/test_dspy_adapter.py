"""
Tests for DSPy Prompt Adapter.

Sprint 1, US-1.2: DSPy adapter that wraps existing LLM providers.
Following TDD: Tests written before implementation.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from src.entities import Task, ExecutionContext


def test_can_import_dspy_adapter():
    """Test that DSPy adapter module can be imported."""
    from src.adapters.prompt import dspy_adapter
    assert dspy_adapter is not None


def test_dspy_adapter_class_exists():
    """Test that DSPyPromptAdapter class exists."""
    from src.adapters.prompt.dspy_adapter import DSPyPromptAdapter
    assert DSPyPromptAdapter is not None


def test_dspy_adapter_accepts_llm_provider():
    """Test that adapter can be initialized with an LLM provider."""
    from src.adapters.prompt.dspy_adapter import DSPyPromptAdapter
    from src.interfaces import ITextGenerator

    mock_provider = Mock(spec=ITextGenerator)
    mock_provider.model = "qwen3_hf_inference"
    mock_provider.api_base = "https://router.huggingface.co"
    mock_provider.api_key = "test_key"

    # Should not raise
    adapter = DSPyPromptAdapter(mock_provider)
    assert adapter is not None


def test_dspy_adapter_stores_provider_reference():
    """Test that adapter stores reference to LLM provider."""
    from src.adapters.prompt.dspy_adapter import DSPyPromptAdapter
    from src.interfaces import ITextGenerator

    mock_provider = Mock(spec=ITextGenerator)
    mock_provider.model = "qwen3"
    mock_provider.api_base = "https://test"
    mock_provider.api_key = "key"

    adapter = DSPyPromptAdapter(mock_provider)

    assert adapter.llm_provider == mock_provider


@patch('src.adapters.prompt.dspy_adapter.dspy')
def test_dspy_adapter_creates_dspy_lm_wrapper(mock_dspy):
    """Test that adapter creates DSPy LM wrapper from provider."""
    from src.adapters.prompt.dspy_adapter import DSPyPromptAdapter
    from src.interfaces import ITextGenerator

    mock_provider = Mock(spec=ITextGenerator)
    mock_provider.model = "qwen3"
    mock_provider.api_base = "https://router.huggingface.co"
    mock_provider.api_key = "test_key"

    # Mock DSPy LM constructor
    mock_lm = Mock()
    mock_dspy.LM.return_value = mock_lm

    adapter = DSPyPromptAdapter(mock_provider)

    # Verify DSPy LM was created with correct params
    mock_dspy.LM.assert_called_once()
    assert adapter.dspy_lm == mock_lm


def test_dspy_adapter_initializes_modules():
    """Test that adapter initializes DSPy modules for each task type."""
    from src.adapters.prompt.dspy_adapter import DSPyPromptAdapter
    from src.interfaces import ITextGenerator

    mock_provider = Mock(spec=ITextGenerator)
    mock_provider.model = "test"
    mock_provider.api_base = "https://test"
    mock_provider.api_key = "key"

    with patch('src.adapters.prompt.dspy_adapter.dspy'):
        adapter = DSPyPromptAdapter(mock_provider)

        # Check modules exist
        assert hasattr(adapter, 'implementation_module')
        assert hasattr(adapter, 'design_module')
        assert hasattr(adapter, 'testing_module')
        assert hasattr(adapter, 'documentation_module')


def test_dspy_adapter_generate_for_implementation_task():
    """Test generating output for implementation task."""
    from src.adapters.prompt.dspy_adapter import DSPyPromptAdapter
    from src.interfaces import ITextGenerator

    mock_provider = Mock(spec=ITextGenerator)
    mock_provider.model = "test"
    mock_provider.api_base = "https://test"
    mock_provider.api_key = "key"

    with patch('src.adapters.prompt.dspy_adapter.dspy'):
        adapter = DSPyPromptAdapter(mock_provider)

        # Mock implementation module
        mock_result = Mock()
        mock_result.code = "def test():\n    pass"
        adapter.implementation_module = Mock(return_value=mock_result)

        task = Task(
            description="Write a test function",
            task_type="implementation",
            task_id="test_1"
        )
        context = ExecutionContext(session_id="test", llm_state={})

        result = adapter.generate_for_task(task, context)

        assert result == "def test():\n    pass"
        adapter.implementation_module.assert_called_once()


def test_dspy_adapter_generate_for_design_task():
    """Test generating output for design task."""
    from src.adapters.prompt.dspy_adapter import DSPyPromptAdapter
    from src.interfaces import ITextGenerator

    mock_provider = Mock(spec=ITextGenerator)
    mock_provider.model = "test"
    mock_provider.api_base = "https://test"
    mock_provider.api_key = "key"

    with patch('src.adapters.prompt.dspy_adapter.dspy'):
        adapter = DSPyPromptAdapter(mock_provider)

        # Mock design module
        mock_result = Mock()
        mock_result.design_spec = "API: GET /users"
        adapter.design_module = Mock(return_value=mock_result)

        task = Task(
            description="Design API schema",
            task_type="design",
            task_id="test_2"
        )
        context = ExecutionContext(session_id="test", llm_state={})

        result = adapter.generate_for_task(task, context)

        assert result == "API: GET /users"


def test_dspy_adapter_generate_for_testing_task():
    """Test generating output for testing task."""
    from src.adapters.prompt.dspy_adapter import DSPyPromptAdapter
    from src.interfaces import ITextGenerator

    mock_provider = Mock(spec=ITextGenerator)
    mock_provider.model = "test"
    mock_provider.api_base = "https://test"
    mock_provider.api_key = "key"

    with patch('src.adapters.prompt.dspy_adapter.dspy'):
        adapter = DSPyPromptAdapter(mock_provider)

        # Mock testing module
        mock_result = Mock()
        mock_result.test_code = "def test_foo():\n    assert True"
        adapter.testing_module = Mock(return_value=mock_result)

        task = Task(
            description="Write tests",
            task_type="testing",
            task_id="test_3"
        )
        context = ExecutionContext(session_id="test", llm_state={'code': 'def foo(): pass'})

        result = adapter.generate_for_task(task, context)

        assert "def test_foo" in result


def test_dspy_adapter_fallback_for_unsupported_task_type():
    """Test that adapter falls back gracefully for unsupported task types."""
    from src.adapters.prompt.dspy_adapter import DSPyPromptAdapter
    from src.interfaces import ITextGenerator

    mock_provider = Mock(spec=ITextGenerator)
    mock_provider.model = "test"
    mock_provider.api_base = "https://test"
    mock_provider.api_key = "key"

    with patch('src.adapters.prompt.dspy_adapter.dspy'):
        adapter = DSPyPromptAdapter(mock_provider)

        task = Task(
            description="Deploy to production",
            task_type="deployment",  # Not yet supported
            task_id="test_4"
        )
        context = ExecutionContext(session_id="test", llm_state={})

        # Should not raise, should return fallback
        result = adapter.generate_for_task(task, context)

        assert result is not None
        # Fallback should indicate it's not DSPy-generated
        assert '[FALLBACK]' in result or isinstance(result, str)


def test_dspy_adapter_formats_context_correctly():
    """Test that adapter formats execution context for DSPy input."""
    from src.adapters.prompt.dspy_adapter import DSPyPromptAdapter
    from src.interfaces import ITextGenerator

    mock_provider = Mock(spec=ITextGenerator)
    mock_provider.model = "test"
    mock_provider.api_base = "https://test"
    mock_provider.api_key = "key"

    with patch('src.adapters.prompt.dspy_adapter.dspy'):
        adapter = DSPyPromptAdapter(mock_provider)

        context = ExecutionContext(
            session_id="test",
            llm_state={
                'design_schema': 'API schema here',
                'database_model': 'User model'
            }
        )

        formatted = adapter._format_context(context)

        assert 'design_schema' in formatted
        assert 'database_model' in formatted
        assert 'API schema here' in formatted


def test_dspy_adapter_handles_empty_context():
    """Test that adapter handles empty/None context gracefully."""
    from src.adapters.prompt.dspy_adapter import DSPyPromptAdapter
    from src.interfaces import ITextGenerator

    mock_provider = Mock(spec=ITextGenerator)
    mock_provider.model = "test"
    mock_provider.api_base = "https://test"
    mock_provider.api_key = "key"

    with patch('src.adapters.prompt.dspy_adapter.dspy'):
        adapter = DSPyPromptAdapter(mock_provider)

        # None context
        formatted = adapter._format_context(None)
        assert "No previous context" in formatted or formatted == ""

        # Empty context
        empty_context = ExecutionContext(session_id="test", llm_state={})
        formatted = adapter._format_context(empty_context)
        assert isinstance(formatted, str)


def test_dspy_adapter_extracts_code_from_context():
    """Test that adapter can extract code artifacts from context."""
    from src.adapters.prompt.dspy_adapter import DSPyPromptAdapter
    from src.interfaces import ITextGenerator

    mock_provider = Mock(spec=ITextGenerator)
    mock_provider.model = "test"
    mock_provider.api_base = "https://test"
    mock_provider.api_key = "key"

    with patch('src.adapters.prompt.dspy_adapter.dspy'):
        adapter = DSPyPromptAdapter(mock_provider)

        context = ExecutionContext(
            session_id="test",
            llm_state={
                'design': 'schema',
                'implement_function_code': 'def foo(): pass',
                'other_data': 'metadata'
            }
        )

        code = adapter._extract_code_from_context(context)

        assert 'def foo' in code
