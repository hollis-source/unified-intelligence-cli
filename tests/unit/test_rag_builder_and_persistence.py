import asyncio
import types
import pytest

# Tests for scripts/build_rag_patterns.py guards and inference
from scripts.build_rag_patterns import PatternCollector, TaskTemplate
from pathlib import Path

# Tests for SurrealDBStore routing persistence fallback
from src.adapters.rag.surrealdb_store import SurrealDBStore


def test_select_balanced_tasks_empty_returns_empty():
    collector = PatternCollector(tasks_dir=Path("/nonexistent"), target_count=5, parallel=2, dry_run=True)
    # Pass empty list to simulate no tasks for the selected domain
    selected = collector.select_balanced_tasks([], 5)
    assert selected == []


def test_tasktemplate_domain_inference_path_and_tags():
    # Path-based inference
    t1 = TaskTemplate(Path("tasks/research/r1.yaml"), {"metadata": {"tags": []}, "prompt": ""})
    assert t1.domain == "research"

    # Tag-based inference
    t2 = TaskTemplate(Path("tasks/misc/x.yaml"), {"metadata": {"tags": ["frontend", "react"]}, "prompt": ""})
    assert t2.domain == "frontend"


@pytest.mark.asyncio
async def test_store_execution_log_classifies_when_missing(monkeypatch):
    # Monkeypatch query to capture insert vars and simulate empty routing_decisions
    captured = {}

    async def fake_query(self, sql, vars=None):
        # When called for the final INSERT, the vars dict will include 'id'
        if isinstance(sql, str) and "CREATE execution_log SET" in sql:
            captured.update(vars or {})
            # Return a trivial success
            return {"result": [{"ok": True}]}
        # For the lookup from routing_decisions, return empty result
        return [{"result": []}]

    monkeypatch.setattr(SurrealDBStore, "query", fake_query, raising=True)

    store = SurrealDBStore("ws://localhost:8000", "atado", "rag")

    # No routing_domain and no task_id -> triggers DomainClassifier fallback
    await store.store_execution_log(
        execution_id="exec-1",
        task_description="Write unit tests for login (pytest)",
        task_domain=None,
        agent_role="unit-test-engineer",
        success=True,
        status="success",
        latency_seconds=0.1,
        output_excerpt="ok",
        embedding=None,
        embedding_model="stub",
        metadata={},
    )

    # Expect routing_domain classified as 'testing'
    assert captured.get("routing_domain") == "testing"


@pytest.mark.asyncio
async def test_store_execution_log_uses_routing_decisions(monkeypatch):
    captured = {}

    async def fake_query(self, sql, vars=None):
        # First call: lookup routing_decisions -> return a row
        if isinstance(sql, str) and "SELECT task_domain, confidence FROM routing_decisions" in sql:
            return [{"result": [{"task_domain": "qa", "confidence": 0.85}]}]
        # Second call: insert execution_log -> capture vars
        if isinstance(sql, str) and "CREATE execution_log SET" in sql:
            captured.update(vars or {})
            return {"result": [{"ok": True}]}
        return [{"result": []}]

    monkeypatch.setattr(SurrealDBStore, "query", fake_query, raising=True)

    store = SurrealDBStore("ws://localhost:8000", "atado", "rag")

    await store.store_execution_log(
        execution_id="exec-2",
        task_description="Write BDD tests for login",
        task_domain=None,
        agent_role="qa-engineer",
        success=True,
        status="success",
        latency_seconds=0.2,
        output_excerpt="ok",
        embedding=None,
        embedding_model="stub",
        metadata={"task_id": "abc-123"},
    )

    assert captured.get("routing_domain") == "qa"
    assert pytest.approx(captured.get("routing_confidence"), 1e-6) == 0.85

