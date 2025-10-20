"""
Unit tests for Prompt Metrics Store adapters (Phase 4).
"""
import pytest
from src.interface.prompt_metrics_store import PromptMetrics
from src.adapters.db.prompt_metrics_store import NoOpPromptMetricsStore, InMemoryPromptMetricsStore


def test_noop_store_health_and_log():
    store = NoOpPromptMetricsStore()
    assert store.health() is True
    # Should not raise
    store.log(PromptMetrics(
        timestamp=PromptMetrics.now_iso(),
        domain="backend",
        agent_type="backend-developer",
        template_used=False,
        validation_score=70.0,
        specificity=60.0,
        clarity=80.0,
        completeness=True,
    ))


def test_inmemory_store_persists_records():
    store = InMemoryPromptMetricsStore()
    assert store.health() is True
    assert store.count() == 0

    m = PromptMetrics(
        timestamp=PromptMetrics.now_iso(),
        domain="frontend",
        agent_type="frontend-developer",
        template_used=True,
        validation_score=85.0,
        specificity=80.0,
        clarity=90.0,
        completeness=True,
        task_success=True,
        metadata={"notes": "ok"}
    )
    store.log(m)

    assert store.count() == 1
    last = store.last()
    assert last is not None
    assert last.domain == "frontend"
    assert last.template_used is True

