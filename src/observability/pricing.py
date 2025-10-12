"""Model pricing configuration and cost calculation utilities.

Provides pricing data for common LLM models and utilities to calculate costs.
Pricing data is based on public API pricing as of October 2025.

Pricing sources:
- X.AI (Grok): https://x.ai/api
- HuggingFace: https://huggingface.co/pricing
- OpenAI: https://openai.com/pricing
- Anthropic: https://anthropic.com/pricing
"""

from dataclasses import dataclass
from typing import Dict, Optional


@dataclass(frozen=True)
class ModelPricing:
    """Pricing configuration for a specific model.

    Immutable pricing data with input/output token costs.
    All costs in USD per 1000 tokens.
    """

    model_name: str
    provider: str
    input_cost_per_1k: float  # USD per 1000 input tokens
    output_cost_per_1k: float  # USD per 1000 output tokens
    context_window: int  # Maximum tokens (context + generation)
    notes: str = ""

    def calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Calculate total cost for token usage.

        Args:
            input_tokens: Number of input (prompt) tokens
            output_tokens: Number of output (completion) tokens

        Returns:
            Total cost in USD
        """
        input_cost = (input_tokens / 1000.0) * self.input_cost_per_1k
        output_cost = (output_tokens / 1000.0) * self.output_cost_per_1k
        return input_cost + output_cost


# Default pricing database
# Pricing as of October 2025 (update as needed)
DEFAULT_MODEL_PRICING: Dict[str, ModelPricing] = {
    # X.AI Models
    "grok-1": ModelPricing(
        model_name="grok-1",
        provider="x-ai",
        input_cost_per_1k=0.005,  # $5 per 1M input tokens
        output_cost_per_1k=0.015,  # $15 per 1M output tokens
        context_window=131072,  # 128K context
        notes="Grok-1 base model with 314B parameters",
    ),
    "grok-2": ModelPricing(
        model_name="grok-2",
        provider="x-ai",
        input_cost_per_1k=0.010,  # $10 per 1M input tokens
        output_cost_per_1k=0.030,  # $30 per 1M output tokens
        context_window=131072,
        notes="Grok-2 advanced reasoning model",
    ),
    # HuggingFace Models (Inference API)
    "meta-llama/Llama-3-8b": ModelPricing(
        model_name="meta-llama/Llama-3-8b",
        provider="huggingface",
        input_cost_per_1k=0.0002,  # $0.20 per 1M tokens
        output_cost_per_1k=0.0002,
        context_window=8192,
        notes="Llama 3 8B via HuggingFace Inference API",
    ),
    "meta-llama/Llama-3-70b": ModelPricing(
        model_name="meta-llama/Llama-3-70b",
        provider="huggingface",
        input_cost_per_1k=0.0008,  # $0.80 per 1M tokens
        output_cost_per_1k=0.0008,
        context_window=8192,
        notes="Llama 3 70B via HuggingFace Inference API",
    ),
    "mistralai/Mistral-7B-v0.1": ModelPricing(
        model_name="mistralai/Mistral-7B-v0.1",
        provider="huggingface",
        input_cost_per_1k=0.0002,
        output_cost_per_1k=0.0002,
        context_window=8192,
        notes="Mistral 7B via HuggingFace",
    ),
    # Qwen Models
    "qwen3-next-80b": ModelPricing(
        model_name="qwen3-next-80b",
        provider="huggingface",
        input_cost_per_1k=0.0010,  # $1 per 1M tokens
        output_cost_per_1k=0.0010,
        context_window=32768,
        notes="Qwen3-Next-80B-Thinking premium reasoning model",
    ),
    # OpenAI Models
    "gpt-4": ModelPricing(
        model_name="gpt-4",
        provider="openai",
        input_cost_per_1k=0.030,  # $30 per 1M input tokens
        output_cost_per_1k=0.060,  # $60 per 1M output tokens
        context_window=8192,
        notes="GPT-4 base model",
    ),
    "gpt-4-turbo": ModelPricing(
        model_name="gpt-4-turbo",
        provider="openai",
        input_cost_per_1k=0.010,  # $10 per 1M input tokens
        output_cost_per_1k=0.030,  # $30 per 1M output tokens
        context_window=128000,
        notes="GPT-4 Turbo with 128K context",
    ),
    "gpt-3.5-turbo": ModelPricing(
        model_name="gpt-3.5-turbo",
        provider="openai",
        input_cost_per_1k=0.0005,  # $0.50 per 1M input tokens
        output_cost_per_1k=0.0015,  # $1.50 per 1M output tokens
        context_window=16384,
        notes="GPT-3.5 Turbo with 16K context",
    ),
    # Anthropic Models
    "claude-3-opus": ModelPricing(
        model_name="claude-3-opus",
        provider="anthropic",
        input_cost_per_1k=0.015,  # $15 per 1M input tokens
        output_cost_per_1k=0.075,  # $75 per 1M output tokens
        context_window=200000,
        notes="Claude 3 Opus with 200K context",
    ),
    "claude-3-sonnet": ModelPricing(
        model_name="claude-3-sonnet",
        provider="anthropic",
        input_cost_per_1k=0.003,  # $3 per 1M input tokens
        output_cost_per_1k=0.015,  # $15 per 1M output tokens
        context_window=200000,
        notes="Claude 3 Sonnet with 200K context",
    ),
    "claude-3-haiku": ModelPricing(
        model_name="claude-3-haiku",
        provider="anthropic",
        input_cost_per_1k=0.00025,  # $0.25 per 1M input tokens
        output_cost_per_1k=0.00125,  # $1.25 per 1M output tokens
        context_window=200000,
        notes="Claude 3 Haiku with 200K context",
    ),
}


class PricingDatabase:
    """Database of model pricing configurations.

    Provides lookup and calculation utilities for model costs.
    """

    def __init__(self, pricing: Optional[Dict[str, ModelPricing]] = None):
        """Initialize pricing database.

        Args:
            pricing: Optional custom pricing dict (defaults to DEFAULT_MODEL_PRICING)
        """
        self._pricing = pricing if pricing is not None else DEFAULT_MODEL_PRICING.copy()

    def get_pricing(self, model_name: str) -> Optional[ModelPricing]:
        """Get pricing for a model.

        Args:
            model_name: Model name (e.g., "grok-1", "gpt-4")

        Returns:
            ModelPricing if found, None otherwise
        """
        return self._pricing.get(model_name)

    def add_pricing(self, pricing: ModelPricing) -> None:
        """Add or update pricing for a model.

        Args:
            pricing: ModelPricing configuration
        """
        self._pricing[pricing.model_name] = pricing

    def calculate_cost(
        self, model_name: str, input_tokens: int, output_tokens: int
    ) -> Optional[float]:
        """Calculate cost for model usage.

        Args:
            model_name: Model name
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens

        Returns:
            Total cost in USD, or None if model not found
        """
        pricing = self.get_pricing(model_name)
        if pricing is None:
            return None
        return pricing.calculate_cost(input_tokens, output_tokens)

    def get_all_models(self) -> list[str]:
        """Get list of all model names in database.

        Returns:
            List of model names
        """
        return list(self._pricing.keys())

    def get_models_by_provider(self, provider: str) -> list[str]:
        """Get models for a specific provider.

        Args:
            provider: Provider name (e.g., "x-ai", "openai", "anthropic")

        Returns:
            List of model names for provider
        """
        return [
            name
            for name, pricing in self._pricing.items()
            if pricing.provider == provider
        ]

    def estimate_cost_range(
        self, model_name: str, min_tokens: int, max_tokens: int
    ) -> Optional[tuple[float, float]]:
        """Estimate cost range for token range.

        Assumes average 75% input, 25% output token split.

        Args:
            model_name: Model name
            min_tokens: Minimum total tokens
            max_tokens: Maximum total tokens

        Returns:
            Tuple of (min_cost, max_cost) in USD, or None if model not found
        """
        pricing = self.get_pricing(model_name)
        if pricing is None:
            return None

        # Assume 75% input, 25% output split
        min_input = int(min_tokens * 0.75)
        min_output = int(min_tokens * 0.25)
        max_input = int(max_tokens * 0.75)
        max_output = int(max_tokens * 0.25)

        min_cost = pricing.calculate_cost(min_input, min_output)
        max_cost = pricing.calculate_cost(max_input, max_output)

        return (min_cost, max_cost)


# Global pricing database instance
_global_pricing_db: Optional[PricingDatabase] = None


def get_pricing_database() -> PricingDatabase:
    """Get global pricing database instance.

    Returns:
        Global PricingDatabase instance
    """
    global _global_pricing_db
    if _global_pricing_db is None:
        _global_pricing_db = PricingDatabase()
    return _global_pricing_db


def set_pricing_database(db: PricingDatabase) -> None:
    """Set global pricing database instance.

    Args:
        db: PricingDatabase to use globally
    """
    global _global_pricing_db
    _global_pricing_db = db


def calculate_cost(model_name: str, input_tokens: int, output_tokens: int) -> Optional[float]:
    """Calculate cost using global pricing database.

    Convenience function for quick cost calculations.

    Args:
        model_name: Model name
        input_tokens: Number of input tokens
        output_tokens: Number of output tokens

    Returns:
        Total cost in USD, or None if model not found

    Example:
        >>> cost = calculate_cost("grok-1", 1000, 500)
        >>> print(f"Cost: ${cost:.4f}")
        Cost: $0.0125
    """
    return get_pricing_database().calculate_cost(model_name, input_tokens, output_tokens)
