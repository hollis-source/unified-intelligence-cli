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
            "tongyi": lambda config: self._create_tongyi_provider(config),
            "tongyi-local": lambda config: self._create_tongyi_local_provider(config),
            "replicate": lambda config: self._create_replicate_provider(config),
            "qwen3_zerogpu": lambda config: self._create_qwen3_provider(config),
            "auto": lambda config: self._create_orchestrator(config),
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

    def _create_tongyi_provider(self, config: Optional[Dict[str, Any]]) -> ITextGenerator:
        """Create Tongyi-DeepResearch-30B provider via llama.cpp (sync, requests)."""
        from src.adapters.llm.tongyi_adapter import TongyiDeepResearchAdapter
        server_url = config.get("server_url", "http://localhost:8080") if config else "http://localhost:8080"
        return TongyiDeepResearchAdapter(server_url=server_url)

    def _create_tongyi_local_provider(self, config: Optional[Dict[str, Any]]) -> ITextGenerator:
        """
        Create local Tongyi provider via llama.cpp (async, aiohttp).

        Week 8: LocalTongyiAdapter with async HTTP for better performance.
        Default: http://localhost:8080 (llama-cpp-server Docker container)
        """
        from src.adapters.llm.tongyi_local_adapter import LocalTongyiAdapter
        base_url = config.get("base_url", "http://localhost:8080") if config else "http://localhost:8080"
        timeout = config.get("timeout", 120) if config else 120
        return LocalTongyiAdapter(base_url=base_url, timeout=timeout)

    def _create_replicate_provider(self, config: Optional[Dict[str, Any]]) -> ITextGenerator:
        """Create Replicate GPU inference provider (Week 9: parallel data collection)."""
        from src.adapters.llm.replicate_adapter import ReplicateAdapter
        model = config.get("model", "meta/llama-2-70b-chat") if config else "meta/llama-2-70b-chat"
        return ReplicateAdapter(model=model)

    def _create_qwen3_provider(self, config: Optional[Dict[str, Any]]) -> ITextGenerator:
        """
        Create Qwen3-8B ZeroGPU provider (Week 13: Production inference).

        Uses production inference Space (hollis-source/qwen3-inference) with:
        - 100% success rate (validated via evaluation)
        - 13.8s avg latency
        - FREE with HF Pro subscription
        """
        from src.adapters.llm.qwen3_zerogpu_adapter import Qwen3InferenceAdapter
        space_id = config.get("space_id", "hollis-source/qwen3-inference") if config else "hollis-source/qwen3-inference"
        timeout = config.get("timeout", 60) if config else 60
        return Qwen3InferenceAdapter(space_id=space_id, timeout=timeout)

    def _create_orchestrator(self, config: Optional[Dict[str, Any]]) -> ITextGenerator:
        """
        Create intelligent multi-model orchestrator (Week 13: Smart model selection).

        Orchestrator features:
        - Automatic model selection based on criteria (speed, quality, cost, privacy)
        - Graceful fallback on failures (Qwen3 → Tongyi → Grok)
        - Statistics tracking for monitoring

        Configuration:
            criteria: "speed", "quality", "cost", "privacy", or "balanced" (default)
            available_providers: List of provider names to use (default: all)
            enable_fallback: Enable automatic fallback (default: True)
            max_fallback_attempts: Maximum fallback attempts (default: 3)
        """
        from src.adapters.llm.model_orchestrator import ModelOrchestrator
        from src.routing.model_selector import SelectionCriteria

        # Parse criteria from config
        criteria_str = config.get("criteria", "balanced") if config else "balanced"
        criteria_map = {
            "speed": SelectionCriteria.SPEED,
            "quality": SelectionCriteria.QUALITY,
            "cost": SelectionCriteria.COST,
            "privacy": SelectionCriteria.PRIVACY,
            "balanced": SelectionCriteria.BALANCED
        }
        criteria = criteria_map.get(criteria_str.lower(), SelectionCriteria.BALANCED)

        # Get available providers (default: all production models)
        available_providers = config.get("available_providers") if config else None
        if available_providers is None:
            available_providers = ["qwen3_zerogpu", "tongyi-local", "grok"]

        # Get fallback settings
        enable_fallback = config.get("enable_fallback", True) if config else True
        max_fallback_attempts = config.get("max_fallback_attempts", 3) if config else 3

        return ModelOrchestrator(
            provider_factory=self,
            criteria=criteria,
            available_providers=available_providers,
            enable_fallback=enable_fallback,
            max_fallback_attempts=max_fallback_attempts
        )

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