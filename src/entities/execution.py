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
    """
    status: ExecutionStatus
    output: Any  # Can be str, dict, or domain-specific
    errors: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


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