"""Abstract interfaces for dependency inversion - Clean Architecture."""

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