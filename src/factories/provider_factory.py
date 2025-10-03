"""
LLM Provider Factory - Registry Pattern for provider creation.

Clean Architecture: DIP, OCP compliance via creator registry.
Week 13: Refactored to fix DIP violation (no direct adapter imports).
"""

from typing import Optional, Dict, Any
from src.interfaces import ITextGenerator, IProviderFactory
from src.factories.provider_creators import (
    IProviderCreator,
    MockProviderCreator,
    GrokProviderCreator,
    TongyiProviderCreator,
    TongyiLocalProviderCreator,
    ReplicateProviderCreator,
    Qwen3ProviderCreator,
    OrchestratorProviderCreator
)


class ProviderFactory(IProviderFactory):
    """
    Factory for creating LLM providers via creator registry.

    Clean Architecture Compliance:
    - DIP: Depends on IProviderCreator abstraction, not concrete adapters
    - OCP: Open for extension via register_creator(), closed for modification
    - SRP: Single responsibility - coordinate creator registry

    Week 13: Refactored to eliminate direct adapter imports.
    """

    def __init__(self):
        """
        Initialize provider factory with creator registry.

        Registers default creators for all supported providers.
        """
        self._creators: Dict[str, IProviderCreator] = {}

        # Register default creators
        self._register_default_creators()

    def _register_default_creators(self) -> None:
        """
        Register default provider creators.

        Internal method to set up built-in providers.
        """
        self._creators["mock"] = MockProviderCreator()
        self._creators["grok"] = GrokProviderCreator()
        self._creators["tongyi"] = TongyiProviderCreator()
        self._creators["tongyi-local"] = TongyiLocalProviderCreator()
        self._creators["replicate"] = ReplicateProviderCreator()
        self._creators["qwen3_zerogpu"] = Qwen3ProviderCreator()

        # Orchestrator needs factory reference (circular dependency handled via lazy import)
        self._creators["auto"] = OrchestratorProviderCreator(provider_factory=self)

    def register_creator(
        self,
        name: str,
        creator: IProviderCreator
    ) -> None:
        """
        Register custom provider creator.

        OCP: Extend with new providers without modifying factory code.

        Args:
            name: Provider name (e.g., "custom-model")
            creator: Creator instance implementing IProviderCreator

        Example:
            factory.register_creator("my-model", MyModelCreator())
        """
        self._creators[name] = creator

    def register_provider(self, name: str, provider_class: Any) -> None:
        """
        Legacy method for backward compatibility.

        Deprecated: Use register_creator() instead for better DIP compliance.
        """
        # Wrap provider class in lambda creator for backward compatibility
        class LegacyCreator:
            def __init__(self, provider_class):
                self.provider_class = provider_class

            def create(self, config: Optional[Dict[str, Any]] = None) -> ITextGenerator:
                return self.provider_class(**(config or {}))

        self._creators[name] = LegacyCreator(provider_class)

    def create_provider(
        self,
        provider_type: str,
        config: Optional[Dict[str, Any]] = None
    ) -> ITextGenerator:
        """
        Create LLM provider by type using creator registry.

        DIP Compliance: All creation delegated to IProviderCreator implementations.

        Args:
            provider_type: Type of provider (mock, grok, tongyi-local, qwen3_zerogpu, auto)
            config: Provider configuration dict

        Returns:
            ITextGenerator implementation

        Raises:
            ValueError: If provider type not found in registry

        Example:
            provider = factory.create_provider("qwen3_zerogpu", {"timeout": 120})
        """
        if provider_type not in self._creators:
            available = ", ".join(sorted(self._creators.keys()))
            raise ValueError(
                f"Unknown provider type: {provider_type}. "
                f"Available providers: {available}"
            )

        creator = self._creators[provider_type]
        return creator.create(config)