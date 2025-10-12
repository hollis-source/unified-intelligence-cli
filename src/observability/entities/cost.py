"""Cost tracking domain entities.

Entities for tracking API costs and usage:
- CostEntry: Individual API call cost record
- CostSummary: Aggregated cost statistics

All entities are immutable (frozen dataclasses) following Clean Architecture.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Optional
import uuid


@dataclass(frozen=True)
class CostEntry:
    """Individual API call cost record.

    Immutable entity tracking a single LLM API call cost.
    Records token usage and calculates cost based on pricing.
    """

    id: str
    model_name: str  # e.g., "grok-1", "qwen3-next-80b", "meta-llama/Llama-3-8b"
    provider: str  # e.g., "x-ai", "huggingface", "openai"

    # Token usage
    input_tokens: int
    output_tokens: int
    total_tokens: int

    # Pricing (USD per 1000 tokens)
    input_cost_per_1k: float
    output_cost_per_1k: float

    # Metadata
    timestamp: datetime
    project_id: Optional[str] = None
    task_id: Optional[str] = None
    agent_name: Optional[str] = None
    trace_id: Optional[str] = None  # Link to distributed trace
    tags: Dict[str, str] = field(default_factory=dict)

    def __post_init__(self):
        """Validate cost entry data."""
        # Validate ID
        if not self.id or not self.id.strip():
            raise ValueError("Cost entry ID cannot be empty")

        # Validate model name
        if not self.model_name or not self.model_name.strip():
            raise ValueError("Model name cannot be empty")

        # Validate provider
        if not self.provider or not self.provider.strip():
            raise ValueError("Provider cannot be empty")

        # Validate token counts (non-negative)
        if self.input_tokens < 0:
            raise ValueError(f"Input tokens cannot be negative: {self.input_tokens}")
        if self.output_tokens < 0:
            raise ValueError(f"Output tokens cannot be negative: {self.output_tokens}")
        if self.total_tokens < 0:
            raise ValueError(f"Total tokens cannot be negative: {self.total_tokens}")

        # Validate total tokens matches sum
        expected_total = self.input_tokens + self.output_tokens
        if self.total_tokens != expected_total:
            raise ValueError(
                f"Total tokens ({self.total_tokens}) does not match "
                f"sum of input + output ({expected_total})"
            )

        # Validate pricing (non-negative)
        if self.input_cost_per_1k < 0:
            raise ValueError(f"Input cost per 1k cannot be negative: {self.input_cost_per_1k}")
        if self.output_cost_per_1k < 0:
            raise ValueError(f"Output cost per 1k cannot be negative: {self.output_cost_per_1k}")

    @staticmethod
    def create(
        model_name: str,
        provider: str,
        input_tokens: int,
        output_tokens: int,
        input_cost_per_1k: float,
        output_cost_per_1k: float,
        project_id: Optional[str] = None,
        task_id: Optional[str] = None,
        agent_name: Optional[str] = None,
        trace_id: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None,
    ) -> "CostEntry":
        """Factory method to create a cost entry with generated ID.

        Args:
            model_name: Name of the model used
            provider: Provider name (x-ai, huggingface, etc.)
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            input_cost_per_1k: Cost per 1000 input tokens (USD)
            output_cost_per_1k: Cost per 1000 output tokens (USD)
            project_id: Optional project identifier
            task_id: Optional task identifier
            agent_name: Optional agent name
            trace_id: Optional trace identifier
            tags: Optional metadata tags

        Returns:
            New CostEntry with generated ID
        """
        return CostEntry(
            id=str(uuid.uuid4()),
            model_name=model_name,
            provider=provider,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
            input_cost_per_1k=input_cost_per_1k,
            output_cost_per_1k=output_cost_per_1k,
            timestamp=datetime.now(),
            project_id=project_id,
            task_id=task_id,
            agent_name=agent_name,
            trace_id=trace_id,
            tags=tags or {},
        )

    def calculate_cost(self) -> float:
        """Calculate total cost in USD.

        Returns:
            Total cost in USD
        """
        input_cost = (self.input_tokens / 1000.0) * self.input_cost_per_1k
        output_cost = (self.output_tokens / 1000.0) * self.output_cost_per_1k
        return input_cost + output_cost

    def input_cost(self) -> float:
        """Calculate input cost in USD.

        Returns:
            Input cost in USD
        """
        return (self.input_tokens / 1000.0) * self.input_cost_per_1k

    def output_cost(self) -> float:
        """Calculate output cost in USD.

        Returns:
            Output cost in USD
        """
        return (self.output_tokens / 1000.0) * self.output_cost_per_1k

    def cost_per_token(self) -> float:
        """Calculate average cost per token.

        Returns:
            Average cost per token in USD, or 0 if no tokens
        """
        if self.total_tokens == 0:
            return 0.0
        return self.calculate_cost() / self.total_tokens

    def is_expensive(self, threshold_usd: float = 0.10) -> bool:
        """Check if cost exceeds threshold.

        Args:
            threshold_usd: Threshold in USD (default $0.10)

        Returns:
            True if cost exceeds threshold
        """
        return self.calculate_cost() > threshold_usd

    def to_dict(self) -> Dict[str, any]:
        """Serialize cost entry to dictionary.

        Returns:
            Dictionary representation of cost entry
        """
        return {
            "id": self.id,
            "model_name": self.model_name,
            "provider": self.provider,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.total_tokens,
            "input_cost_per_1k": self.input_cost_per_1k,
            "output_cost_per_1k": self.output_cost_per_1k,
            "timestamp": self.timestamp.isoformat(),
            "project_id": self.project_id,
            "task_id": self.task_id,
            "agent_name": self.agent_name,
            "trace_id": self.trace_id,
            "tags": self.tags,
            "total_cost_usd": self.calculate_cost(),
        }


@dataclass(frozen=True)
class CostSummary:
    """Aggregated cost statistics.

    Immutable summary of costs for a time period or entity.
    """

    total_cost_usd: float
    total_input_tokens: int
    total_output_tokens: int
    total_tokens: int
    entry_count: int

    # Time period
    start_time: datetime
    end_time: datetime

    # Breakdown by model
    cost_by_model: Dict[str, float] = field(default_factory=dict)

    # Breakdown by provider
    cost_by_provider: Dict[str, float] = field(default_factory=dict)

    # Breakdown by agent (if applicable)
    cost_by_agent: Dict[str, float] = field(default_factory=dict)

    def __post_init__(self):
        """Validate cost summary data."""
        if self.entry_count < 0:
            raise ValueError(f"Entry count cannot be negative: {self.entry_count}")

        if self.total_cost_usd < 0:
            raise ValueError(f"Total cost cannot be negative: {self.total_cost_usd}")

        if self.start_time > self.end_time:
            raise ValueError("Start time cannot be after end time")

    def average_cost_per_entry(self) -> float:
        """Calculate average cost per entry.

        Returns:
            Average cost per entry in USD, or 0 if no entries
        """
        if self.entry_count == 0:
            return 0.0
        return self.total_cost_usd / self.entry_count

    def average_cost_per_token(self) -> float:
        """Calculate average cost per token.

        Returns:
            Average cost per token in USD, or 0 if no tokens
        """
        if self.total_tokens == 0:
            return 0.0
        return self.total_cost_usd / self.total_tokens

    def tokens_per_entry(self) -> float:
        """Calculate average tokens per entry.

        Returns:
            Average tokens per entry, or 0 if no entries
        """
        if self.entry_count == 0:
            return 0.0
        return self.total_tokens / self.entry_count

    def most_expensive_model(self) -> Optional[str]:
        """Get the model with highest total cost.

        Returns:
            Model name, or None if no models
        """
        if not self.cost_by_model:
            return None
        return max(self.cost_by_model.items(), key=lambda x: x[1])[0]

    def most_expensive_provider(self) -> Optional[str]:
        """Get the provider with highest total cost.

        Returns:
            Provider name, or None if no providers
        """
        if not self.cost_by_provider:
            return None
        return max(self.cost_by_provider.items(), key=lambda x: x[1])[0]
