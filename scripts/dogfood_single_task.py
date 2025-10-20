#!/usr/bin/env python3
"""
Run a single dogfooding task for quick testing.

Usage: python3 dogfood_single_task.py <task_number>
"""

import sys
import subprocess
import time
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# Import task definitions
sys.path.insert(0, str(Path(__file__).parent))

# Real tasks (simplified for single execution)
TASKS = {
    "1": {
        "id": "task1_testing_infrastructure",
        "title": "P2 Testing Infrastructure Analysis",
        "description": """Analyze our current testing infrastructure and create a plan.

CONTEXT:
- Current: 131/134 tests passing (98%)
- Goal: 90%+ coverage for DSL runtime and CLI
- Priority: HIGH

TASK:
1. Analyze existing test coverage
2. Identify gaps in DSL workflow tests
3. Design mock CLI adapter for testing
4. Create prioritized implementation plan

DELIVERABLES:
- Gap analysis with specific examples
- Test architecture design
- Prioritized roadmap with effort estimates""",
    },
    "2": {
        "id": "task2_code_quality_review",
        "title": "Code Quality Review: Phase 2 Refactoring",
        "description": """Review quality of Phase 2 naming refactoring.

FILES TO REVIEW:
- PHASE_2_COMPLETION_SUMMARY.md
- src/entity/ (renamed from entities/)
- src/interface/ (renamed from interfaces/)

TASK:
1. Evaluate refactoring quality
2. Check backward compatibility approach
3. Identify remaining issues
4. Suggest improvements

DELIVERABLES:
- Quality score (1-10) with justification
- List of remaining issues
- Actionable recommendations""",
    },
    "3": {
        "id": "task3_architecture_analysis",
        "title": "Priority Dependencies Analysis",
        "description": """Analyze priorities.yaml and identify optimal work sequence.

TASK:
1. Read priorities.yaml
2. Identify all dependencies (explicit + implicit)
3. Create dependency graph
4. Recommend optimal sequence

DELIVERABLES:
- Dependency graph (ASCII or Mermaid)
- Critical path
- Recommended work sequence""",
    }
}


def run_task(task_num):
    """Run a single task."""

    if task_num not in TASKS:
        print(f"❌ Invalid task number: {task_num}")
        print(f"Available tasks: {', '.join(TASKS.keys())}")
        return 1

    task = TASKS[task_num]

    print(f"{'='*70}")
    print(f"TASK {task_num}: {task['title']}")
    print(f"{'='*70}\n")

    # Just use the provider directly for simpler testing
    from src.factories.provider_factory import ProviderFactory

    factory = ProviderFactory()

    # Use Thinking model (our deployed endpoint)
    config = {
        "model": "Qwen/Qwen3-Next-80B-A3B-Instruct",
        "thinking_mode": False
    }
    provider = factory.create_provider("qwen-agent", config)

    print(f"✅ Qwen provider loaded")
    print(f"   Model: {provider.config.model}")
    print(f"   Endpoint: {provider.config.model_server}")
    print(f"\n🚀 Generating response...")
    print(f"   (Thinking mode enabled - you'll see reasoning process)\n")

    start_time = time.time()

    try:
        result = provider.generate(task['description'])
        end_time = time.time()
        duration = end_time - start_time

        # Save output
        output_dir = Path(__file__).parent.parent / "dogfooding_results"
        output_dir.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = output_dir / f"{task['id']}_{timestamp}.txt"

        with open(output_file, 'w') as f:
            f.write(f"Task: {task['title']}\n")
            f.write(f"Timestamp: {timestamp}\n")
            f.write(f"Duration: {duration:.1f}s\n")
            f.write(f"\n{'='*70}\n")
            f.write("RESPONSE:\n")
            f.write(f"{'='*70}\n\n")
            f.write(result)

        print(f"{'='*70}")
        print(f"COMPLETED IN {duration:.1f}s ({duration/60:.1f} minutes)")
        print(f"{'='*70}\n")

        print("RESPONSE PREVIEW (first 2000 chars):")
        print(f"{'='*70}")
        print(result[:2000])
        if len(result) > 2000:
            print(f"\n... [{len(result) - 2000} more characters]")

        print(f"\n{'='*70}")
        print(f"✅ Full response saved to: {output_file}")
        print(f"{'='*70}")

        # Basic quality check
        has_deliverables = any(word in result.lower() for word in ['analysis', 'recommendation', 'design', 'plan'])
        has_details = len(result) > 500
        has_structure = result.count('\n\n') > 5

        print(f"\nQuality Indicators:")
        print(f"  {'✅' if has_deliverables else '❌'} Contains deliverables")
        print(f"  {'✅' if has_details else '❌'} Sufficient detail (>{len(result)} chars)")
        print(f"  {'✅' if has_structure else '❌'} Well-structured")

        return 0

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python3 dogfood_single_task.py <task_number>")
        print(f"Available tasks: {', '.join(TASKS.keys())}")
        sys.exit(1)

    task_num = sys.argv[1]
    sys.exit(run_task(task_num))
