#!/usr/bin/env python3
"""
Benchmark Hybrid Orchestration Mode

Compares performance across orchestration modes:
- simple: TaskCoordinatorUseCase (baseline)
- openai-agents: OpenAI Agents SDK
- hybrid: Intelligent routing (default)

Tests both single-agent and multi-agent tasks.
"""

import asyncio
import time
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.entities import Task
from src.factories import AgentFactory, ProviderFactory, OrchestrationFactory
from src.use_cases.task_planner import TaskPlannerUseCase
from src.adapters.agent.llm_executor import LLMAgentExecutor
from src.adapters.agent.capability_selector import CapabilityBasedSelector


# Test tasks
SINGLE_AGENT_TASKS = [
    "Write a Python function to calculate factorial",
    "Create a function to reverse a string",
    "Implement a function to check if number is prime",
    "Write a function to find max element in list",
    "Create a function to count vowels in string",
]

MULTI_AGENT_TASKS = [
    "Research quicksort then implement it in Python",
    "Investigate binary search and code an example",
    "Write a function to merge two sorted lists then test it",
    "Create a stack class and verify with tests",
    "Implement bubble sort algorithm and validate correctness",
]


async def benchmark_mode(mode: str, tasks_dict: dict, provider_name: str = "tongyi"):
    """
    Benchmark specific orchestration mode.

    Args:
        mode: Orchestration mode
        tasks_dict: Dict of task categories {"single": [...], "multi": [...]}
        provider_name: LLM provider to use

    Returns:
        Dict with benchmark results
    """
    print(f"\n{'='*60}")
    print(f"Benchmarking: {mode.upper()} MODE")
    print(f"{'='*60}")

    # Create dependencies
    agent_factory = AgentFactory()
    agents = agent_factory.create_default_agents()

    provider_factory = ProviderFactory()
    llm_provider = provider_factory.create_provider(provider_name)

    agent_selector = CapabilityBasedSelector()
    task_planner = TaskPlannerUseCase(
        llm_provider=llm_provider,
        agent_selector=agent_selector
    )
    agent_executor = LLMAgentExecutor(llm_provider=llm_provider)

    # Create orchestrator
    orchestrator = OrchestrationFactory.create_orchestrator(
        mode=mode,
        llm_provider=llm_provider,
        task_planner=task_planner,
        agent_executor=agent_executor,
        agents=agents
    )

    results = {
        "mode": mode,
        "single_agent": [],
        "multi_agent": [],
        "totals": {}
    }

    # Benchmark single-agent tasks
    print(f"\n--- Single-Agent Tasks ({len(tasks_dict['single'])}) ---")
    for i, task_desc in enumerate(tasks_dict["single"], 1):
        task = Task(
            task_id=f"single_{i}",
            description=task_desc,
            priority=1
        )

        start = time.time()
        try:
            task_results = await orchestrator.coordinate([task], agents)
            duration = time.time() - start
            success = task_results[0].status.value == "success"

            results["single_agent"].append({
                "task": task_desc,
                "duration": duration,
                "success": success
            })

            status = "✅" if success else "❌"
            print(f"  {i}. {status} {duration:.2f}s - {task_desc[:50]}...")

        except Exception as e:
            duration = time.time() - start
            results["single_agent"].append({
                "task": task_desc,
                "duration": duration,
                "success": False,
                "error": str(e)
            })
            print(f"  {i}. ❌ {duration:.2f}s - ERROR: {str(e)[:50]}")

    # Benchmark multi-agent tasks
    print(f"\n--- Multi-Agent Tasks ({len(tasks_dict['multi'])}) ---")
    for i, task_desc in enumerate(tasks_dict["multi"], 1):
        task = Task(
            task_id=f"multi_{i}",
            description=task_desc,
            priority=1
        )

        start = time.time()
        try:
            task_results = await orchestrator.coordinate([task], agents)
            duration = time.time() - start
            success = task_results[0].status.value == "success"

            results["multi_agent"].append({
                "task": task_desc,
                "duration": duration,
                "success": success
            })

            status = "✅" if success else "❌"
            print(f"  {i}. {status} {duration:.2f}s - {task_desc[:50]}...")

        except Exception as e:
            duration = time.time() - start
            results["multi_agent"].append({
                "task": task_desc,
                "duration": duration,
                "success": False,
                "error": str(e)
            })
            print(f"  {i}. ❌ {duration:.2f}s - ERROR: {str(e)[:50]}")

    # Calculate totals
    single_successes = sum(1 for r in results["single_agent"] if r["success"])
    single_duration = sum(r["duration"] for r in results["single_agent"])

    multi_successes = sum(1 for r in results["multi_agent"] if r["success"])
    multi_duration = sum(r["duration"] for r in results["multi_agent"])

    total_tasks = len(tasks_dict["single"]) + len(tasks_dict["multi"])
    total_successes = single_successes + multi_successes
    total_duration = single_duration + multi_duration

    results["totals"] = {
        "single_agent": {
            "count": len(results["single_agent"]),
            "successes": single_successes,
            "success_rate": (single_successes / len(results["single_agent"]) * 100) if results["single_agent"] else 0,
            "duration": single_duration,
            "avg_duration": single_duration / len(results["single_agent"]) if results["single_agent"] else 0
        },
        "multi_agent": {
            "count": len(results["multi_agent"]),
            "successes": multi_successes,
            "success_rate": (multi_successes / len(results["multi_agent"]) * 100) if results["multi_agent"] else 0,
            "duration": multi_duration,
            "avg_duration": multi_duration / len(results["multi_agent"]) if results["multi_agent"] else 0
        },
        "overall": {
            "count": total_tasks,
            "successes": total_successes,
            "success_rate": (total_successes / total_tasks * 100) if total_tasks else 0,
            "duration": total_duration,
            "avg_duration": total_duration / total_tasks if total_tasks else 0
        }
    }

    # Get hybrid stats if available
    if hasattr(orchestrator, 'get_stats'):
        results["routing_stats"] = orchestrator.get_stats()

    return results


def print_summary(all_results: list):
    """Print benchmark summary comparing all modes."""
    print(f"\n\n{'='*80}")
    print("BENCHMARK SUMMARY")
    print(f"{'='*80}\n")

    # Header
    print(f"{'Mode':<15} {'Tasks':<8} {'Success':<10} {'Total Time':<12} {'Avg Time':<12} {'Throughput':<12}")
    print("-" * 80)

    for results in all_results:
        mode = results["mode"]
        totals = results["totals"]["overall"]

        print(f"{mode:<15} "
              f"{totals['count']:<8} "
              f"{totals['success_rate']:.1f}%{'':<6} "
              f"{totals['duration']:.1f}s{'':<8} "
              f"{totals['avg_duration']:.1f}s{'':<8} "
              f"{(totals['count'] / totals['duration']):.2f} tasks/s{'':<0}")

    # Detailed breakdown
    print(f"\n{'='*80}")
    print("DETAILED BREAKDOWN")
    print(f"{'='*80}\n")

    for results in all_results:
        mode = results["mode"]
        print(f"\n{mode.upper()} MODE:")
        print("-" * 40)

        # Single-agent
        single = results["totals"]["single_agent"]
        print(f"  Single-Agent: {single['successes']}/{single['count']} "
              f"({single['success_rate']:.1f}%) "
              f"- Avg: {single['avg_duration']:.1f}s")

        # Multi-agent
        multi = results["totals"]["multi_agent"]
        print(f"  Multi-Agent:  {multi['successes']}/{multi['count']} "
              f"({multi['success_rate']:.1f}%) "
              f"- Avg: {multi['avg_duration']:.1f}s")

        # Routing stats (hybrid only)
        if "routing_stats" in results:
            stats = results["routing_stats"]
            print(f"\n  Routing Stats:")
            print(f"    SDK Mode:    {stats['sdk_mode']} tasks ({stats['sdk_percentage']:.1f}%)")
            print(f"    Simple Mode: {stats['simple_mode']} tasks ({stats['simple_percentage']:.1f}%)")


async def main():
    """Run full benchmark suite."""
    print("="*80)
    print("HYBRID ORCHESTRATION BENCHMARK")
    print("="*80)
    print(f"Provider: tongyi (llama-cpp-server)")
    print(f"Single-agent tasks: {len(SINGLE_AGENT_TASKS)}")
    print(f"Multi-agent tasks: {len(MULTI_AGENT_TASKS)}")
    print(f"Total tasks: {len(SINGLE_AGENT_TASKS) + len(MULTI_AGENT_TASKS)}")

    tasks_dict = {
        "single": SINGLE_AGENT_TASKS,
        "multi": MULTI_AGENT_TASKS
    }

    all_results = []

    # Benchmark hybrid mode (default)
    hybrid_results = await benchmark_mode("hybrid", tasks_dict)
    all_results.append(hybrid_results)

    # Optional: Benchmark other modes for comparison
    # Uncomment to compare with simple and SDK modes
    # simple_results = await benchmark_mode("simple", tasks_dict)
    # all_results.append(simple_results)
    #
    # sdk_results = await benchmark_mode("openai-agents", tasks_dict)
    # all_results.append(sdk_results)

    # Print summary
    print_summary(all_results)

    print(f"\n{'='*80}")
    print("BENCHMARK COMPLETE")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    asyncio.run(main())
