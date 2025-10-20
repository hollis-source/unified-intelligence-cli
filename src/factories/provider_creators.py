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
from src.interface import ITextGenerator


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


class GraniteProviderCreator:
    """
    Creator for IBM Granite 4.0-H provider (local llama.cpp).

    Features:
    - Zero-cost local inference
    - 512K context window
    - Load balancing across 2 instances (ports 8080, 8081)
    - Better instruction-following than Grok
    - OpenAI-compatible API
    """

    def create(self, config: Optional[Dict[str, Any]] = None) -> ITextGenerator:
        from src.adapters.llm.granite_adapter_v3 import GraniteAdapterV3

        instances = ["http://localhost:8080", "http://localhost:8081"]
        enable_rag = False
        timeout = 300

        if config:
            if "instances" in config:
                instances = config["instances"]
            if "enable_rag" in config:
                enable_rag = config["enable_rag"]
            if "timeout" in config:
                timeout = config["timeout"]

        return GraniteAdapterV3(
            instances=instances,
            enable_rag=enable_rag,
            timeout=timeout
        )


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


class QwenAgentProviderCreator:
    """
    Creator for Qwen-Agent provider (Official Qwen framework).

    Wraps Qwen-Agent framework for optimized Qwen3 model inference.

    Features:
    - Hermes-style function calling (Qwen3-optimized)
    - Parallel tool calls
    - MCP support
    - Built-in Qwen-Agent tools

    Configuration:
        model: Model ID (default: Qwen/Qwen3-Next-80B-A3B-Instruct)
        endpoint_url: Inference endpoint URL (default: from QWEN_ENDPOINT env)
        thinking_mode: Enable thinking mode (default: False)
        temperature: Sampling temperature (default: 0.7)
        max_tokens: Maximum output tokens (default: 16384)
    """

    def create(self, config: Optional[Dict[str, Any]] = None) -> ITextGenerator:
        from src.adapters.llm.qwen_agent_adapter import create_qwen_agent_adapter

        model = "Qwen/Qwen3-Next-80B-A3B-Instruct"
        endpoint_url = None
        thinking_mode = False

        if config:
            if "model" in config:
                model = config["model"]
            if "endpoint_url" in config:
                endpoint_url = config["endpoint_url"]
            if "thinking_mode" in config:
                thinking_mode = config["thinking_mode"]

        return create_qwen_agent_adapter(
            model=model,
            endpoint_url=endpoint_url,
            thinking_mode=thinking_mode
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


class Qwen3NextProviderCreator:
    """Creator for Qwen3-Next-80B via HuggingFace Inference API.

    Performance: 47-95x faster than local Granite (1.88s vs 60-120s per task)
    Model: Qwen/Qwen3-Next-80B-A3B-Instruct (80B parameters, latest generation)
    Infrastructure: HuggingFace serverless Inference API

    Note: max_tokens increased to 2048 (from 2000) per dogfooding recommendation
    to prevent output truncation on complex tasks.
    """

    def create(self, config: Optional[Dict[str, Any]] = None) -> ITextGenerator:
        from src.adapters.llm.qwen3_next_adapter import Qwen3NextAdapter

        max_tokens = 2048
        temperature = 0.7
        timeout = 30

        if config:
            if "max_tokens" in config:
                max_tokens = config["max_tokens"]
            if "temperature" in config:
                temperature = config["temperature"]
            if "timeout" in config:
                timeout = config["timeout"]

        return Qwen3NextAdapter(
            max_tokens=max_tokens,
            temperature=temperature,
            timeout=timeout
        )
