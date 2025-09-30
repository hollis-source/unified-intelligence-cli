"""Grok LLM adapter - Integrates GrokSession with Clean Architecture."""

import sys
import os
from typing import List, Dict, Any, Optional

# Add scripts directory to path for GrokSession
sys.path.append(os.path.join(os.path.dirname(__file__), "../../../scripts"))

from grok_session import GrokSession
from src.interfaces import IToolSupportedProvider, LLMConfig


class GrokAdapter(IToolSupportedProvider):
    """
    Adapter for Grok LLM using GrokSession.
    DIP: Implements interface, hides Grok specifics.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "grok-code-fast-1"
    ):
        """
        Initialize Grok adapter.

        Args:
            api_key: XAI API key (uses env if not provided)
            model: Grok model to use
        """
        self.session = GrokSession(
            api_key=api_key,
            model=model,
            enable_logging=False
        )

    def generate(
        self,
        messages: List[Dict[str, Any]],
        config: Optional[LLMConfig] = None
    ) -> str:
        """
        Generate text using Grok.

        Adapter pattern: Translates interface to Grok specifics.
        """
        # Convert messages to Grok format
        for msg in messages:
            if msg["role"] == "system" and not self.session.messages:
                # Set system message
                self.session.messages.append(msg)
            elif msg["role"] in ["user", "assistant"]:
                # Regular conversation
                pass

        # Get last user message
        user_messages = [m for m in messages if m["role"] == "user"]
        if not user_messages:
            return "No user message provided"

        last_user_msg = user_messages[-1]["content"]

        # Configure temperature if provided
        temperature = config.temperature if config else 0.7

        # Generate response
        result = self.session.send_message(
            user_message=last_user_msg,
            temperature=temperature,
            use_tools=False
        )

        return result["response"]

    def generate_with_tools(
        self,
        messages: List[Dict[str, Any]],
        tools: List[Dict[str, Any]],
        config: Optional[LLMConfig] = None,
        tool_functions: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate with tool support.

        Production: Full tool execution via GrokSession.

        Args:
            messages: Conversation messages
            tools: Tool definitions (OpenAI format)
            config: Optional LLM configuration
            tool_functions: Dict mapping tool names to callable functions

        Returns:
            Dict with response, tool_calls, and tool_results
        """
        # Set system message if provided
        for msg in messages:
            if msg["role"] == "system" and not self.session.messages:
                self.session.messages.append(msg)

        # Get last user message
        user_messages = [m for m in messages if m["role"] == "user"]
        if not user_messages:
            return {
                "response": "No user message",
                "tool_calls": [],
                "tool_results": []
            }

        last_user_msg = user_messages[-1]["content"]
        temperature = config.temperature if config else 0.7

        # Register custom tools and their functions
        if tools:
            for tool in tools:
                tool_name = tool["function"]["name"]
                if tool not in self.session.tools:
                    self.session.tools.append(tool)

                # Register function if provided
                if tool_functions and tool_name in tool_functions:
                    self.session.tool_functions[tool_name] = tool_functions[tool_name]

        # Generate with tools
        result = self.session.send_message(
            user_message=last_user_msg,
            temperature=temperature,
            use_tools=True
        )

        return {
            "response": result["response"],
            "tool_calls": result.get("tool_calls", []),
            "tool_results": result.get("tool_results", [])
        }

    def supports_tools(self) -> bool:
        """Grok supports tool calling."""
        return True