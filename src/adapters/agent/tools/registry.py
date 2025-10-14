"""Tool registry for agent tool-use (adapter layer)."""
from __future__ import annotations

from typing import Dict, Optional, List

from .base import AgentTool


class ToolRegistry:
    """Manages available tools for agents.

    - register(tool): add or replace tool by name
    - get_tool(name): retrieve tool instance
    - list_tools(): list names
    - get_tool_descriptions(): formatted descriptions for LLM context
    """

    def __init__(self) -> None:
        self._tools: Dict[str, AgentTool] = {}

    def register(self, tool: AgentTool) -> None:
        if not isinstance(tool, AgentTool):  # Defensive programming
            raise TypeError("tool must implement AgentTool")
        self._tools[tool.name] = tool

    def get_tool(self, name: str) -> Optional[AgentTool]:
        return self._tools.get(name)

    def list_tools(self) -> List[str]:
        return sorted(self._tools.keys())

    def get_tool_descriptions(self) -> str:
        parts: List[str] = []
        for tool in self._tools.values():
            parts.append(
                f"Tool: {tool.name}\n"
                f"Description: {tool.description}\n"
                f"Parameters: {tool.parameters}\n"
            )
        return "\n".join(parts)

