#!/usr/bin/env python3
"""
Test the agent performance measurement system

Validates:
1. Scoring functions work correctly
2. Metrics aggregation is accurate
3. Dashboard loads data properly
4. File I/O works

Usage:
    python test_metrics_system.py
"""

import sys
import json
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from test_agent_performance import (
    score_quality,
    score_specificity,
    estimate_cost,
    calculate_percentile,
    aggregate_metrics,
    TaskResult,
)
from agent_metrics_dashboard import AgentMetricsDashboard


def test_quality_scoring():
    """Test quality scoring function"""
    print("Testing quality scoring...")
    
    # Test cases
    test_cases = [
        {
            "output": "Short",
            "task": "Test task",
            "agent": "python-engineer",
            "expected_range": (1.0, 5.0),
            "description": "Too short"
        },
        {
            "output": """
# Refactoring Plan

Apply SOLID principles to src/routing/team_router.py:

1. **Single Responsibility Principle (SRP)**:
   - Extract routing logic from TeamRouter class
   - Create separate DomainClassifier class (line 45-67)
   
2. **Implementation**:
```python
class DomainClassifier:
    def classify(self, task: Task) -> str:
        # Classification logic here
        pass
```

3. **Benefits**:
   - Easier to test
   - Better separation of concerns
   - Follows Clean Architecture
""",
            "task": "Apply SOLID principles to src/routing/team_router.py",
            "agent": "python-engineer",
            "expected_range": (7.0, 10.0),
            "description": "High quality with code, structure, specificity"
        },
        {
            "output": "I think you should refactor the code to make it better.",
            "task": "Refactor code",
            "agent": "python-engineer",
            "expected_range": (3.0, 6.0),
            "description": "Vague, no specifics"
        },
    ]
    
    passed = 0
    for i, test in enumerate(test_cases, 1):
        score = score_quality(test["output"], test["task"], test["agent"])
        min_score, max_score = test["expected_range"]
        
        if min_score <= score <= max_score:
            print(f"  ✓ Test {i}: {test['description']} - Score: {score:.1f}")
            passed += 1
        else:
            print(f"  ✗ Test {i}: {test['description']} - Score: {score:.1f} (expected {min_score}-{max_score})")
    
    print(f"  Quality Scoring: {passed}/{len(test_cases)} passed\n")
    return passed == len(test_cases)


def test_specificity_scoring():
    """Test specificity scoring function"""
    print("Testing specificity scoring...")
    
    test_cases = [
        {
            "output": "You should improve the code.",
            "expected_range": (0.0, 20.0),
            "description": "No specifics"
        },
        {
            "output": """
Refactor src/adapters/agent/llm_executor.py:
- Extract error handling (line 45-67)
- Create ErrorHandler class
- Update execute() method (line 123)
- Add type hints: def handle_error(self, error: Exception) -> None
""",
            "expected_range": (40.0, 100.0),
            "description": "High specificity with file paths, line numbers, code"
        },
    ]
    
    passed = 0
    for i, test in enumerate(test_cases, 1):
        score = score_specificity(test["output"])
        min_score, max_score = test["expected_range"]
        
        if min_score <= score <= max_score:
            print(f"  ✓ Test {i}: {test['description']} - Score: {score:.1f}%")
            passed += 1
        else:
            print(f"  ✗ Test {i}: {test['description']} - Score: {score:.1f}% (expected {min_score}-{max_score})")
    
    print(f"  Specificity Scoring: {passed}/{len(test_cases)} passed\n")
    return passed == len(test_cases)


def test_cost_estimation():
    """Test cost estimation function"""
    print("Testing cost estimation...")
    
    test_cases = [
        {"tokens": 1000, "model": "gpt-4", "expected_range": (0.04, 0.06)},
        {"tokens": 1000, "model": "gpt-3.5", "expected_range": (0.001, 0.003)},
        {"tokens": 1000, "model": "claude-sonnet", "expected_range": (0.008, 0.012)},
    ]
    
    passed = 0
    for i, test in enumerate(test_cases, 1):
        cost = estimate_cost(test["tokens"], test["model"])
        min_cost, max_cost = test["expected_range"]
        
        if min_cost <= cost <= max_cost:
            print(f"  ✓ Test {i}: {test['model']} - Cost: ${cost:.4f}")
            passed += 1
        else:
            print(f"  ✗ Test {i}: {test['model']} - Cost: ${cost:.4f} (expected ${min_cost}-${max_cost})")
    
    print(f"  Cost Estimation: {passed}/{len(test_cases)} passed\n")
    return passed == len(test_cases)


def test_percentile_calculation():
    """Test percentile calculation"""
    print("Testing percentile calculation...")
    
    values = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]
    
    test_cases = [
        {"percentile": 50, "expected": 5.0},
        {"percentile": 95, "expected": 9.0},
        {"percentile": 0, "expected": 1.0},
        {"percentile": 100, "expected": 10.0},
    ]
    
    passed = 0
    for test in test_cases:
        result = calculate_percentile(values, test["percentile"])
        if abs(result - test["expected"]) < 1.0:  # Allow some tolerance
            print(f"  ✓ P{test['percentile']}: {result:.1f}")
            passed += 1
        else:
            print(f"  ✗ P{test['percentile']}: {result:.1f} (expected {test['expected']})")
    
    print(f"  Percentile Calculation: {passed}/{len(test_cases)} passed\n")
    return passed == len(test_cases)


def test_metrics_aggregation():
    """Test metrics aggregation"""
    print("Testing metrics aggregation...")
    
    # Create sample results
    results = [
        TaskResult(
            task_id="test-01",
            description="Test task 1",
            agent_role="python-engineer",
            success=True,
            duration_seconds=10.0,
            quality_score=8.0,
            specificity_score=75.0,
            token_count=1000,
            cost_estimate=0.05,
        ),
        TaskResult(
            task_id="test-02",
            description="Test task 2",
            agent_role="python-engineer",
            success=True,
            duration_seconds=15.0,
            quality_score=7.0,
            specificity_score=65.0,
            token_count=1200,
            cost_estimate=0.06,
        ),
        TaskResult(
            task_id="test-03",
            description="Test task 3",
            agent_role="python-engineer",
            success=False,
            duration_seconds=5.0,
            quality_score=3.0,
            specificity_score=20.0,
            token_count=500,
            cost_estimate=0.025,
            error="Test error",
        ),
    ]
    
    metrics = aggregate_metrics(results)
    
    tests_passed = 0
    total_tests = 5
    
    # Check completion rate (2/3 = 66.67%)
    if 65.0 <= metrics.completion_rate <= 68.0:
        print(f"  ✓ Completion rate: {metrics.completion_rate:.1f}%")
        tests_passed += 1
    else:
        print(f"  ✗ Completion rate: {metrics.completion_rate:.1f}% (expected ~66.7%)")
    
    # Check avg quality (successful only: (8.0 + 7.0) / 2 = 7.5)
    if 7.4 <= metrics.avg_quality_score <= 7.6:
        print(f"  ✓ Avg quality: {metrics.avg_quality_score:.1f}/10")
        tests_passed += 1
    else:
        print(f"  ✗ Avg quality: {metrics.avg_quality_score:.1f}/10 (expected ~7.5)")
    
    # Check total cost
    expected_cost = 0.05 + 0.06 + 0.025
    if abs(metrics.total_cost - expected_cost) < 0.01:
        print(f"  ✓ Total cost: ${metrics.total_cost:.4f}")
        tests_passed += 1
    else:
        print(f"  ✗ Total cost: ${metrics.total_cost:.4f} (expected ${expected_cost:.4f})")
    
    # Check cost per task
    expected_cost_per_task = expected_cost / 3
    if abs(metrics.cost_per_task - expected_cost_per_task) < 0.01:
        print(f"  ✓ Cost per task: ${metrics.cost_per_task:.4f}")
        tests_passed += 1
    else:
        print(f"  ✗ Cost per task: ${metrics.cost_per_task:.4f} (expected ${expected_cost_per_task:.4f})")
    
    # Check agent role
    if metrics.agent_role == "python-engineer":
        print(f"  ✓ Agent role: {metrics.agent_role}")
        tests_passed += 1
    else:
        print(f"  ✗ Agent role: {metrics.agent_role} (expected python-engineer)")
    
    print(f"  Metrics Aggregation: {tests_passed}/{total_tests} passed\n")
    return tests_passed == total_tests


def test_dashboard_loading():
    """Test dashboard data loading"""
    print("Testing dashboard loading...")
    
    # Create test data directory
    test_dir = Path("data/agent_performance_test")
    test_dir.mkdir(parents=True, exist_ok=True)
    
    # Create sample data file
    sample_data = {
        "timestamp": "2025-10-16T14:30:00",
        "metrics": [
            {
                "agent_role": "python-engineer",
                "total_tasks": 20,
                "completion_rate": 85.0,
                "avg_quality_score": 7.5,
                "avg_latency_p50": 12.0,
                "avg_latency_p95": 25.0,
                "avg_specificity": 70.0,
                "total_cost": 0.85,
                "cost_per_task": 0.0425,
                "timestamp": "2025-10-16T14:30:00"
            }
        ]
    }
    
    test_file = test_dir / "test_results.json"
    with open(test_file, "w") as f:
        json.dump(sample_data, f)
    
    # Test dashboard loading
    try:
        dashboard = AgentMetricsDashboard(str(test_dir))
        
        if len(dashboard.metrics_history) == 1:
            print(f"  ✓ Loaded 1 metric")
        else:
            print(f"  ✗ Loaded {len(dashboard.metrics_history)} metrics (expected 1)")
            return False
        
        latest = dashboard.get_latest_metrics()
        if "python-engineer" in latest:
            print(f"  ✓ Found python-engineer metrics")
        else:
            print(f"  ✗ python-engineer not found in latest metrics")
            return False
        
        # Clean up
        test_file.unlink()
        test_dir.rmdir()
        
        print(f"  Dashboard Loading: 2/2 passed\n")
        return True
        
    except Exception as e:
        print(f"  ✗ Dashboard loading failed: {e}\n")
        # Clean up on error
        if test_file.exists():
            test_file.unlink()
        if test_dir.exists():
            test_dir.rmdir()
        return False


def main():
    """Run all tests"""
    print("="*80)
    print("AGENT METRICS SYSTEM TESTS")
    print("="*80 + "\n")
    
    results = []
    
    results.append(("Quality Scoring", test_quality_scoring()))
    results.append(("Specificity Scoring", test_specificity_scoring()))
    results.append(("Cost Estimation", test_cost_estimation()))
    results.append(("Percentile Calculation", test_percentile_calculation()))
    results.append(("Metrics Aggregation", test_metrics_aggregation()))
    results.append(("Dashboard Loading", test_dashboard_loading()))
    
    print("="*80)
    print("SUMMARY")
    print("="*80)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {name}")
    
    print(f"\nTotal: {passed}/{total} passed ({passed/total*100:.0f}%)")
    
    if passed == total:
        print("\n✅ All tests passed! System is ready to use.")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Please review.")
        return 1


if __name__ == "__main__":
    sys.exit(main())

