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

from .llm_provider import ITextGenerator, IToolSupportedProvider, LLMConfig
from .agent_executor import IAgentExecutor, IAgentSelector, IAgentCoordinator
from .factory_interfaces import IAgentFactory, IProviderFactory
from .task_planner import ITaskPlanner, ExecutionPlan

__all__ = [
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