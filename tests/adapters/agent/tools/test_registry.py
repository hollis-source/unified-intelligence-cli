"""Tests for the ToolRegistry."""
from src.adapters.agent.tools.registry import ToolRegistry
from src.adapters.agent.tools.base import AgentTool


class T1(AgentTool):
    name = "t1"
    description = "tool one"

    @property
    def parameters(self):
        return {"type": "object", "properties": {}}

    def execute(self, **kwargs) -> str:
        return "ok1"


class T2(AgentTool):
    name = "t2"
    description = "tool two"

    @property
    def parameters(self):
        return {"type": "object", "properties": {"a": {"type": "string"}}}

    def execute(self, **kwargs) -> str:
        return f"a={kwargs.get('a')}"


def test_register_and_get_tools_and_descriptions():
    reg = ToolRegistry()
    reg.register(T1())
    reg.register(T2())

    assert reg.get_tool("t1").execute() == "ok1"
    assert reg.get_tool("t2").execute(a="x") == "a=x"

    desc = reg.get_tool_descriptions()
    assert "Tool: t1" in desc
    assert "Tool: t2" in desc
    assert "Parameters:" in desc

