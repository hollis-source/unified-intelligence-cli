"""
Test script for Project Builder Phase 1 implementation.

Demonstrates:
1. Goal decomposition using Qwen3-Next-80B-Thinking
2. HTN to DSL translation
3. State management with SQLite persistence
4. Sequential task execution
"""

import asyncio
from datetime import datetime

from src.project_builder import (
    ProjectOrchestrator,
    ProjectStateManager,
    SQLiteStateRepository,
    GoalDecomposer,
    HTNDSLTranslator
)
from src.adapters.llm.qwen3_next_80b_thinking_adapter import Qwen3Next80BThinkingAdapter


async def test_project_builder():
    """Test end-to-end project builder flow."""

    print("=" * 80)
    print("AGENTIC PROJECT BUILDER - PHASE 1 TEST")
    print("=" * 80)
    print()

    # Initialize components
    print("[INIT] Initializing components...")

    # 1. State management
    state_repo = SQLiteStateRepository(db_path="data/test_project_builder.db")
    state_manager = ProjectStateManager(state_repo)

    # 2. Goal decomposer with thinking model
    thinking_model = Qwen3Next80BThinkingAdapter(timeout=300)
    goal_decomposer = GoalDecomposer(thinking_model)

    # 3. HTN-DSL translator
    htn_dsl_translator = HTNDSLTranslator()

    # 4. Project orchestrator
    orchestrator = ProjectOrchestrator(
        goal_decomposer=goal_decomposer,
        htn_dsl_translator=htn_dsl_translator,
        state_manager=state_manager
    )

    print("[INIT] Components initialized successfully")
    print()

    # Test project
    project_goal = "Create a simple REST API with user authentication"
    project_id = f"rest-api-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

    print(f"[PROJECT] Goal: {project_goal}")
    print(f"[PROJECT] ID: {project_id}")
    print()

    # Execute project
    print("[EXECUTE] Starting project execution...")
    print()

    result = await orchestrator.execute_project(
        goal=project_goal,
        project_id=project_id
    )

    # Display results
    print()
    print("=" * 80)
    print("PROJECT EXECUTION RESULTS")
    print("=" * 80)
    print(f"Success: {'✓' if result.success else '✗'}")
    print(f"Execution Time: {result.execution_time:.2f}s")
    print(f"Estimated Cost: ${result.cost:.4f}")
    print(f"Tasks Completed: {len(result.task_results)}")
    print()

    if result.success:
        print("Task Results:")
        for i, task_result in enumerate(result.task_results, 1):
            status = "✓" if task_result.success else "✗"
            print(f"  {i}. {status} {task_result.task_id}")
            if task_result.metadata.get("description"):
                print(f"     Description: {task_result.metadata['description']}")

        print()
        print("Artifacts:")
        if result.artifacts:
            for key, value in result.artifacts.items():
                print(f"  - {key}: {value}")
        else:
            print("  (No artifacts generated in Phase 1)")
    else:
        print(f"Error: {result.error}")

    print()
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(test_project_builder())
