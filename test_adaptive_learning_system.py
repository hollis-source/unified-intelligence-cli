"""
Comprehensive test for Adaptive Learning System.

Tests the full architecture:
1. Performance log collection
2. Learning service aggregation
3. Adaptive model selection
4. Cost savings vs static selection

Based on Qwen3-Next-80B-Thinking architectural design.
"""

import asyncio
import os
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

# Add src to path
import sys
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.routing.adaptive_interfaces import (
    PerformanceLog,
    SelectionRequirements,
    SelectionStrategy
)
from src.routing.performance_repository import PerformanceDataRepository
from src.routing.summary_repository import ModelSummaryRepository
from src.routing.learning_service import LearningService
from src.routing.adaptive_selector import AdaptiveModelSelector
from src.routing.model_selector import ModelSelector


async def create_sample_logs(perf_repo: PerformanceDataRepository):
    """
    Create sample performance logs simulating real usage.

    Simulates:
    - qwen3_hf_inference: Fast (1.2s), cheap ($0.001), 100% success for simple tasks
    - qwen3_zerogpu: Medium (14s), free ($0), 100% success for standard tasks
    - qwen3_next_80b_thinking: Slow (48s), expensive ($0.14), 100% success for complex tasks
    - tongyi-local: Medium (20s), moderate ($0.01), 98% success for all tasks
    """
    print("Creating sample performance logs...")

    models = {
        "qwen3_hf_inference": {
            "latency_ms": (800, 1500),  # 0.8-1.5s
            "cost_usd": 0.001,
            "success_rate": 1.0
        },
        "qwen3_zerogpu": {
            "latency_ms": (12000, 16000),  # 12-16s
            "cost_usd": 0.0,
            "success_rate": 1.0
        },
        "qwen3_next_80b_thinking": {
            "latency_ms": (40000, 55000),  # 40-55s
            "cost_usd": 0.14,
            "success_rate": 1.0
        },
        "tongyi-local": {
            "latency_ms": (18000, 22000),  # 18-22s
            "cost_usd": 0.01,
            "success_rate": 0.98
        }
    }

    task_types = {
        "simple_query": ["qwen3_hf_inference", "qwen3_zerogpu"],
        "code_analysis": ["qwen3_hf_inference", "qwen3_zerogpu", "tongyi-local"],
        "complex_reasoning": ["qwen3_next_80b_thinking", "qwen3_zerogpu", "tongyi-local"],
        "architectural_design": ["qwen3_next_80b_thinking"]
    }

    import random

    now = datetime.now()
    total_logs = 0

    for task_type, applicable_models in task_types.items():
        # Simulate 20 tasks per type
        for i in range(20):
            # Pick a model (randomly for simulation)
            model_id = random.choice(applicable_models)
            model_config = models[model_id]

            # Generate latency
            min_lat, max_lat = model_config["latency_ms"]
            latency_ms = random.uniform(min_lat, max_lat)

            # Determine success (based on success rate)
            success = random.random() < model_config["success_rate"]

            # Create log
            log = PerformanceLog(
                model_id=model_id,
                task_type=task_type,
                latency_ms=latency_ms,
                success=success,
                cost_usd=model_config["cost_usd"],
                timestamp=now - timedelta(minutes=random.randint(0, 60)),
                task_description=f"{task_type} example {i+1}"
            )

            await perf_repo.save_performance_log(log)
            total_logs += 1

    print(f"✓ Created {total_logs} sample logs")


async def test_learning_service(
    perf_repo: PerformanceDataRepository,
    summary_repo: ModelSummaryRepository
):
    """Test learning service aggregation."""
    print("\n=== Testing Learning Service ===")

    learning_service = LearningService(
        performance_repo=perf_repo,
        summary_repo=summary_repo,
        min_sample_size=3
    )

    # Update summaries from logs
    updated = learning_service.update_summaries(time_window_minutes=120)
    print(f"✓ Updated {updated} summaries")

    # Get stats
    stats = learning_service.get_learning_stats()
    print(f"  Total summaries: {stats['total_summaries']}")
    print(f"  Total logs: {stats['total_logs']}")
    print(f"  Models tracked: {stats['num_models_tracked']}")
    print(f"  Task types: {stats['num_task_types']}")
    print(f"  Avg sample size: {stats['avg_sample_size']:.1f}")

    # Display summaries
    print("\n  Summaries created:")
    all_summaries = summary_repo.get_all_summaries()
    for summary in all_summaries:
        print(
            f"    {summary.model_id:30} | {summary.task_type:20} | "
            f"Latency: {summary.avg_latency_ms/1000:5.1f}s | "
            f"Success: {summary.success_rate:5.1%} | "
            f"Cost: ${summary.avg_cost_per_task:7.4f} | "
            f"Samples: {summary.sample_size}"
        )

    return learning_service


async def test_adaptive_selection(
    summary_repo: ModelSummaryRepository
):
    """Test adaptive model selection."""
    print("\n=== Testing Adaptive Model Selection ===")

    selector = AdaptiveModelSelector(summary_repo=summary_repo)

    test_cases = [
        {
            "name": "Simple query - minimize cost",
            "task_type": "simple_query",
            "requirements": SelectionRequirements(strategy=SelectionStrategy.MINIMIZE_COST)
        },
        {
            "name": "Simple query - minimize latency",
            "task_type": "simple_query",
            "requirements": SelectionRequirements(strategy=SelectionStrategy.MINIMIZE_LATENCY)
        },
        {
            "name": "Code analysis - balanced",
            "task_type": "code_analysis",
            "requirements": SelectionRequirements(strategy=SelectionStrategy.BALANCED)
        },
        {
            "name": "Code analysis - max latency 2s",
            "task_type": "code_analysis",
            "requirements": SelectionRequirements(
                max_latency_ms=2000,
                strategy=SelectionStrategy.BALANCED
            )
        },
        {
            "name": "Complex reasoning - maximize quality",
            "task_type": "complex_reasoning",
            "requirements": SelectionRequirements(strategy=SelectionStrategy.MAXIMIZE_QUALITY)
        },
        {
            "name": "Complex reasoning - cost < $0.05",
            "task_type": "complex_reasoning",
            "requirements": SelectionRequirements(
                max_cost_per_task=0.05,
                strategy=SelectionStrategy.BALANCED
            )
        },
        {
            "name": "Architectural design - balanced",
            "task_type": "architectural_design",
            "requirements": SelectionRequirements(strategy=SelectionStrategy.BALANCED)
        }
    ]

    for test_case in test_cases:
        model_id = selector.select_model(
            task_type=test_case["task_type"],
            requirements=test_case["requirements"]
        )

        rationale = selector.get_selection_rationale(model_id, test_case["task_type"])

        print(f"\n  {test_case['name']}:")
        print(f"    Selected: {model_id}")

        if "metrics" in rationale:
            metrics = rationale["metrics"]
            print(f"    Latency: {metrics['avg_latency_ms']/1000:.2f}s")
            print(f"    Success: {metrics['success_rate']:.1%}")
            print(f"    Cost: ${metrics['avg_cost_per_task']:.4f}")
            print(f"    Samples: {metrics['sample_size']}")

            if "rankings" in rationale:
                rankings = rationale["rankings"]
                print(f"    Rankings: Cost={rankings['cost_rank']}, Latency={rankings['latency_rank']}, Quality={rankings['quality_rank']}")


async def compare_static_vs_adaptive(
    summary_repo: ModelSummaryRepository
):
    """Compare cost of static vs adaptive selection."""
    print("\n=== Comparing Static vs Adaptive Selection ===")

    static_selector = ModelSelector()
    adaptive_selector = AdaptiveModelSelector(summary_repo=summary_repo)

    # Simulate 100 tasks with distribution:
    # - 60% simple queries
    # - 30% code analysis
    # - 8% complex reasoning
    # - 2% architectural design
    task_distribution = [
        ("simple_query", 60),
        ("code_analysis", 30),
        ("complex_reasoning", 8),
        ("architectural_design", 2)
    ]

    # Static costs from ModelCapabilities
    static_costs_latency = {
        "qwen3_hf_inference": (0.001, 1.2 * 1000),
        "qwen3_zerogpu": (0.0, 13.8 * 1000),
        "qwen3_next_80b_thinking": (0.14, 48.0 * 1000),
        "tongyi-local": (0.01, 20.1 * 1000),
        "grok": (0.02, 5.0 * 1000)
    }

    # Static strategy: Use task description keywords to pick model (simulating manual selection)
    # This is what users do WITHOUT adaptive learning
    static_rules = {
        "simple_query": "qwen3_zerogpu",  # Pick free option for simple tasks
        "code_analysis": "qwen3_zerogpu",  # Pick free option for standard tasks
        "complex_reasoning": "qwen3_zerogpu",  # Still try to save money (wrong choice!)
        "architectural_design": "qwen3_next_80b_thinking"  # Only use expensive for obvious cases
    }

    static_total_cost = 0.0
    adaptive_total_cost = 0.0

    static_total_latency = 0.0
    adaptive_total_latency = 0.0

    for task_type, count in task_distribution:
        for _ in range(count):
            # Static selection (rule-based, what users do manually)
            static_model = static_rules.get(task_type, "qwen3_zerogpu")
            static_cost, static_latency = static_costs_latency.get(static_model, (0.001, 1200))
            static_total_cost += static_cost
            static_total_latency += static_latency

            # Adaptive selection (learned from actual performance)
            adaptive_model = adaptive_selector.select_model(
                task_type=task_type,
                requirements=SelectionRequirements(strategy=SelectionStrategy.BALANCED)
            )

            # Get adaptive cost from summary
            summary = summary_repo.get_summary(adaptive_model, task_type)
            if summary:
                adaptive_total_cost += summary.avg_cost_per_task
                adaptive_total_latency += summary.avg_latency_ms
            else:
                # Fallback
                adaptive_cost, adaptive_latency = static_costs_latency.get(adaptive_model, (0.001, 1200))
                adaptive_total_cost += adaptive_cost
                adaptive_total_latency += adaptive_latency

    print(f"\n  Task distribution: 100 tasks")
    for task_type, count in task_distribution:
        print(f"    {task_type}: {count} tasks ({count}%)")

    print(f"\n  Static Selection (manual rules, prefers free models):")
    print(f"    Strategy: ZeroGPU for most tasks, 80B only for obvious complex cases")
    print(f"    Total cost: ${static_total_cost:.4f}")
    print(f"    Avg cost/task: ${static_total_cost/100:.4f}")
    print(f"    Total latency: {static_total_latency/1000:.1f}s")
    print(f"    Avg latency/task: {static_total_latency/100/1000:.2f}s")

    print(f"\n  Adaptive Selection (learned from actual performance):")
    print(f"    Strategy: Task-aware routing using learned metrics")
    print(f"    Total cost: ${adaptive_total_cost:.4f}")
    print(f"    Avg cost/task: ${adaptive_total_cost/100:.4f}")
    print(f"    Total latency: {adaptive_total_latency/1000:.1f}s")
    print(f"    Avg latency/task: {adaptive_total_latency/100/1000:.2f}s")

    cost_savings = ((static_total_cost - adaptive_total_cost) / static_total_cost * 100) if static_total_cost > 0 else 0
    latency_improvement = ((static_total_latency - adaptive_total_latency) / static_total_latency * 100) if static_total_latency > 0 else 0

    print(f"\n  Savings:")
    print(f"    Cost reduction: {cost_savings:.1f}%")
    print(f"    Latency improvement: {latency_improvement:.1f}%")

    return {
        "cost_savings_percent": cost_savings,
        "latency_improvement_percent": latency_improvement
    }


async def main():
    """Run comprehensive test."""
    print("="*70)
    print("ADAPTIVE LEARNING SYSTEM - COMPREHENSIVE TEST")
    print("="*70)

    # Use temporary databases for testing
    with tempfile.TemporaryDirectory() as tmpdir:
        perf_db = os.path.join(tmpdir, "performance_logs.db")
        summary_db = os.path.join(tmpdir, "model_summaries.db")

        print(f"\nTest databases:")
        print(f"  Performance logs: {perf_db}")
        print(f"  Summaries: {summary_db}")

        # Initialize repositories
        perf_repo = PerformanceDataRepository(perf_db)
        summary_repo = ModelSummaryRepository(summary_db)

        # Test 1: Create sample logs
        await create_sample_logs(perf_repo)

        # Test 2: Learning service
        learning_service = await test_learning_service(perf_repo, summary_repo)

        # Test 3: Adaptive selection
        await test_adaptive_selection(summary_repo)

        # Test 4: Cost comparison
        results = await compare_static_vs_adaptive(summary_repo)

        # Final summary
        print("\n" + "="*70)
        print("TEST SUMMARY")
        print("="*70)

        stats = learning_service.get_learning_stats()
        print(f"✓ Created {stats['total_logs']} performance logs")
        print(f"✓ Generated {stats['total_summaries']} model summaries")
        print(f"✓ Tracked {stats['num_models_tracked']} models across {stats['num_task_types']} task types")
        print(f"✓ Cost savings: {results['cost_savings_percent']:.1f}%")
        print(f"✓ Latency improvement: {results['latency_improvement_percent']:.1f}%")

        # Verification against 80B design estimates
        print("\n" + "="*70)
        print("VERIFICATION vs QWEN3-NEXT-80B-THINKING DESIGN")
        print("="*70)

        design_estimates = {
            "cost_reduction": (20, 40),  # 20-40% claimed
            "latency_improvement": (15, 25)  # 15-25% claimed
        }

        cost_ok = design_estimates["cost_reduction"][0] <= results["cost_savings_percent"] <= design_estimates["cost_reduction"][1]
        latency_ok = design_estimates["latency_improvement"][0] <= results["latency_improvement_percent"] <= design_estimates["latency_improvement"][1]

        print(f"  Cost reduction:")
        print(f"    Design estimate: {design_estimates['cost_reduction'][0]}-{design_estimates['cost_reduction'][1]}%")
        print(f"    Actual result: {results['cost_savings_percent']:.1f}%")
        print(f"    Status: {'✓ MATCHES' if cost_ok else '⚠ OUTSIDE RANGE'}")

        print(f"\n  Latency improvement:")
        print(f"    Design estimate: {design_estimates['latency_improvement'][0]}-{design_estimates['latency_improvement'][1]}%")
        print(f"    Actual result: {results['latency_improvement_percent']:.1f}%")
        print(f"    Status: {'✓ MATCHES' if latency_ok else '⚠ OUTSIDE RANGE'}")

        overall_success = cost_ok and latency_ok
        print(f"\n{'='*70}")
        print(f"OVERALL: {'✓ SUCCESS - Design estimates validated' if overall_success else '⚠ PARTIAL - Results differ from estimates'}")
        print(f"{'='*70}")

        return overall_success


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
