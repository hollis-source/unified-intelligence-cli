"""
Integration test for RAG fallback decision tracking.

Tests that when RAG pattern retrieval returns empty results:
1. Router falls back to base routing
2. Routing decision is tracked with strategy="fallback"
3. metadata.rag_used=False is persisted
4. fallback_used=True is set

Critical for A/B testing: ensures fallback decisions are observable
in routing_decisions table for source count analysis.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.entity import Task, Agent, AgentTeam
from src.routing.rag_team_router import RAGTeamRouter
from src.routing.domain_classifier import DomainClassifier


pytestmark = pytest.mark.anyio


@pytest.fixture
def mock_db_store():
    """Mock SurrealDBStore for tracking calls."""
    store = AsyncMock()
    store.store_routing_decision = AsyncMock()
    return store


@pytest.fixture
def mock_embedding_pipeline():
    """Mock EmbeddingPipeline for embedding generation."""
    pipeline = AsyncMock()
    pipeline.embed_text = AsyncMock(return_value=[0.1] * 768)
    return pipeline


@pytest.fixture
def sample_task():
    """Sample task for routing tests."""
    return Task(
        task_id="task-fallback-001",
        description="Write unit tests for authentication module",
        priority=5
    )


@pytest.fixture
def sample_teams():
    """Sample teams with agents for routing."""
    # Frontend team
    frontend_agent = Agent(
        role="frontend-specialist",
        capabilities=["React", "TypeScript"]
    )
    frontend_team = AgentTeam(
        name="Frontend",
        domain="frontend",
        agents=[frontend_agent],
        lead_agent=frontend_agent
    )

    # Testing team
    testing_agent = Agent(
        role="unit-test-engineer",
        capabilities=["pytest", "unittest"]
    )
    testing_team = AgentTeam(
        name="Testing",
        domain="testing",
        agents=[testing_agent],
        lead_agent=testing_agent
    )

    return [frontend_team, testing_team]


@pytest.mark.anyio
async def test_fallback_when_no_patterns_found(
    mock_db_store,
    mock_embedding_pipeline,
    sample_task,
    sample_teams
):
    """
    Test fallback decision tracking when pattern retrieval returns empty.
    
    Scenario:
    - RAG enabled
    - Pattern retrieval returns [] (no similar patterns)
    - Router should fallback to base routing
    - Decision should be tracked with strategy="fallback"
    """
    router = RAGTeamRouter(
        domain_classifier=DomainClassifier(),
        db_store=mock_db_store,
        embedding_pipeline=mock_embedding_pipeline,
        use_rag=True
    )
    
    # Mock _retrieve_similar_patterns to return empty list
    router._retrieve_similar_patterns = AsyncMock(return_value=[])
    
    # Route task
    agent = await router.route_with_rag(sample_task, sample_teams)
    
    # Verify routing completed (returned an agent)
    assert agent is not None
    assert isinstance(agent, Agent)
    
    # Verify store_routing_decision was called
    assert mock_db_store.store_routing_decision.called
    call_kwargs = mock_db_store.store_routing_decision.call_args[1]
    
    # Verify routing_strategy="fallback"
    assert call_kwargs["routing_strategy"] == "fallback"
    
    # Verify fallback_used=True
    assert call_kwargs["fallback_used"] is True
    
    # Verify metadata.rag_used=False
    metadata = call_kwargs["metadata"]
    assert metadata["rag_used"] is False
    
    # Verify pattern_count=0
    assert metadata["pattern_count"] == 0
    
    # Verify routing_hints is empty
    assert metadata["routing_hints"] == {}


@pytest.mark.anyio
async def test_fallback_on_pattern_retrieval_exception(
    mock_db_store,
    mock_embedding_pipeline,
    sample_task,
    sample_teams
):
    """
    Test fallback decision tracking when pattern retrieval raises exception.
    
    Scenario:
    - RAG enabled
    - Pattern retrieval raises exception (DB unavailable)
    - Router should fallback to base routing
    - Decision should be tracked with strategy="fallback"
    """
    router = RAGTeamRouter(
        domain_classifier=DomainClassifier(),
        db_store=mock_db_store,
        embedding_pipeline=mock_embedding_pipeline,
        use_rag=True
    )
    
    # Mock _retrieve_similar_patterns to raise exception
    router._retrieve_similar_patterns = AsyncMock(
        side_effect=Exception("Database connection timeout")
    )
    
    # Route task (should not raise, should fallback gracefully)
    agent = await router.route_with_rag(sample_task, sample_teams)
    
    # Verify routing completed
    assert agent is not None
    
    # Verify store_routing_decision was called with fallback strategy
    assert mock_db_store.store_routing_decision.called
    call_kwargs = mock_db_store.store_routing_decision.call_args[1]
    
    assert call_kwargs["routing_strategy"] == "fallback"
    assert call_kwargs["fallback_used"] is True
    assert call_kwargs["metadata"]["rag_used"] is False


@pytest.mark.anyio
async def test_rag_strategy_when_patterns_found(
    mock_db_store,
    mock_embedding_pipeline,
    sample_task,
    sample_teams
):
    """
    Test RAG decision tracking when patterns are found.
    
    Scenario:
    - RAG enabled
    - Pattern retrieval returns successful patterns
    - Router should use RAG routing
    - Decision should be tracked with strategy="rag"
    """
    router = RAGTeamRouter(
        domain_classifier=DomainClassifier(),
        db_store=mock_db_store,
        embedding_pipeline=mock_embedding_pipeline,
        use_rag=True
    )
    
    # Mock _retrieve_similar_patterns to return patterns
    mock_patterns = [
        {
            "agent_role": "unit-test-engineer",
            "team_id": "Testing",
            "task_domain": "testing",
            "similarity": 0.85
        },
        {
            "agent_role": "unit-test-engineer",
            "team_id": "Testing",
            "task_domain": "testing",
            "similarity": 0.78
        }
    ]
    router._retrieve_similar_patterns = AsyncMock(return_value=mock_patterns)
    
    # Route task
    agent = await router.route_with_rag(sample_task, sample_teams)
    
    # Verify routing completed
    assert agent is not None
    
    # Verify store_routing_decision was called with RAG strategy
    assert mock_db_store.store_routing_decision.called
    call_kwargs = mock_db_store.store_routing_decision.call_args[1]
    
    assert call_kwargs["routing_strategy"] == "rag"
    assert call_kwargs["fallback_used"] is False  # Not a fallback
    assert call_kwargs["metadata"]["rag_used"] is True  # RAG was used
    assert call_kwargs["metadata"]["pattern_count"] == 2


@pytest.mark.anyio
async def test_no_tracking_when_db_store_unavailable(
    mock_embedding_pipeline,
    sample_task,
    sample_teams
):
    """
    Test that routing completes even when tracking fails.
    
    Scenario:
    - RAG enabled but db_store.store_routing_decision raises exception
    - Router should complete routing without failing
    - Exception should be caught and logged
    """
    mock_db_store = AsyncMock()
    mock_db_store.store_routing_decision = AsyncMock(
        side_effect=Exception("Database write failed")
    )
    
    router = RAGTeamRouter(
        domain_classifier=DomainClassifier(),
        db_store=mock_db_store,
        embedding_pipeline=mock_embedding_pipeline,
        use_rag=True
    )
    
    # Mock empty patterns (fallback case)
    router._retrieve_similar_patterns = AsyncMock(return_value=[])
    
    # Route task (should not raise despite tracking failure)
    agent = await router.route_with_rag(sample_task, sample_teams)
    
    # Verify routing completed successfully
    assert agent is not None
    assert isinstance(agent, Agent)


@pytest.mark.anyio
async def test_fallback_decision_observable_in_db(
    mock_db_store,
    mock_embedding_pipeline,
    sample_task,
    sample_teams
):
    """
    Integration test: Verify fallback decisions are observable in database.
    
    Critical for A/B testing:
    - Baseline runs use fallback (no RAG)
    - RAG runs use fallback when no patterns found
    - Both should be tracked with strategy="fallback" and rag_used=False
    - This allows source count analysis to distinguish empty pattern scenarios
    """
    router = RAGTeamRouter(
        domain_classifier=DomainClassifier(),
        db_store=mock_db_store,
        embedding_pipeline=mock_embedding_pipeline,
        use_rag=True
    )
    
    # Mock empty patterns
    router._retrieve_similar_patterns = AsyncMock(return_value=[])
    
    # Route task
    await router.route_with_rag(sample_task, sample_teams)
    
    # Verify decision is observable in DB
    assert mock_db_store.store_routing_decision.called
    
    # Extract stored decision
    call_kwargs = mock_db_store.store_routing_decision.call_args[1]
    
    # Verify decision fields match A/B evaluator expectations
    assert "task_id" in call_kwargs
    assert "task_description" in call_kwargs
    assert "task_domain" in call_kwargs
    assert "routing_strategy" in call_kwargs
    assert "metadata" in call_kwargs
    
    # Verify fallback indicators
    assert call_kwargs["routing_strategy"] == "fallback"
    assert call_kwargs["metadata"]["rag_used"] is False
    
    # These fields allow A/B evaluator to:
    # 1. Query routing_decisions by task_description
    # 2. Extract routing_strategy for source counts
    # 3. Distinguish RAG vs baseline via rag_used flag


@pytest.mark.anyio
async def test_rag_disabled_uses_base_routing_no_tracking(
    mock_db_store,
    mock_embedding_pipeline,
    sample_task,
    sample_teams
):
    """
    Test that when use_rag=False, base routing is used without tracking.
    
    Scenario:
    - RAG disabled (use_rag=False)
    - Should use base TeamRouter.route() directly
    - Should NOT call store_routing_decision
    """
    router = RAGTeamRouter(
        domain_classifier=DomainClassifier(),
        db_store=mock_db_store,
        embedding_pipeline=mock_embedding_pipeline,
        use_rag=False  # RAG disabled
    )
    
    # Route task
    agent = await router.route_with_rag(sample_task, sample_teams)
    
    # Verify routing completed
    assert agent is not None
    
    # Verify NO tracking occurred (RAG disabled)
    assert not mock_db_store.store_routing_decision.called
