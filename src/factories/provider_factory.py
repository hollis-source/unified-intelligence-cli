"""LLM Provider factory - Creates providers based on configuration."""

import os
from typing import Optional, Dict, Any
from src.interfaces import ITextGenerator
from src.adapters.llm.mock_provider import MockLLMProvider


class ProviderFactory:
    """
    Factory for creating LLM providers.

    OCP: Open for extension (new providers), closed for modification.
    DIP: Returns interface, hides implementation.
    """

    # Registry of available providers
    _providers: Dict[str, Any] = {
        "mock": MockLLMProvider,
    }

    @classmethod
    def register_provider(cls, name: str, provider_class: Any) -> None:
        """
        Register a new provider type.

        OCP: Extend without modifying existing code.
        """
        cls._providers[name] = provider_class

    @classmethod
    def create_provider(
        cls,
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
        if provider_type == "grok":
            # Lazy import to avoid dependency if not used
            if not os.getenv("XAI_API_KEY"):
                raise ValueError("XAI_API_KEY not set for Grok provider")

            from src.adapters.llm.grok_adapter import GrokAdapter
            return GrokAdapter()

        elif provider_type == "mock":
            return MockLLMProvider(
                default_response=config.get("response", "Mock response") if config else "Mock response"
            )

        elif provider_type in cls._providers:
            # Use registered provider
            provider_class = cls._providers[provider_type]
            return provider_class(**(config or {}))

        else:
            raise ValueError(f"Unknown provider type: {provider_type}")