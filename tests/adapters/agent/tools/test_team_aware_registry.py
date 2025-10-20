"""Tests for TeamAwareToolRegistry with team-based tool filtering."""
from __future__ import annotations

import logging

from src.adapters.agent.tools.base import AgentTool
from src.adapters.agent.tools.registry import ToolRegistry
from src.adapters.agent.tools.team_aware_registry import TeamAwareToolRegistry


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


def make_base_registry() -> ToolRegistry:
    reg = ToolRegistry()
    reg.register(T1())
    reg.register(T2())
    return reg


def test_filtering_by_team_and_policy_enforcement(caplog):
    base = make_base_registry()
    policies = {"Testing": ["t1"], "Frontend": ["t2"]}
    reg = TeamAwareToolRegistry(base, team_policies=policies)

    # Allowed tool
    tool = reg.get_tool("t1", team_name="Testing")
    assert tool is not None
    assert tool.execute() == "ok1"

    # Disallowed tool returns None and logs warning
    caplog.set_level(logging.WARNING)
    tool2 = reg.get_tool("t2", team_name="Testing")
    assert tool2 is None
    assert any("policy_denied" in rec.message or getattr(rec, "extra_fields", {}).get("event") == "policy_denied" for rec in caplog.records)

    # Other team allowed different tool
    tool2b = reg.get_tool("t2", team_name="Frontend")
    assert tool2b is not None
    assert tool2b.execute(a="x") == "a=x"


def test_get_tool_descriptions_filtered():
    base = make_base_registry()
    policies = {"Testing": ["t1"]}
    reg = TeamAwareToolRegistry(base, team_policies=policies)

    desc = reg.get_tool_descriptions(team_name="Testing")
    assert "Tool: t1" in desc
    assert "Tool: t2" not in desc


def test_unknown_team_secure_by_default(caplog):
    base = make_base_registry()
    reg = TeamAwareToolRegistry(base, team_policies={})  # No teams defined

    caplog.set_level(logging.WARNING)
    tool = reg.get_tool("t1", team_name="UnknownTeam")
    assert tool is None
    # Should log unknown_team event
    assert any("unknown_team" in rec.message or getattr(rec, "extra_fields", {}).get("event") == "unknown_team" for rec in caplog.records)

    # Descriptions empty
    assert reg.get_tool_descriptions(team_name="UnknownTeam") == ""


def test_unknown_tool_handling_logs(caplog):
    base = make_base_registry()
    # Policy includes non-existent tool t3
    policies = {"Testing": ["t1", "t3"]}
    reg = TeamAwareToolRegistry(base, team_policies=policies)

    caplog.set_level(logging.WARNING)

    # Request explicitly unknown but allowed-by-policy tool
    t = reg.get_tool("t3", team_name="Testing")
    assert t is None
    assert any("unknown_tool" in rec.message or getattr(rec, "extra_fields", {}).get("event") == "unknown_tool" for rec in caplog.records)

    # Descriptions should warn and skip missing tool
    desc = reg.get_tool_descriptions(team_name="Testing")
    assert "Tool: t1" in desc
    assert "Tool: t3" not in desc
    assert any("missing_base_tool" in rec.message or getattr(rec, "extra_fields", {}).get("event") == "missing_base_tool" for rec in caplog.records)


def test_backward_compatibility_base_registry_unchanged():
    base = make_base_registry()
    # Base registry still works with all tools
    assert sorted(base.list_tools()) == ["t1", "t2"]
    assert base.get_tool("t1").execute() == "ok1"
    assert base.get_tool("t2").execute(a="y") == "a=y"

    # Team-aware wrapper can mimic base when policy allows all
    reg = TeamAwareToolRegistry(base, team_policies={"All": ["t1", "t2"]}, default_team_name="All")
    assert reg.list_allowed_tools() == ["t1", "t2"]
    assert reg.get_tool("t1").execute() == "ok1"  # uses default team
    assert reg.get_tool("t2").execute(a="z") == "a=z"


def test_is_tool_allowed_and_default_team():
    base = make_base_registry()
    policies = {"QA": ["t1"]}
    reg = TeamAwareToolRegistry(base, team_policies=policies, default_team_name="QA")

    assert reg.is_tool_allowed("t1") is True  # default team
    assert reg.is_tool_allowed("t2") is False
    assert reg.list_allowed_tools() == ["t1"]

    # Explicit team still works
    assert reg.is_tool_allowed("t1", team_name="QA") is True
    assert reg.is_tool_allowed("t1", team_name="Other") is False

