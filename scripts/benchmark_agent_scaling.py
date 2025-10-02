#!/usr/bin/env python3
"""
Benchmark Agent Scaling - Compare 5-agent vs 12-agent performance.

Week 11 Phase 2: Validate that 12-agent system provides throughput improvements.

Metrics:
- Total execution time
- Tasks per second (throughput)
- Agent utilization
- Tier distribution
- Parallel execution efficiency
"""

import sys
import time
import asyncio
from pathlib import Path
from typing import List, Dict, Any
from dataclasses import dataclass

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.entities import Task, Agent, ExecutionContext
from src.factories import AgentFactory, ProviderFactory
from src.composition import compose_dependencies


@dataclass
class BenchmarkResult:
    """Results from a single benchmark run."""
    agent_count: int
    agent_mode: str
    total_time: float
    task_count: int
    throughput: float  # tasks/second
    agent_utilization: Dict[str, int]
    tier_distribution: Dict[int, int]
    parallel_groups: int
    success_rate: float


def create_benchmark_tasks() -> List[Task]:
    """
    Create representative task set covering all domains.

    Task distribution:
    - 4 planning/coordination tasks (Tier 1)
    - 8 design tasks (Tier 2, various domains)
    - 16 implementation tasks (Tier 3, various domains)

    Total: 28 tasks
    """
    tasks = []
    task_id = 1

    # Tier 1: Planning & Coordination (4 tasks)
    planning_tasks = [
        "Plan the overall microservices architecture",
        "Organize sprint backlog and prioritize features",
        "Review codebase for clean architecture violations",
        "Audit code quality and test coverage"
    ]
    for desc in planning_tasks:
        tasks.append(Task(
            description=desc,
            task_id=f"task_{task_id}",
            priority=task_id
        ))
        task_id += 1

    # Tier 2: Design (8 tasks across domains)
    design_tasks = [
        "Design REST API for user authentication",
        "Design React dashboard with responsive layout",
        "Design database schema for microservices",
        "Design CI/CD pipeline for deployment",
        "Design comprehensive test strategy",
        "Design documentation structure and ADRs",
        "Design state management architecture for UI",
        "Design Kubernetes infrastructure setup"
    ]
    for desc in design_tasks:
        tasks.append(Task(
            description=desc,
            task_id=f"task_{task_id}",
            priority=task_id
        ))
        task_id += 1

    # Tier 3: Implementation (16 tasks across domains)
    implementation_tasks = [
        # Backend
        "Implement FastAPI endpoint for user login",
        "Write Python function to process async requests",
        "Implement database migrations with Alembic",
        "Write Python service layer for user management",
        # Frontend
        "Implement React component for user profile",
        "Write TypeScript interfaces for API client",
        "Implement React form validation logic",
        "Write JavaScript utility functions for data formatting",
        # Testing
        "Write unit tests with pytest for auth service",
        "Create test fixtures and mocks for API",
        "Write end-to-end tests for login flow",
        "Create API integration tests with Postman",
        # DevOps
        "Write Dockerfile for Python backend",
        "Create Kubernetes deployment manifests",
        # Documentation
        "Document REST API endpoints",
        "Write tutorial for getting started"
    ]
    for desc in implementation_tasks:
        tasks.append(Task(
            description=desc,
            task_id=f"task_{task_id}",
            priority=task_id
        ))
        task_id += 1

    return tasks


async def run_benchmark(
    agent_mode: str,
    tasks: List[Task],
    verbose: bool = False
) -> BenchmarkResult:
    """
    Run benchmark for specified agent mode.

    Args:
        agent_mode: "default" (5 agents) or "scaled" (12 agents)
        tasks: Tasks to execute
        verbose: Enable verbose output

    Returns:
        BenchmarkResult with metrics
    """
    print(f"\n{'='*70}")
    print(f"BENCHMARKING {agent_mode.upper()} MODE")
    print(f"{'='*70}")

    # Create agents
    agent_factory = AgentFactory()
    if agent_mode == "scaled":
        agents = agent_factory.create_scaled_agents()
    elif agent_mode == "extended":
        agents = agent_factory.create_extended_agents()
    else:
        agents = agent_factory.create_default_agents()

    print(f"✅ Created {len(agents)} agents")

    # Create mock provider (fast execution for benchmarking)
    provider_factory = ProviderFactory()
    llm_provider = provider_factory.create_provider("mock")

    # Compose dependencies
    coordinator = compose_dependencies(
        llm_provider=llm_provider,
        agents=agents,
        logger=None,
        orchestrator_mode="simple",  # Use simple mode for consistent benchmarking
        collect_data=False,
        data_dir="data/training",
        provider_name="mock"
    )

    # Run benchmark
    start_time = time.time()

    results = await coordinator.coordinate(
        tasks=tasks,
        agents=agents
    )

    end_time = time.time()
    total_time = end_time - start_time

    # Calculate metrics
    success_count = sum(1 for r in results if r.status.name == "SUCCESS")
    success_rate = success_count / len(results) if results else 0
    throughput = len(tasks) / total_time if total_time > 0 else 0

    # Collect agent utilization (from planner)
    # This is a simplification - in real usage we'd track actual execution
    agent_utilization = {}
    tier_distribution = {1: 0, 2: 0, 3: 0}

    for agent in agents:
        # Count how many tasks this agent could handle
        count = sum(1 for task in tasks if agent.can_handle(task))
        if count > 0:
            agent_utilization[agent.role] = count
            tier_distribution[agent.tier] += count

    # Estimate parallel groups (simplified)
    # In reality, this comes from the execution plan
    parallel_groups = max(1, len(tasks) // (len(agents) // 2))

    return BenchmarkResult(
        agent_count=len(agents),
        agent_mode=agent_mode,
        total_time=total_time,
        task_count=len(tasks),
        throughput=throughput,
        agent_utilization=agent_utilization,
        tier_distribution=tier_distribution,
        parallel_groups=parallel_groups,
        success_rate=success_rate
    )


def print_results(result: BenchmarkResult):
    """Print benchmark results."""
    print(f"\n{'='*70}")
    print(f"RESULTS - {result.agent_mode.upper()} MODE ({result.agent_count} agents)")
    print(f"{'='*70}")

    print(f"\nPerformance Metrics:")
    print(f"  Total time: {result.total_time:.3f}s")
    print(f"  Tasks: {result.task_count}")
    print(f"  Throughput: {result.throughput:.2f} tasks/second")
    print(f"  Success rate: {result.success_rate * 100:.1f}%")
    print(f"  Parallel groups: {result.parallel_groups}")

    if result.agent_mode != "default":
        print(f"\n  Tier Distribution:")
        for tier, count in sorted(result.tier_distribution.items()):
            percentage = (count / result.task_count * 100) if result.task_count > 0 else 0
            print(f"    Tier {tier}: {count} tasks ({percentage:.1f}%)")

    print(f"\n  Agent Utilization:")
    for agent_role, count in sorted(result.agent_utilization.items()):
        print(f"    {agent_role}: {count} tasks")


def compare_results(baseline: BenchmarkResult, scaled: BenchmarkResult):
    """Compare and analyze results."""
    print(f"\n{'='*70}")
    print("COMPARISON ANALYSIS")
    print(f"{'='*70}")

    speedup = scaled.throughput / baseline.throughput if baseline.throughput > 0 else 0
    time_reduction = ((baseline.total_time - scaled.total_time) / baseline.total_time * 100) if baseline.total_time > 0 else 0

    print(f"\nThroughput Improvement:")
    print(f"  5-agent:  {baseline.throughput:.2f} tasks/s")
    print(f"  12-agent: {scaled.throughput:.2f} tasks/s")
    print(f"  Speedup:  {speedup:.2f}x")

    print(f"\nExecution Time:")
    print(f"  5-agent:  {baseline.total_time:.3f}s")
    print(f"  12-agent: {scaled.total_time:.3f}s")
    print(f"  Reduction: {time_reduction:.1f}%")

    print(f"\nAgent Utilization:")
    print(f"  5-agent:  {len(baseline.agent_utilization)}/{baseline.agent_count} agents utilized")
    print(f"  12-agent: {len(scaled.agent_utilization)}/{scaled.agent_count} agents utilized")

    print(f"\n{'='*70}")
    if speedup >= 2.0:
        print("✅ EXCELLENT: 12-agent system provides 2x+ speedup!")
    elif speedup >= 1.5:
        print("✅ GOOD: 12-agent system provides 1.5x+ speedup")
    elif speedup >= 1.2:
        print("⚠️  MODERATE: 12-agent system provides 1.2x+ speedup")
    else:
        print("❌ POOR: 12-agent system does not provide significant speedup")
    print(f"{'='*70}")


async def main():
    """Run benchmarks and compare."""
    print(f"\n{'='*70}")
    print("AGENT SCALING BENCHMARK")
    print("Week 11 Phase 2: 5-agent vs 12-agent comparison")
    print(f"{'='*70}")

    # Create benchmark tasks
    tasks = create_benchmark_tasks()
    print(f"\n✅ Created {len(tasks)} benchmark tasks")

    # Run benchmarks
    print("\n🔄 Running benchmarks...")

    # Baseline: 5-agent mode
    baseline_result = await run_benchmark("default", tasks)
    print_results(baseline_result)

    # Scaled: 12-agent mode
    scaled_result = await run_benchmark("scaled", tasks)
    print_results(scaled_result)

    # Compare
    compare_results(baseline_result, scaled_result)

    # Determine exit code
    speedup = scaled_result.throughput / baseline_result.throughput if baseline_result.throughput > 0 else 0
    return 0 if speedup >= 1.2 else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
