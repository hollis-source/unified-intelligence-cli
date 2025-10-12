"""
Integration tests for LLM provider integrations.

Tests provider factory, mock provider, and provider interfaces.
"""

import pytest
import os
from src.factories.provider_factory import ProviderFactory
from src.adapters.llm.mock_provider import MockLLMProvider
from src.interfaces import ITextGenerator


class TestProviderIntegration:
    """Integration tests for LLM providers."""

    @pytest.fixture
    def factory(self):
        """Create provider factory."""
        return ProviderFactory()

    def test_create_mock_provider(self, factory):
        """Test creating mock provider via factory."""
        provider = factory.create_provider("mock")

        assert provider is not None
        assert isinstance(provider, MockLLMProvider)
        assert isinstance(provider, ITextGenerator)

    def test_create_mock_provider_with_config(self, factory):
        """Test creating mock provider with custom config."""
        config = {"response": "Custom mock response"}
        provider = factory.create_provider("mock", config)

        assert provider is not None
        # Use neutral message that doesn't trigger keyword-based responses
        messages = [{"role": "user", "content": "hello world"}]
        response = provider.generate(messages)
        assert response == "Custom mock response"

    def test_mock_provider_generate(self):
        """Test mock provider generation."""
        provider = MockLLMProvider(default_response="Test output")

        messages = [{"role": "user", "content": "Any prompt"}]
        response = provider.generate(messages)

        assert response == "Test output"
        assert isinstance(response, str)

    def test_mock_provider_with_llm_config(self):
        """Test mock provider with LLMConfig."""
        from src.interfaces import LLMConfig

        provider = MockLLMProvider(default_response="Config test")
        config = LLMConfig(temperature=0.7, max_tokens=100)

        messages = [{"role": "user", "content": "prompt"}]
        response = provider.generate(messages, config=config)

        assert response == "Config test"

    def test_provider_factory_registry(self, factory):
        """Test registering new provider types."""
        # Create a custom provider
        class CustomProvider(ITextGenerator):
            def generate(self, messages, config=None) -> str:
                return "custom"

        # Register it
        factory.register_provider("custom", CustomProvider)

        # Create instance
        provider = factory.create_provider("custom")

        assert provider is not None
        messages = [{"role": "user", "content": "test"}]
        assert provider.generate(messages) == "custom"

    def test_unknown_provider_raises_error(self, factory):
        """Test that unknown provider type raises ValueError."""
        with pytest.raises(ValueError, match="Unknown provider type"):
            factory.create_provider("nonexistent")

    def test_grok_provider_requires_api_key(self, factory):
        """Test that Grok provider validates API key presence."""
        # Temporarily remove API key if present
        original_key = os.environ.get("XAI_API_KEY")
        if "XAI_API_KEY" in os.environ:
            del os.environ["XAI_API_KEY"]

        try:
            with pytest.raises(ValueError, match="XAI_API_KEY"):
                factory.create_provider("grok")
        finally:
            # Restore original key
            if original_key:
                os.environ["XAI_API_KEY"] = original_key

    @pytest.mark.skipif(
        not os.getenv("XAI_API_KEY"),
        reason="XAI_API_KEY not set - skip live API test"
    )
    def test_grok_provider_creation(self, factory):
        """Test creating Grok provider with API key (live API test)."""
        provider = factory.create_provider("grok")

        assert provider is not None
        # Don't call generate in CI to avoid API costs
        assert hasattr(provider, "generate")

    def test_provider_interface_compliance(self):
        """Test that providers comply with ITextGenerator interface."""
        provider = MockLLMProvider()

        # Check interface methods exist
        assert hasattr(provider, "generate")
        assert callable(provider.generate)

        # Check generate signature
        import inspect
        sig = inspect.signature(provider.generate)
        assert "messages" in sig.parameters
        assert "config" in sig.parameters

    def test_multiple_provider_instances(self, factory):
        """Test creating multiple provider instances."""
        provider1 = factory.create_provider("mock", {"response": "Response 1"})
        provider2 = factory.create_provider("mock", {"response": "Response 2"})

        # Use neutral message that doesn't trigger keyword responses
        messages = [{"role": "user", "content": "hello"}]
        assert provider1.generate(messages) == "Response 1"
        assert provider2.generate(messages) == "Response 2"

    def test_provider_factory_ocp(self, factory):
        """Test that provider factory follows Open-Closed Principle."""
        # Should be able to extend with new providers without modifying factory
        class NewProvider(ITextGenerator):
            def generate(self, messages, config=None) -> str:
                if messages and messages[-1].get("content"):
                    return f"New: {messages[-1]['content']}"
                return "New:"

        # Extension without modification
        factory.register_provider("new", NewProvider)
        provider = factory.create_provider("new")

        messages = [{"role": "user", "content": "test"}]
        assert provider.generate(messages) == "New: test"