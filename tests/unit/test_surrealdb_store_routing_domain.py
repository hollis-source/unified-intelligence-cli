"""
Unit tests for SurrealDBStore.store_execution_log routing_domain fallback logic.

Tests the three-tier fallback mechanism that ensures routing_domain is always populated:
1. Tier 1: metadata["routing_domain"] or task_domain parameter
2. Tier 2: Query routing_decisions table by task_id
3. Tier 3: Classify domain from task_description using DomainClassifier
"""

import numpy as np
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.adapters.rag.surrealdb_store import SurrealDBStore


# Use only asyncio backend (trio is not installed)
pytestmark = pytest.mark.anyio


@pytest.mark.anyio
async def test_tier1_routing_domain_from_metadata():
    """
    Tier 1: routing_domain from metadata takes precedence.
    
    When metadata contains routing_domain, use it directly without fallback.
    """
    store = SurrealDBStore(url="memory", namespace="test", database="test")
    
    # Mock the query method to track what gets called
    store.query = AsyncMock()
    
    metadata = {
        "task_id": "task-123",
        "routing_domain": "frontend",  # Tier 1: Explicit routing_domain
        "routing_confidence": 0.95
    }
    
    await store.store_execution_log(
        execution_id="exec-001",
        task_description="Build React component",
        task_domain="",  # Empty, should use metadata routing_domain
        agent_role="frontend-specialist",
        team_id="Frontend",
        success=True,
        status="completed",
        latency_seconds=10.5,
        output_excerpt="Component created",
        embedding=np.random.rand(768),
        embedding_model="qwen3",
        metadata=metadata
    )
    
    # Verify query was called with frontend domain (from metadata)
    assert store.query.call_count == 1
    call_args = store.query.call_args
    params = call_args[0][1]  # Second positional arg is params dict
    
    assert params["routing_domain"] == "frontend"
    assert params["routing_confidence"] == 0.95


@pytest.mark.anyio
async def test_tier1_routing_domain_from_task_domain():
    """
    Tier 1 fallback: Use task_domain if metadata.routing_domain is empty.
    
    When metadata has no routing_domain, but task_domain is provided,
    use task_domain as Tier 1 fallback.
    """
    store = SurrealDBStore(url="memory", namespace="test", database="test")
    store.query = AsyncMock()
    
    metadata = {
        "task_id": "task-456",
        # No routing_domain in metadata
    }
    
    await store.store_execution_log(
        execution_id="exec-002",
        task_description="Write API endpoint",
        task_domain="backend",  # Tier 1 fallback: Use task_domain
        agent_role="backend-engineer",
        team_id="Backend",
        success=True,
        status="completed",
        latency_seconds=15.2,
        output_excerpt="API created",
        embedding=np.random.rand(768),
        embedding_model="qwen3",
        metadata=metadata
    )
    
    call_args = store.query.call_args
    params = call_args[0][1]
    
    assert params["routing_domain"] == "backend"


@pytest.mark.anyio
async def test_tier2_routing_domain_from_routing_decisions():
    """
    Tier 2: Query routing_decisions table when metadata and task_domain are empty.
    
    When Tier 1 sources are empty, but task_id exists in metadata,
    query routing_decisions table to backfill routing_domain.
    """
    store = SurrealDBStore(url="memory", namespace="test", database="test")
    
    # Mock two query calls:
    # 1. First call queries routing_decisions (Tier 2)
    # 2. Second call creates execution_log
    routing_decision_result = [{
        "task_domain": "testing",
        "confidence": 0.88
    }]
    
    store.query = AsyncMock(side_effect=[
        routing_decision_result,  # First call: routing_decisions query
        None  # Second call: CREATE execution_log
    ])
    
    metadata = {
        "task_id": "task-789",
        # No routing_domain (triggers Tier 2)
    }
    
    await store.store_execution_log(
        execution_id="exec-003",
        task_description="Write unit tests",
        task_domain="",  # Empty (triggers Tier 2)
        agent_role="test-engineer",
        team_id="Testing",
        success=True,
        status="completed",
        latency_seconds=8.3,
        output_excerpt="Tests written",
        embedding=np.random.rand(768),
        embedding_model="qwen3",
        metadata=metadata
    )
    
    # Verify two queries: routing_decisions lookup + execution_log creation
    assert store.query.call_count == 2
    
    # First call: routing_decisions query
    first_call = store.query.call_args_list[0]
    assert "routing_decisions" in first_call[0][0]
    assert first_call[0][1]["task_id"] == "task-789"
    
    # Second call: execution_log creation with backfilled domain
    second_call = store.query.call_args_list[1]
    params = second_call[0][1]
    assert params["routing_domain"] == "testing"
    assert params["routing_confidence"] == 0.88


@pytest.mark.anyio
async def test_tier2_routing_decisions_nested_result_format():
    """
    Tier 2: Handle nested result format from routing_decisions query.
    
    Some SurrealDB client versions return results as:
    [{"result": [{"task_domain": "...", "confidence": ...}]}]
    
    Ensure fallback logic handles both direct and nested formats.
    """
    store = SurrealDBStore(url="memory", namespace="test", database="test")
    
    # Nested result format
    routing_decision_result = [{
        "result": [{
            "task_domain": "devops",
            "confidence": 0.92
        }]
    }]
    
    store.query = AsyncMock(side_effect=[
        routing_decision_result,
        None
    ])
    
    metadata = {"task_id": "task-nested"}
    
    await store.store_execution_log(
        execution_id="exec-004",
        task_description="Configure CI/CD",
        task_domain="",
        agent_role="devops-engineer",
        team_id="Infrastructure",
        success=True,
        status="completed",
        latency_seconds=12.1,
        output_excerpt="Pipeline configured",
        embedding=np.random.rand(768),
        embedding_model="qwen3",
        metadata=metadata
    )
    
    # Verify domain was extracted from nested result
    second_call = store.query.call_args_list[1]
    params = second_call[0][1]
    assert params["routing_domain"] == "devops"
    assert params["routing_confidence"] == 0.92


@pytest.mark.anyio
async def test_tier2_routing_decisions_empty_result():
    """
    Tier 2 → Tier 3: If routing_decisions query returns empty, fall through to Tier 3.
    
    When task_id has no corresponding routing_decision, should proceed to
    Tier 3 (DomainClassifier).
    """
    store = SurrealDBStore(url="memory", namespace="test", database="test")
    
    # Mock routing_decisions returning empty (no decision found)
    store.query = AsyncMock(side_effect=[
        [],  # Empty routing_decisions result
        None  # execution_log creation
    ])
    
    metadata = {"task_id": "task-no-decision"}
    
    with patch("src.routing.domain_classifier.DomainClassifier") as mock_classifier:
        mock_instance = MagicMock()
        mock_instance.classify.return_value = "qa"  # Tier 3: Classifier returns qa
        mock_classifier.return_value = mock_instance
        
        await store.store_execution_log(
            execution_id="exec-005",
            task_description="Write acceptance tests with Gherkin",
            task_domain="",
            agent_role="qa-engineer",
            team_id="Quality Assurance",
            success=True,
            status="completed",
            latency_seconds=20.5,
            output_excerpt="Scenarios written",
            embedding=np.random.rand(768),
            embedding_model="qwen3",
            metadata=metadata
        )
    
    # Verify DomainClassifier was called (Tier 3)
    assert mock_instance.classify.call_count == 1
    
    # Verify execution_log was created with classifier domain
    second_call = store.query.call_args_list[1]
    params = second_call[0][1]
    assert params["routing_domain"] == "qa"


@pytest.mark.anyio
async def test_tier3_classifier_fallback():
    """
    Tier 3: Use DomainClassifier when all prior tiers are empty.
    
    When:
    - No metadata.routing_domain
    - No task_domain
    - No task_id (can't query routing_decisions)
    
    Then: Classify domain from task_description using DomainClassifier.
    """
    store = SurrealDBStore(url="memory", namespace="test", database="test")
    store.query = AsyncMock()
    
    with patch("src.routing.domain_classifier.DomainClassifier") as mock_classifier:
        mock_instance = MagicMock()
        mock_instance.classify.return_value = "research"
        mock_classifier.return_value = mock_instance
        
        await store.store_execution_log(
            execution_id="exec-006",
            task_description="Write architecture decision record for microservices",
            task_domain="",  # Empty
            agent_role="research-lead",
            team_id="Research",
            success=True,
            status="completed",
            latency_seconds=30.2,
            output_excerpt="ADR created",
            embedding=np.random.rand(768),
            embedding_model="qwen3",
            metadata={}  # No task_id, no routing_domain
        )
    
    # Verify classifier was called
    assert mock_instance.classify.call_count == 1
    task_arg = mock_instance.classify.call_args[0][0]
    assert task_arg.description == "Write architecture decision record for microservices"
    
    # Verify execution_log used classifier result
    params = store.query.call_args[0][1]
    assert params["routing_domain"] == "research"


@pytest.mark.anyio
async def test_tier3_classifier_exception_handling():
    """
    Tier 3 exception handling: Gracefully handle classifier failures.
    
    If DomainClassifier raises an exception, should not crash -
    just use empty routing_domain.
    """
    store = SurrealDBStore(url="memory", namespace="test", database="test")
    store.query = AsyncMock()
    
    with patch("src.routing.domain_classifier.DomainClassifier") as mock_classifier:
        mock_classifier.side_effect = Exception("Classifier unavailable")
        
        # Should not raise exception
        await store.store_execution_log(
            execution_id="exec-007",
            task_description="Some task",
            task_domain="",
            agent_role="agent",
            team_id="team",
            success=True,
            status="completed",
            latency_seconds=5.0,
            output_excerpt="output",
            embedding=np.random.rand(768),
            embedding_model="qwen3",
            metadata={}
        )
    
    # Verify execution_log was created with empty routing_domain
    params = store.query.call_args[0][1]
    assert params["routing_domain"] == ""


@pytest.mark.anyio
async def test_full_fallback_chain():
    """
    Integration test: Verify complete fallback chain Tier 1 → 2 → 3.
    
    Test scenario where:
    - Tier 1 fails (no metadata.routing_domain, no task_domain)
    - Tier 2 fails (routing_decisions query returns empty)
    - Tier 3 succeeds (DomainClassifier returns domain)
    """
    store = SurrealDBStore(url="memory", namespace="test", database="test")
    
    # Tier 2 query returns empty
    store.query = AsyncMock(side_effect=[
        [],  # routing_decisions query: empty
        None  # execution_log creation
    ])
    
    metadata = {"task_id": "task-full-fallback"}
    
    with patch("src.routing.domain_classifier.DomainClassifier") as mock_classifier:
        mock_instance = MagicMock()
        mock_instance.classify.return_value = "architecture"
        mock_classifier.return_value = mock_instance
        
        await store.store_execution_log(
            execution_id="exec-008",
            task_description="Design system architecture for distributed tracing",
            task_domain="",  # Tier 1 empty
            agent_role="architecture-lead",
            team_id="Architecture",
            success=True,
            status="completed",
            latency_seconds=45.0,
            output_excerpt="Architecture designed",
            embedding=np.random.rand(768),
            embedding_model="qwen3",
            metadata=metadata
        )
    
    # Verify full chain:
    # 1. Tier 1 failed (empty task_domain)
    # 2. Tier 2 attempted (routing_decisions query)
    assert "routing_decisions" in store.query.call_args_list[0][0][0]
    
    # 3. Tier 3 succeeded (classifier called)
    assert mock_instance.classify.call_count == 1
    
    # 4. Final result uses Tier 3 domain
    final_params = store.query.call_args_list[1][0][1]
    assert final_params["routing_domain"] == "architecture"


@pytest.mark.anyio
async def test_no_fallback_when_tier1_succeeds():
    """
    Verify Tier 2 and 3 are skipped when Tier 1 provides routing_domain.
    
    When metadata.routing_domain exists, should NOT query routing_decisions
    or call DomainClassifier.
    """
    store = SurrealDBStore(url="memory", namespace="test", database="test")
    store.query = AsyncMock()
    
    metadata = {
        "task_id": "task-123",
        "routing_domain": "frontend"  # Tier 1 succeeds
    }
    
    with patch("src.routing.domain_classifier.DomainClassifier") as mock_classifier:
        mock_instance = MagicMock()
        mock_classifier.return_value = mock_instance
        
        await store.store_execution_log(
            execution_id="exec-009",
            task_description="Build component",
            task_domain="",
            agent_role="frontend-engineer",
            team_id="Frontend",
            success=True,
            status="completed",
            latency_seconds=10.0,
            output_excerpt="Component built",
            embedding=np.random.rand(768),
            embedding_model="qwen3",
            metadata=metadata
        )
    
    # Verify only ONE query call (execution_log creation)
    # No routing_decisions query (Tier 2 skipped)
    assert store.query.call_count == 1
    assert "routing_decisions" not in store.query.call_args[0][0]
    
    # Verify classifier was NOT called (Tier 3 skipped)
    assert mock_instance.classify.call_count == 0


@pytest.mark.anyio
async def test_routing_confidence_backfilled_from_tier2():
    """
    Verify routing_confidence is also backfilled from routing_decisions (Tier 2).
    
    When routing_domain comes from routing_decisions, routing_confidence
    should also be extracted from the same row.
    """
    store = SurrealDBStore(url="memory", namespace="test", database="test")
    
    routing_decision_result = [{
        "task_domain": "security",
        "confidence": 0.97  # Should be backfilled
    }]
    
    store.query = AsyncMock(side_effect=[
        routing_decision_result,
        None
    ])
    
    metadata = {"task_id": "task-security"}
    
    await store.store_execution_log(
        execution_id="exec-010",
        task_description="Audit security vulnerabilities",
        task_domain="",
        agent_role="security-engineer",
        team_id="Backend",  # Security maps to Backend team
        success=True,
        status="completed",
        latency_seconds=25.5,
        output_excerpt="Audit complete",
        embedding=np.random.rand(768),
        embedding_model="qwen3",
        metadata=metadata
    )
    
    # Verify both domain and confidence were backfilled
    final_params = store.query.call_args_list[1][0][1]
    assert final_params["routing_domain"] == "security"
    assert final_params["routing_confidence"] == 0.97
