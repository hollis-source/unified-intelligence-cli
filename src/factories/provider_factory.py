"""LLM Provider factory - Creates providers based on configuration."""

import os
from typing import Optional, Dict, Any
from src.interfaces import ITextGenerator, IProviderFactory
from src.adapters.llm.mock_provider import MockLLMProvider


class ProviderFactory(IProviderFactory):
    """
    Factory for creating LLM providers.

    OCP: Open for extension (new providers), closed for modification.
    DIP: Returns interface, hides implementation.
    """

    def __init__(self):
        """Initialize provider factory with registry."""
        self._creators = {
            "mock": lambda config: MockLLMProvider(
                default_response=config.get("response", "Mock response") if config else "Mock response"
            ),
            "grok": lambda config: self._create_grok_provider(config),
        }
        self._providers: Dict[str, Any] = {}

    def register_provider(self, name: str, provider_class: Any) -> None:
        """
        Register a new provider type.

        OCP: Extend without modifying existing code.
        """
        self._providers[name] = provider_class

    def _create_grok_provider(self, config: Optional[Dict[str, Any]]) -> ITextGenerator:
        """Create Grok provider with validation."""
        if not os.getenv("XAI_API_KEY"):
            raise ValueError("XAI_API_KEY not set for Grok provider")
        from src.adapters.llm.grok_adapter import GrokAdapter
        return GrokAdapter()

    def create_provider(
        self,
        provider_type: str,
        config: Optional[Dict[str, Any]] = None
    ) -> ITextGenerator:
        """
        Create LLM provider by type.

        Args:
            provider_type: Type of provider (mock, grok, openai)
            config: Provider configuration

        Returns:
            ITextGenerator implementation

        Raises:
            ValueError: If provider type not found
        """
        if provider_type in self._creators:
            return self._creators[provider_type](config)
        elif provider_type in self._providers:
            provider_class = self._providers[provider_type]
            return provider_class(**(config or {}))
        else:
            raise ValueError(f"Unknown provider type: {provider_type}")