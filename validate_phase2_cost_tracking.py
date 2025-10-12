#!/usr/bin/env python3
"""Phase 2 validation script for Cost Tracking implementation.

Validates:
- CostEntry and CostSummary entities
- ICostTracker interface contract
- InMemoryCostTracker adapter implementation
- ModelPricing and PricingDatabase utilities

Uses manual testing approach due to test directory permissions.
Run with: python3 validate_phase2_cost_tracking.py
"""

import sys
from datetime import datetime, timedelta
from typing import List

# Add src to path
sys.path.insert(0, "/home/ui-cli_jake/unified-intelligence-cli")

from src.observability.entities import CostEntry, CostSummary
from src.observability.interfaces import ICostTracker
from src.observability.adapters import InMemoryCostTracker
from src.observability.pricing import (
    ModelPricing,
    PricingDatabase,
    calculate_cost,
    get_pricing_database,
)


# Test tracking
tests_passed = 0
tests_failed = 0
test_results: List[str] = []


def test(name: str):
    """Decorator to track test execution."""

    def decorator(func):
        def wrapper():
            global tests_passed, tests_failed, test_results
            try:
                func()
                tests_passed += 1
                test_results.append(f"✓ {name}")
                print(f"✓ {name}")
            except AssertionError as e:
                tests_failed += 1
                test_results.append(f"✗ {name}: {e}")
                print(f"✗ {name}: {e}")
            except Exception as e:
                tests_failed += 1
                test_results.append(f"✗ {name}: Unexpected error: {e}")
                print(f"✗ {name}: Unexpected error: {e}")

        return wrapper

    return decorator


# ============================================================================
# CostEntry Entity Tests
# ============================================================================


@test("CostEntry: Factory creates valid entry with required fields")
def test_cost_entry_factory():
    entry = CostEntry.create(
        model_name="grok-1",
        provider="x-ai",
        input_tokens=1000,
        output_tokens=500,
        input_cost_per_1k=0.005,
        output_cost_per_1k=0.015,
    )

    assert entry.model_name == "grok-1"
    assert entry.provider == "x-ai"
    assert entry.input_tokens == 1000
    assert entry.output_tokens == 500
    assert entry.total_tokens == 1500
    assert entry.input_cost_per_1k == 0.005
    assert entry.output_cost_per_1k == 0.015
    assert entry.id is not None
    assert entry.timestamp is not None
    assert entry.project_id is None


@test("CostEntry: Factory accepts optional metadata fields")
def test_cost_entry_optional_fields():
    entry = CostEntry.create(
        model_name="gpt-4",
        provider="openai",
        input_tokens=2000,
        output_tokens=1000,
        input_cost_per_1k=0.030,
        output_cost_per_1k=0.060,
        project_id="proj-123",
        task_id="task-456",
        agent_name="test-agent",
    )

    assert entry.project_id == "proj-123"
    assert entry.task_id == "task-456"
    assert entry.agent_name == "test-agent"


@test("CostEntry: Validates non-negative token counts")
def test_cost_entry_negative_tokens():
    try:
        CostEntry.create(
            model_name="grok-1",
            provider="x-ai",
            input_tokens=-100,
            output_tokens=500,
            input_cost_per_1k=0.005,
            output_cost_per_1k=0.015,
        )
        assert False, "Should raise ValueError for negative input tokens"
    except ValueError as e:
        assert "cannot be negative" in str(e).lower()


@test("CostEntry: Validates positive pricing")
def test_cost_entry_negative_pricing():
    try:
        CostEntry.create(
            model_name="grok-1",
            provider="x-ai",
            input_tokens=1000,
            output_tokens=500,
            input_cost_per_1k=-0.005,
            output_cost_per_1k=0.015,
        )
        assert False, "Should raise ValueError for negative pricing"
    except ValueError as e:
        assert "cannot be negative" in str(e).lower()


@test("CostEntry: Validates total tokens equals sum")
def test_cost_entry_total_tokens():
    try:
        entry = CostEntry(
            id="test-id",
            model_name="grok-1",
            provider="x-ai",
            input_tokens=1000,
            output_tokens=500,
            total_tokens=2000,  # Wrong total
            input_cost_per_1k=0.005,
            output_cost_per_1k=0.015,
            timestamp=datetime.now(),
        )
        assert False, "Should raise ValueError for invalid total"
    except ValueError as e:
        assert "does not match" in str(e).lower() or "total" in str(e).lower()


@test("CostEntry: Is immutable (frozen dataclass)")
def test_cost_entry_immutable():
    entry = CostEntry.create(
        model_name="grok-1",
        provider="x-ai",
        input_tokens=1000,
        output_tokens=500,
        input_cost_per_1k=0.005,
        output_cost_per_1k=0.015,
    )

    try:
        entry.input_tokens = 2000
        assert False, "Should not allow modification"
    except (AttributeError, Exception):
        pass


@test("CostEntry: Calculates cost correctly")
def test_cost_entry_calculate_cost():
    entry = CostEntry.create(
        model_name="grok-1",
        provider="x-ai",
        input_tokens=1000,
        output_tokens=500,
        input_cost_per_1k=0.005,
        output_cost_per_1k=0.015,
    )

    cost = entry.calculate_cost()
    expected = (1000 / 1000.0 * 0.005) + (500 / 1000.0 * 0.015)
    assert abs(cost - expected) < 0.0001, f"Expected {expected}, got {cost}"


@test("CostEntry: to_dict serialization includes all fields")
def test_cost_entry_to_dict():
    entry = CostEntry.create(
        model_name="grok-1",
        provider="x-ai",
        input_tokens=1000,
        output_tokens=500,
        input_cost_per_1k=0.005,
        output_cost_per_1k=0.015,
        project_id="proj-123",
    )

    data = entry.to_dict()
    assert data["model_name"] == "grok-1"
    assert data["provider"] == "x-ai"
    assert data["input_tokens"] == 1000
    assert data["output_tokens"] == 500
    assert data["total_tokens"] == 1500
    assert data["project_id"] == "proj-123"
    assert "id" in data
    assert "timestamp" in data


# ============================================================================
# InMemoryCostTracker Tests
# ============================================================================


@test("InMemoryCostTracker: Implements ICostTracker interface")
def test_tracker_implements_interface():
    tracker = InMemoryCostTracker()
    assert isinstance(tracker, ICostTracker)


@test("InMemoryCostTracker: Records cost entry")
def test_tracker_record_cost():
    tracker = InMemoryCostTracker()

    entry = CostEntry.create(
        model_name="grok-1",
        provider="x-ai",
        input_tokens=1000,
        output_tokens=500,
        input_cost_per_1k=0.005,
        output_cost_per_1k=0.015,
    )

    tracker.record_cost(entry)
    assert tracker.get_entry_count() == 1


@test("InMemoryCostTracker: Rejects invalid entry type")
def test_tracker_invalid_entry():
    tracker = InMemoryCostTracker()

    try:
        tracker.record_cost("not a cost entry")
        assert False, "Should raise ValueError for invalid type"
    except ValueError as e:
        assert "CostEntry" in str(e)


@test("InMemoryCostTracker: Gets total cost (no filters)")
def test_tracker_total_cost_no_filters():
    tracker = InMemoryCostTracker()

    # Record multiple entries
    for i in range(3):
        entry = CostEntry.create(
            model_name="grok-1",
            provider="x-ai",
            input_tokens=1000,
            output_tokens=500,
            input_cost_per_1k=0.005,
            output_cost_per_1k=0.015,
        )
        tracker.record_cost(entry)

    total = tracker.get_total_cost()
    expected = 3 * ((1000 / 1000.0 * 0.005) + (500 / 1000.0 * 0.015))
    assert abs(total - expected) < 0.0001, f"Expected {expected}, got {total}"


@test("InMemoryCostTracker: Filters by project_id")
def test_tracker_filter_project():
    tracker = InMemoryCostTracker()

    # Project A entries
    for i in range(2):
        entry = CostEntry.create(
            model_name="grok-1",
            provider="x-ai",
            input_tokens=1000,
            output_tokens=500,
            input_cost_per_1k=0.005,
            output_cost_per_1k=0.015,
            project_id="proj-a",
        )
        tracker.record_cost(entry)

    # Project B entry
    entry = CostEntry.create(
        model_name="grok-1",
        provider="x-ai",
        input_tokens=1000,
        output_tokens=500,
        input_cost_per_1k=0.005,
        output_cost_per_1k=0.015,
        project_id="proj-b",
    )
    tracker.record_cost(entry)

    cost_a = tracker.get_total_cost(project_id="proj-a")
    cost_b = tracker.get_total_cost(project_id="proj-b")
    expected = (1000 / 1000.0 * 0.005) + (500 / 1000.0 * 0.015)

    assert abs(cost_a - 2 * expected) < 0.0001
    assert abs(cost_b - expected) < 0.0001


@test("InMemoryCostTracker: Filters by model_name")
def test_tracker_filter_model():
    tracker = InMemoryCostTracker()

    # Grok entry
    entry1 = CostEntry.create(
        model_name="grok-1",
        provider="x-ai",
        input_tokens=1000,
        output_tokens=500,
        input_cost_per_1k=0.005,
        output_cost_per_1k=0.015,
    )
    tracker.record_cost(entry1)

    # GPT-4 entry
    entry2 = CostEntry.create(
        model_name="gpt-4",
        provider="openai",
        input_tokens=1000,
        output_tokens=500,
        input_cost_per_1k=0.030,
        output_cost_per_1k=0.060,
    )
    tracker.record_cost(entry2)

    cost_grok = tracker.get_total_cost(model_name="grok-1")
    cost_gpt4 = tracker.get_total_cost(model_name="gpt-4")

    assert abs(cost_grok - entry1.calculate_cost()) < 0.0001
    assert abs(cost_gpt4 - entry2.calculate_cost()) < 0.0001


@test("InMemoryCostTracker: Filters by time range")
def test_tracker_filter_time_range():
    tracker = InMemoryCostTracker()

    now = datetime.now()
    past = now - timedelta(days=1)
    future = now + timedelta(days=1)

    # Past entry
    entry_past = CostEntry(
        id="past-id",
        model_name="grok-1",
        provider="x-ai",
        input_tokens=1000,
        output_tokens=500,
        total_tokens=1500,
        input_cost_per_1k=0.005,
        output_cost_per_1k=0.015,
        timestamp=past,
    )
    tracker.record_cost(entry_past)

    # Current entry
    entry_now = CostEntry.create(
        model_name="grok-1",
        provider="x-ai",
        input_tokens=1000,
        output_tokens=500,
        input_cost_per_1k=0.005,
        output_cost_per_1k=0.015,
    )
    tracker.record_cost(entry_now)

    # Get cost after past
    cost = tracker.get_total_cost(start_time=past + timedelta(seconds=1))
    assert abs(cost - entry_now.calculate_cost()) < 0.0001


@test("InMemoryCostTracker: Cost breakdown by model")
def test_tracker_breakdown_model():
    tracker = InMemoryCostTracker()

    # Two grok entries
    for i in range(2):
        entry = CostEntry.create(
            model_name="grok-1",
            provider="x-ai",
            input_tokens=1000,
            output_tokens=500,
            input_cost_per_1k=0.005,
            output_cost_per_1k=0.015,
        )
        tracker.record_cost(entry)

    # One GPT-4 entry
    entry = CostEntry.create(
        model_name="gpt-4",
        provider="openai",
        input_tokens=1000,
        output_tokens=500,
        input_cost_per_1k=0.030,
        output_cost_per_1k=0.060,
    )
    tracker.record_cost(entry)

    breakdown = tracker.get_cost_breakdown("model")

    assert "grok-1" in breakdown
    assert "gpt-4" in breakdown
    assert breakdown["gpt-4"] > breakdown["grok-1"]  # GPT-4 is more expensive


@test("InMemoryCostTracker: Cost breakdown by provider")
def test_tracker_breakdown_provider():
    tracker = InMemoryCostTracker()

    # X.AI entry
    entry1 = CostEntry.create(
        model_name="grok-1",
        provider="x-ai",
        input_tokens=1000,
        output_tokens=500,
        input_cost_per_1k=0.005,
        output_cost_per_1k=0.015,
    )
    tracker.record_cost(entry1)

    # OpenAI entry
    entry2 = CostEntry.create(
        model_name="gpt-4",
        provider="openai",
        input_tokens=1000,
        output_tokens=500,
        input_cost_per_1k=0.030,
        output_cost_per_1k=0.060,
    )
    tracker.record_cost(entry2)

    breakdown = tracker.get_cost_breakdown("provider")

    assert "x-ai" in breakdown
    assert "openai" in breakdown


@test("InMemoryCostTracker: Gets entries with filters")
def test_tracker_get_entries():
    tracker = InMemoryCostTracker()

    # Add multiple entries
    for i in range(5):
        entry = CostEntry.create(
            model_name="grok-1",
            provider="x-ai",
            input_tokens=1000,
            output_tokens=500,
            input_cost_per_1k=0.005,
            output_cost_per_1k=0.015,
            project_id="proj-a" if i < 3 else "proj-b",
        )
        tracker.record_cost(entry)

    # Get project A entries
    entries = tracker.get_entries(project_id="proj-a")
    assert len(entries) == 3

    # Get with limit
    entries = tracker.get_entries(limit=2)
    assert len(entries) == 2


@test("InMemoryCostTracker: Gets summary with statistics")
def test_tracker_get_summary():
    tracker = InMemoryCostTracker()

    # Add entries
    for i in range(3):
        entry = CostEntry.create(
            model_name="grok-1",
            provider="x-ai",
            input_tokens=1000,
            output_tokens=500,
            input_cost_per_1k=0.005,
            output_cost_per_1k=0.015,
        )
        tracker.record_cost(entry)

    summary = tracker.get_summary()

    assert isinstance(summary, CostSummary)
    assert summary.entry_count == 3
    assert summary.total_input_tokens == 3000
    assert summary.total_output_tokens == 1500
    assert summary.total_tokens == 4500
    assert summary.total_cost_usd > 0
    assert "grok-1" in summary.cost_by_model
    assert "x-ai" in summary.cost_by_provider


@test("InMemoryCostTracker: Entry count with filters")
def test_tracker_entry_count():
    tracker = InMemoryCostTracker()

    # Add entries
    for i in range(3):
        entry = CostEntry.create(
            model_name="grok-1",
            provider="x-ai",
            input_tokens=1000,
            output_tokens=500,
            input_cost_per_1k=0.005,
            output_cost_per_1k=0.015,
            project_id="proj-a" if i < 2 else "proj-b",
        )
        tracker.record_cost(entry)

    assert tracker.get_entry_count() == 3
    assert tracker.get_entry_count(project_id="proj-a") == 2
    assert tracker.get_entry_count(project_id="proj-b") == 1


@test("InMemoryCostTracker: Deletes entries with safety check")
def test_tracker_delete_entries():
    tracker = InMemoryCostTracker()

    now = datetime.now()
    past = now - timedelta(days=2)

    # Old entry
    entry_old = CostEntry(
        id="old-id",
        model_name="grok-1",
        provider="x-ai",
        input_tokens=1000,
        output_tokens=500,
        total_tokens=1500,
        input_cost_per_1k=0.005,
        output_cost_per_1k=0.015,
        timestamp=past,
    )
    tracker.record_cost(entry_old)

    # Recent entry
    entry_new = CostEntry.create(
        model_name="grok-1",
        provider="x-ai",
        input_tokens=1000,
        output_tokens=500,
        input_cost_per_1k=0.005,
        output_cost_per_1k=0.015,
    )
    tracker.record_cost(entry_new)

    # Delete old entries
    deleted = tracker.delete_entries(before=now - timedelta(days=1))
    assert deleted == 1
    assert tracker.get_entry_count() == 1


@test("InMemoryCostTracker: Delete requires at least one filter")
def test_tracker_delete_safety():
    tracker = InMemoryCostTracker()

    try:
        tracker.delete_entries()
        assert False, "Should raise ValueError for no filters"
    except ValueError as e:
        assert "at least one filter" in str(e).lower()


# ============================================================================
# Pricing Utilities Tests
# ============================================================================


@test("ModelPricing: Calculates cost correctly")
def test_model_pricing_calculate():
    pricing = ModelPricing(
        model_name="grok-1",
        provider="x-ai",
        input_cost_per_1k=0.005,
        output_cost_per_1k=0.015,
        context_window=131072,
    )

    cost = pricing.calculate_cost(input_tokens=1000, output_tokens=500)
    expected = (1000 / 1000.0 * 0.005) + (500 / 1000.0 * 0.015)
    assert abs(cost - expected) < 0.0001


@test("PricingDatabase: Looks up model pricing")
def test_pricing_db_lookup():
    db = PricingDatabase()
    pricing = db.get_pricing("grok-1")

    assert pricing is not None
    assert pricing.model_name == "grok-1"
    assert pricing.provider == "x-ai"


@test("PricingDatabase: Returns None for unknown model")
def test_pricing_db_unknown():
    db = PricingDatabase()
    pricing = db.get_pricing("unknown-model")
    assert pricing is None


@test("PricingDatabase: Calculates cost for model")
def test_pricing_db_calculate():
    db = PricingDatabase()
    cost = db.calculate_cost("grok-1", input_tokens=1000, output_tokens=500)

    assert cost is not None
    assert cost > 0


@test("PricingDatabase: Gets all models")
def test_pricing_db_all_models():
    db = PricingDatabase()
    models = db.get_all_models()

    assert len(models) > 0
    assert "grok-1" in models
    assert "gpt-4" in models
    assert "claude-3-opus" in models


@test("PricingDatabase: Gets models by provider")
def test_pricing_db_by_provider():
    db = PricingDatabase()

    xai_models = db.get_models_by_provider("x-ai")
    assert "grok-1" in xai_models
    assert "gpt-4" not in xai_models

    openai_models = db.get_models_by_provider("openai")
    assert "gpt-4" in openai_models
    assert "grok-1" not in openai_models


@test("PricingDatabase: Adds custom pricing")
def test_pricing_db_add_custom():
    db = PricingDatabase()

    custom = ModelPricing(
        model_name="custom-model",
        provider="custom-provider",
        input_cost_per_1k=0.001,
        output_cost_per_1k=0.002,
        context_window=4096,
    )

    db.add_pricing(custom)
    retrieved = db.get_pricing("custom-model")

    assert retrieved is not None
    assert retrieved.model_name == "custom-model"


@test("PricingDatabase: Estimates cost range")
def test_pricing_db_cost_range():
    db = PricingDatabase()
    min_cost, max_cost = db.estimate_cost_range("grok-1", min_tokens=1000, max_tokens=5000)

    assert min_cost > 0
    assert max_cost > min_cost


@test("Global pricing database: calculate_cost convenience")
def test_global_calculate_cost():
    cost = calculate_cost("grok-1", input_tokens=1000, output_tokens=500)
    assert cost is not None
    assert cost > 0


@test("Global pricing database: get_pricing_database returns instance")
def test_global_get_db():
    db = get_pricing_database()
    assert isinstance(db, PricingDatabase)


# ============================================================================
# Integration Tests
# ============================================================================


@test("Integration: Multi-entry cost tracking workflow")
def test_integration_multi_entry():
    tracker = InMemoryCostTracker()

    # Simulate a project with multiple API calls
    project_id = "integration-test"

    # 3 grok calls
    for i in range(3):
        entry = CostEntry.create(
            model_name="grok-1",
            provider="x-ai",
            input_tokens=1500,
            output_tokens=750,
            input_cost_per_1k=0.005,
            output_cost_per_1k=0.015,
            project_id=project_id,
            agent_name="research-agent",
        )
        tracker.record_cost(entry)

    # 2 GPT-4 calls
    for i in range(2):
        entry = CostEntry.create(
            model_name="gpt-4",
            provider="openai",
            input_tokens=2000,
            output_tokens=1000,
            input_cost_per_1k=0.030,
            output_cost_per_1k=0.060,
            project_id=project_id,
            agent_name="backend-agent",
        )
        tracker.record_cost(entry)

    # Verify totals
    summary = tracker.get_summary(project_id=project_id)
    assert summary.entry_count == 5
    assert summary.total_input_tokens == (3 * 1500) + (2 * 2000)
    assert summary.total_output_tokens == (3 * 750) + (2 * 1000)

    # Verify breakdowns
    model_breakdown = tracker.get_cost_breakdown("model", project_id=project_id)
    assert len(model_breakdown) == 2
    assert "grok-1" in model_breakdown
    assert "gpt-4" in model_breakdown


@test("Integration: Cost aggregation accuracy")
def test_integration_aggregation_accuracy():
    tracker = InMemoryCostTracker()

    # Add known entries
    entry1 = CostEntry.create(
        model_name="grok-1",
        provider="x-ai",
        input_tokens=1000,
        output_tokens=500,
        input_cost_per_1k=0.005,
        output_cost_per_1k=0.015,
    )
    tracker.record_cost(entry1)

    entry2 = CostEntry.create(
        model_name="grok-1",
        provider="x-ai",
        input_tokens=2000,
        output_tokens=1000,
        input_cost_per_1k=0.005,
        output_cost_per_1k=0.015,
    )
    tracker.record_cost(entry2)

    # Verify exact cost calculation
    expected_total = entry1.calculate_cost() + entry2.calculate_cost()
    actual_total = tracker.get_total_cost()

    assert abs(actual_total - expected_total) < 0.0001


@test("Integration: Filter combinations")
def test_integration_filter_combinations():
    tracker = InMemoryCostTracker()

    now = datetime.now()

    # Add varied entries
    entry1 = CostEntry.create(
        model_name="grok-1",
        provider="x-ai",
        input_tokens=1000,
        output_tokens=500,
        input_cost_per_1k=0.005,
        output_cost_per_1k=0.015,
        project_id="proj-a",
        agent_name="agent-1",
    )
    tracker.record_cost(entry1)

    entry2 = CostEntry.create(
        model_name="gpt-4",
        provider="openai",
        input_tokens=1000,
        output_tokens=500,
        input_cost_per_1k=0.030,
        output_cost_per_1k=0.060,
        project_id="proj-a",
        agent_name="agent-2",
    )
    tracker.record_cost(entry2)

    entry3 = CostEntry.create(
        model_name="grok-1",
        provider="x-ai",
        input_tokens=1000,
        output_tokens=500,
        input_cost_per_1k=0.005,
        output_cost_per_1k=0.015,
        project_id="proj-b",
        agent_name="agent-1",
    )
    tracker.record_cost(entry3)

    # Test multiple filter combinations
    cost1 = tracker.get_total_cost(project_id="proj-a", agent_name="agent-1")
    assert abs(cost1 - entry1.calculate_cost()) < 0.0001

    cost2 = tracker.get_total_cost(project_id="proj-a", model_name="gpt-4")
    assert abs(cost2 - entry2.calculate_cost()) < 0.0001

    cost3 = tracker.get_total_cost(model_name="grok-1")
    expected = entry1.calculate_cost() + entry3.calculate_cost()
    assert abs(cost3 - expected) < 0.0001


@test("Integration: Real-world usage scenario")
def test_integration_real_world():
    tracker = InMemoryCostTracker()
    db = get_pricing_database()

    project_id = "real-world-test"

    # Simulate a multi-agent research task
    # Research agent uses Grok for initial research
    grok_pricing = db.get_pricing("grok-1")
    for i in range(5):
        entry = CostEntry.create(
            model_name=grok_pricing.model_name,
            provider=grok_pricing.provider,
            input_tokens=2000,
            output_tokens=1000,
            input_cost_per_1k=grok_pricing.input_cost_per_1k,
            output_cost_per_1k=grok_pricing.output_cost_per_1k,
            project_id=project_id,
            agent_name="research-agent",
            task_id="research-task",
        )
        tracker.record_cost(entry)

    # Backend agent uses GPT-4 for code generation
    gpt4_pricing = db.get_pricing("gpt-4")
    for i in range(3):
        entry = CostEntry.create(
            model_name=gpt4_pricing.model_name,
            provider=gpt4_pricing.provider,
            input_tokens=3000,
            output_tokens=1500,
            input_cost_per_1k=gpt4_pricing.input_cost_per_1k,
            output_cost_per_1k=gpt4_pricing.output_cost_per_1k,
            project_id=project_id,
            agent_name="backend-agent",
            task_id="code-gen-task",
        )
        tracker.record_cost(entry)

    # Get project summary
    summary = tracker.get_summary(project_id=project_id)

    assert summary.entry_count == 8
    assert summary.total_cost_usd > 0

    # Verify breakdowns
    assert len(summary.cost_by_model) == 2
    assert len(summary.cost_by_provider) == 2
    assert len(summary.cost_by_agent) == 2

    # Get cost by task
    task_breakdown = tracker.get_cost_breakdown("task", project_id=project_id)
    assert "research-task" in task_breakdown
    assert "code-gen-task" in task_breakdown


@test("Integration: Empty tracker returns sensible defaults")
def test_integration_empty_tracker():
    tracker = InMemoryCostTracker()

    assert tracker.get_total_cost() == 0.0
    assert tracker.get_entry_count() == 0

    summary = tracker.get_summary()
    assert summary.total_cost_usd == 0.0
    assert summary.entry_count == 0


# ============================================================================
# Main Execution
# ============================================================================


def main():
    print("=" * 70)
    print("Phase 2 Validation: Cost Tracking")
    print("=" * 70)
    print()

    # Run all tests
    print("Running CostEntry Entity Tests...")
    test_cost_entry_factory()
    test_cost_entry_optional_fields()
    test_cost_entry_negative_tokens()
    test_cost_entry_negative_pricing()
    test_cost_entry_total_tokens()
    test_cost_entry_immutable()
    test_cost_entry_calculate_cost()
    test_cost_entry_to_dict()

    print("\nRunning InMemoryCostTracker Tests...")
    test_tracker_implements_interface()
    test_tracker_record_cost()
    test_tracker_invalid_entry()
    test_tracker_total_cost_no_filters()
    test_tracker_filter_project()
    test_tracker_filter_model()
    test_tracker_filter_time_range()
    test_tracker_breakdown_model()
    test_tracker_breakdown_provider()
    test_tracker_get_entries()
    test_tracker_get_summary()
    test_tracker_entry_count()
    test_tracker_delete_entries()
    test_tracker_delete_safety()

    print("\nRunning Pricing Utilities Tests...")
    test_model_pricing_calculate()
    test_pricing_db_lookup()
    test_pricing_db_unknown()
    test_pricing_db_calculate()
    test_pricing_db_all_models()
    test_pricing_db_by_provider()
    test_pricing_db_add_custom()
    test_pricing_db_cost_range()
    test_global_calculate_cost()
    test_global_get_db()

    print("\nRunning Integration Tests...")
    test_integration_multi_entry()
    test_integration_aggregation_accuracy()
    test_integration_filter_combinations()
    test_integration_real_world()
    test_integration_empty_tracker()

    # Print summary
    print()
    print("=" * 70)
    print("Validation Summary")
    print("=" * 70)
    print(f"Tests Passed: {tests_passed}")
    print(f"Tests Failed: {tests_failed}")
    print(f"Total Tests:  {tests_passed + tests_failed}")
    print(f"Success Rate: {100 * tests_passed / (tests_passed + tests_failed):.1f}%")
    print()

    if tests_failed > 0:
        print("Failed Tests:")
        for result in test_results:
            if result.startswith("✗"):
                print(f"  {result}")
        print()
        sys.exit(1)
    else:
        print("✅ All Phase 2 validation tests passed!")
        print()
        print("Phase 2 (Cost Tracking) Status: VALIDATED ✓")
        print()
        sys.exit(0)


if __name__ == "__main__":
    main()
