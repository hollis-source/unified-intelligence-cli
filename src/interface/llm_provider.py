"""LLM Provider interfaces - ISP: Split interfaces for text generation and tools."""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class LLMConfig:
    """Configuration for LLM providers."""
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    model: Optional[str] = None
    # Provider-specific options can be added here


@dataclass
class GenerationResult:
    """
    Structured result from text generation.
    Provides content plus metadata (usage, tool calls, etc.)
    """
    content: str
    usage: Dict[str, Any]
    metadata: Optional[Dict[str, Any]] = None

    @property
    def prompt_tokens(self) -> int:
        """Get prompt tokens from usage."""
        return self.usage.get("prompt_tokens", 0)

    @property
    def completion_tokens(self) -> int:
        """Get completion tokens from usage."""
        return self.usage.get("completion_tokens", 0)

    @property
    def total_tokens(self) -> int:
        """Get total tokens from usage."""
        return self.usage.get("total_tokens", 0)


class ITextGenerator(ABC):
    """
    Core abstraction for text generation.
    ISP: Minimal interface for basic text generation needs.
    """

    @abstractmethod
    def generate(
        self,
        messages: List[Dict[str, Any]],
        config: Optional[LLMConfig] = None
    ) -> GenerationResult:
        """
        Generate text response from messages.

        Args:
            messages: Conversation messages in standard format
                     [{"role": "user", "content": "Hello"}]
            config: Optional configuration object

        Returns:
            GenerationResult containing:
                - content: Generated text response
                - usage: Token usage (prompt_tokens, completion_tokens, total_tokens)
                - metadata: Optional additional metadata (tool_calls, etc.)

        Example:
            result = provider.generate([{"role": "user", "content": "Hello"}])
            print(result.content)  # "Hello! How can I help?"
            print(result.total_tokens)  # 42
        """
        pass


class IToolSupportedProvider(ITextGenerator):
    """
    Extended interface for LLMs with tool/function support.
    ISP: Separate interface for advanced tool-using capabilities.
    """

    @abstractmethod
    def generate_with_tools(
        self,
        messages: List[Dict[str, Any]],
        tools: List[Dict[str, Any]],
        config: Optional[LLMConfig] = None
    ) -> Dict[str, Any]:
        """
        Generate response with tool/function calling capability.

        Args:
            messages: Conversation messages
            tools: Tool definitions in OpenAI format
            config: Optional configuration

        Returns:
            Dict containing:
            - response: str
            - tool_calls: List of tool calls made
            - tool_results: List of tool execution results
        """
        pass

    @abstractmethod
    def supports_tools(self) -> bool:
        """Check if this provider supports tool/function calling."""
        pass