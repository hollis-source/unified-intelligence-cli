"""Tests for AgentTool base interface."""
import pytest

from src.adapters.agent.tools.base import AgentTool


class DummyTool(AgentTool):
    name = "dummy"
    description = "A dummy tool for testing"

    @property
    def parameters(self):
        return {"type": "object", "properties": {"x": {"type": "integer"}}}

    def execute(self, **kwargs) -> str:
        x = int(kwargs.get("x", 0))
        return f"x={x}"


def test_agent_tool_contract_and_execution():
    tool = DummyTool()
    assert tool.name == "dummy"
    assert "dummy" in tool.description
    assert "properties" in tool.parameters
    assert tool.execute(x=5) == "x=5"


def test_misconfigured_tool_missing_name():
    class BadTool(AgentTool):
        # name missing
        description = "bad"

        @property
        def parameters(self):
            return {}

        def execute(self, **kwargs) -> str:
            return "ok"

    with pytest.raises(NotImplementedError):
        _ = BadTool().name

