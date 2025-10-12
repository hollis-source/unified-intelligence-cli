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

        default_response = None
        if config and "response" in config:
            default_response = config["response"]

        return MockLLMProvider(default_response=default_response)


class GrokProviderCreator:
    """Creator for Grok-Code-Fast-1 provider (X.AI API)."""

    def create(self, config: Optional[Dict[str, Any]] = None) -> ITextGenerator:
        from src.utils.secrets import require_secret

        # Read API key from Docker secret or environment variable
        require_secret(
            "XAI_API_KEY",
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


class Qwen3HFInferenceCreator:
    """
    Creator for Qwen3-8B HuggingFace Serverless Inference provider.

    Phase 4 Priority #2: 37x faster than ZeroGPU (1.2s vs 45s).
    Performance: 100% success rate, 1.2s avg latency, FREE with HF Pro ($2/month credits).
    Cost: Uses PRO credits, pay-as-you-go after (~$0.001-0.01/request).
    """

    def create(self, config: Optional[Dict[str, Any]] = None) -> ITextGenerator:
        from src.adapters.llm.qwen3_hf_inference_adapter import Qwen3HFInferenceAdapter

        model_id = "Qwen/Qwen3-8B"
        token = None
        timeout = 30

        if config:
            if "model_id" in config:
                model_id = config["model_id"]
            if "token" in config:
                token = config["token"]
            if "timeout" in config:
                timeout = config["timeout"]

        return Qwen3HFInferenceAdapter(
            model_id=model_id,
            token=token,
            timeout=timeout
        )


class Qwen3Next80BThinkingCreator:
    """
    Creator for Qwen3-Next-80B-A3B-Thinking Inference Endpoint.

    Phase 4 Priority #3: Premium reasoning model for complex architectural tasks.
    Performance: 80B params (3B activated), explicit thinking process, superior reasoning.
    Benchmarks: 87.8% AIME25, 73.9% HMMT25, 68.7% LiveCodeBench (beats Gemini-Flash).
    Cost: $10/hour when active (scale-to-zero saves costs when idle).

    Best For:
    - Complex architectural design
    - Multi-step reasoning tasks
    - Code analysis requiring deep understanding
    - Research and exploration
    """

    def create(self, config: Optional[Dict[str, Any]] = None) -> ITextGenerator:
        from src.adapters.llm.qwen3_next_80b_thinking_adapter import Qwen3Next80BThinkingAdapter

        endpoint_url = "https://crlqq5n5zwaz4rnh.us-east-2.aws.endpoints.huggingface.cloud"
        token = None
        timeout = 300  # 5 minutes for complex reasoning

        if config:
            if "endpoint_url" in config:
                endpoint_url = config["endpoint_url"]
            if "token" in config:
                token = config["token"]
            if "timeout" in config:
                timeout = config["timeout"]

        return Qwen3Next80BThinkingAdapter(
            endpoint_url=endpoint_url,
            token=token,
            timeout=timeout
        )


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
            available_providers = [
                "qwen3_hf_inference",  # Priority 1: 1.2s latency
                "qwen3_zerogpu",       # Priority 2: 45s latency (FREE fallback)
                "tongyi-local",        # Priority 3: Local inference
                "grok"                 # Priority 4: High-quality fallback
            ]

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
