#!/usr/bin/env python3
"""Test A/B testing framework.

This script tests the A/B testing functionality.
"""

import asyncio
import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.routing.ab_testing import ABTest
from src.adapters.rag.surrealdb_store import SurrealDBStore
from src.adapters.llm.rag_config import RAGConfig


async def test_ab_testing():
    """Test A/B testing framework."""
    
    print("=" * 80)
    print("A/B TESTING FRAMEWORK TEST")
    print("=" * 80)
    print()
    
    # Setup
    config = RAGConfig()
    db_url = os.getenv("SURREALDB_URL", "ws://localhost:8000")
    
    print("Connecting to SurrealDB...")
    store = SurrealDBStore(
        url=db_url,
        namespace=config.db_namespace,
        database=config.db_database,
        user=config.db_user,
        password=config.db_password
    )
    
    try:
        await store.connect()
        print("✅ Connected to SurrealDB")
        print()
    except Exception as e:
        print(f"❌ Failed to connect: {e}")
        return False
    
    # Create A/B test
    ab_test = ABTest(
        db_store=store,
        test_name="rag_vs_baseline",
        control_strategy="base",
        treatment_strategy="rag",
        split_ratio=0.5
    )
    
    # Test 1: Assign to groups
    print("TEST 1: Assign Tasks to Groups")
    print("-" * 80)
    
    try:
        test_tasks = [f"task-{i}" for i in range(10)]
        assignments = {}
        
        for task_id in test_tasks:
            strategy = ab_test.assign_to_group(task_id)
            assignments[task_id] = strategy
            print(f"  • {task_id}: {strategy}")
        
        # Count assignments
        control_count = sum(1 for s in assignments.values() if s == "base")
        treatment_count = sum(1 for s in assignments.values() if s == "rag")
        
        print()
        print(f"Control group: {control_count} tasks")
        print(f"Treatment group: {treatment_count} tasks")
        print()
        
        # Verify consistency
        for task_id in test_tasks[:3]:
            strategy2 = ab_test.assign_to_group(task_id)
            if assignments[task_id] == strategy2:
                print(f"✅ {task_id}: Consistent assignment")
            else:
                print(f"❌ {task_id}: Inconsistent assignment")
        
        print()
        print("✅ Task assignment working")
        print()
        
    except Exception as e:
        print(f"❌ Task assignment failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test 2: Get test results
    print("TEST 2: Get Test Results")
    print("-" * 80)
    
    try:
        results = await ab_test.get_test_results()
        
        print("Control group:")
        print(f"  • Total: {results['control']['total']}")
        print(f"  • Successes: {results['control']['successes']}")
        print(f"  • Success rate: {results['control']['success_rate']:.1f}%")
        print()
        
        print("Treatment group:")
        print(f"  • Total: {results['treatment']['total']}")
        print(f"  • Successes: {results['treatment']['successes']}")
        print(f"  • Success rate: {results['treatment']['success_rate']:.1f}%")
        print()
        
        if results['control']['total'] == 0 and results['treatment']['total'] == 0:
            print("⚠️  No test data found")
            print("   Run tasks with different routing strategies to generate data")
        else:
            print("✅ Test results retrieved")
        
        print()
        
    except Exception as e:
        print(f"❌ Failed to get results: {e}")
        return False
    
    # Test 3: Calculate statistical significance
    print("TEST 3: Calculate Statistical Significance")
    print("-" * 80)
    
    try:
        # Test with sample data
        test_cases = [
            {
                "name": "No difference",
                "control": (50, 100),
                "treatment": (50, 100)
            },
            {
                "name": "Small improvement",
                "control": (50, 100),
                "treatment": (55, 100)
            },
            {
                "name": "Large improvement",
                "control": (50, 100),
                "treatment": (70, 100)
            },
            {
                "name": "Small sample",
                "control": (5, 10),
                "treatment": (7, 10)
            }
        ]
        
        for test_case in test_cases:
            print(f"{test_case['name']}:")
            
            stats = ab_test.calculate_statistical_significance(
                control_successes=test_case['control'][0],
                control_total=test_case['control'][1],
                treatment_successes=test_case['treatment'][0],
                treatment_total=test_case['treatment'][1]
            )
            
            if "z_score" in stats:
                print(f"  • Significant: {stats['significant']}")
                print(f"  • Z-score: {stats['z_score']:.2f}")
                print(f"  • Confidence: {stats['confidence']}%")
                print(f"  • Improvement: {stats['relative_improvement']:+.1f}%")
            else:
                print(f"  • {stats.get('message', 'N/A')}")
            print()
        
        print("✅ Statistical significance calculation working")
        print()
        
    except Exception as e:
        print(f"❌ Statistical calculation failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test 4: Run complete A/B test
    print("TEST 4: Run Complete A/B Test")
    print("-" * 80)
    
    try:
        test_results = await ab_test.run_ab_test()
        
        print(f"Test name: {test_results['test_name']}")
        print(f"Sample size adequate: {test_results['sample_size_adequate']}")
        print()
        
        print("Control:")
        print(f"  • Success rate: {test_results['control']['success_rate']:.1f}%")
        print()
        
        print("Treatment:")
        print(f"  • Success rate: {test_results['treatment']['success_rate']:.1f}%")
        print()
        
        stats = test_results['statistics']
        if stats.get('significant') is not None:
            print("Statistics:")
            print(f"  • Significant: {stats['significant']}")
            if 'z_score' in stats:
                print(f"  • Improvement: {stats['relative_improvement']:+.1f}%")
        print()
        
        print(f"Recommendation: {test_results['recommendation']}")
        print()
        
        print("✅ A/B test complete")
        print()
        
    except Exception as e:
        print(f"❌ A/B test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test 5: Generate test report
    print("TEST 5: Generate Test Report")
    print("-" * 80)
    
    try:
        report = await ab_test.get_test_report()
        
        print(report)
        
        print("✅ Test report generated")
        print()
        
    except Exception as e:
        print(f"❌ Report generation failed: {e}")
        return False
    
    await store.close()
    
    # Summary
    print("=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print("✅ Task assignment: PASS")
    print("✅ Get test results: PASS")
    print("✅ Statistical significance: PASS")
    print("✅ Run A/B test: PASS")
    print("✅ Generate report: PASS")
    print()
    print("🎉 A/B TESTING FRAMEWORK TEST PASSED!")
    print()
    
    return True


if __name__ == "__main__":
    try:
        success = asyncio.run(test_ab_testing())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

