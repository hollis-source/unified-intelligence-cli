"""Execution-related entities for agent system."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class ExecutionStatus(Enum):
    """Status of an execution."""
    SUCCESS = "success"
    FAILURE = "failure"
    PENDING = "pending"
    RUNNING = "running"


@dataclass
class ExecutionResult:
    """
    Result of an agent execution.
    Clean Architecture: Strong typing for use case contracts.

    Enhanced with error_details for debugging (discovered via user simulation).
    """
    status: ExecutionStatus
    output: Any  # Can be str, dict, or domain-specific
    errors: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Added for debug & error visibility (Week 1)
    error_details: Optional[Dict[str, Any]] = None
    # error_details structure:
    # {
    #     "error_type": "ValidationError" | "ToolError" | "ProviderError" | "ExecutionError",
    #     "component": "validator" | "tool_name" | "provider_name" | "executor",
    #     "input": <what was provided>,
    #     "root_cause": <technical reason>,
    #     "user_message": <user-friendly explanation>,
    #     "suggestion": <actionable fix>,
    #     "context": {<additional debugging info>}
    # }

    @property
    def error(self) -> Optional[str]:
        """Get first error message (backward compatibility for Phase 3 feedback loops)."""
        return self.errors[0] if self.errors else None

    @property
    def task_id(self) -> Optional[str]:
        """Get task ID from metadata (backward compatibility for Phase 3 feedback loops)."""
        return self.metadata.get("task_id")


@dataclass
class ExecutionContext:
    """
    Context for agent execution.
    Keeps state separate from immutable Agent entity.
    """
    session_id: str
    history: List[Dict[str, Any]] = field(default_factory=list)
    llm_state: Dict[str, Any] = field(default_factory=dict)
    user_data: Dict[str, Any] = field(default_factory=dict)