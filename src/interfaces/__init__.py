"""Abstract interfaces for dependency inversion - Clean Architecture.

DEPRECATED: This module location (src.interfaces) is deprecated.
Use src.interface instead. This compatibility shim will be removed in a future version.
"""

import warnings
warnings.warn(
    "Module 'src.interfaces' is deprecated, use 'src.interface' instead",
    DeprecationWarning,
    stacklevel=2
)
from typing import Protocol, Dict, Any
from dataclasses import dataclass, field


class ProjectState(Protocol):
    project_id: str
    htn_graph: Any
    world_state: Dict[str, Any]
    task_status: Dict[str, Any]

    def copy(self) -> "ProjectState": ...


@dataclass
class ExecutionResult:
    task_id: str
    success: bool
    effects: Dict[str, Any]
    error: str
    metadata: Dict[str, Any] = field(default_factory=dict)


from src.entities.task_model.task_model import TaskStatus


from .llm_provider import ITextGenerator, IToolSupportedProvider, LLMConfig
from .agent_executor import IAgentExecutor, IAgentSelector, IAgentCoordinator
from .factory_interfaces import IAgentFactory, IProviderFactory
from .task_planner import ITaskPlanner, ExecutionPlan

__all__ = [
    "ProjectState",
    "ExecutionResult",
    "TaskStatus",
    "ITextGenerator",
    "IToolSupportedProvider",
    "LLMConfig",
    "IAgentExecutor",
    "IAgentSelector",
    "IAgentCoordinator",
    "IAgentFactory",
    "IProviderFactory",
    "ITaskPlanner",
    "ExecutionPlan"
]