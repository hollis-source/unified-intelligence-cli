"""
Provider Creators - Strategy Pattern for provider instantiation.

Clean Architecture: Separates provider creation logic from factory.
DIP: ProviderFactory depends on IProviderCreator abstraction.
OCP: Add new providers without modifying ProviderFactory.
SRP: Each creator has single responsibility.

Week 13: Extracted from ProviderFactory to fix DIP violation.
"""

import os
from typing import Optional, Dict, Any, Protocol
from src.interfaces import ITextGenerator


class IProviderCreator(Protocol):
    """
    Interface for provider creators.

    DIP: ProviderFactory depends on this abstraction, not concrete creators.
    Strategy Pattern: Each creator encapsulates provider instantiation logic.
    """

    def create(self, config: Optional[Dict[str, Any]] = None) -> ITextGenerator:
        """
        Create provider instance.

        Args:
            config: Provider configuration

        Returns:
            ITextGenerator implementation

        Raises:
            ValueError: If creation fails (e.g., missing API keys)
        """
        ...


class MockProviderCreator:
    """Creator for mock LLM provider (testing)."""

    def create(self, config: Optional[Dict[str, Any]] = None) -> ITextGenerator:
        from src.adapters.llm.mock_provider import MockLLMProvider

        default_response = "Mock response"
        if config and "response" in config:
            default_response = config["response"]

        return MockLLMProvider(default_response=default_response)


class GrokProviderCreator:
    """Creator for Grok-Code-Fast-1 provider (X.AI API)."""

    def create(self, config: Optional[Dict[str, Any]] = None) -> ITextGenerator:
        if not os.getenv("XAI_API_KEY"):
            raise ValueError(
                "XAI_API_KEY not set. Get key from: https://x.ai/api"
            )

        from src.adapters.llm.grok_adapter import GrokAdapter
        return GrokAdapter()


class TongyiProviderCreator:
    """
    Creator for Tongyi-DeepResearch-30B provider (llama.cpp, sync).

    Legacy provider using sync requests. Prefer TongyiLocalProviderCreator.
    """

    def create(self, config: Optional[Dict[str, Any]] = None) -> ITextGenerator:
        from src.adapters.llm.tongyi_adapter import TongyiDeepResearchAdapter

        server_url = "http://localhost:8080"
        if config and "server_url" in config:
            server_url = config["server_url"]

        return TongyiDeepResearchAdapter(server_url=server_url)


class TongyiLocalProviderCreator:
    """
    Creator for local Tongyi provider (llama.cpp, async).

    Week 8: Async aiohttp for better performance.
    Default: http://localhost:8080 (llama-cpp-server Docker container)
    """

    def create(self, config: Optional[Dict[str, Any]] = None) -> ITextGenerator:
        from src.adapters.llm.tongyi_local_adapter import LocalTongyiAdapter

        base_url = "http://localhost:8080"
        timeout = 120

        if config:
            if "base_url" in config:
                base_url = config["base_url"]
            if "timeout" in config:
                timeout = config["timeout"]

        return LocalTongyiAdapter(base_url=base_url, timeout=timeout)


class ReplicateProviderCreator:
    """
    Creator for Replicate GPU inference provider.

    Week 9: Parallel data collection with cloud GPU.
    """

    def create(self, config: Optional[Dict[str, Any]] = None) -> ITextGenerator:
        from src.adapters.llm.replicate_adapter import ReplicateAdapter

        model = "meta/llama-2-70b-chat"
        if config and "model" in config:
            model = config["model"]

        return ReplicateAdapter(model=model)


class Qwen3ProviderCreator:
    """
    Creator for Qwen3-8B ZeroGPU provider.

    Week 13: Production inference via HuggingFace ZeroGPU Space.
    Performance: 100% success rate, 13.8s avg latency, FREE with HF Pro.
    """

    def create(self, config: Optional[Dict[str, Any]] = None) -> ITextGenerator:
        from src.adapters.llm.qwen3_zerogpu_adapter import Qwen3InferenceAdapter

        space_id = "hollis-source/qwen3-inference"
        timeout = 60

        if config:
            if "space_id" in config:
                space_id = config["space_id"]
            if "timeout" in config:
                timeout = config["timeout"]

        return Qwen3InferenceAdapter(space_id=space_id, timeout=timeout)


class OrchestratorProviderCreator:
    """
    Creator for intelligent multi-model orchestrator.

    Week 13: Smart model selection with automatic fallback.

    Features:
    - Automatic selection based on criteria (speed, quality, cost, privacy)
    - 3-level fallback chain (Qwen3 → Tongyi → Grok)
    - Thread-safe statistics tracking

    Configuration:
        criteria: "speed", "quality", "cost", "privacy", "balanced" (default)
        available_providers: List of provider names (default: all)
        enable_fallback: Enable automatic fallback (default: True)
        max_fallback_attempts: Maximum fallback attempts (default: 3)
    """

    def __init__(self, provider_factory):
        """
        Initialize orchestrator creator.

        Args:
            provider_factory: Factory for creating fallback providers

        Note: Circular dependency handled via lazy import.
        """
        self.provider_factory = provider_factory

    def create(self, config: Optional[Dict[str, Any]] = None) -> ITextGenerator:
        from src.adapters.llm.model_orchestrator import ModelOrchestrator
        from src.routing.model_selector import SelectionCriteria

        # Parse criteria
        criteria_str = "balanced"
        if config and "criteria" in config:
            criteria_str = config["criteria"]

        criteria_map = {
            "speed": SelectionCriteria.SPEED,
            "quality": SelectionCriteria.QUALITY,
            "cost": SelectionCriteria.COST,
            "privacy": SelectionCriteria.PRIVACY,
            "balanced": SelectionCriteria.BALANCED
        }
        criteria = criteria_map.get(criteria_str.lower(), SelectionCriteria.BALANCED)

        # Get available providers
        available_providers = None
        if config and "available_providers" in config:
            available_providers = config["available_providers"]

        if available_providers is None:
            available_providers = ["qwen3_zerogpu", "tongyi-local", "grok"]

        # Get fallback settings
        enable_fallback = True
        max_fallback_attempts = 3

        if config:
            if "enable_fallback" in config:
                enable_fallback = config["enable_fallback"]
            if "max_fallback_attempts" in config:
                max_fallback_attempts = config["max_fallback_attempts"]

        return ModelOrchestrator(
            provider_factory=self.provider_factory,
            criteria=criteria,
            available_providers=available_providers,
            enable_fallback=enable_fallback,
            max_fallback_attempts=max_fallback_attempts
        )
