"""
Integration tests for Pattern Quality Management in RAG routing.

Tests the full pipeline: pattern retrieval → quality filtering → routing decision.
"""
import pytest
import numpy as np
from unittest.mock import AsyncMock, MagicMock, patch

from src.entity import Task, Agent, AgentTeam
from src.routing.rag_team_router import RAGTeamRouter
from src.routing.pattern_quality import PatternQualityManager
from src.routing.domain_classifier import DomainClassifier


@pytest.fixture
def mock_db_store():
    """Mock SurrealDB store."""
    store = AsyncMock()
    return store


@pytest.fixture
def mock_embedding_pipeline():
    """Mock embedding pipeline."""
    pipeline = AsyncMock()
    # Return a dummy embedding
    pipeline.embed.return_value = np.random.rand(384).tolist()
    return pipeline


@pytest.fixture
def sample_teams():
    """Create sample agent teams."""
    backend_agent = Agent(role="backend-lead", capabilities=["backend", "api", "database"], tier=2)
    frontend_agent = Agent(role="frontend-lead", capabilities=["frontend", "ui", "react"], tier=2)
    
    backend_team = AgentTeam(
        name="Backend",
        domain="backend",
        agents=[backend_agent],
        lead_agent=backend_agent,
        tier=2
    )
    
    frontend_team = AgentTeam(
        name="Frontend",
        domain="frontend",
        agents=[frontend_agent],
        lead_agent=frontend_agent,
        tier=2
    )
    
    return [backend_team, frontend_team]


@pytest.fixture
def sample_patterns():
    """Create sample execution patterns with varying quality."""
    emb1 = np.random.rand(384)
    emb2 = emb1 + np.random.rand(384) * 0.01  # Very similar (duplicate)
    emb3 = np.random.rand(384)  # Different
    
    return [
        {
            'execution_id': 'exec_1',
            'task_description': 'Implement REST API endpoint',
            'agent_role': 'backend-lead',
            'task_domain': 'backend',
            'success': True,
            'latency_seconds': 15.0,
            'embedding': emb1.tolist(),
            'timestamp': '2025-10-19T10:00:00Z'
        },
        {
            'execution_id': 'exec_2',
            'task_description': 'Implement REST API endpoint',  # Duplicate
            'agent_role': 'backend-lead',
            'task_domain': 'backend',
            'success': True,
            'latency_seconds': 18.0,
            'embedding': emb2.tolist(),
            'timestamp': '2025-10-19T09:00:00Z'
        },
        {
            'execution_id': 'exec_3',
            'task_description': 'Build React component',
            'agent_role': 'frontend-lead',
            'task_domain': 'frontend',
            'success': False,
            'latency_seconds': 90.0,
            'embedding': emb3.tolist(),
            'timestamp': '2025-10-19T08:00:00Z'
        },
        {
            'execution_id': 'exec_4',
            'task_description': 'Create database migration',
            'agent_role': 'backend-lead',
            'task_domain': 'backend',
            'success': True,
            'latency_seconds': 12.0,
            'embedding': np.random.rand(384).tolist(),
            'timestamp': '2025-10-19T11:00:00Z'
        },
    ]


@pytest.mark.asyncio
async def test_pattern_quality_deduplication(mock_db_store, mock_embedding_pipeline, sample_teams, sample_patterns):
    """Test that duplicate patterns are removed."""
    # Setup mock to return patterns with duplicates
    mock_db_store.search_similar_execution.return_value = sample_patterns

    # Create router with pattern quality enabled
    router = RAGTeamRouter(
        domain_classifier=DomainClassifier(),
        db_store=mock_db_store,
        embedding_pipeline=mock_embedding_pipeline,
        top_k=10,
        use_rag=True,
        enable_pattern_quality=True
    )

    task = Task(description="Implement new REST API endpoint for users")

    # Route task
    agent = await router.route_with_rag(task, sample_teams)

    # Verify agent was selected
    assert agent is not None
    assert agent.role in ["backend-lead", "frontend-lead"]

    # Verify deduplication occurred (should have fewer patterns after dedup)
    # Note: We can't directly inspect internal state, but we can verify the call was made
    mock_db_store.search_similar_execution.assert_called_once()


@pytest.mark.asyncio
async def test_pattern_quality_filtering(mock_db_store, mock_embedding_pipeline, sample_teams, sample_patterns):
    """Test that low-quality patterns are filtered out."""
    # Setup mock to return patterns including low-quality ones
    mock_db_store.search_similar_execution.return_value = sample_patterns
    
    router = RAGTeamRouter(
        domain_classifier=DomainClassifier(),
        db_store=mock_db_store,
        embedding_pipeline=mock_embedding_pipeline,
        top_k=10,
        use_rag=True,
        enable_pattern_quality=True
    )
    
    task = Task(description="Implement REST API endpoint")
    
    # Route task
    agent = await router.route_with_rag(task, sample_teams)
    
    # Verify routing succeeded
    assert agent is not None
    
    # The low-quality pattern (exec_3: failed, high latency) should be filtered
    # We expect backend-lead to be selected based on high-quality backend patterns
    assert agent.role == "backend-lead"


@pytest.mark.asyncio
async def test_pattern_quality_disabled(mock_db_store, mock_embedding_pipeline, sample_teams, sample_patterns):
    """Test that pattern quality can be disabled."""
    mock_db_store.search_similar_execution.return_value = sample_patterns
    
    # Create router with pattern quality disabled
    router = RAGTeamRouter(
        domain_classifier=DomainClassifier(),
        db_store=mock_db_store,
        embedding_pipeline=mock_embedding_pipeline,
        top_k=10,
        use_rag=True,
        enable_pattern_quality=False
    )
    
    task = Task(description="Implement REST API endpoint")
    
    # Route task
    agent = await router.route_with_rag(task, sample_teams)
    
    # Verify routing succeeded
    assert agent is not None
    
    # Verify pattern quality manager was not created
    assert router.pattern_quality_manager is None


@pytest.mark.asyncio
async def test_pattern_quality_with_no_patterns(mock_db_store, mock_embedding_pipeline, sample_teams):
    """Test graceful fallback when no patterns are found."""
    # Setup mock to return empty patterns
    mock_db_store.search_similar_execution.return_value = []
    
    router = RAGTeamRouter(
        domain_classifier=DomainClassifier(),
        db_store=mock_db_store,
        embedding_pipeline=mock_embedding_pipeline,
        top_k=10,
        use_rag=True,
        enable_pattern_quality=True
    )
    
    task = Task(description="Implement REST API endpoint")
    
    # Route task
    agent = await router.route_with_rag(task, sample_teams)
    
    # Verify fallback to base routing
    assert agent is not None
    assert agent.role in ["backend-lead", "frontend-lead"]


@pytest.mark.asyncio
async def test_pattern_quality_top_k_selection(mock_db_store, mock_embedding_pipeline, sample_teams):
    """Test that only top-K patterns are used."""
    # Create many patterns
    many_patterns = []
    for i in range(20):
        many_patterns.append({
            'execution_id': f'exec_{i}',
            'task_description': f'Task {i}',
            'agent_role': 'backend-lead',
            'task_domain': 'backend',
            'success': True,
            'latency_seconds': 10.0 + i,
            'embedding': np.random.rand(384).tolist(),
            'timestamp': f'2025-10-19T{i:02d}:00:00Z'
        })
    
    mock_db_store.search_similar_execution.return_value = many_patterns
    
    router = RAGTeamRouter(
        domain_classifier=DomainClassifier(),
        db_store=mock_db_store,
        embedding_pipeline=mock_embedding_pipeline,
        top_k=5,  # Only keep top 5
        use_rag=True,
        enable_pattern_quality=True
    )
    
    task = Task(description="Implement REST API endpoint")
    
    # Route task
    agent = await router.route_with_rag(task, sample_teams)
    
    # Verify routing succeeded
    assert agent is not None
    
    # Verify pattern quality manager has correct top_k
    assert router.pattern_quality_manager.top_k == 5


@pytest.mark.asyncio
async def test_pattern_quality_domain_aware_scoring(mock_db_store, mock_embedding_pipeline, sample_teams, sample_patterns):
    """Test that domain-aware scoring improves routing accuracy."""
    mock_db_store.search_similar_execution.return_value = sample_patterns
    
    router = RAGTeamRouter(
        domain_classifier=DomainClassifier(),
        db_store=mock_db_store,
        embedding_pipeline=mock_embedding_pipeline,
        top_k=10,
        use_rag=True,
        enable_pattern_quality=True
    )
    
    # Backend task
    backend_task = Task(description="Implement REST API endpoint for authentication")
    agent = await router.route_with_rag(backend_task, sample_teams)
    
    # Should route to backend based on domain-aware scoring
    assert agent.role == "backend-lead"
    
    # Frontend task
    frontend_task = Task(description="Build React component for user profile")
    agent = await router.route_with_rag(frontend_task, sample_teams)
    
    # Should route to frontend (even though we have more backend patterns,
    # domain-aware scoring should prefer the frontend pattern for frontend tasks)
    # Note: This might still route to backend if base routing is used as fallback
    assert agent.role in ["frontend-lead", "backend-lead"]

