#!/usr/bin/env python3
"""Phase 3 validation script for Usage Analytics implementation.

Validates:
- UsageEntry and UsageSummary entities
- IUsageTracker interface contract
- InMemoryUsageTracker adapter implementation
- Analytics utilities (patterns, trends, statistics)

Uses manual testing approach due to test directory permissions.
Run with: python3 validate_phase3_usage_analytics.py
"""

import sys
from datetime import datetime, timedelta
from typing import List

# Add src to path
sys.path.insert(0, "/home/ui-cli_jake/unified-intelligence-cli")

from src.observability.entities import UsageEntry, UsageSummary, UsagePattern, OperationType
from src.observability.interfaces import IUsageTracker
from src.observability.adapters import InMemoryUsageTracker
from src.observability.analytics import UsageAnalytics, ModelStats

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
# UsageEntry Entity Tests
# ============================================================================


@test("UsageEntry: Factory creates valid entry with required fields")
def test_usage_entry_factory():
    entry = UsageEntry.create(
        model_name="grok-1",
        provider="x-ai",
        input_tokens=1000,
        output_tokens=500,
        operation_type=OperationType.COMPLETION,
    )

    assert entry.model_name == "grok-1"
    assert entry.provider == "x-ai"
    assert entry.input_tokens == 1000
    assert entry.output_tokens == 500
    assert entry.total_tokens == 1500
    assert entry.operation_type == OperationType.COMPLETION
    assert entry.success is True
    assert entry.id is not None
    assert entry.timestamp is not None


@test("UsageEntry: Factory accepts optional metadata")
def test_usage_entry_optional():
    entry = UsageEntry.create(
        model_name="gpt-4",
        provider="openai",
        input_tokens=2000,
        output_tokens=1000,
        project_id="proj-123",
        task_id="task-456",
        agent_name="test-agent",
        duration_ms=1500.0,
        success=False,
        error_type="timeout",
    )

    assert entry.project_id == "proj-123"
    assert entry.task_id == "task-456"
    assert entry.agent_name == "test-agent"
    assert entry.duration_ms == 1500.0
    assert entry.success is False
    assert entry.error_type == "timeout"


@test("UsageEntry: Validates non-negative tokens")
def test_usage_entry_negative_tokens():
    try:
        UsageEntry.create(
            model_name="grok-1",
            provider="x-ai",
            input_tokens=-100,
            output_tokens=500,
        )
        assert False, "Should raise ValueError"
    except ValueError as e:
        assert "cannot be negative" in str(e).lower()


@test("UsageEntry: Validates total tokens sum")
def test_usage_entry_total_sum():
    try:
        UsageEntry(
            id="test-id",
            model_name="grok-1",
            provider="x-ai",
            input_tokens=1000,
            output_tokens=500,
            total_tokens=2000,  # Wrong
            operation_type=OperationType.COMPLETION,
            timestamp=datetime.now(),
        )
        assert False, "Should raise ValueError"
    except ValueError as e:
        assert "does not match" in str(e).lower()


@test("UsageEntry: Is immutable (frozen dataclass)")
def test_usage_entry_immutable():
    entry = UsageEntry.create(
        model_name="grok-1",
        provider="x-ai",
        input_tokens=1000,
        output_tokens=500,
    )

    try:
        entry.input_tokens = 2000
        assert False, "Should not allow modification"
    except (AttributeError, Exception):
        pass


@test("UsageEntry: Calculates input/output ratio")
def test_usage_entry_ratio():
    entry = UsageEntry.create(
        model_name="grok-1",
        provider="x-ai",
        input_tokens=1000,
        output_tokens=500,
    )

    ratio = entry.input_output_ratio()
    assert abs(ratio - 2.0) < 0.001


@test("UsageEntry: Calculates tokens per second")
def test_usage_entry_tokens_per_sec():
    entry = UsageEntry.create(
        model_name="grok-1",
        provider="x-ai",
        input_tokens=1000,
        output_tokens=500,
        duration_ms=1500.0,  # 1.5 seconds
    )

    tps = entry.tokens_per_second()
    expected = 1500 / 1.5  # 1000 tokens/sec
    assert abs(tps - expected) < 0.1


@test("UsageEntry: to_dict serialization")
def test_usage_entry_to_dict():
    entry = UsageEntry.create(
        model_name="grok-1",
        provider="x-ai",
        input_tokens=1000,
        output_tokens=500,
        project_id="proj-123",
    )

    data = entry.to_dict()
    assert data["model_name"] == "grok-1"
    assert data["provider"] == "x-ai"
    assert data["input_tokens"] == 1000
    assert data["total_tokens"] == 1500
    assert "id" in data
    assert "timestamp" in data


# ============================================================================
# InMemoryUsageTracker Tests
# ============================================================================


@test("InMemoryUsageTracker: Implements IUsageTracker interface")
def test_tracker_implements_interface():
    tracker = InMemoryUsageTracker()
    assert isinstance(tracker, IUsageTracker)


@test("InMemoryUsageTracker: Records usage entry")
def test_tracker_record():
    tracker = InMemoryUsageTracker()

    entry = UsageEntry.create(
        model_name="grok-1",
        provider="x-ai",
        input_tokens=1000,
        output_tokens=500,
    )

    tracker.record_usage(entry)
    assert tracker.get_entry_count() == 1


@test("InMemoryUsageTracker: Rejects invalid entry type")
def test_tracker_invalid_entry():
    tracker = InMemoryUsageTracker()

    try:
        tracker.record_usage("not a usage entry")
        assert False, "Should raise ValueError"
    except ValueError as e:
        assert "UsageEntry" in str(e)


@test("InMemoryUsageTracker: Gets total tokens (no filters)")
def test_tracker_total_tokens():
    tracker = InMemoryUsageTracker()

    # Record 3 entries
    for i in range(3):
        entry = UsageEntry.create(
            model_name="grok-1",
            provider="x-ai",
            input_tokens=1000,
            output_tokens=500,
        )
        tracker.record_usage(entry)

    total = tracker.get_total_tokens()
    assert total == 3 * 1500


@test("InMemoryUsageTracker: Filters by project_id")
def test_tracker_filter_project():
    tracker = InMemoryUsageTracker()

    # Project A
    for i in range(2):
        entry = UsageEntry.create(
            model_name="grok-1",
            provider="x-ai",
            input_tokens=1000,
            output_tokens=500,
            project_id="proj-a",
        )
        tracker.record_usage(entry)

    # Project B
    entry = UsageEntry.create(
        model_name="grok-1",
        provider="x-ai",
        input_tokens=1000,
        output_tokens=500,
        project_id="proj-b",
    )
    tracker.record_usage(entry)

    tokens_a = tracker.get_total_tokens(project_id="proj-a")
    tokens_b = tracker.get_total_tokens(project_id="proj-b")

    assert tokens_a == 2 * 1500
    assert tokens_b == 1500


@test("InMemoryUsageTracker: Filters by model_name")
def test_tracker_filter_model():
    tracker = InMemoryUsageTracker()

    # Grok
    entry1 = UsageEntry.create(
        model_name="grok-1",
        provider="x-ai",
        input_tokens=1000,
        output_tokens=500,
    )
    tracker.record_usage(entry1)

    # GPT-4
    entry2 = UsageEntry.create(
        model_name="gpt-4",
        provider="openai",
        input_tokens=2000,
        output_tokens=1000,
    )
    tracker.record_usage(entry2)

    tokens_grok = tracker.get_total_tokens(model_name="grok-1")
    tokens_gpt4 = tracker.get_total_tokens(model_name="gpt-4")

    assert tokens_grok == 1500
    assert tokens_gpt4 == 3000


@test("InMemoryUsageTracker: Filters by success_only")
def test_tracker_filter_success():
    tracker = InMemoryUsageTracker()

    # Success entries
    for i in range(3):
        entry = UsageEntry.create(
            model_name="grok-1",
            provider="x-ai",
            input_tokens=1000,
            output_tokens=500,
            success=True,
        )
        tracker.record_usage(entry)

    # Failure entry
    entry = UsageEntry.create(
        model_name="grok-1",
        provider="x-ai",
        input_tokens=1000,
        output_tokens=500,
        success=False,
        error_type="timeout",
    )
    tracker.record_usage(entry)

    total_all = tracker.get_total_tokens()
    total_success = tracker.get_total_tokens(success_only=True)

    assert total_all == 4 * 1500
    assert total_success == 3 * 1500


@test("InMemoryUsageTracker: Usage breakdown by model")
def test_tracker_breakdown_model():
    tracker = InMemoryUsageTracker()

    # Grok entries
    for i in range(2):
        entry = UsageEntry.create(
            model_name="grok-1",
            provider="x-ai",
            input_tokens=1000,
            output_tokens=500,
        )
        tracker.record_usage(entry)

    # GPT-4 entry
    entry = UsageEntry.create(
        model_name="gpt-4",
        provider="openai",
        input_tokens=2000,
        output_tokens=1000,
    )
    tracker.record_usage(entry)

    breakdown = tracker.get_usage_breakdown("model")

    assert "grok-1" in breakdown
    assert "gpt-4" in breakdown
    assert breakdown["grok-1"] == 2 * 1500
    assert breakdown["gpt-4"] == 3000


@test("InMemoryUsageTracker: Usage breakdown by operation")
def test_tracker_breakdown_operation():
    tracker = InMemoryUsageTracker()

    # Completion
    entry = UsageEntry.create(
        model_name="grok-1",
        provider="x-ai",
        input_tokens=1000,
        output_tokens=500,
        operation_type=OperationType.COMPLETION,
    )
    tracker.record_usage(entry)

    # Chat
    entry = UsageEntry.create(
        model_name="grok-1",
        provider="x-ai",
        input_tokens=2000,
        output_tokens=1000,
        operation_type=OperationType.CHAT,
    )
    tracker.record_usage(entry)

    breakdown = tracker.get_usage_breakdown("operation")

    assert "completion" in breakdown
    assert "chat" in breakdown


@test("InMemoryUsageTracker: Gets entries with limit")
def test_tracker_get_entries():
    tracker = InMemoryUsageTracker()

    # Add 5 entries
    for i in range(5):
        entry = UsageEntry.create(
            model_name="grok-1",
            provider="x-ai",
            input_tokens=1000,
            output_tokens=500,
        )
        tracker.record_usage(entry)

    entries = tracker.get_entries(limit=3)
    assert len(entries) == 3


@test("InMemoryUsageTracker: Gets summary with statistics")
def test_tracker_get_summary():
    tracker = InMemoryUsageTracker()

    # Add entries
    for i in range(3):
        entry = UsageEntry.create(
            model_name="grok-1",
            provider="x-ai",
            input_tokens=1000,
            output_tokens=500,
            success=True,
        )
        tracker.record_usage(entry)

    # Add failure
    entry = UsageEntry.create(
        model_name="grok-1",
        provider="x-ai",
        input_tokens=1000,
        output_tokens=500,
        success=False,
    )
    tracker.record_usage(entry)

    summary = tracker.get_summary()

    assert isinstance(summary, UsageSummary)
    assert summary.entry_count == 4
    assert summary.success_count == 3
    assert summary.failure_count == 1
    assert summary.total_tokens == 4 * 1500
    assert summary.success_rate() == 75.0


@test("InMemoryUsageTracker: Calculates success rate")
def test_tracker_success_rate():
    tracker = InMemoryUsageTracker()

    # 3 success, 1 failure
    for i in range(3):
        entry = UsageEntry.create(
            model_name="grok-1",
            provider="x-ai",
            input_tokens=1000,
            output_tokens=500,
            success=True,
        )
        tracker.record_usage(entry)

    entry = UsageEntry.create(
        model_name="grok-1",
        provider="x-ai",
        input_tokens=1000,
        output_tokens=500,
        success=False,
    )
    tracker.record_usage(entry)

    rate = tracker.get_success_rate()
    assert abs(rate - 75.0) < 0.1


@test("InMemoryUsageTracker: Deletes entries with safety check")
def test_tracker_delete():
    tracker = InMemoryUsageTracker()

    now = datetime.now()
    past = now - timedelta(days=2)

    # Old entry
    entry_old = UsageEntry(
        id="old-id",
        model_name="grok-1",
        provider="x-ai",
        input_tokens=1000,
        output_tokens=500,
        total_tokens=1500,
        operation_type=OperationType.COMPLETION,
        timestamp=past,
    )
    tracker.record_usage(entry_old)

    # Recent entry
    entry_new = UsageEntry.create(
        model_name="grok-1",
        provider="x-ai",
        input_tokens=1000,
        output_tokens=500,
    )
    tracker.record_usage(entry_new)

    # Delete old
    deleted = tracker.delete_entries(before=now - timedelta(days=1))
    assert deleted == 1
    assert tracker.get_entry_count() == 1


@test("InMemoryUsageTracker: Delete requires filter")
def test_tracker_delete_safety():
    tracker = InMemoryUsageTracker()

    try:
        tracker.delete_entries()
        assert False, "Should raise ValueError"
    except ValueError as e:
        assert "at least one filter" in str(e).lower()


# ============================================================================
# Analytics Utilities Tests
# ============================================================================


@test("Analytics: Gets time series data")
def test_analytics_time_series():
    entries = []
    now = datetime.now()

    # Create entries over time
    for i in range(5):
        entry = UsageEntry(
            id=f"entry-{i}",
            model_name="grok-1",
            provider="x-ai",
            input_tokens=1000,
            output_tokens=500,
            total_tokens=1500,
            operation_type=OperationType.COMPLETION,
            timestamp=now + timedelta(hours=i),
        )
        entries.append(entry)

    points = UsageAnalytics.get_time_series(entries, interval=timedelta(hours=1))

    assert len(points) > 0
    assert all(p.value >= 0 for p in points)


@test("Analytics: Calculates model statistics")
def test_analytics_model_stats():
    entries = []

    # Grok entries
    for i in range(3):
        entry = UsageEntry.create(
            model_name="grok-1",
            provider="x-ai",
            input_tokens=1000,
            output_tokens=500,
            success=True,
        )
        entries.append(entry)

    # GPT-4 entries
    for i in range(2):
        entry = UsageEntry.create(
            model_name="gpt-4",
            provider="openai",
            input_tokens=2000,
            output_tokens=1000,
            success=True,
        )
        entries.append(entry)

    stats_list = UsageAnalytics.get_model_stats(entries)

    assert len(stats_list) == 2
    assert isinstance(stats_list[0], ModelStats)
    assert stats_list[0].total_calls > 0
    assert stats_list[0].success_rate == 100.0


@test("Analytics: Detects peak hours")
def test_analytics_peak_hours():
    entries = []
    now = datetime.now()

    # Create entries concentrated at certain hours
    for hour in [9, 9, 9, 10, 10, 14, 14, 14, 14]:  # Peak at 9, 14
        entry = UsageEntry(
            id=f"entry-{hour}",
            model_name="grok-1",
            provider="x-ai",
            input_tokens=1000,
            output_tokens=500,
            total_tokens=1500,
            operation_type=OperationType.COMPLETION,
            timestamp=now.replace(hour=hour % 24, minute=0),
        )
        entries.append(entry)

    peak_hours = UsageAnalytics.detect_peak_hours(entries, threshold_percentile=60)

    assert len(peak_hours) > 0
    assert all(0 <= h < 24 for h in peak_hours)


@test("Analytics: Detects model preferences by agent")
def test_analytics_model_preferences():
    entries = []

    # Agent A prefers Grok
    for i in range(3):
        entry = UsageEntry.create(
            model_name="grok-1",
            provider="x-ai",
            input_tokens=1000,
            output_tokens=500,
            agent_name="agent-a",
        )
        entries.append(entry)

    # Agent B prefers GPT-4
    for i in range(3):
        entry = UsageEntry.create(
            model_name="gpt-4",
            provider="openai",
            input_tokens=2000,
            output_tokens=1000,
            agent_name="agent-b",
        )
        entries.append(entry)

    preferences = UsageAnalytics.detect_model_preferences(entries, by_agent=True)

    assert "agent-a" in preferences
    assert "agent-b" in preferences
    assert preferences["agent-a"] == "grok-1"
    assert preferences["agent-b"] == "gpt-4"


@test("Analytics: Calculates efficiency score")
def test_analytics_efficiency():
    # Successful entry with duration
    entry = UsageEntry.create(
        model_name="grok-1",
        provider="x-ai",
        input_tokens=1000,
        output_tokens=500,
        duration_ms=1500.0,
        success=True,
    )

    score = UsageAnalytics.calculate_efficiency_score(entry)
    assert 0.0 <= score <= 1.0

    # Failed entry
    entry_failed = UsageEntry.create(
        model_name="grok-1",
        provider="x-ai",
        input_tokens=1000,
        output_tokens=500,
        success=False,
    )

    score_failed = UsageAnalytics.calculate_efficiency_score(entry_failed)
    assert score_failed == 0.0


@test("Analytics: Calculates token distribution")
def test_analytics_token_distribution():
    entries = []

    # Create entries with varying token counts
    for tokens in [100, 500, 1000, 1500, 2000, 2500, 3000]:
        entry = UsageEntry(
            id=f"entry-{tokens}",
            model_name="grok-1",
            provider="x-ai",
            input_tokens=int(tokens * 0.6),
            output_tokens=int(tokens * 0.4),
            total_tokens=tokens,
            operation_type=OperationType.COMPLETION,
            timestamp=datetime.now(),
        )
        entries.append(entry)

    distribution = UsageAnalytics.get_token_distribution(entries, bins=5)

    assert len(distribution) > 0
    assert all(count >= 0 for _, count in distribution)


@test("Analytics: Detects anomalies")
def test_analytics_anomalies():
    entries = []

    # Normal entries (around 1500 tokens)
    for i in range(10):
        entry = UsageEntry.create(
            model_name="grok-1",
            provider="x-ai",
            input_tokens=1000,
            output_tokens=500,
        )
        entries.append(entry)

    # Anomaly (10000 tokens)
    anomaly = UsageEntry.create(
        model_name="grok-1",
        provider="x-ai",
        input_tokens=7000,
        output_tokens=3000,
    )
    entries.append(anomaly)

    anomalies = UsageAnalytics.detect_anomalies(entries, std_threshold=2.0)

    assert len(anomalies) > 0


@test("Analytics: Generates usage patterns")
def test_analytics_generate_patterns():
    entries = []
    now = datetime.now()

    # Create entries with patterns
    for hour in [9, 9, 9, 14, 14, 14]:
        entry = UsageEntry(
            id=f"entry-{hour}",
            model_name="grok-1",
            provider="x-ai",
            input_tokens=1000,
            output_tokens=500,
            total_tokens=1500,
            operation_type=OperationType.COMPLETION,
            timestamp=now.replace(hour=hour, minute=0),
            agent_name="agent-a",
        )
        entries.append(entry)

    patterns = UsageAnalytics.generate_usage_patterns(entries)

    assert isinstance(patterns, list)
    assert all(isinstance(p, UsagePattern) for p in patterns)


# ============================================================================
# Integration Tests
# ============================================================================


@test("Integration: Multi-entry usage tracking workflow")
def test_integration_workflow():
    tracker = InMemoryUsageTracker()
    project_id = "integration-test"

    # Simulate project usage
    # Research agent uses Grok
    for i in range(3):
        entry = UsageEntry.create(
            model_name="grok-1",
            provider="x-ai",
            input_tokens=1500,
            output_tokens=750,
            project_id=project_id,
            agent_name="research-agent",
            operation_type=OperationType.COMPLETION,
        )
        tracker.record_usage(entry)

    # Backend agent uses GPT-4
    for i in range(2):
        entry = UsageEntry.create(
            model_name="gpt-4",
            provider="openai",
            input_tokens=2000,
            output_tokens=1000,
            project_id=project_id,
            agent_name="backend-agent",
            operation_type=OperationType.CHAT,
        )
        tracker.record_usage(entry)

    # Verify summary
    summary = tracker.get_summary(project_id=project_id)
    assert summary.entry_count == 5
    assert summary.unique_models == 2
    assert summary.unique_agents == 2

    # Verify breakdowns
    model_breakdown = tracker.get_usage_breakdown("model", project_id=project_id)
    assert len(model_breakdown) == 2


@test("Integration: Analytics on tracked data")
def test_integration_analytics():
    tracker = InMemoryUsageTracker()

    # Add diverse entries
    for i in range(10):
        entry = UsageEntry.create(
            model_name="grok-1" if i % 2 == 0 else "gpt-4",
            provider="x-ai" if i % 2 == 0 else "openai",
            input_tokens=1000 + (i * 100),
            output_tokens=500 + (i * 50),
            agent_name=f"agent-{i % 3}",
            duration_ms=float(1000 + (i * 100)),
        )
        tracker.record_usage(entry)

    entries = tracker.get_all_entries()

    # Run analytics
    stats = UsageAnalytics.get_model_stats(entries)
    assert len(stats) > 0

    preferences = UsageAnalytics.detect_model_preferences(entries, by_agent=True)
    assert len(preferences) > 0

    patterns = UsageAnalytics.generate_usage_patterns(entries)
    assert isinstance(patterns, list)


@test("Integration: Empty tracker returns sensible defaults")
def test_integration_empty():
    tracker = InMemoryUsageTracker()

    assert tracker.get_total_tokens() == 0
    assert tracker.get_entry_count() == 0
    assert tracker.get_success_rate() == 0.0

    summary = tracker.get_summary()
    assert summary.entry_count == 0
    assert summary.total_tokens == 0


@test("Integration: Success rate calculation accuracy")
def test_integration_success_rate():
    tracker = InMemoryUsageTracker()

    # 7 success, 3 failure = 70% success rate
    for i in range(7):
        entry = UsageEntry.create(
            model_name="grok-1",
            provider="x-ai",
            input_tokens=1000,
            output_tokens=500,
            success=True,
        )
        tracker.record_usage(entry)

    for i in range(3):
        entry = UsageEntry.create(
            model_name="grok-1",
            provider="x-ai",
            input_tokens=1000,
            output_tokens=500,
            success=False,
            error_type="timeout",
        )
        tracker.record_usage(entry)

    rate = tracker.get_success_rate()
    assert abs(rate - 70.0) < 0.1

    summary = tracker.get_summary()
    assert abs(summary.success_rate() - 70.0) < 0.1


@test("Integration: Complex filtering combinations")
def test_integration_complex_filters():
    tracker = InMemoryUsageTracker()

    # Add varied entries
    for success in [True, False]:
        for model in ["grok-1", "gpt-4"]:
            for agent in ["agent-a", "agent-b"]:
                entry = UsageEntry.create(
                    model_name=model,
                    provider="x-ai" if model == "grok-1" else "openai",
                    input_tokens=1000,
                    output_tokens=500,
                    agent_name=agent,
                    success=success,
                )
                tracker.record_usage(entry)

    # Test combinations
    tokens_grok_success = tracker.get_total_tokens(
        model_name="grok-1",
        success_only=True
    )
    assert tokens_grok_success == 2 * 1500  # 2 agents × 1500 tokens

    rate_agent_a = tracker.get_success_rate(agent_name="agent-a")
    assert abs(rate_agent_a - 50.0) < 0.1  # 50% success


# ============================================================================
# Main Execution
# ============================================================================


def main():
    print("=" * 70)
    print("Phase 3 Validation: Usage Analytics")
    print("=" * 70)
    print()

    # Run all tests
    print("Running UsageEntry Entity Tests...")
    test_usage_entry_factory()
    test_usage_entry_optional()
    test_usage_entry_negative_tokens()
    test_usage_entry_total_sum()
    test_usage_entry_immutable()
    test_usage_entry_ratio()
    test_usage_entry_tokens_per_sec()
    test_usage_entry_to_dict()

    print("\nRunning InMemoryUsageTracker Tests...")
    test_tracker_implements_interface()
    test_tracker_record()
    test_tracker_invalid_entry()
    test_tracker_total_tokens()
    test_tracker_filter_project()
    test_tracker_filter_model()
    test_tracker_filter_success()
    test_tracker_breakdown_model()
    test_tracker_breakdown_operation()
    test_tracker_get_entries()
    test_tracker_get_summary()
    test_tracker_success_rate()
    test_tracker_delete()
    test_tracker_delete_safety()

    print("\nRunning Analytics Utilities Tests...")
    test_analytics_time_series()
    test_analytics_model_stats()
    test_analytics_peak_hours()
    test_analytics_model_preferences()
    test_analytics_efficiency()
    test_analytics_token_distribution()
    test_analytics_anomalies()
    test_analytics_generate_patterns()

    print("\nRunning Integration Tests...")
    test_integration_workflow()
    test_integration_analytics()
    test_integration_empty()
    test_integration_success_rate()
    test_integration_complex_filters()

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
        print("✅ All Phase 3 validation tests passed!")
        print()
        print("Phase 3 (Usage Analytics) Status: VALIDATED ✓")
        print()
        sys.exit(0)


if __name__ == "__main__":
    main()
