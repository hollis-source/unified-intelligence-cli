from unittest.mock import AsyncMock

from src.routing.tracking_router import TrackingTeamRouter
from src.routing.domain_classifier import DomainClassifier
from src.routing.team_router import TeamRouter


class DummyAgent:
    def __init__(self, role: str):
        self.role = role


class DummyTeam:
    def __init__(self, name: str, agents):
        self.name = name
        self.domain = "testing"
        self.agents = agents
    def route_internally(self, task):
        # Deterministic: pick second agent
        return self.agents[1]


def test_tracking_router_persists_baseline_decision(monkeypatch):
    # Mock db store with async method
    mock_store = AsyncMock()

    # Router under test
    router = TrackingTeamRouter(domain_classifier=DomainClassifier(), db_store=mock_store)

    # Build teams and a task
    agents = [DummyAgent("dev"), DummyAgent("tester")]
    team = DummyTeam("Engineering", agents)

    class DummyTask:
        def __init__(self):
            self.description = "Implement feature X"
            self.task_id = "t-123"

    task = DummyTask()

    # Force base TeamRouter to select our dummy team
    monkeypatch.setattr(TeamRouter, "_select_team", lambda self, t, ts: team, raising=True)

    # Call route; TrackingTeamRouter should store decision
    agent = router.route(task, [team])
    assert agent is agents[1]

    # Ensure async store called once with baseline strategy and rag_used False
    assert mock_store.store_routing_decision.await_count == 1
    kwargs = mock_store.store_routing_decision.await_args.kwargs
    assert kwargs.get("routing_strategy") == "baseline"
    meta = kwargs.get("metadata") or {}
    assert meta.get("rag_used") is False

