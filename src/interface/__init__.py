"""Abstract interfaces for dependency inversion - Clean Architecture."""

from .llm_provider import ITextGenerator, IToolSupportedProvider, LLMConfig, GenerationResult
from .agent_executor import IAgentExecutor, IAgentSelector, IAgentCoordinator
from .factory_interfaces import IAgentFactory, IProviderFactory
from .task_planner import ITaskPlanner, ExecutionPlan
from .prompt_validator import (
    IPromptValidator,
    IPromptEnhancer,
    ValidationResult,
    ValidationChecks
)

__all__ = [
    "ITextGenerator",
    "IToolSupportedProvider",
    "LLMConfig",
    "GenerationResult",
    "IAgentExecutor",
    "IAgentSelector",
    "IAgentCoordinator",
    "IAgentFactory",
    "IProviderFactory",
    "ITaskPlanner",
    "ExecutionPlan",
    "IPromptValidator",
    "IPromptEnhancer",
    "ValidationResult",
    "ValidationChecks"
]