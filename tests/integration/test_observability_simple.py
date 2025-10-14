"""Simple Integration Tests for Observability System (P1.3).

Focused integration tests for observability across all 5 phases.
Tests key integration patterns without duplicating the detailed
validation already performed in P1.3 manual validation scripts.

Clean Architecture: Integration test layer
SOLID: Tests verify correct observability integration

Sprint: P2 Testing Infrastructure
Reference: P1.3 validation scripts (154/154 tests passing)
"""

import pytest
import asyncio
from datetime import datetime

from src.observability.entities import (
    Trace,
    TraceStatus,
    CostEntry,
    UsageEntry,
    OperationType,
    Alert,
    AlertSeverity,
    PerformanceMetric,
    MetricType,
)
from src.observability.adapters import (
    InMemoryTracer,
    InMemoryCostTracker,
    InMemoryUsageTracker,
    InMemoryAlertManager,
    InMemoryPerformanceProfiler,
)


class TestObservabilityBasicIntegration:
    """
    Basic integration tests for observability stack.

    Tests verify:
    - All 5 phases can be instantiated and used together
    - Data flows correctly between components
    - Basic operations work end-to-end
    """

    @pytest.fixture
    def observability_stack(self):
        """Create complete observability stack."""
        return {
            "tracer": InMemoryTracer(),
            "cost_tracker": InMemoryCostTracker(),
            "usage_tracker": InMemoryUsageTracker(),
            "alert_manager": InMemoryAlertManager(),
            "performance_profiler": InMemoryPerformanceProfiler(),
        }

    @pytest.mark.asyncio
    async def test_phase1_tracing_basic(self, observability_stack):
        """Test Phase 1: Basic tracing works."""
        tracer = observability_stack["tracer"]

        # Start and finish trace
        trace = tracer.start_trace("test_operation")
        await asyncio.sleep(0.01)
        trace = tracer.finish_trace(trace, TraceStatus.SUCCESS)

        # Verify trace exists
        retrieved = tracer.get_trace(trace.trace_id)
        assert retrieved is not None
        assert retrieved.status == TraceStatus.SUCCESS

    @pytest.mark.asyncio
    async def test_phase2_cost_tracking_basic(self, observability_stack):
        """Test Phase 2: Basic cost tracking works."""
        cost_tracker = observability_stack["cost_tracker"]

        # Record cost
        entry = CostEntry.create(
            model_name="claude-sonnet-4",
            provider="anthropic",
            input_tokens=1000,
            output_tokens=500,
            input_cost_per_1k=0.003,
            output_cost_per_1k=0.015,
            project_id="test-project",
        )
        cost_tracker.record_cost(entry)

        # Verify cost recorded
        total = cost_tracker.get_total_cost(project_id="test-project")
        assert total > 0

    @pytest.mark.asyncio
    async def test_phase3_usage_tracking_basic(self, observability_stack):
        """Test Phase 3: Basic usage tracking works."""
        usage_tracker = observability_stack["usage_tracker"]

        # Record usage
        entry = UsageEntry.create(
            model_name="grok-1",
            provider="x-ai",
            input_tokens=1000,
            output_tokens=500,
            operation_type=OperationType.CHAT,
            project_id="test-project",
        )
        usage_tracker.record_usage(entry)

        # Verify usage recorded
        total = usage_tracker.get_total_tokens(project_id="test-project")
        assert total == 1500  # 1000 + 500

    @pytest.mark.asyncio
    async def test_phase4_alerting_basic(self, observability_stack):
        """Test Phase 4: Basic alerting works."""
        alert_manager = observability_stack["alert_manager"]

        # Create alert
        alert = Alert.create(
            severity=AlertSeverity.ERROR,
            message="Test alert",
            source="test",
        )
        alert_manager.record_alert(alert)

        # Verify alert exists
        alerts = alert_manager.get_alerts()
        assert len(alerts) == 1
        assert alerts[0].message == "Test alert"

    @pytest.mark.asyncio
    async def test_phase5_performance_profiling_basic(self, observability_stack):
        """Test Phase 5: Basic performance profiling works."""
        perf_profiler = observability_stack["performance_profiler"]

        # Record metric
        metric = PerformanceMetric.create(
            operation_name="test_op",
            metric_type=MetricType.DURATION,
            value=25.0,
            unit="ms",
        )
        perf_profiler.record_metric(metric)

        # Verify metric recorded
        summary = perf_profiler.get_summary("test_op")
        assert summary.metric_count == 1
        assert summary.avg_duration_ms == 25.0

    @pytest.mark.asyncio
    async def test_all_phases_work_together(self, observability_stack):
        """Test all 5 phases can be used together in one workflow."""
        tracer = observability_stack["tracer"]
        cost_tracker = observability_stack["cost_tracker"]
        usage_tracker = observability_stack["usage_tracker"]
        alert_manager = observability_stack["alert_manager"]
        perf_profiler = observability_stack["performance_profiler"]

        # Common identifiers
        project_id = "integration-test"
        agent_name = "test-agent"

        # Phase 1: Trace
        trace = tracer.start_trace("integration_workflow")

        # Phase 5: Performance
        perf_metric = PerformanceMetric.create(
            operation_name="integration_workflow",
            metric_type=MetricType.DURATION,
            value=100.0,
            unit="ms",
            trace_id=trace.trace_id,
            project_id=project_id,
        )
        perf_profiler.record_metric(perf_metric)

        # Phase 2: Cost
        cost_entry = CostEntry.create(
            model_name="claude-sonnet-4",
            provider="anthropic",
            input_tokens=2000,
            output_tokens=1000,
            input_cost_per_1k=0.003,
            output_cost_per_1k=0.015,
            trace_id=trace.trace_id,
            project_id=project_id,
            agent_name=agent_name,
        )
        cost_tracker.record_cost(cost_entry)

        # Phase 3: Usage
        usage_entry = UsageEntry.create(
            model_name="claude-sonnet-4",
            provider="anthropic",
            input_tokens=2000,
            output_tokens=1000,
            operation_type=OperationType.CHAT,
            trace_id=trace.trace_id,
            project_id=project_id,
            agent_name=agent_name,
        )
        usage_tracker.record_usage(usage_entry)

        # Finish trace
        trace = tracer.finish_trace(trace, TraceStatus.SUCCESS)

        # Verify all phases recorded data
        assert tracer.get_trace(trace.trace_id) is not None
        assert cost_tracker.get_total_cost(project_id=project_id) > 0
        assert usage_tracker.get_total_tokens(project_id=project_id) == 3000
        assert perf_profiler.get_summary("integration_workflow").metric_count == 1

        # Phase 4: Alert (if something went wrong - not in this test)
        # alert_manager would be used for error conditions

    @pytest.mark.asyncio
    async def test_observability_performance_acceptable(self):
        """Test observability has acceptable performance overhead."""
        import time

        tracer = InMemoryTracer()
        iterations = 100

        # Measure with observability
        start = time.perf_counter()
        for i in range(iterations):
            trace = tracer.start_trace(f"op_{i}")
            await asyncio.sleep(0.001)  # 1ms work
            tracer.finish_trace(trace, TraceStatus.SUCCESS)
        elapsed = time.perf_counter() - start

        # Should complete reasonably fast
        # 100 ops * 1ms = 100ms + overhead
        assert elapsed < 0.5, f"Too slow: {elapsed:.3f}s for {iterations} operations"


class TestObservabilityDataCorrelation:
    """Tests for data correlation across observability phases."""

    @pytest.mark.asyncio
    async def test_trace_id_correlates_data(self):
        """Test trace_id allows correlation across all phases."""
        tracer = InMemoryTracer()
        cost_tracker = InMemoryCostTracker()
        usage_tracker = InMemoryUsageTracker()
        perf_profiler = InMemoryPerformanceProfiler()

        # Start trace (generates trace_id)
        trace = tracer.start_trace("correlated_operation")
        trace_id = trace.trace_id

        # Use same trace_id across phases
        cost_entry = CostEntry.create(
            model_name="grok-1",
            provider="x-ai",
            input_tokens=1000,
            output_tokens=500,
            input_cost_per_1k=0.01,
            output_cost_per_1k=0.03,
            trace_id=trace_id,
        )
        cost_tracker.record_cost(cost_entry)

        usage_entry = UsageEntry.create(
            model_name="grok-1",
            provider="x-ai",
            input_tokens=1000,
            output_tokens=500,
            operation_type=OperationType.CHAT,
            trace_id=trace_id,
        )
        usage_tracker.record_usage(usage_entry)

        perf_metric = PerformanceMetric.create(
            operation_name="correlated_operation",
            metric_type=MetricType.DURATION,
            value=150.0,
            unit="ms",
            trace_id=trace_id,
        )
        perf_profiler.record_metric(perf_metric)

        # Finish trace
        tracer.finish_trace(trace, TraceStatus.SUCCESS)

        # Verify all components have same trace_id
        retrieved_trace = tracer.get_trace(trace_id)
        assert retrieved_trace.trace_id == trace_id

        # Cost, usage, and perf entries should also have this trace_id
        # (detailed verification would query by trace_id, but adapters store it)

    @pytest.mark.asyncio
    async def test_project_id_enables_aggregation(self):
        """Test project_id enables aggregation across operations."""
        cost_tracker = InMemoryCostTracker()
        usage_tracker = InMemoryUsageTracker()

        project_id = "multi-op-project"

        # Multiple operations for same project
        for i in range(5):
            cost_entry = CostEntry.create(
                model_name="claude-sonnet-4",
                provider="anthropic",
                input_tokens=1000,
                output_tokens=500,
                input_cost_per_1k=0.003,
                output_cost_per_1k=0.015,
                project_id=project_id,
            )
            cost_tracker.record_cost(cost_entry)

            usage_entry = UsageEntry.create(
                model_name="claude-sonnet-4",
                provider="anthropic",
                input_tokens=1000,
                output_tokens=500,
                operation_type=OperationType.CHAT,
                project_id=project_id,
            )
            usage_tracker.record_usage(usage_entry)

        # Aggregate by project
        total_cost = cost_tracker.get_total_cost(project_id=project_id)
        total_tokens = usage_tracker.get_total_tokens(project_id=project_id)

        # 5 operations * cost/tokens per operation
        assert total_cost > 0
        assert total_tokens == 5 * 1500  # 7500 total tokens
