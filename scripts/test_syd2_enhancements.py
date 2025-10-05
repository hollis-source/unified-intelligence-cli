#!/usr/bin/env python3
"""
Integration test for SYD2 Agent Enhancements Prototype
Validates that enhancements integrate properly with SYD2 agent structure.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from syd2_enhancements_prototype import (
    ErrorHandler,
    PerformanceOptimizer,
    DSLIntegrationHook,
    create_enhancement_suite,
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
)


async def test_error_handler():
    """Test ErrorHandler functionality."""
    print("\n=== Testing ErrorHandler ===")

    error_handler = ErrorHandler(max_retries=3, base_delay=0.1)

    # Test 1: Retry with success
    attempt_count = [0]
    async def flaky_ssh_command():
        attempt_count[0] += 1
        if attempt_count[0] < 3:
            raise ConnectionError(f"SSH connection failed (attempt {attempt_count[0]})")
        return {"exit_code": 0, "stdout": "Success", "stderr": "", "latency": 0.5}

    result = await error_handler.retry_with_backoff(flaky_ssh_command)
    assert result["exit_code"] == 0, "Retry should eventually succeed"
    print(f"✅ Retry test passed (succeeded after {attempt_count[0]} attempts)")

    # Test 2: Graceful degradation
    async def primary_func():
        raise TimeoutError("Primary function timed out")

    async def fallback_func():
        return {"status": "degraded", "result": "Fallback executed"}

    result = await error_handler.degrade_gracefully(primary_func, fallback_func)
    assert result["status"] == "degraded", "Should fall back on primary failure"
    print("✅ Graceful degradation test passed")

    # Test 3: Pattern detection
    for i in range(6):
        error_handler._log_error("ssh_command", "ConnectionError: Connection refused", i+1)

    patterns = error_handler.detect_patterns()
    assert "ConnectionError" in patterns, "Should detect connection error pattern"
    assert patterns["ConnectionError"].frequency >= 5, "Should track frequency"
    print(f"✅ Pattern detection test passed (detected {len(patterns)} patterns)")


async def test_performance_optimizer():
    """Test PerformanceOptimizer functionality."""
    print("\n=== Testing PerformanceOptimizer ===")

    perf_optimizer = PerformanceOptimizer(max_concurrent=5, default_cache_ttl=60)

    # Test 1: Caching
    compute_count = [0]
    def expensive_computation():
        compute_count[0] += 1
        return f"Computed result {compute_count[0]}"

    result1 = perf_optimizer.cache_get("test_key", expensive_computation)
    result2 = perf_optimizer.cache_get("test_key", expensive_computation)

    assert compute_count[0] == 1, "Should only compute once (second is cached)"
    assert result1 == result2, "Cached result should match original"
    print(f"✅ Caching test passed (cache hit rate: {perf_optimizer._calculate_cache_hit_rate():.2f})")

    # Test 2: Async execution
    async def slow_task(task_id):
        await asyncio.sleep(0.05)
        return f"Task {task_id} completed"

    results = await asyncio.gather(
        perf_optimizer.async_execute(slow_task, 1),
        perf_optimizer.async_execute(slow_task, 2),
        perf_optimizer.async_execute(slow_task, 3),
    )

    assert len(results) == 3, "Should complete all async tasks"
    print(f"✅ Async execution test passed ({len(results)} tasks completed)")

    # Test 3: Metrics tracking
    @perf_optimizer.track_metrics("test_operation")
    async def tracked_task():
        await asyncio.sleep(0.01)
        return "Tracked result"

    await tracked_task()
    await tracked_task()

    stats = perf_optimizer.get_metrics_summary()
    assert stats["total_operations"] >= 2, "Should track all operations"
    assert "test_operation" in stats["by_operation"], "Should track by operation name"
    print(f"✅ Metrics tracking test passed (tracked {stats['total_operations']} operations)")


async def test_dsl_integration_hook():
    """Test DSLIntegrationHook functionality."""
    print("\n=== Testing DSLIntegrationHook ===")

    error_handler = ErrorHandler()
    perf_optimizer = PerformanceOptimizer()
    dsl_hook = DSLIntegrationHook(error_handler, perf_optimizer)

    # Test 1: Task start hook
    await dsl_hook.on_task_start("test_task_1")
    print("✅ Task start hook test passed")

    # Test 2: Task error hook
    test_error = ValueError("Test error for pattern detection")
    await dsl_hook.on_task_error("test_task_1", test_error)
    print("✅ Task error hook test passed")

    # Test 3: Enhancement stats
    stats = dsl_hook.get_enhancement_stats()
    assert "error_patterns" in stats, "Should include error patterns"
    assert "performance_metrics" in stats, "Should include performance metrics"
    print(f"✅ Enhancement stats test passed (patterns: {len(stats['error_patterns'])})")


async def test_enhancement_suite_integration():
    """Test complete enhancement suite integration."""
    print("\n=== Testing Enhancement Suite Integration ===")

    # Create suite using factory
    suite = create_enhancement_suite(
        max_retries=3,
        max_concurrent=10,
        cache_ttl=300,
    )

    assert "error_handler" in suite, "Suite should include error handler"
    assert "performance_optimizer" in suite, "Suite should include performance optimizer"
    assert "dsl_hook" in suite, "Suite should include DSL hook"

    error_handler = suite["error_handler"]
    perf_optimizer = suite["performance_optimizer"]
    dsl_hook = suite["dsl_hook"]

    # Simulate SYD2 agent workflow
    async def mock_ssh_command():
        await asyncio.sleep(0.02)
        return {"exit_code": 0, "stdout": "Mock output", "stderr": ""}

    # Execute with retry
    result = await error_handler.retry_with_backoff(mock_ssh_command)
    assert result["exit_code"] == 0, "Should execute successfully"

    # Track with performance optimizer
    @perf_optimizer.track_metrics("ssh_execution")
    async def execute_with_tracking():
        return await mock_ssh_command()

    await execute_with_tracking()

    # Get combined stats
    stats = dsl_hook.get_enhancement_stats()
    assert stats["performance_metrics"]["total_operations"] > 0, "Should track operations"

    print("✅ Enhancement suite integration test passed")
    print(f"   Performance: {stats['performance_metrics']['success_rate']:.1%} success rate")


async def main():
    """Run all integration tests."""
    print("=" * 60)
    print("SYD2 Agent Enhancements - Integration Tests")
    print("=" * 60)

    try:
        await test_error_handler()
        await test_performance_optimizer()
        await test_dsl_integration_hook()
        await test_enhancement_suite_integration()

        print("\n" + "=" * 60)
        print("✅ ALL INTEGRATION TESTS PASSED")
        print("=" * 60)
        print("\nEnhancements are ready for SYD2 agent integration!")

        return 0

    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
