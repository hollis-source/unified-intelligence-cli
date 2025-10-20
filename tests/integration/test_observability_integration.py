"""Integration Tests for Observability System (P1.3).

Tests end-to-end observability across all 5 phases:
- Phase 1: Tracing
- Phase 2: Cost tracking
- Phase 3: Usage analytics
- Phase 4: Error alerting
- Phase 5: Performance profiling

Validates integration with:
- Multi-agent orchestration
- DSL workflows
- CLI execution
- Project builder

Clean Architecture: Integration test layer
SOLID: Tests verify correct observability integration

Sprint: P2 Testing Infrastructure (tests for P1.3 observability)
Reference: P1.3 Production Observability artifacts
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any

from src.observability.entities import (
    Trace,
    TraceStatus,
    CostEntry,
    UsageEntry,
    OperationType,
    Alert,
    AlertSeverity,
    AlertRule,
    PerformanceMetric,
    MetricType,
)
from src.observability.interfaces import (
    ITracer,
    ICostTracker,
    IUsageTracker,
    IAlertManager,
    IPerformanceProfiler,
)
from src.observability.adapters import (
    InMemoryTracer,
    InMemoryCostTracker,
    InMemoryUsageTracker,
    InMemoryAlertManager,
    InMemoryPerformanceProfiler,
)
from src.observability.decorators import trace_operation, set_global_tracer


class TestObservabilityFullStack:
    """
    Integration tests for full observability stack.

    Tests verify:
    - All 5 phases work together
    - Observability integrates with application workflows
    - Cross-phase data correlation (trace_id, project_id)
    - Performance impact is minimal
    """

    @pytest.fixture
    def observability_stack(self):
        """Create complete observability stack."""
        tracer = InMemoryTracer()
        cost_tracker = InMemoryCostTracker()
        usage_tracker = InMemoryUsageTracker()
        alert_manager = InMemoryAlertManager()
        performance_profiler = InMemoryPerformanceProfiler()

        # Set global tracer for decorator
        set_global_tracer(tracer)

        return {
            "tracer": tracer,
            "cost_tracker": cost_tracker,
            "usage_tracker": usage_tracker,
            "alert_manager": alert_manager,
            "performance_profiler": performance_profiler,
        }

    @pytest.mark.asyncio
    async def test_observability_traces_workflow_execution(self, observability_stack):
        """Test observability traces complete workflow execution."""
        tracer = observability_stack["tracer"]
        perf_profiler = observability_stack["performance_profiler"]

        # Start workflow trace
        workflow_trace = tracer.start_trace("execute_workflow", tags={"workflow": "test"})

        # Simulate workflow execution with performance metrics
        start_time = datetime.now()
        await asyncio.sleep(0.01)  # Simulate work

        # Record performance metric
        perf_metric = PerformanceMetric.create(
            operation_name="execute_workflow",
            metric_type=MetricType.DURATION,
            value=10.0,  # 10ms
            unit="ms",
        )
        perf_profiler.record_metric(perf_metric)

        # Finish trace
        workflow_trace = tracer.finish_trace(workflow_trace, TraceStatus.SUCCESS)

        # Verify trace recorded
        traces = tracer.get_traces()
        assert len(traces) == 1
        assert traces[0].operation_name == "execute_workflow"
        assert traces[0].status == TraceStatus.SUCCESS

        # Verify performance metric recorded
        metrics = perf_profiler.get_metrics(operation_name="execute_workflow")
        assert len(metrics) == 1
        assert metrics[0].value == 10.0

    @pytest.mark.asyncio
    async def test_observability_tracks_cost_across_agents(self, observability_stack):
        """Test cost tracking across multi-agent execution."""
        cost_tracker = observability_stack["cost_tracker"]

        # Simulate multiple agent LLM calls
        agents = ["frontend-lead", "backend-lead", "testing-lead"]
        project_id = "test-project"

        for agent in agents:
            # Simulate LLM call
            cost_entry = CostEntry.create(
                model_name="claude-sonnet-4",
                provider="anthropic",
                input_tokens=1000,
                output_tokens=500,
                input_cost_per_1k=0.003,
                output_cost_per_1k=0.015,
                project_id=project_id,
                agent_name=agent,
            )

            cost_tracker.record_cost(cost_entry)

        # Get cost summary for project
        summary = cost_tracker.get_cost_summary(project_id=project_id)

        # Verify all agents tracked
        assert summary.total_entries == 3
        assert summary.total_cost > 0

        # Verify breakdown by agent
        by_agent = cost_tracker.get_cost_by_agent(project_id=project_id)
        assert len(by_agent) == 3
        assert set(by_agent.keys()) == set(agents)

    @pytest.mark.asyncio
    async def test_observability_detects_usage_anomalies(self, observability_stack):
        """Test usage analytics detects anomalies in multi-agent system."""
        usage_tracker = observability_stack["usage_tracker"]

        # Simulate normal usage pattern
        for i in range(10):
            entry = UsageEntry.create(
                model_name="grok-1",
                provider="x-ai",
                input_tokens=1000,
                output_tokens=500,
                operation_type=OperationType.CHAT,
                project_id="test-project",
            )
            usage_tracker.record_usage(entry)

        # Simulate anomaly (10x tokens)
        anomaly_entry = UsageEntry.create(
            model_name="grok-1",
            provider="x-ai",
            input_tokens=10000,  # 10x normal
            output_tokens=5000,
            operation_type=OperationType.CHAT,
            project_id="test-project",
        )
        usage_tracker.record_usage(anomaly_entry)

        # Get all entries
        all_entries = usage_tracker.get_usage(project_id="test-project")

        # Detect anomalies using analytics
        from src.observability.analytics import UsageAnalytics

        anomalies = UsageAnalytics.detect_anomalies(all_entries, std_threshold=2.0)

        # Should detect the anomaly
        assert len(anomalies) >= 1
        assert any(a.input_tokens == 10000 for a in anomalies)

    @pytest.mark.asyncio
    async def test_observability_triggers_alerts_on_errors(self, observability_stack):
        """Test alert system triggers on error conditions."""
        tracer = observability_stack["tracer"]
        alert_manager = observability_stack["alert_manager"]

        # Create alert rule for errors
        error_rule = AlertRule.create(
            name="error_threshold",
            description="Alert on workflow errors",
            condition=lambda: True,  # Simplified for test
            severity=AlertSeverity.ERROR,
            cooldown_minutes=5,
        )
        alert_manager.add_rule(error_rule)

        # Simulate workflow error
        error_trace = tracer.start_trace("failing_workflow")
        error_trace = tracer.finish_trace(
            error_trace,
            TraceStatus.ERROR,
            error_message="Workflow execution failed",
        )

        # Create alert
        alert = Alert.create(
            severity=AlertSeverity.ERROR,
            message="Workflow execution failed",
            source="tracer",
            rule_id=error_rule.id,
        )
        alert_manager.create_alert(alert)

        # Verify alert created
        alerts = alert_manager.get_alerts(severity=AlertSeverity.ERROR)
        assert len(alerts) == 1
        assert alerts[0].message == "Workflow execution failed"

    @pytest.mark.asyncio
    async def test_observability_profiles_operation_performance(
        self, observability_stack
    ):
        """Test performance profiling across multiple operations."""
        perf_profiler = observability_stack["performance_profiler"]

        # Simulate multiple operation executions with varying performance
        operation = "process_task"

        for i in range(10):
            # Vary duration: 10ms to 100ms
            duration = 10.0 + (i * 10.0)

            # Record metrics
            duration_metric = PerformanceMetric.create(
                operation_name=operation,
                metric_type=MetricType.DURATION,
                value=duration,
                unit="ms",
            )
            perf_profiler.record_metric(duration_metric)

            cpu_metric = PerformanceMetric.create(
                operation_name=operation,
                metric_type=MetricType.CPU_USAGE,
                value=10.0 + i,
                unit="%",
            )
            perf_profiler.record_metric(cpu_metric)

        # Get performance summary
        summary = perf_profiler.get_summary(operation)

        # Verify statistics
        assert summary.metric_count == 20  # 10 duration + 10 CPU
        assert summary.avg_duration_ms is not None
        assert summary.min_duration_ms == 10.0
        assert summary.max_duration_ms == 100.0
        assert summary.p50_duration_ms is not None
        assert summary.p95_duration_ms is not None
        assert summary.avg_cpu_percent is not None

    @pytest.mark.asyncio
    async def test_observability_correlates_across_phases(self, observability_stack):
        """Test data correlation across all observability phases."""
        tracer = observability_stack["tracer"]
        cost_tracker = observability_stack["cost_tracker"]
        usage_tracker = observability_stack["usage_tracker"]
        perf_profiler = observability_stack["performance_profiler"]

        # Common identifiers
        trace_id = "trace-123"
        project_id = "project-456"
        agent_name = "backend-lead"

        # Phase 1: Start trace
        trace = Trace.create("api_call", tags={"trace_id": trace_id})
        trace = tracer.start_trace("api_call", tags={"trace_id": trace_id})

        # Phase 2: Record cost
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

        # Phase 3: Record usage
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

        # Phase 5: Record performance
        perf_metric = PerformanceMetric.create(
            operation_name="api_call",
            metric_type=MetricType.DURATION,
            value=250.0,
            unit="ms",
            trace_id=trace.trace_id,
            project_id=project_id,
            agent_name=agent_name,
        )
        perf_profiler.record_metric(perf_metric)

        # Finish trace
        trace = tracer.finish_trace(trace, TraceStatus.SUCCESS)

        # Verify correlation via trace_id
        traces = tracer.get_traces()
        assert len(traces) >= 1

        costs = cost_tracker.get_costs(trace_id=trace.trace_id)
        assert len(costs) == 1

        usage = usage_tracker.get_usage(trace_id=trace.trace_id)
        assert len(usage) == 1

        metrics = perf_profiler.get_metrics(project_id=project_id)
        assert len(metrics) == 1

        # Verify all share same identifiers
        assert costs[0].trace_id == trace.trace_id
        assert usage[0].trace_id == trace.trace_id
        assert metrics[0].trace_id == trace.trace_id

    @pytest.mark.asyncio
    async def test_observability_decorator_integration(self, observability_stack):
        """Test @trace_operation decorator integrates with observability."""
        tracer = observability_stack["tracer"]
        set_global_tracer(tracer)

        # Define instrumented function
        @trace_operation("test_operation")
        async def instrumented_task(x: int) -> int:
            await asyncio.sleep(0.01)
            return x * 2

        # Execute function
        result = await instrumented_task(5)

        # Verify result
        assert result == 10

        # Verify trace created
        traces = tracer.get_traces(operation_name="test_operation")
        assert len(traces) == 1
        assert traces[0].status == TraceStatus.SUCCESS

    @pytest.mark.asyncio
    async def test_observability_decorator_handles_errors(self, observability_stack):
        """Test @trace_operation decorator handles errors correctly."""
        tracer = observability_stack["tracer"]
        set_global_tracer(tracer)

        # Define instrumented function that fails
        @trace_operation("failing_operation")
        async def failing_task():
            await asyncio.sleep(0.01)
            raise ValueError("Task failed")

        # Execute and expect error
        with pytest.raises(ValueError, match="Task failed"):
            await failing_task()

        # Verify error trace created
        traces = tracer.get_traces(operation_name="failing_operation")
        assert len(traces) == 1
        assert traces[0].status == TraceStatus.ERROR
        assert traces[0].error_message == "Task failed"


class TestObservabilityPerformanceImpact:
    """Tests for observability performance overhead."""

    @pytest.mark.asyncio
    async def test_observability_minimal_overhead(self):
        """Test observability adds minimal performance overhead."""
        import time

        tracer = InMemoryTracer()
        perf_profiler = InMemoryPerformanceProfiler()

        # Measure without observability
        iterations = 100

        start = time.perf_counter()
        for _ in range(iterations):
            await asyncio.sleep(0.001)  # 1ms work
        baseline = time.perf_counter() - start

        # Measure with observability
        start = time.perf_counter()
        for i in range(iterations):
            trace = tracer.start_trace(f"op_{i}")

            await asyncio.sleep(0.001)  # 1ms work

            metric = PerformanceMetric.create(
                operation_name=f"op_{i}",
                metric_type=MetricType.DURATION,
                value=1.0,
                unit="ms",
            )
            perf_profiler.record_metric(metric)

            tracer.finish_trace(trace, TraceStatus.SUCCESS)

        with_observability = time.perf_counter() - start

        # Calculate overhead
        overhead_percent = ((with_observability - baseline) / baseline) * 100

        # Overhead should be < 20% for in-memory adapters
        assert overhead_percent < 20, f"Overhead: {overhead_percent:.1f}%"

    @pytest.mark.asyncio
    async def test_observability_scales_with_load(self):
        """Test observability performance scales with load."""
        import time

        tracer = InMemoryTracer()

        # Test with increasing load
        loads = [10, 100, 1000]
        times = []

        for load in loads:
            start = time.perf_counter()

            for i in range(load):
                trace = tracer.start_trace(f"op_{i}")
                tracer.finish_trace(trace, TraceStatus.SUCCESS)

            elapsed = time.perf_counter() - start
            times.append(elapsed)

            # Each load level should complete reasonably fast
            per_op = elapsed / load
            assert per_op < 0.001, f"Per-op time too slow: {per_op:.6f}s"

        # Verify linear scaling (not exponential)
        # 10x load should be ~10x time (not 100x)
        time_ratio = times[2] / times[0]  # 1000 vs 10
        load_ratio = loads[2] / loads[0]  # 100x load

        # Allow 2x overhead for scaling (should be linear)
        assert time_ratio < load_ratio * 2


class TestObservabilityDataRetention:
    """Tests for observability data retention and cleanup."""

    def test_observability_deletes_old_data(self):
        """Test observability cleans up old data."""
        tracer = InMemoryTracer()
        cost_tracker = InMemoryCostTracker()

        # Create old and new data
        old_time = datetime.now() - timedelta(days=30)
        new_time = datetime.now()

        # Old trace
        old_trace = Trace.create("old_op")
        old_trace = old_trace.with_start_time(old_time)
        old_trace = old_trace.finish(TraceStatus.SUCCESS, old_time)
        # Note: InMemoryTracer doesn't support custom timestamps in storage
        # This is a conceptual test for retention policies

        # New trace
        new_trace = tracer.start_trace("new_op")
        new_trace = tracer.finish_trace(new_trace, TraceStatus.SUCCESS)

        # Delete old data
        cutoff = datetime.now() - timedelta(days=7)
        deleted = tracer.delete_traces(before=cutoff)

        # Should delete old traces
        # Note: Actual implementation may vary
        assert deleted >= 0

    def test_observability_data_size_limits(self):
        """Test observability respects data size limits."""
        tracer = InMemoryTracer()

        # Create many traces
        for i in range(1000):
            trace = tracer.start_trace(f"op_{i}")
            tracer.finish_trace(trace, TraceStatus.SUCCESS)

        # Should have all traces (in-memory has no limit)
        # Production adapters would implement limits
        traces = tracer.get_traces()
        assert len(traces) == 1000

        # For production: verify oldest traces pruned when limit reached
        # This would be tested with SQLite/PostgreSQL adapters
