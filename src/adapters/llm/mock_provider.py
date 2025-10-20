"""Mock LLM provider for testing - Adapter layer."""

from typing import List, Dict, Any, Optional
from src.interface import ITextGenerator, IToolSupportedProvider, LLMConfig
from src.interface.llm_provider import GenerationResult


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
    ) -> GenerationResult:
        """
        Generate mock response.

        Testing: Records calls for verification.
        """
        self.call_history.append({
            "messages": messages,
            "config": config
        })

        # Determine response content based on last message
        content = self.default_response
        if messages:
            last_msg = messages[-1].get("content", "")
            text = str(last_msg).lower()
            if "plan" in text:
                # Return a simple JSON plan to help downstream parsers
                content = '{"task_order": ["task_1", "task_2"], "task_assignments": {"task_1": "master-orchestrator", "task_2": "unit-test-engineer"}}'
            elif "code" in text:
                content = "def hello(): return 'Hello, World!'"
            elif "test" in text:
                content = "assert hello() == 'Hello, World!'"

        return GenerationResult(
            content=content,
            usage={"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
            metadata={"provider": "mock"}
        )


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
    ) -> GenerationResult:
        """Generate basic response as GenerationResult."""
        return GenerationResult(
            content="Mock tool response",
            usage={"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
            metadata={"provider": "mock"}
        )

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