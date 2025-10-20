#!/usr/bin/env python3
"""Test script for Phase 7 Autonomous Orchestrator.

Tests one iteration of the autonomous loop:
1. Context analysis
2. Task generation
3. Task execution
"""

from src.claude_orchestrator.entities.worker import WorkerPoolConfig
from src.claude_orchestrator.adapters.single_worker_pool import SingleWorkerPool
from src.claude_orchestrator.adapters.git_context_analyzer import GitContextAnalyzer
from src.claude_orchestrator.adapters.pytest_analyzer import PytestAnalyzer
from src.claude_orchestrator.adapters.coverage_analyzer import CoverageAnalyzer
from src.claude_orchestrator.adapters.goal_parser import GoalParser
from src.claude_orchestrator.adapters.heuristic_task_generator import HeuristicTaskGenerator
from src.claude_orchestrator.use_cases.analyze_context_use_case import AnalyzeContextUseCase
from src.claude_orchestrator.use_cases.generate_next_task_use_case import GenerateNextTaskUseCase
from src.claude_orchestrator.orchestrators.autonomous_orchestrator import AutonomousOrchestrator

print("="*70)
print("PHASE 7 AUTONOMOUS ORCHESTRATOR TEST")
print("="*70)
print()

# Configure SYD2 worker pool
print("1. Configuring worker pool (SYD2)...")
worker_config = WorkerPoolConfig(
    pool_type="ssh",
    max_workers=1,
    ssh_host="root@208.87.135.78",
    working_dir="/root",
    model_name="sonnet4",
)
worker_pool = SingleWorkerPool(worker_config)
print("   ✓ Worker pool configured")

# Create context analysis use case
print("2. Creating context analysis use case...")
analyze_context = AnalyzeContextUseCase(
    git_analyzer=GitContextAnalyzer(),
    test_analyzer=PytestAnalyzer(),
    coverage_analyzer=CoverageAnalyzer(),
    goal_parser=GoalParser(),
)
print("   ✓ Context analysis ready")

# Create task generation use case
print("3. Creating task generation use case...")
generate_task = GenerateNextTaskUseCase(
    task_generator=HeuristicTaskGenerator(),
    goal_parser=GoalParser(),
)
print("   ✓ Task generation ready")

# Create autonomous orchestrator
print("4. Creating autonomous orchestrator...")
orchestrator = AutonomousOrchestrator(
    worker_pool=worker_pool,
    analyze_context=analyze_context,
    generate_task=generate_task,
    project_path=".",
    priorities_file="priorities.yaml",
)
print("   ✓ Orchestrator created")

print()
print("="*70)
print("RUNNING ONE AUTONOMOUS ITERATION")
print("="*70)
print()

try:
    # Run one iteration (skip tests for speed)
    success = orchestrator.run_iteration(run_tests=False)

    print()
    print("="*70)
    print("TEST RESULT")
    print("="*70)

    if success:
        print("✅ ITERATION SUCCEEDED")
    else:
        print("❌ ITERATION FAILED (task execution failed)")

    # Get statistics
    stats = orchestrator.get_statistics()

except Exception as e:
    print()
    print("="*70)
    print("TEST FAILED")
    print("="*70)
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()

finally:
    # Shutdown
    print()
    print("Shutting down...")
    orchestrator.shutdown()
    print("Done.")
