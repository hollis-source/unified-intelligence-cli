"""Unit tests for Agent and Task entities - TDD first approach."""

import pytest
from src.entities import Agent, Task


class TestTask:
    """Test Task entity."""

    def test_task_creation(self):
        """Task should be created with description and priority."""
        task = Task(description="Generate unit tests", priority=2)
        assert task.description == "Generate unit tests"
        assert task.priority == 2

    def test_task_default_priority(self):
        """Task should have default priority of 1."""
        task = Task(description="Review code")
        assert task.priority == 1


class TestAgent:
    """Test Agent entity - LSP compliance."""

    def test_agent_creation(self):
        """Agent should be created with role and capabilities."""
        agent = Agent(
            role="coder",
            capabilities=["code_gen", "refactor"]
        )
        assert agent.role == "coder"
        assert len(agent.capabilities) == 2

    def test_agent_can_handle_matching_task(self):
        """Agent should handle tasks matching its capabilities."""
        agent = Agent(
            role="tester",
            capabilities=["test", "validate"]
        )
        task = Task(description="Write test cases for auth module")
        assert agent.can_handle(task) is True

    def test_agent_cannot_handle_mismatched_task(self):
        """Agent should not handle tasks outside its capabilities."""
        agent = Agent(
            role="reviewer",
            capabilities=["review", "approve"]
        )
        task = Task(description="Deploy to production")
        assert agent.can_handle(task) is False

    def test_specialized_agent_substitution(self):
        """LSP: Specialized agents should substitute base seamlessly."""
        # Base agent
        base_agent = Agent(role="generic", capabilities=["analyze"])

        # Specialized coder agent (same interface)
        coder_agent = Agent(
            role="coder",
            capabilities=["code_gen", "analyze", "debug"]
        )

        # Both should handle analysis tasks
        analysis_task = Task(description="Analyze performance bottlenecks")
        assert base_agent.can_handle(analysis_task) is True
        assert coder_agent.can_handle(analysis_task) is True

        # Specialized can handle more
        coding_task = Task(description="code_gen for API endpoint")
        assert base_agent.can_handle(coding_task) is False
        assert coder_agent.can_handle(coding_task) is True