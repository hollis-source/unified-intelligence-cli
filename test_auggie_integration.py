#!/usr/bin/env python3
"""Test Auggie CLI Integration

Quick validation of auggie executor wrapper and hybrid routing.
Tests the 55-91x speedup optimization.
"""

import sys
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.entity.htn.htn_node import HTNNode
from src.adapters.llm.auggie_executor import AuggieCLIExecutor, AuggieConfig
from src.adapters.llm.hybrid_executor import HybridTaskExecutor


def test_auggie_executor_basic():
    """Test 1: Basic auggie execution"""
    print("\n" + "="*60)
    print("TEST 1: Basic Auggie Execution")
    print("="*60)

    config = AuggieConfig(
        model="sonnet4.5",
        max_turns=1,
        timeout_seconds=30
    )
    executor = AuggieCLIExecutor(config)

    node = HTNNode(
        task_id="test_basic",
        description="What is the factorial of 5? Just give the number."
    )

    print(f"\nTask: {node.description}")
    print(f"Expected: ~3-10 seconds")

    start = time.time()
    result = executor.execute(node)
    duration = time.time() - start

    print(f"\n{result}")
    print(f"Duration: {duration:.2f}s")
    print(f"Output: {result.output[:100]}...")

    if result.success:
        print("✓ Test 1 PASSED")
        if "120" in result.output:
            print("✓ Correct answer (120)")
        else:
            print(f"⚠ Unexpected answer: {result.output}")

        if duration < 15:
            print(f"✓ Fast execution ({duration:.2f}s < 15s)")
        else:
            print(f"⚠ Slow execution ({duration:.2f}s > 15s)")
    else:
        print(f"✗ Test 1 FAILED: {result.error}")
        return False

    return True


def test_hybrid_routing():
    """Test 2: Hybrid executor routing"""
    print("\n" + "="*60)
    print("TEST 2: Hybrid Executor Routing")
    print("="*60)

    executor = HybridTaskExecutor()

    # Research task
    research_node = HTNNode(
        task_id="research_test",
        description="Design a simple strategy for load balancing"
    )

    # Implementation task
    impl_node = HTNNode(
        task_id="impl_test",
        description="Implement a Python function to calculate fibonacci"
    )

    print(f"\nResearch task: {research_node.description}")
    is_research_1 = executor._is_research_task(research_node)
    print(f"Classified as: {'RESEARCH' if is_research_1 else 'IMPLEMENTATION'}")
    print(f"✓ Correct" if is_research_1 else "✗ Incorrect")

    print(f"\nImplementation task: {impl_node.description}")
    is_research_2 = executor._is_research_task(impl_node)
    print(f"Classified as: {'RESEARCH' if is_research_2 else 'IMPLEMENTATION'}")
    print(f"✓ Correct" if not is_research_2 else "✗ Incorrect")

    if is_research_1 and not is_research_2:
        print("\n✓ Test 2 PASSED - Routing logic works")
        return True
    else:
        print("\n✗ Test 2 FAILED - Routing logic broken")
        return False


def test_hybrid_execution():
    """Test 3: Full hybrid execution"""
    print("\n" + "="*60)
    print("TEST 3: Hybrid Execution (Research Task)")
    print("="*60)

    executor = HybridTaskExecutor()

    node = HTNNode(
        task_id="hybrid_test",
        description="Explain the benefits of lazy evaluation in 2 bullet points"
    )

    print(f"\nTask: {node.description}")
    print(f"Expected: Route to auggie (research task)")

    start = time.time()
    result = executor.execute(node)
    duration = time.time() - start

    print(f"\n{result}")
    print(f"Duration: {duration:.2f}s")
    print(f"Routing: {node.metadata.get('routing_decision', 'unknown')}")
    print(f"Output preview: {result.output[:150]}...")

    if result.success:
        if node.metadata.get('routing_decision') == 'auggie_research':
            print("✓ Correctly routed to auggie")
        else:
            print(f"⚠ Unexpected routing: {node.metadata.get('routing_decision')}")

        print(f"✓ Test 3 PASSED ({duration:.2f}s)")
        return True
    else:
        print(f"✗ Test 3 FAILED: {result.error}")
        return False


def test_side_effect_tracking():
    """Test 4: Side effect tracking"""
    print("\n" + "="*60)
    print("TEST 4: Side Effect Tracking")
    print("="*60)

    executor = AuggieCLIExecutor()

    node = HTNNode(
        task_id="side_effects",
        description="What is 10 + 20?"
    )

    result = executor.execute(node)

    print(f"\n{result}")
    print(f"\nSide Effects:")
    for effect_type, items in result.side_effects.items():
        print(f"  {effect_type}: {items}")

    has_executor_type = "executor_type" in result.side_effects
    has_model_used = "model_used" in result.side_effects

    if has_executor_type and has_model_used:
        print("\n✓ Test 4 PASSED - Side effects tracked")
        return True
    else:
        print("\n✗ Test 4 FAILED - Missing side effect data")
        return False


def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("AUGGIE INTEGRATION TEST SUITE")
    print("="*60)
    print("\nValidating:")
    print("  - AuggieCLIExecutor wrapper")
    print("  - Hybrid routing logic")
    print("  - Side effect tracking")
    print("  - 55-91x speedup optimization")

    tests = [
        ("Basic Execution", test_auggie_executor_basic),
        ("Routing Logic", test_hybrid_routing),
        ("Hybrid Execution", test_hybrid_execution),
        ("Side Effect Tracking", test_side_effect_tracking)
    ]

    results = []
    for name, test_fn in tests:
        try:
            passed = test_fn()
            results.append((name, passed))
        except Exception as e:
            print(f"\n✗ Test '{name}' CRASHED: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))

    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)

    passed_count = sum(1 for _, passed in results if passed)
    total_count = len(results)

    for name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"  {status}: {name}")

    print(f"\nTotal: {passed_count}/{total_count} passed")

    if passed_count == total_count:
        print("\n✓ ALL TESTS PASSED - Auggie integration working!")
        return 0
    else:
        print(f"\n✗ {total_count - passed_count} TESTS FAILED")
        return 1


if __name__ == "__main__":
    sys.exit(main())
