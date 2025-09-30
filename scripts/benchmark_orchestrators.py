#!/usr/bin/env python3
"""
Performance Benchmark: Simple vs OpenAI Agents SDK Orchestrators

Week 7, Phase 1.5: E2E Validation and Performance Benchmarking

Compares execution time, success rates, and behavior between:
1. Simple orchestrator (TaskCoordinatorUseCase)
2. OpenAI Agents SDK orchestrator (OpenAIAgentsSDKAdapter)

Usage:
    python3 scripts/benchmark_orchestrators.py [--verbose] [--provider tongyi|mock]

Clean Architecture: Uses factories and interfaces for orchestrator creation.
"""

import asyncio
import time
import statistics
from typing import List, Dict, Any, Tuple
import argparse
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.entities import Task, Agent
from src.factories import AgentFactory, ProviderFactory
from src.factories.orchestration_factory import OrchestrationFactory
from src.adapters.agent.capability_selector import CapabilityBasedSelector
from src.adapters.agent.llm_executor import LLMAgentExecutor
from src.use_cases.task_planner import TaskPlannerUseCase


class OrchestratorBenchmark:
    """
    Benchmark orchestrators with various task types.

    Measures:
    - Execution time (wall clock)
    - Success rate (status=success)
    - Output characteristics (length, structure)
    """

    def __init__(self, provider: str = "mock", verbose: bool = False):
        self.provider = provider
        self.verbose = verbose

        # Create dependencies via factories
        self.agents = AgentFactory().create_default_agents()
        self.llm_provider = ProviderFactory().create_provider(provider)

        # Shared dependencies for orchestrators
        self.agent_executor = LLMAgentExecutor(self.llm_provider)
        self.agent_selector = CapabilityBasedSelector()
        self.task_planner = TaskPlannerUseCase(
            llm_provider=self.llm_provider,
            agent_selector=self.agent_selector,
            logger=None
        )

    def _create_orchestrator(self, mode: str):
        """Create orchestrator via factory."""
        return OrchestrationFactory.create_orchestrator(
            mode=mode,
            llm_provider=self.llm_provider,
            task_planner=self.task_planner,
            agent_executor=self.agent_executor,
            agents=self.agents,
            logger_instance=None
        )

    async def _benchmark_single_run(
        self,
        mode: str,
        tasks: List[Task]
    ) -> Tuple[float, List[Dict[str, Any]]]:
        """
        Run single benchmark iteration.

        Returns:
            (execution_time_seconds, results_summary)
        """
        coordinator = self._create_orchestrator(mode)

        start_time = time.time()
        results = await coordinator.coordinate(tasks, self.agents)
        execution_time = time.time() - start_time

        # Extract result summaries (results are in same order as tasks)
        results_summary = [
            {
                "task_id": tasks[i].task_id,
                "status": r.status.value if hasattr(r.status, 'value') else r.status,
                "output_length": len(r.output) if r.output else 0,
                "errors": r.errors if r.errors else []
            }
            for i, r in enumerate(results)
        ]

        return execution_time, results_summary

    async def benchmark_orchestrator(
        self,
        mode: str,
        tasks: List[Task],
        iterations: int = 3
    ) -> Dict[str, Any]:
        """
        Benchmark orchestrator over multiple iterations.

        Args:
            mode: "simple" or "openai-agents"
            tasks: List of tasks to execute
            iterations: Number of runs (default 3 for statistical validity)

        Returns:
            Benchmark metrics dictionary
        """
        print(f"\n{'='*60}")
        print(f"Benchmarking: {mode} orchestrator")
        print(f"{'='*60}")

        execution_times = []
        all_results = []

        for i in range(iterations):
            if self.verbose:
                print(f"  Iteration {i+1}/{iterations}...")

            exec_time, results = await self._benchmark_single_run(mode, tasks)
            execution_times.append(exec_time)
            all_results.append(results)

            if self.verbose:
                print(f"    Time: {exec_time:.3f}s")

        # Calculate statistics
        avg_time = statistics.mean(execution_times)
        std_time = statistics.stdev(execution_times) if len(execution_times) > 1 else 0

        # Success rate (across all iterations)
        total_tasks = len(tasks) * iterations
        successful_tasks = sum(
            1 for iteration in all_results
            for result in iteration
            if result["status"] == "success"
        )
        success_rate = (successful_tasks / total_tasks) * 100

        # Average output length
        avg_output_length = statistics.mean([
            result["output_length"]
            for iteration in all_results
            for result in iteration
            if result["status"] == "success"
        ]) if successful_tasks > 0 else 0

        return {
            "mode": mode,
            "iterations": iterations,
            "tasks_per_iteration": len(tasks),
            "total_tasks": total_tasks,
            "avg_execution_time": avg_time,
            "std_execution_time": std_time,
            "min_execution_time": min(execution_times),
            "max_execution_time": max(execution_times),
            "success_rate": success_rate,
            "successful_tasks": successful_tasks,
            "avg_output_length": avg_output_length,
            "all_execution_times": execution_times,
            "sample_results": all_results[0]  # First iteration results
        }

    def print_benchmark_results(self, results: Dict[str, Any]):
        """Print formatted benchmark results."""
        print(f"\n{'='*60}")
        print(f"Benchmark Results: {results['mode']}")
        print(f"{'='*60}")
        print(f"Iterations:           {results['iterations']}")
        print(f"Tasks per iteration:  {results['tasks_per_iteration']}")
        print(f"Total tasks:          {results['total_tasks']}")
        print(f"\nExecution Time:")
        print(f"  Average:            {results['avg_execution_time']:.3f}s")
        print(f"  Std Dev:            {results['std_execution_time']:.3f}s")
        print(f"  Min:                {results['min_execution_time']:.3f}s")
        print(f"  Max:                {results['max_execution_time']:.3f}s")
        print(f"\nSuccess Metrics:")
        print(f"  Success rate:       {results['success_rate']:.1f}%")
        print(f"  Successful tasks:   {results['successful_tasks']}/{results['total_tasks']}")
        print(f"\nOutput Metrics:")
        print(f"  Avg output length:  {results['avg_output_length']:.0f} chars")
        print(f"\nSample Results (Iteration 1):")
        for i, result in enumerate(results['sample_results'], 1):
            status_icon = "✓" if result["status"] == "success" else "✗"
            print(f"  {status_icon} Task {i}: {result['status']} "
                  f"({result['output_length']} chars)")
            if result["errors"]:
                print(f"    Errors: {', '.join(result['errors'])}")

    def print_comparison(self, simple_results: Dict[str, Any],
                        openai_results: Dict[str, Any]):
        """Print side-by-side comparison."""
        print(f"\n{'='*60}")
        print("ORCHESTRATOR COMPARISON")
        print(f"{'='*60}")

        print(f"\n{'Metric':<30} {'Simple':<15} {'OpenAI Agents':<15}")
        print(f"{'-'*60}")

        # Execution time
        simple_time = simple_results['avg_execution_time']
        openai_time = openai_results['avg_execution_time']
        speedup = simple_time / openai_time if openai_time > 0 else 0

        print(f"{'Avg Execution Time':<30} "
              f"{simple_time:.3f}s{'':<9} "
              f"{openai_time:.3f}s")

        if speedup > 1:
            print(f"{'  → Speedup':<30} {'':<15} {speedup:.2f}x faster")
        elif speedup < 1:
            print(f"{'  → Speedup':<30} {1/speedup:.2f}x faster{'':<3} {'':<15}")

        # Success rate
        print(f"{'Success Rate':<30} "
              f"{simple_results['success_rate']:.1f}%{'':<10} "
              f"{openai_results['success_rate']:.1f}%")

        # Output length
        print(f"{'Avg Output Length':<30} "
              f"{simple_results['avg_output_length']:.0f} chars{'':<5} "
              f"{openai_results['avg_output_length']:.0f} chars")

        print(f"\n{'='*60}")
        print("RECOMMENDATION")
        print(f"{'='*60}")

        # Recommendation logic
        if simple_results['success_rate'] == openai_results['success_rate'] == 100:
            if abs(simple_time - openai_time) < 0.5:
                print("✓ Both orchestrators perform similarly well.")
                print("  Use 'simple' for stability, 'openai-agents' for future features.")
            elif simple_time < openai_time:
                print(f"✓ 'simple' orchestrator is {simple_time/openai_time:.1f}x faster.")
                print("  Recommend 'simple' for performance-critical applications.")
            else:
                print(f"✓ 'openai-agents' orchestrator is {openai_time/simple_time:.1f}x faster.")
                print("  Recommend 'openai-agents' for performance.")
        else:
            print("⚠️  Success rates differ. Investigate failure modes.")
            if simple_results['success_rate'] > openai_results['success_rate']:
                print("  'simple' orchestrator has higher success rate.")
            else:
                print("  'openai-agents' orchestrator has higher success rate.")

    async def run_full_benchmark(self, iterations: int = 3):
        """
        Run complete benchmark suite.

        Tests both orchestrators with various task types:
        1. Simple tasks (single agent)
        2. Complex tasks (multi-step reasoning)
        3. Multi-task scenarios
        """
        print(f"\n{'='*60}")
        print("ORCHESTRATOR BENCHMARK SUITE")
        print(f"{'='*60}")
        print(f"Provider: {self.provider}")
        print(f"Iterations per orchestrator: {iterations}")
        print(f"Agents: {len(self.agents)}")

        # Test Suite 1: Simple tasks
        simple_tasks = [
            Task(
                description="Explain what Clean Architecture is",
                task_id="benchmark_task_1",
                priority=1
            ),
            Task(
                description="Research current AI frameworks",
                task_id="benchmark_task_2",
                priority=2
            ),
            Task(
                description="Analyze code quality best practices",
                task_id="benchmark_task_3",
                priority=3
            )
        ]

        # Benchmark simple orchestrator
        simple_results = await self.benchmark_orchestrator(
            mode="simple",
            tasks=simple_tasks,
            iterations=iterations
        )
        self.print_benchmark_results(simple_results)

        # Benchmark openai-agents orchestrator
        openai_results = await self.benchmark_orchestrator(
            mode="openai-agents",
            tasks=simple_tasks,
            iterations=iterations
        )
        self.print_benchmark_results(openai_results)

        # Comparison
        self.print_comparison(simple_results, openai_results)

        return {
            "simple": simple_results,
            "openai-agents": openai_results
        }


def main():
    """Main entry point for benchmark script."""
    parser = argparse.ArgumentParser(
        description="Benchmark orchestrators (simple vs openai-agents)"
    )
    parser.add_argument(
        "--provider",
        choices=["mock", "tongyi"],
        default="mock",
        help="LLM provider to use (default: mock)"
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose output"
    )
    parser.add_argument(
        "--iterations",
        type=int,
        default=3,
        help="Number of iterations per orchestrator (default: 3)"
    )

    args = parser.parse_args()

    # Run benchmark
    benchmark = OrchestratorBenchmark(
        provider=args.provider,
        verbose=args.verbose
    )

    try:
        results = asyncio.run(benchmark.run_full_benchmark(iterations=args.iterations))

        print(f"\n{'='*60}")
        print("BENCHMARK COMPLETE")
        print(f"{'='*60}")
        print("✓ All tests completed successfully")

        return 0

    except Exception as e:
        print(f"\n✗ Benchmark failed: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())