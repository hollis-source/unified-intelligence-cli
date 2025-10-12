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
    ) -> str:
        """
        Generate text response from messages.

        Args:
            messages: Conversation messages in standard format
                     [{"role": "user", "content": "Hello"}]
            config: Optional configuration object

        Returns:
            Generated text response
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