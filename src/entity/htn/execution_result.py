"""HTN Execution Result with Auggie-Inspired Side Effect Tracking

Implements auggie's pattern of tracking:
- Side effects (files, commands, API calls)
- Timing metrics (duration, timestamp)
- Success/failure state
- Reasoning capture
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime


@dataclass
class HTNExecutionResult:
    """Result of executing an HTN node

    Inspired by auggie's session tracking (see docs/AUGGIE_VS_HTN_COMPARISON.md).
    Captures execution metadata for debugging, auditing, and cost tracking.

    Example:
        >>> result = HTNExecutionResult(
        ...     node=my_node,
        ...     success=True,
        ...     timestamp="2025-10-15T01:20:00",
        ...     duration_seconds=3.2,
        ...     output="Task completed",
        ...     side_effects={
        ...         "files_created": ["config.yml"],
        ...         "commands_run": ["pytest tests/"]
        ...     }
        ... )
    """

    # Core execution info
    node: "HTNNode"  # Forward reference
    success: bool
    timestamp: str  # ISO 8601 format
    duration_seconds: float

    # Output and errors
    output: Optional[str] = None
    error: Optional[str] = None

    # Side effects tracking (auggie pattern)
    side_effects: Dict[str, List[str]] = field(default_factory=dict)
    # Common side effect keys:
    # - "files_created": List of created file paths
    # - "files_modified": List of modified file paths
    # - "files_deleted": List of deleted file paths
    # - "commands_run": List of executed commands
    # - "apis_called": List of API endpoints called
    # - "executor_type": "auggie" | "htn_agent" | "manual"
    # - "model_used": Model identifier (e.g., "sonnet4.5")

    # Metrics
    tokens_used: Optional[int] = None
    cost_usd: Optional[float] = None

    # Reasoning (auggie pattern)
    thinking_summary: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize for session persistence

        Returns:
            Dict compatible with JSON serialization
        """
        return {
            "task_id": self.node.task_id,
            "description": self.node.description,
            "success": self.success,
            "timestamp": self.timestamp,
            "duration_seconds": self.duration_seconds,
            "output": self.output,
            "error": self.error,
            "side_effects": self.side_effects,
            "tokens_used": self.tokens_used,
            "cost_usd": self.cost_usd,
            "thinking_summary": self.thinking_summary
        }

    @staticmethod
    def from_dict(data: Dict[str, Any], node: "HTNNode") -> "HTNExecutionResult":
        """Deserialize from session JSON

        Args:
            data: Dictionary from session JSON
            node: Reconstructed HTNNode

        Returns:
            HTNExecutionResult instance
        """
        return HTNExecutionResult(
            node=node,
            success=data.get("success", False),
            timestamp=data.get("timestamp", datetime.now().isoformat()),
            duration_seconds=data.get("duration_seconds", 0.0),
            output=data.get("output"),
            error=data.get("error"),
            side_effects=data.get("side_effects", {}),
            tokens_used=data.get("tokens_used"),
            cost_usd=data.get("cost_usd"),
            thinking_summary=data.get("thinking_summary")
        )

    def __repr__(self) -> str:
        """Human-readable representation"""
        status = "✓" if self.success else "✗"
        return (
            f"HTNExecutionResult({status} {self.node.task_id}, "
            f"{self.duration_seconds:.2f}s, "
            f"{len(self.side_effects)} side effect types)"
        )
