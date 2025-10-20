import asyncio
import pytest

from src.routing.rag_team_router import RAGTeamRouter
from src.entity import Task, Agent


class DummyTeam:
    def __init__(self, name: str, agents):
        self.name = name
        self.agents = agents

    def route_internally(self, task: Task):
        return self.agents[0]


class DummyDB:
    def __init__(self):
        self.calls = []

    async def store_routing_decision(self, **kwargs):
        self.calls.append(kwargs)


class DummyEmbed:
    async def embed_text(self, text: str):
        return [0.0, 0.1]


@pytest.mark.asyncio
async def test_rag_team_router_marks_rag_used_metadata():
    # Arrange: router with RAG enabled (db + embed provided)
    db = DummyDB()
    embed = DummyEmbed()
    router = RAGTeamRouter(db_store=db, embedding_pipeline=embed, use_rag=True)

    # Prepare a team and agents
    agent = Agent(role="unit-test-engineer", capabilities=["test", "pytest"], tier=2)
    team = DummyTeam("Testing", [agent])

    # Patterns retrieval will be attempted but we don't intercept it; the router
    # will still call _track_routing_decision with rag strategy if it returns any list.
    # We patch _retrieve_similar_patterns to force a non-empty list and hints.
    async def fake_retrieve(task):
        return [{"agent_role": "unit-test-engineer", "similarity": 0.9, "task_domain": "testing"}]

    router._retrieve_similar_patterns = fake_retrieve  # type: ignore

    # Act
    t = Task(description="Write unit tests", task_id="t-1")
    await router.route_with_rag(t, [team])

    # Assert
    assert db.calls, "store_routing_decision was not called"
    meta = db.calls[0].get("metadata", {})
    assert meta.get("rag_used") is True

