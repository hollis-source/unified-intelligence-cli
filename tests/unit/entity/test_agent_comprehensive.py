# tests/unit/entity/test_agent_comprehensive.py
import pytest
from src.entity.agent import Agent, Task


@pytest.fixture
def sample_agent():
    return Agent(
        role="coordinator",
        capabilities=["code_gen", "test"],
        tier=3,
        parent_agent="team_lead",
        specialization="python"
    )


@pytest.fixture
def sample_task():
    return Task(
        description="Implement login feature",
        priority=2,
        task_id="task_123",
        dependencies=["task_456"]
    )


def test_agent_creation(sample_agent):
    assert sample_agent.role == "coordinator"
    assert sample_agent.capabilities == ["code_gen", "test"]
    assert sample_agent.tier == 3
    assert sample_agent.parent_agent == "team_lead"
    assert sample_agent.specialization == "python"


def test_tier_system():
    agent1 = Agent(role="low", capabilities=["low"], tier=1)
    agent2 = Agent(role="mid", capabilities=["mid"], tier=2)
    agent3 = Agent(role="high", capabilities=["high"], tier=3)
    assert agent1.tier == 1
    assert agent2.tier == 2
    assert agent3.tier == 3


def test_specialization_and_parent_agent():
    agent = Agent(role="dev", capabilities=["code"], specialization="python", parent_agent="lead")
    assert agent.specialization == "python"
    assert agent.parent_agent == "lead"


@pytest.mark.parametrize("capabilities, description, expected", [
    (["code"], "write code", True),           # Exact match (ratio=1.0)
    (["code"], "programming", False),         # Low ratio (0.133 < 0.6)
    (["code"], "test", False),                # No match
    (["frontend"], "front-end", True),        # High ratio (>0.6)
    (["ui"], "ui design", True),              # Contains exact match
    (["ui"], "user interface", False),        # Low ratio
    (["database"], "database", True),         # Exact match
    (["database"], "sql", False),             # No match
    (["test"], "testing", True),              # High ratio (0.727 > 0.6)
    (["test"], "test case", True),            # Contains exact match
    (["backend"], "server", False),           # Different words
    (["backend"], "backend server", True),    # Contains exact match
    (["ui", "database"], "database UI", True), # Multi-capability match
    (["ui", "database"], "server", False),    # No match
    ([""], "something", False),               # Empty capability
    (["something"], "", False),               # Empty description
    (["something"], " ", False),              # Whitespace only
    (["code"], "CODE", True),                 # Case insensitive
    (["code"], "Code", True),                 # Mixed case
    (["code"], "coding", False),              # Ratio=0.600 (not > 0.6)
])
def test_can_handle(capabilities, description, expected):
    agent = Agent(role="test", capabilities=capabilities)
    task = Task(description=description)
    assert agent.can_handle(task) == expected
