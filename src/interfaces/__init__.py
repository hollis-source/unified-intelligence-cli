"""Abstract interfaces for dependency inversion - Clean Architecture."""

from .llm_provider import ITextGenerator, IToolSupportedProvider, LLMConfig
from .agent_executor import IAgentExecutor, IAgentSelector, IAgentCoordinator

__all__ = [
    "ITextGenerator",
    "IToolSupportedProvider",
    "LLMConfig",
    "IAgentExecutor",
    "IAgentSelector",
    "IAgentCoordinator"
]