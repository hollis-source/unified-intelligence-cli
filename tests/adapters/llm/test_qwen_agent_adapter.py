"""Tests for Qwen-Agent adapter.

Unit tests for QwenAgentAdapter using mocks - no endpoint required.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, call
from src.entity.agent import Task


@pytest.fixture
def mock_qwen_agent_available():
    """Mock qwen-agent availability."""
    with patch('src.adapters.llm.qwen_agent_adapter.QWEN_AGENT_AVAILABLE', True):
        yield


@pytest.fixture
def mock_assistant():
    """Mock Qwen-Agent Assistant class."""
    with patch('src.adapters.llm.qwen_agent_adapter.Assistant') as mock:
        instance = MagicMock()
        # Mock run method to return iterator of responses
        instance.run.return_value = iter([
            {'role': 'assistant', 'content': 'Test response'}
        ])
        mock.return_value = instance
        yield mock, instance


@pytest.fixture
def mock_register_tool():
    """Mock register_tool decorator."""
    with patch('src.adapters.llm.qwen_agent_adapter.register_tool') as mock:
        def decorator(name):
            def wrapper(cls):
                return cls
            return wrapper
        mock.side_effect = decorator
        yield mock


class TestQwenAgentAdapter:
    """Test suite for QwenAgentAdapter."""

    def test_adapter_initialization(self, mock_qwen_agent_available, mock_assistant):
        """Test adapter initializes correctly."""
        from src.adapters.llm.qwen_agent_adapter import QwenAgentAdapter, QwenAgentConfig

        config = QwenAgentConfig(model="Qwen/Qwen3-8B")
        adapter = QwenAgentAdapter(config)

        assert adapter.config.model == "Qwen/Qwen3-8B"
        assert adapter._bot is None  # Lazy initialization
        assert adapter._custom_tools == {}

    def test_adapter_initialization_without_qwen_agent(self):
        """Test adapter raises error when qwen-agent not available."""
        from src.adapters.llm.qwen_agent_adapter import QwenAgentConfig

        with patch('src.adapters.llm.qwen_agent_adapter.QWEN_AGENT_AVAILABLE', False):
            from src.adapters.llm.qwen_agent_adapter import QwenAgentAdapter

            config = QwenAgentConfig()

            with pytest.raises(ImportError, match="qwen-agent is required"):
                QwenAgentAdapter(config)

    def test_create_llm_config(self, mock_qwen_agent_available, mock_assistant):
        """Test LLM configuration creation."""
        from src.adapters.llm.qwen_agent_adapter import QwenAgentAdapter, QwenAgentConfig

        config = QwenAgentConfig(
            model="Qwen/Qwen3-Next-80B-A3B-Instruct",
            model_server="http://test:8000/v1",
            temperature=0.8,
            max_tokens=8192
        )
        adapter = QwenAgentAdapter(config)

        llm_cfg = adapter._llm_cfg

        assert llm_cfg['model'] == "Qwen/Qwen3-Next-80B-A3B-Instruct"
        assert llm_cfg['model_server'] == "http://test:8000/v1"
        assert llm_cfg['generate_cfg']['temperature'] == 0.8
        assert llm_cfg['generate_cfg']['max_tokens'] == 8192

    def test_generate_basic(self, mock_qwen_agent_available, mock_assistant):
        """Test basic generation."""
        from src.adapters.llm.qwen_agent_adapter import QwenAgentAdapter, QwenAgentConfig

        mock_assistant_class, mock_instance = mock_assistant

        config = QwenAgentConfig()
        adapter = QwenAgentAdapter(config)

        result = adapter.generate("Test prompt")

        assert result == "Test response"
        mock_assistant_class.assert_called_once()
        mock_instance.run.assert_called_once()


class TestProviderFactoryIntegration:
    """Test integration with ProviderFactory."""

    def test_factory_creates_qwen_agent_provider(self, mock_qwen_agent_available, mock_assistant):
        """Test ProviderFactory can create qwen-agent provider."""
        from src.factories.provider_factory import ProviderFactory

        factory = ProviderFactory()

        # Verify qwen-agent is registered
        assert "qwen-agent" in factory._creators

        # Create provider
        provider = factory.create_provider("qwen-agent")

        # Verify it's our adapter
        from src.adapters.llm.qwen_agent_adapter import QwenAgentAdapter
        assert isinstance(provider, QwenAgentAdapter)
