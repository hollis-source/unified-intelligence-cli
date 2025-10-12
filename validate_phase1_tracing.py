#!/usr/bin/env python3
"""Manual validation script for P1.3 Phase 1 tracing implementation.

Tests that tracing entities, adapter, and decorator work correctly
without requiring pytest or test directory permissions.

Run: python validate_phase1_tracing.py
"""

import asyncio
import sys
from datetime import datetime, timedelta

# Add src to path
sys.path.insert(0, '/home/ui-cli_jake/unified-intelligence-cli')

from src.observability.entities import Trace, Span, TraceStatus
from src.observability.adapters import InMemoryTracer
from src.observability.decorators import trace_operation, set_global_tracer


def print_test(name: str, passed: bool):
    """Print test result."""
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"  {status}: {name}")
    return passed


def validate_entities() -> bool:
    """Validate Trace, Span, TraceStatus entities."""
    print("\n🧪 Validating Entities...")
    all_passed = True

    # Test 1: TraceStatus enum
    all_passed &= print_test(
        "TraceStatus.SUCCESS not failure",
        not TraceStatus.SUCCESS.is_failure()
    )
    all_passed &= print_test(
        "TraceStatus.ERROR is failure",
        TraceStatus.ERROR.is_failure()
    )

    # Test 2: Span creation
    try:
        span = Span(
            span_id="test-span",
            trace_id="test-trace",
            parent_span_id=None,
            operation_name="test.operation",
            start_time=datetime.now(),
        )
        all_passed &= print_test("Span creation", True)
    except Exception as e:
        all_passed &= print_test(f"Span creation: {e}", False)

    # Test 3: Span immutability
    try:
        span.status = TraceStatus.ERROR
        all_passed &= print_test("Span immutability", False)
    except AttributeError:
        all_passed &= print_test("Span immutability (frozen)", True)

    # Test 4: Span validation (empty span_id)
    try:
        Span(
            span_id="",
            trace_id="test-trace",
            parent_span_id=None,
            operation_name="test",
            start_time=datetime.now(),
        )
        all_passed &= print_test("Span validation (empty ID)", False)
    except ValueError:
        all_passed &= print_test("Span validation (empty ID raises)", True)

    # Test 5: Span duration calculation
    start = datetime.now()
    end = start + timedelta(milliseconds=100)
    span = Span(
        span_id="span-1",
        trace_id="trace-1",
        parent_span_id=None,
        operation_name="test",
        start_time=start,
        end_time=end,
    )
    duration = span.duration_ms()
    all_passed &= print_test(
        "Span duration calculation",
        duration is not None and 90 < duration < 110
    )

    # Test 6: Trace factory method
    trace1 = Trace.create("test.operation")
    trace2 = Trace.create("test.operation")
    all_passed &= print_test(
        "Trace.create() generates unique IDs",
        trace1.trace_id != trace2.trace_id and len(trace1.trace_id) == 36
    )

    # Test 7: Trace immutability
    try:
        trace1.status = TraceStatus.ERROR
        all_passed &= print_test("Trace immutability", False)
    except AttributeError:
        all_passed &= print_test("Trace immutability (frozen)", True)

    # Test 8: Trace.finish()
    trace = Trace.create("test")
    finished = trace.finish(TraceStatus.SUCCESS)
    all_passed &= print_test(
        "Trace.finish() creates new trace",
        not trace.is_complete() and finished.is_complete()
    )

    # Test 9: Trace.add_span()
    trace = Trace.create("test")
    span = Span(
        span_id="span-1",
        trace_id=trace.trace_id,
        parent_span_id=None,
        operation_name="child",
        start_time=datetime.now(),
    )
    new_trace = trace.add_span(span)
    all_passed &= print_test(
        "Trace.add_span() creates new trace",
        trace.span_count() == 0 and new_trace.span_count() == 1
    )

    # Test 10: Trace.has_errors()
    error_span = Span(
        span_id="span-2",
        trace_id=trace.trace_id,
        parent_span_id=None,
        operation_name="error_op",
        start_time=datetime.now(),
        status=TraceStatus.ERROR,
    )
    trace_with_error = trace.add_span(error_span)
    all_passed &= print_test(
        "Trace.has_errors() detects span errors",
        trace_with_error.has_errors()
    )

    return all_passed


def validate_in_memory_tracer() -> bool:
    """Validate InMemoryTracer adapter."""
    print("\n🧪 Validating InMemoryTracer...")
    all_passed = True

    tracer = InMemoryTracer()

    # Test 1: start_trace
    trace = tracer.start_trace("test.operation", tags={"user": "alice"})
    all_passed &= print_test(
        "start_trace() creates trace",
        trace is not None and trace.operation_name == "test.operation"
    )
    all_passed &= print_test(
        "start_trace() stores trace",
        tracer.get_trace(trace.trace_id) == trace
    )

    # Test 2: finish_trace
    finished = tracer.finish_trace(trace, TraceStatus.SUCCESS)
    all_passed &= print_test(
        "finish_trace() completes trace",
        finished.is_complete() and finished.status == TraceStatus.SUCCESS
    )

    # Test 3: add_span
    trace2 = tracer.start_trace("test.operation2")
    updated_trace, span = tracer.add_span(trace2, "child.operation")
    all_passed &= print_test(
        "add_span() creates span",
        span is not None and span.operation_name == "child.operation"
    )
    all_passed &= print_test(
        "add_span() updates trace",
        updated_trace.span_count() == 1
    )

    # Test 4: finish_span
    updated_trace2, finished_span = tracer.finish_span(updated_trace, span, TraceStatus.SUCCESS)
    all_passed &= print_test(
        "finish_span() completes span",
        finished_span.is_complete()
    )

    # Test 5: get_active_traces
    trace3 = tracer.start_trace("test.active")
    active_traces = tracer.get_active_traces()
    all_passed &= print_test(
        "get_active_traces() returns unfinished traces",
        trace3 in active_traces and finished not in active_traces
    )

    # Test 6: export_traces
    traces_to_export = [finished, updated_trace2]
    tracer.export_traces(traces_to_export)
    exported = tracer.get_exported_traces()
    all_passed &= print_test(
        "export_traces() stores exported traces",
        len(exported) == 2
    )

    # Test 7: Validation (parent span not found)
    try:
        tracer.add_span(trace3, "child", parent_span_id="nonexistent")
        all_passed &= print_test("add_span() validates parent", False)
    except ValueError:
        all_passed &= print_test("add_span() validates parent (raises)", True)

    return all_passed


def validate_decorator_sync() -> bool:
    """Validate @trace_operation decorator with sync functions."""
    print("\n🧪 Validating Decorator (Sync)...")
    all_passed = True

    tracer = InMemoryTracer()
    set_global_tracer(tracer)

    # Test 1: Basic sync function
    @trace_operation("test.sync.basic")
    def basic_function(x: int) -> int:
        return x * 2

    result = basic_function(5)
    all_passed &= print_test(
        "Decorator doesn't break function",
        result == 10
    )

    traces = tracer.get_all_traces()
    all_passed &= print_test(
        "Decorator creates trace",
        len(traces) == 1
    )
    all_passed &= print_test(
        "Trace has correct operation name",
        traces[0].operation_name == "test.sync.basic"
    )
    all_passed &= print_test(
        "Trace marked as SUCCESS",
        traces[0].status == TraceStatus.SUCCESS
    )

    # Test 2: Function with error
    tracer.clear()

    @trace_operation("test.sync.error")
    def failing_function():
        raise ValueError("Test error")

    try:
        failing_function()
    except ValueError:
        pass

    traces = tracer.get_all_traces()
    all_passed &= print_test(
        "Decorator captures errors",
        len(traces) == 1 and traces[0].status == TraceStatus.ERROR
    )
    all_passed &= print_test(
        "Error message captured",
        traces[0].error_message is not None and "ValueError" in traces[0].error_message
    )

    # Test 3: Tag extraction
    tracer.clear()

    @trace_operation("test.sync.tags")
    def function_with_args(username: str, age: int):
        return f"{username}:{age}"

    function_with_args("alice", 30)
    traces = tracer.get_all_traces()
    all_passed &= print_test(
        "Decorator extracts argument tags",
        "arg.username" in traces[0].tags and traces[0].tags["arg.username"] == "alice"
    )

    return all_passed


async def validate_decorator_async() -> bool:
    """Validate @trace_operation decorator with async functions."""
    print("\n🧪 Validating Decorator (Async)...")
    all_passed = True

    tracer = InMemoryTracer()
    set_global_tracer(tracer)

    # Test 1: Basic async function
    @trace_operation("test.async.basic")
    async def async_function(x: int) -> int:
        await asyncio.sleep(0.01)
        return x * 3

    result = await async_function(5)
    all_passed &= print_test(
        "Decorator works with async",
        result == 15
    )

    traces = tracer.get_all_traces()
    all_passed &= print_test(
        "Async function creates trace",
        len(traces) == 1 and traces[0].status == TraceStatus.SUCCESS
    )

    # Test 2: Async function with error
    tracer.clear()

    @trace_operation("test.async.error")
    async def async_failing():
        await asyncio.sleep(0.01)
        raise RuntimeError("Async error")

    try:
        await async_failing()
    except RuntimeError:
        pass

    traces = tracer.get_all_traces()
    all_passed &= print_test(
        "Decorator captures async errors",
        len(traces) == 1 and traces[0].status == TraceStatus.ERROR
    )

    # Test 3: Async timeout handling
    tracer.clear()

    @trace_operation("test.async.timeout")
    async def async_timeout():
        raise asyncio.TimeoutError("Operation timed out")

    try:
        await async_timeout()
    except asyncio.TimeoutError:
        pass

    traces = tracer.get_all_traces()
    all_passed &= print_test(
        "Decorator handles TimeoutError",
        len(traces) == 1 and traces[0].status == TraceStatus.TIMEOUT
    )

    # Test 4: Async cancellation
    tracer.clear()

    @trace_operation("test.async.cancel")
    async def async_cancel():
        raise asyncio.CancelledError()

    try:
        await async_cancel()
    except asyncio.CancelledError:
        pass

    traces = tracer.get_all_traces()
    all_passed &= print_test(
        "Decorator handles CancelledError",
        len(traces) == 1 and traces[0].status == TraceStatus.CANCELLED
    )

    return all_passed


def validate_integration() -> bool:
    """Validate integration patterns."""
    print("\n🧪 Validating Integration...")
    all_passed = True

    tracer = InMemoryTracer()
    set_global_tracer(tracer)

    # Test: Complex workflow with parent/child operations
    @trace_operation("workflow.main")
    def main_workflow():
        sub_operation()
        return "done"

    @trace_operation("workflow.sub")
    def sub_operation():
        return "sub_done"

    result = main_workflow()
    all_passed &= print_test(
        "Complex workflow completes",
        result == "done"
    )

    traces = tracer.get_all_traces()
    all_passed &= print_test(
        "Multiple operations traced",
        len(traces) == 2
    )

    operation_names = {t.operation_name for t in traces}
    all_passed &= print_test(
        "All operations captured",
        "workflow.main" in operation_names and "workflow.sub" in operation_names
    )

    return all_passed


def main():
    """Run all validation tests."""
    print("=" * 60)
    print("P1.3 Phase 1 - Tracing Implementation Validation")
    print("=" * 60)

    results = {
        "Entities": validate_entities(),
        "InMemoryTracer": validate_in_memory_tracer(),
        "Decorator (Sync)": validate_decorator_sync(),
        "Decorator (Async)": asyncio.run(validate_decorator_async()),
        "Integration": validate_integration(),
    }

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    all_passed = all(results.values())
    for category, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {category}")

    print("=" * 60)

    if all_passed:
        print("🎉 ALL VALIDATIONS PASSED")
        print("\nP1.3 Phase 1 implementation is working correctly!")
        print("Ready to proceed to Phase 2 (Cost Tracking) or add automated tests.")
        return 0
    else:
        print("❌ SOME VALIDATIONS FAILED")
        print("\nPlease fix issues before proceeding.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
