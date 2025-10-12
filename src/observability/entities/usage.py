"""Usage tracking domain entities.

Entities for tracking API usage patterns:
- UsageEntry: Individual API call usage record
- UsageSummary: Aggregated usage statistics
- UsagePattern: Detected usage patterns and trends

All entities are immutable (frozen dataclasses) following Clean Architecture.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional
from enum import Enum
import uuid


class OperationType(str, Enum):
    """Type of LLM operation."""

    COMPLETION = "completion"
    CHAT = "chat"
    EMBEDDING = "embedding"
    FINE_TUNING = "fine_tuning"
    OTHER = "other"


@dataclass(frozen=True)
class UsageEntry:
    """Individual API call usage record.

    Immutable entity tracking a single LLM API call usage.
    Records token usage, model selection, and operation metadata.
    """

    id: str
    model_name: str  # e.g., "grok-1", "qwen3-next-80b", "meta-llama/Llama-3-8b"
    provider: str  # e.g., "x-ai", "huggingface", "openai"

    # Token usage
    input_tokens: int
    output_tokens: int
    total_tokens: int

    # Operation metadata
    operation_type: OperationType
    timestamp: datetime

    # Optional metadata
    project_id: Optional[str] = None
    task_id: Optional[str] = None
    agent_name: Optional[str] = None
    trace_id: Optional[str] = None  # Link to distributed trace

    # Performance (optional)
    duration_ms: Optional[float] = None  # Duration in milliseconds

    # Success tracking
    success: bool = True
    error_type: Optional[str] = None

    # Tags for categorization
    tags: Dict[str, str] = field(default_factory=dict)

    def __post_init__(self):
        """Validate usage entry data."""
        # Validate ID
        if not self.id or not self.id.strip():
            raise ValueError("Usage entry ID cannot be empty")

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

        # Validate duration if provided
        if self.duration_ms is not None and self.duration_ms < 0:
            raise ValueError(f"Duration cannot be negative: {self.duration_ms}")

        # Validate operation type
        if not isinstance(self.operation_type, OperationType):
            raise ValueError(f"Invalid operation type: {self.operation_type}")

    @staticmethod
    def create(
        model_name: str,
        provider: str,
        input_tokens: int,
        output_tokens: int,
        operation_type: OperationType = OperationType.COMPLETION,
        project_id: Optional[str] = None,
        task_id: Optional[str] = None,
        agent_name: Optional[str] = None,
        trace_id: Optional[str] = None,
        duration_ms: Optional[float] = None,
        success: bool = True,
        error_type: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None,
    ) -> "UsageEntry":
        """Factory method to create a usage entry with generated ID.

        Args:
            model_name: Name of the model used
            provider: Provider name (x-ai, huggingface, etc.)
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            operation_type: Type of operation (completion, chat, etc.)
            project_id: Optional project identifier
            task_id: Optional task identifier
            agent_name: Optional agent name
            trace_id: Optional trace identifier
            duration_ms: Optional duration in milliseconds
            success: Whether the operation succeeded
            error_type: Optional error type if failed
            tags: Optional metadata tags

        Returns:
            New UsageEntry with generated ID
        """
        return UsageEntry(
            id=str(uuid.uuid4()),
            model_name=model_name,
            provider=provider,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
            operation_type=operation_type,
            timestamp=datetime.now(),
            project_id=project_id,
            task_id=task_id,
            agent_name=agent_name,
            trace_id=trace_id,
            duration_ms=duration_ms,
            success=success,
            error_type=error_type,
            tags=tags or {},
        )

    def input_output_ratio(self) -> float:
        """Calculate ratio of input to output tokens.

        Returns:
            Input/output ratio, or 0 if no output tokens
        """
        if self.output_tokens == 0:
            return 0.0
        return self.input_tokens / self.output_tokens

    def tokens_per_second(self) -> float:
        """Calculate token throughput.

        Returns:
            Tokens per second, or 0 if duration not available
        """
        if self.duration_ms is None or self.duration_ms == 0:
            return 0.0
        return (self.total_tokens / self.duration_ms) * 1000.0

    def is_high_usage(self, threshold_tokens: int = 10000) -> bool:
        """Check if usage exceeds threshold.

        Args:
            threshold_tokens: Threshold in tokens (default 10,000)

        Returns:
            True if usage exceeds threshold
        """
        return self.total_tokens > threshold_tokens

    def is_efficient(self, min_tokens_per_sec: float = 100.0) -> bool:
        """Check if operation was efficient.

        Args:
            min_tokens_per_sec: Minimum tokens per second (default 100)

        Returns:
            True if tokens per second exceeds threshold, or None if duration unavailable
        """
        if self.duration_ms is None:
            return True  # Can't determine, assume efficient
        return self.tokens_per_second() >= min_tokens_per_sec

    def to_dict(self) -> Dict[str, any]:
        """Serialize usage entry to dictionary.

        Returns:
            Dictionary representation of usage entry
        """
        return {
            "id": self.id,
            "model_name": self.model_name,
            "provider": self.provider,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.total_tokens,
            "operation_type": self.operation_type.value,
            "timestamp": self.timestamp.isoformat(),
            "project_id": self.project_id,
            "task_id": self.task_id,
            "agent_name": self.agent_name,
            "trace_id": self.trace_id,
            "duration_ms": self.duration_ms,
            "success": self.success,
            "error_type": self.error_type,
            "tags": self.tags,
            "input_output_ratio": self.input_output_ratio(),
            "tokens_per_second": self.tokens_per_second() if self.duration_ms else None,
        }


@dataclass(frozen=True)
class UsageSummary:
    """Aggregated usage statistics.

    Immutable summary of usage for a time period or entity.
    """

    total_tokens: int
    total_input_tokens: int
    total_output_tokens: int
    entry_count: int
    success_count: int
    failure_count: int

    # Time period
    start_time: datetime
    end_time: datetime

    # Breakdown by model
    tokens_by_model: Dict[str, int] = field(default_factory=dict)

    # Breakdown by provider
    tokens_by_provider: Dict[str, int] = field(default_factory=dict)

    # Breakdown by agent
    tokens_by_agent: Dict[str, int] = field(default_factory=dict)

    # Breakdown by operation type
    tokens_by_operation: Dict[str, int] = field(default_factory=dict)

    # Unique counts
    unique_models: int = 0
    unique_agents: int = 0
    unique_projects: int = 0

    def __post_init__(self):
        """Validate usage summary data."""
        if self.entry_count < 0:
            raise ValueError(f"Entry count cannot be negative: {self.entry_count}")

        if self.total_tokens < 0:
            raise ValueError(f"Total tokens cannot be negative: {self.total_tokens}")

        if self.success_count < 0:
            raise ValueError(f"Success count cannot be negative: {self.success_count}")

        if self.failure_count < 0:
            raise ValueError(f"Failure count cannot be negative: {self.failure_count}")

        if self.start_time > self.end_time:
            raise ValueError("Start time cannot be after end time")

    def average_tokens_per_call(self) -> float:
        """Calculate average tokens per API call.

        Returns:
            Average tokens per call, or 0 if no calls
        """
        if self.entry_count == 0:
            return 0.0
        return self.total_tokens / self.entry_count

    def average_input_tokens(self) -> float:
        """Calculate average input tokens per call.

        Returns:
            Average input tokens, or 0 if no calls
        """
        if self.entry_count == 0:
            return 0.0
        return self.total_input_tokens / self.entry_count

    def average_output_tokens(self) -> float:
        """Calculate average output tokens per call.

        Returns:
            Average output tokens, or 0 if no calls
        """
        if self.entry_count == 0:
            return 0.0
        return self.total_output_tokens / self.entry_count

    def success_rate(self) -> float:
        """Calculate success rate.

        Returns:
            Success rate as percentage (0-100), or 0 if no calls
        """
        if self.entry_count == 0:
            return 0.0
        return (self.success_count / self.entry_count) * 100.0

    def failure_rate(self) -> float:
        """Calculate failure rate.

        Returns:
            Failure rate as percentage (0-100), or 0 if no calls
        """
        if self.entry_count == 0:
            return 0.0
        return (self.failure_count / self.entry_count) * 100.0

    def input_output_ratio(self) -> float:
        """Calculate average input/output token ratio.

        Returns:
            Input/output ratio, or 0 if no output tokens
        """
        if self.total_output_tokens == 0:
            return 0.0
        return self.total_input_tokens / self.total_output_tokens

    def most_used_model(self) -> Optional[str]:
        """Get the model with highest token usage.

        Returns:
            Model name, or None if no models
        """
        if not self.tokens_by_model:
            return None
        return max(self.tokens_by_model.items(), key=lambda x: x[1])[0]

    def most_used_provider(self) -> Optional[str]:
        """Get the provider with highest token usage.

        Returns:
            Provider name, or None if no providers
        """
        if not self.tokens_by_provider:
            return None
        return max(self.tokens_by_provider.items(), key=lambda x: x[1])[0]

    def most_active_agent(self) -> Optional[str]:
        """Get the agent with highest token usage.

        Returns:
            Agent name, or None if no agents
        """
        if not self.tokens_by_agent:
            return None
        return max(self.tokens_by_agent.items(), key=lambda x: x[1])[0]


@dataclass(frozen=True)
class UsagePattern:
    """Detected usage pattern.

    Represents an identified pattern in usage data.
    """

    pattern_type: str  # e.g., "peak_usage", "model_preference", "token_distribution"
    description: str
    confidence: float  # 0.0 to 1.0
    data: Dict[str, any] = field(default_factory=dict)
    detected_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        """Validate usage pattern data."""
        if not self.pattern_type or not self.pattern_type.strip():
            raise ValueError("Pattern type cannot be empty")

        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"Confidence must be between 0 and 1: {self.confidence}")

    def is_high_confidence(self, threshold: float = 0.75) -> bool:
        """Check if pattern has high confidence.

        Args:
            threshold: Confidence threshold (default 0.75)

        Returns:
            True if confidence exceeds threshold
        """
        return self.confidence >= threshold
