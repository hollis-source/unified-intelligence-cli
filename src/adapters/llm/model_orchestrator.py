"""
Model Orchestrator - Intelligent multi-model coordination with fallback.

Clean Architecture: Adapter pattern implementing ITextGenerator interface.
Strategy Pattern: Delegates to ModelSelector for intelligent model selection.
DIP: Depends on ITextGenerator abstraction, not concrete implementations.

Week 13: Multi-model orchestration with smart selection and graceful fallback.
"""

from typing import List, Dict, Any, Optional
import logging
import threading

from src.interfaces import ITextGenerator, LLMConfig, IProviderFactory
from src.routing.model_selector import ModelSelector, SelectionCriteria


logger = logging.getLogger(__name__)


class ModelOrchestrator(ITextGenerator):
    """
    Intelligent multi-model orchestrator with automatic fallback.

    Architecture:
    - Uses ModelSelector for intelligent model selection
    - Maintains fallback chain for reliability
    - Delegates to ProviderFactory for provider creation
    - Implements ITextGenerator for drop-in compatibility

    SRP: Single responsibility - coordinate model selection and fallback
    DIP: Depends on ITextGenerator and IProviderFactory abstractions
    OCP: Open for new models via ModelSelector extension
    """

    def __init__(
        self,
        provider_factory: IProviderFactory,
        criteria: SelectionCriteria = SelectionCriteria.BALANCED,
        available_providers: Optional[List[str]] = None,
        enable_fallback: bool = True,
        max_fallback_attempts: int = 3
    ):
        """
        Initialize model orchestrator.

        Args:
            provider_factory: Factory for creating providers
            criteria: Default selection criteria
            available_providers: List of available provider names (None = all)
            enable_fallback: Enable automatic fallback on errors
            max_fallback_attempts: Maximum fallback attempts
        """
        self.provider_factory = provider_factory
        self.criteria = criteria
        self.available_providers = available_providers or [
            "qwen3_zerogpu",
            "tongyi-local",
            "grok"
        ]
        self.enable_fallback = enable_fallback
        self.max_fallback_attempts = max_fallback_attempts

        # Model selector for intelligent selection
        self.selector = ModelSelector()

        # Cache for provider instances
        self._provider_cache: Dict[str, ITextGenerator] = {}

        # Statistics tracking (thread-safe)
        self._stats_lock = threading.Lock()
        self.stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "fallback_used": 0,
            "provider_usage": {}
        }

        logger.info(
            f"ModelOrchestrator initialized: criteria={criteria.value}, "
            f"providers={self.available_providers}, fallback={enable_fallback}"
        )

    def generate(
        self,
        messages: List[Dict[str, Any]],
        config: Optional[LLMConfig] = None
    ) -> str:
        """
        Generate text using intelligent model selection with fallback.

        Strategy:
        1. Select optimal model using ModelSelector
        2. Attempt generation with selected model
        3. On error, fallback to next model in chain
        4. Return response or raise error if all models fail

        Args:
            messages: Conversation messages in standard format
            config: Optional LLM configuration

        Returns:
            Generated text response

        Raises:
            RuntimeError: If all models in fallback chain fail
        """
        with self._stats_lock:
            self.stats["total_requests"] += 1

        # Extract task description for intelligent selection
        task_description = self._extract_task_description(messages)

        # Select optimal model
        primary_model = self.selector.select_model(
            criteria=self.criteria,
            available_providers=self.available_providers,
            task_description=task_description
        )

        # Get fallback chain
        if self.enable_fallback:
            fallback_chain = self.selector.get_fallback_chain(
                primary=primary_model,
                criteria=self.criteria
            )[:self.max_fallback_attempts]
        else:
            fallback_chain = [primary_model]

        # Validate fallback chain (edge case handling)
        if not fallback_chain:
            raise ValueError(
                "Empty fallback chain - no models available for selection. "
                f"Available providers: {self.available_providers}"
            )

        logger.info(
            f"Selected model: {primary_model}, fallback chain: {fallback_chain}"
        )

        # Try each model in fallback chain
        last_error = None
        for idx, provider_name in enumerate(fallback_chain):
            is_fallback = idx > 0

            if is_fallback:
                with self._stats_lock:
                    self.stats["fallback_used"] += 1
                logger.warning(
                    f"Falling back to {provider_name} "
                    f"(attempt {idx + 1}/{len(fallback_chain)})"
                )

            try:
                # Get or create provider (may raise ValueError)
                try:
                    provider = self._get_provider(provider_name)
                except (ValueError, KeyError) as creation_error:
                    # Provider creation failed - log and try next
                    last_error = creation_error
                    logger.error(
                        f"Provider creation failed for {provider_name}: {creation_error}"
                    )

                    if idx == len(fallback_chain) - 1:
                        with self._stats_lock:
                            self.stats["failed_requests"] += 1
                        raise RuntimeError(
                            f"All provider creation attempts failed. "
                            f"Last error: {creation_error}"
                        ) from last_error

                    continue

                # Generate response
                logger.info(f"Generating with {provider_name}...")
                response = provider.generate(messages, config)

                # Success - update stats and return
                with self._stats_lock:
                    self.stats["successful_requests"] += 1
                    self.stats["provider_usage"][provider_name] = \
                        self.stats["provider_usage"].get(provider_name, 0) + 1

                logger.info(
                    f"Generation successful with {provider_name} "
                    f"(fallback: {is_fallback})"
                )

                return response

            except Exception as gen_error:
                # Generation failed - log and try next
                last_error = gen_error
                logger.error(
                    f"Generation failed with {provider_name}: {gen_error}",
                    exc_info=True
                )

                # If this is the last attempt, raise
                if idx == len(fallback_chain) - 1:
                    with self._stats_lock:
                        self.stats["failed_requests"] += 1
                    raise RuntimeError(
                        f"All models in fallback chain failed. "
                        f"Last error from {provider_name}: {gen_error}"
                    ) from last_error

                # Otherwise continue to next model
                continue

        # Should never reach here (all providers failed without hitting last attempt check)
        # Ensure last_error is preserved if available
        with self._stats_lock:
            self.stats["failed_requests"] += 1

        if last_error:
            raise RuntimeError(
                f"Fallback chain exhausted. Last error: {last_error}"
            ) from last_error
        else:
            raise RuntimeError(
                "Fallback chain exhausted without result or error"
            )

    def _get_provider(self, provider_name: str) -> ITextGenerator:
        """
        Get or create provider instance.

        Uses cache to avoid recreating providers.

        Args:
            provider_name: Provider name

        Returns:
            ITextGenerator instance
        """
        if provider_name not in self._provider_cache:
            logger.info(f"Creating provider: {provider_name}")
            self._provider_cache[provider_name] = \
                self.provider_factory.create_provider(provider_name)

        return self._provider_cache[provider_name]

    def _extract_task_description(
        self,
        messages: List[Dict[str, Any]]
    ) -> str:
        """
        Extract task description from messages for model selection.

        Uses last user message as task description.

        Args:
            messages: Conversation messages

        Returns:
            Task description string
        """
        for msg in reversed(messages):
            if msg.get("role") == "user":
                return msg.get("content", "")

        return ""

    def get_stats(self) -> Dict[str, Any]:
        """
        Get orchestrator statistics (thread-safe).

        Returns:
            Dict with usage statistics
        """
        with self._stats_lock:
            total = self.stats["total_requests"]

            if total == 0:
                return {
                    **self.stats,
                    "success_rate": 0.0,
                    "fallback_rate": 0.0
                }

            return {
                **self.stats,
                "success_rate": (self.stats["successful_requests"] / total) * 100,
                "fallback_rate": (self.stats["fallback_used"] / total) * 100
            }

    def set_criteria(self, criteria: SelectionCriteria) -> None:
        """
        Update selection criteria.

        Args:
            criteria: New selection criteria
        """
        self.criteria = criteria
        logger.info(f"Selection criteria updated to: {criteria.value}")

    def get_model_info(self, provider_name: str) -> Optional[Dict[str, Any]]:
        """
        Get capabilities info for a model.

        Args:
            provider_name: Provider name

        Returns:
            Dict with model capabilities or None if not found
        """
        caps = self.selector.get_model_info(provider_name)

        if not caps:
            return None

        return {
            "name": caps.name,
            "success_rate": caps.success_rate,
            "avg_latency": caps.avg_latency,
            "cost_per_month": caps.cost_per_month,
            "requires_internet": caps.requires_internet,
            "max_tokens": caps.max_tokens,
            "supports_tools": caps.supports_tools
        }
