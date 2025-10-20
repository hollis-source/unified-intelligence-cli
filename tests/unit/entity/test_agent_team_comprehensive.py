# tests/unit/entity/test_agent_team_comprehensive.py

import pytest
from src.entity.agent_team import (
    AgentTeam,
    FrontendTeam,
    BackendTeam,
    TestingTeam,
    InfrastructureTeam,
    ResearchTeam,
    OrchestrationTeam,
    QualityAssuranceTeam,
    CategoryTheoryTeam,
    DSLTeam
)
from src.entity.agent import Agent, Task

def test_agent_team_creation():
    lead = Agent(role="lead", capabilities=["manage"])
    member = Agent(role="member", capabilities=["code"])
    team = AgentTeam(
        name="Test Team",
        domain="test",
        agents=[member],
        lead_agent=lead,
        tier=2
    )
    assert team.name == "Test Team"
    assert team.domain == "test"
    assert team.agents == [member]
    assert team.lead_agent == lead
    assert team.tier == 2

def test_route_internally_default_with_lead():
    lead = Agent(role="lead", capabilities=["manage"])
    member = Agent(role="member", capabilities=["code"])
    team = AgentTeam(
        name="Team",
        domain="domain",
        agents=[member],
        lead_agent=lead
    )
    task = Task(description="some task")
    assert team.route_internally(task) == lead

def test_route_internally_default_no_lead():
    agent1 = Agent(role="member1", capabilities=["code"])
    agent2 = Agent(role="member2", capabilities=["test"])
    team = AgentTeam(
        name="Team",
        domain="domain",
        agents=[agent1, agent2]
    )
    task = Task(description="some task")
    assert team.route_internally(task) == agent1

def test_route_internally_default_empty_agents():
    team = AgentTeam(name="Empty", domain="empty", agents=[])
    task = Task(description="test")
    assert team.route_internally(task) is None

def test_get_agent_returns_agent():
    agent = Agent(role="tester", capabilities=["test"])
    team = AgentTeam(name="Test", domain="test", agents=[agent])
    found = team.get_agent("tester")
    assert found == agent

def test_get_agent_missing_role():
    agent = Agent(role="coder", capabilities=["code"])
    team = AgentTeam(name="Test", domain="test", agents=[agent])
    found = team.get_agent("tester")
    assert found is None

def test_can_handle_true():
    agent = Agent(role="coder", capabilities=["code"])
    team = AgentTeam(name="Team", domain="test", agents=[agent])
    task = Task(description="write code")
    assert team.can_handle(task) is True

def test_can_handle_false():
    agent = Agent(role="coder", capabilities=["code"])
    team = AgentTeam(name="Team", domain="test", agents=[agent])
    task = Task(description="design a building")
    assert team.can_handle(task) is False

def test_get_all_capabilities():
    agent1 = Agent(role="a", capabilities=["a", "b"])
    agent2 = Agent(role="b", capabilities=["b", "c"])
    team = AgentTeam(name="Team", domain="test", agents=[agent1, agent2])
    caps = team.get_all_capabilities()
    assert caps == ["a", "b", "c"]

def test_repr():
    agent1 = Agent(role="member1", capabilities=["code"])
    lead = Agent(role="lead", capabilities=["manage"])
    team = AgentTeam(name="Test", domain="test", agents=[agent1], lead_agent=lead)
    repr_str = repr(team)
    assert "AgentTeam('Test', domain='test', agents=['member1'] (lead: lead))" in repr_str

def test_frontend_team_design_task_routes_to_lead():
    lead = Agent(role="frontend-lead", capabilities=["design"])
    specialist = Agent(role="javascript-typescript-specialist", capabilities=["code"])
    team = FrontendTeam(
        name="Frontend",
        domain="frontend",
        agents=[specialist],
        lead_agent=lead
    )
    task = Task(description="Design the UI layout")
    assert team.route_internally(task) == lead

def test_frontend_team_implementation_task_routes_to_specialist():
    lead = Agent(role="frontend-lead", capabilities=["design"])
    specialist = Agent(role="javascript-typescript-specialist", capabilities=["code"])
    team = FrontendTeam(
        name="Frontend",
        domain="frontend",
        agents=[specialist],
        lead_agent=lead
    )
    task = Task(description="Implement the login component")
    assert team.route_internally(task) == specialist

def test_frontend_team_no_specialist_fallback_to_lead():
    lead = Agent(role="frontend-lead", capabilities=["design"])
    team = FrontendTeam(
        name="Frontend",
        domain="frontend",
        agents=[],
        lead_agent=lead
    )
    task = Task(description="Implement the login component")
    assert team.route_internally(task) == lead

def test_frontend_team_no_lead_but_has_agents():
    specialist = Agent(role="javascript-typescript-specialist", capabilities=["code"])
    team = FrontendTeam(
        name="Frontend",
        domain="frontend",
        agents=[specialist]
    )
    task = Task(description="Implement the login component")
    assert team.route_internally(task) == specialist

def test_frontend_team_empty_description_fallback():
    lead = Agent(role="frontend-lead", capabilities=["design"])
    specialist = Agent(role="javascript-typescript-specialist", capabilities=["code"])
    team = FrontendTeam(
        name="Frontend",
        domain="frontend",
        agents=[specialist],
        lead_agent=lead
    )
    task = Task(description="")
    assert team.route_internally(task) == lead

def test_backend_team_design_task_routes_to_lead():
    lead = Agent(role="backend-lead", capabilities=["api design"])
    specialist = Agent(role="python-specialist", capabilities=["code"])
    team = BackendTeam(
        name="Backend",
        domain="backend",
        agents=[specialist],
        lead_agent=lead
    )
    task = Task(description="Design API schema")
    assert team.route_internally(task) == lead

def test_backend_team_implementation_task_routes_to_specialist():
    lead = Agent(role="backend-lead", capabilities=["api design"])
    specialist = Agent(role="python-specialist", capabilities=["code"])
    team = BackendTeam(
        name="Backend",
        domain="backend",
        agents=[specialist],
        lead_agent=lead
    )
    task = Task(description="Implement user authentication function")
    assert team.route_internally(task) == specialist

def test_backend_team_no_specialist_fallback_to_lead():
    lead = Agent(role="backend-lead", capabilities=["api design"])
    team = BackendTeam(
        name="Backend",
        domain="backend",
        agents=[],
        lead_agent=lead
    )
    task = Task(description="Implement user auth")
    assert team.route_internally(task) == lead

def test_backend_team_empty_description_fallback():
    lead = Agent(role="backend-lead", capabilities=["api design"])
    specialist = Agent(role="python-specialist", capabilities=["code"])
    team = BackendTeam(
        name="Backend",
        domain="backend",
        agents=[specialist],
        lead_agent=lead
    )
    task = Task(description="")
    assert team.route_internally(task) == lead

@pytest.mark.parametrize("task_desc, expected_role", [
    ("strategy planning", "testing-lead"),
    ("unit test case", "unit-test-engineer"),
    ("integration test", "integration-test-engineer"),
    ("end-to-end test", "integration-test-engineer"),
    ("test case", "unit-test-engineer"),
    ("selenium test", "integration-test-engineer"),
    ("api test", "integration-test-engineer"),
    ("no keywords", "testing-lead")
])
def test_testing_team_routing(task_desc, expected_role):
    lead = Agent(role="testing-lead", capabilities=["strategy"])
    unit_engineer = Agent(role="unit-test-engineer", capabilities=["unit"])
    integration_engineer = Agent(role="integration-test-engineer", capabilities=["integration"])
    team = TestingTeam(
        name="Testing",
        domain="testing",
        agents=[unit_engineer, integration_engineer],
        lead_agent=lead
    )
    task = Task(description=task_desc)
    routed_agent = team.route_internally(task)
    assert routed_agent.role == expected_role

def test_testing_team_no_unit_engineer():
    lead = Agent(role="testing-lead", capabilities=["strategy"])
    integration_engineer = Agent(role="integration-test-engineer", capabilities=["integration"])
    team = TestingTeam(
        name="Testing",
        domain="testing",
        agents=[integration_engineer],
        lead_agent=lead
    )
    task = Task(description="unit test case")
    assert team.route_internally(task) == lead

def test_infrastructure_team_routes_to_lead():
    lead = Agent(role="devops-lead", capabilities=["deploy"])
    team = InfrastructureTeam(
        name="Infra",
        domain="infrastructure",
        agents=[lead],
        lead_agent=lead
    )
    task = Task(description="Deploy app")
    assert team.route_internally(task) == lead

@pytest.mark.parametrize("task_desc, expected_role", [
    ("write documentation", "technical-writer"),
    ("create tutorial", "technical-writer"),
    ("research new technology", "research-lead"),
    ("api docs", "technical-writer"),
    ("no keywords", "research-lead")
])
def test_research_team_routing(task_desc, expected_role):
    lead = Agent(role="research-lead", capabilities=["research"])
    writer = Agent(role="technical-writer", capabilities=["write"])
    team = ResearchTeam(
        name="Research",
        domain="research",
        agents=[writer],
        lead_agent=lead
    )
    task = Task(description=task_desc)
    routed_agent = team.route_internally(task)
    assert routed_agent.role == expected_role

def test_orchestration_team_routes_to_lead():
    lead = Agent(role="master-orchestrator", capabilities=["plan"])
    team = OrchestrationTeam(
        name="Orchestration",
        domain="orchestration",
        agents=[lead],
        lead_agent=lead
    )
    task = Task(description="Plan workflow")
    assert team.route_internally(task) == lead

def test_quality_assurance_team_routes_to_lead():
    lead = Agent(role="qa-lead", capabilities=["audit"])
    team = QualityAssuranceTeam(
        name="QA",
        domain="quality",
        agents=[lead],
        lead_agent=lead
    )
    task = Task(description="Code review")
    assert team.route_internally(task) == lead

@pytest.mark.parametrize("task_desc, expected_role", [
    ("functor composition", "category-theory-expert"),
    ("monad laws", "category-theory-expert"),
    ("parser design", "dsl-architect"),
    ("AST implementation", "dsl-architect"),
    ("no keywords", "category-theory-expert")
])
def test_category_theory_team_routing(task_desc, expected_role):
    expert = Agent(role="category-theory-expert", capabilities=["math"])
    architect = Agent(role="dsl-architect", capabilities=["dsl"])
    team = CategoryTheoryTeam(
        name="CategoryTheory",
        domain="category",
        agents=[architect],
        lead_agent=expert
    )
    task = Task(description=task_desc)
    routed_agent = team.route_internally(task)
    assert routed_agent.role == expected_role

@pytest.mark.parametrize("task_desc, expected_role", [
    ("deploy workflow", "dsl-task-engineer"),  # "workflow" matches impl_keywords first
    ("orchestration strategy", "dsl-deployment-specialist"),
    ("implement task", "dsl-task-engineer"),
    ("create pipeline", "dsl-task-engineer"),
    ("no keywords", "dsl-deployment-specialist")
])
def test_dsl_team_routing(task_desc, expected_role):
    specialist = Agent(role="dsl-deployment-specialist", capabilities=["deploy"])
    engineer = Agent(role="dsl-task-engineer", capabilities=["task"])
    team = DSLTeam(
        name="DSL",
        domain="dsl",
        agents=[engineer],
        lead_agent=specialist
    )
    task = Task(description=task_desc)
    routed_agent = team.route_internally(task)
    assert routed_agent.role == expected_role
