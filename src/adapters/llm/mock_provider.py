"""Mock LLM provider for testing - Adapter layer."""

from typing import List, Dict, Any, Optional
from src.interfaces import ITextGenerator, IToolSupportedProvider, LLMConfig


class MockLLMProvider(ITextGenerator):
    """
    Mock LLM provider for unit testing.
    Clean Architecture: Test double in adapter layer.
    """

    def __init__(self, default_response: str = "Mock response"):
        """Initialize with default response."""
        self.default_response = default_response
        self.call_history = []

    def generate(
        self,
        messages: List[Dict[str, Any]],
        config: Optional[LLMConfig] = None
    ) -> str:
        """
        Generate mock response.

        Testing: Records calls for verification.
        """
        self.call_history.append({
            "messages": messages,
            "config": config
        })

        # Return response based on last message
        if messages:
            last_msg = messages[-1].get("content", "")
            if "plan" in last_msg.lower():
                return "Execute tasks in order: 1, 2, 3"
            elif "code" in last_msg.lower():
                return "def hello(): return 'Hello, World!'"
            elif "test" in last_msg.lower():
                return "assert hello() == 'Hello, World!'"

        return self.default_response


class MockToolProvider(IToolSupportedProvider):
    """
    Mock tool-supported provider for testing.
    ISP: Extends basic provider with tool support.
    """

    def __init__(self):
        """Initialize mock tool provider."""
        self.call_history = []

    def generate(
        self,
        messages: List[Dict[str, Any]],
        config: Optional[LLMConfig] = None
    ) -> str:
        """Generate basic response."""
        return "Mock tool response"

    def generate_with_tools(
        self,
        messages: List[Dict[str, Any]],
        tools: List[Dict[str, Any]],
        config: Optional[LLMConfig] = None
    ) -> Dict[str, Any]:
        """
        Generate response with tool calls.

        Testing: Simulates tool execution.
        """
        self.call_history.append({
            "messages": messages,
            "tools": tools,
            "config": config
        })

        return {
            "response": "Executed tool successfully",
            "tool_calls": [{"name": "test_tool", "args": {}}],
            "tool_results": [{"output": "Tool result"}]
        }

    def supports_tools(self) -> bool:
        """Mock always supports tools."""
        return True