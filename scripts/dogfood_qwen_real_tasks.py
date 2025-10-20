#!/usr/bin/env python3
"""
Dogfooding: Test ATADO + Qwen with REAL production tasks.

This uses actual work from priorities.yaml, not synthetic tests.
Goal: Validate Qwen can handle real development work.
"""

import sys
import subprocess
import time
from pathlib import Path
from datetime import datetime

# Real tasks from our priorities and current work
REAL_TASKS = [
    {
        "id": "task1_testing_infrastructure",
        "title": "P2 Testing Infrastructure: Gap Analysis & Implementation Plan",
        "description": """Analyze our current testing infrastructure and create a comprehensive plan for P2.

CONTEXT:
- Current state: 131/134 tests passing (98%)
- Priority: HIGH (from priorities.yaml)
- Goal: 90%+ coverage for DSL runtime and CLI

TASK:
1. Analyze existing test coverage (what's covered, what's missing)
2. Identify gaps in DSL workflow integration tests
3. Design mock CLI adapter architecture for testing
4. Create implementation plan with effort estimates
5. Prioritize test additions (highest ROI first)

DELIVERABLES:
- Gap analysis report
- Test architecture design
- Prioritized implementation roadmap
- Effort estimates per component

USE THINKING MODE: This requires careful analysis of trade-offs.""",
        "expected_teams": ["Research Team", "Testing Team"],
        "estimated_time_manual": "2-3 hours",
        "success_criteria": [
            "Specific gaps identified with evidence",
            "Architecture diagram for mock CLI adapter",
            "Prioritized list of 10+ test additions",
            "Realistic effort estimates"
        ]
    },

    {
        "id": "task2_code_quality_review",
        "title": "Code Quality Review: Phase 2 Naming Refactoring",
        "description": """Review the quality of our recent Phase 2 naming refactoring work.

CONTEXT:
- Completed: Phase 2A (16 variables), 2B (12 functions), 2C (4 directories), 2D (validation)
- Duration: ~8 hours total
- Files changed: 60+ files
- Commits: 63 commits

TASK:
1. Review PHASE_2_COMPLETION_SUMMARY.md for refactoring scope
2. Check naming_violations_summary.md for original issues
3. Analyze src/entity/ directory structure (renamed from entities/)
4. Evaluate backward compatibility approach (shims)
5. Identify any remaining code quality issues
6. Suggest improvements for Phase 3+ work

DELIVERABLES:
- Code quality score (1-10)
- List of remaining issues
- Best practices applied well
- Areas for improvement in future phases
- Specific actionable recommendations

USE THINKING MODE: Requires critical analysis of our own work.""",
        "expected_teams": ["Backend Team"],
        "estimated_time_manual": "1-2 hours",
        "success_criteria": [
            "Honest assessment (not just praise)",
            "Specific examples from codebase",
            "Actionable improvements",
            "Comparison to Clean Code principles"
        ]
    },

    {
        "id": "task3_architecture_analysis",
        "title": "Architecture Analysis: Priority Dependencies & Work Sequencing",
        "description": """Analyze our priorities.yaml and identify optimal work sequence.

CONTEXT:
- Total priorities: 9
- Completed: 7
- Open: 2 (P2 testing, type checking)
- Some have explicit dependencies, others implicit

TASK:
1. Read and analyze priorities.yaml
2. Identify ALL dependencies (explicit + implicit)
   - P2 testing blocks type checking (explicit)
   - What else?
3. Create dependency graph
4. Identify critical path
5. Recommend optimal sequence for remaining work
6. Estimate total time to complete all priorities

DELIVERABLES:
- Dependency graph (Mermaid or ASCII)
- Critical path analysis
- Recommended work sequence
- Risk analysis (blockers, dependencies)
- Total time estimate

USE THINKING MODE: Complex dependency analysis requires reasoning.""",
        "expected_teams": ["Research Team"],
        "estimated_time_manual": "1 hour",
        "success_criteria": [
            "Complete dependency graph",
            "Critical path identified",
            "Optimal sequence different from current order",
            "Risks identified"
        ]
    },

    {
        "id": "task4_multi_agent_feature",
        "title": "Multi-Agent Workflow: Implement Basic Metrics Dashboard",
        "description": """Complete feature implementation using multi-agent coordination.

CONTEXT:
- Priority: LOW (from priorities.yaml: "metrics_dashboard")
- Goal: Track priority worker effectiveness
- Dependencies: documentation_updates (but can start in parallel)

TASK (Multi-agent workflow):
1. RESEARCH: Best practices for Python metrics dashboards
   - What libraries? (Grafana, Streamlit, Dash?)
   - What metrics to track?
   - How to collect metrics?

2. DESIGN: Architecture for metrics collection
   - Where to instrument code?
   - How to store metrics?
   - Dashboard layout

3. IMPLEMENT: Basic metrics collection
   - Add instrumentation points
   - Create metrics collector class
   - Store to simple file/DB

4. TEST: Verify metrics collection works
   - Unit tests for collector
   - Integration test for full pipeline

DELIVERABLES:
- Research report (libraries, best practices)
- Architecture design doc
- Working code (metrics collector)
- Tests (unit + integration)

USE THINKING MODE: Multi-step coordination requires planning.""",
        "expected_teams": ["Research Team", "Backend Team", "Testing Team"],
        "estimated_time_manual": "4-6 hours",
        "success_criteria": [
            "Complete research with comparisons",
            "Clear architecture design",
            "Working code that runs",
            "Tests that pass"
        ]
    }
]


def run_dogfooding_task(task_spec, provider="qwen-agent"):
    """Execute a real dogfooding task using ATADO CLI."""

    print(f"\n{'='*70}")
    print(f"DOGFOODING TASK: {task_spec['id']}")
    print(f"{'='*70}")
    print(f"\nTitle: {task_spec['title']}")
    print(f"Manual estimate: {task_spec['estimated_time_manual']}")
    print(f"Expected teams: {', '.join(task_spec['expected_teams'])}")
    print(f"\nStarting execution with {provider}...")
    print(f"{'='*70}\n")

    # Create output directory
    output_dir = Path(__file__).parent.parent / "dogfooding_results"
    output_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"{task_spec['id']}_{timestamp}.txt"

    # Run via ATADO CLI
    cmd = [
        "python3", "-m", "src.main",
        "--provider", provider,
        "--routing", "team",
        "--agents", "scaled",
        "--orchestrator", "simple",
        "--collect-metrics",
        "--verbose",
        "--timeout", "300",  # 5 minutes
        "--task", task_spec['description']
    ]

    start_time = time.time()

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=320,  # Slightly longer than --timeout
            cwd=Path(__file__).parent.parent
        )

        end_time = time.time()
        duration = end_time - start_time

        # Save output
        with open(output_file, 'w') as f:
            f.write(f"Task: {task_spec['title']}\n")
            f.write(f"Started: {timestamp}\n")
            f.write(f"Duration: {duration:.1f}s\n")
            f.write(f"Exit code: {result.returncode}\n")
            f.write(f"\n{'='*70}\n")
            f.write("STDOUT:\n")
            f.write(f"{'='*70}\n")
            f.write(result.stdout)
            f.write(f"\n{'='*70}\n")
            f.write("STDERR:\n")
            f.write(f"{'='*70}\n")
            f.write(result.stderr)

        # Display results
        print(f"\n{'='*70}")
        print(f"TASK COMPLETED: {task_spec['id']}")
        print(f"{'='*70}")
        print(f"Duration: {duration:.1f}s ({duration/60:.1f} minutes)")
        print(f"Exit code: {result.returncode}")
        print(f"Output saved to: {output_file}")

        # Show preview
        print(f"\n{'='*70}")
        print("OUTPUT PREVIEW (first 1000 chars):")
        print(f"{'='*70}")
        print(result.stdout[:1000])
        if len(result.stdout) > 1000:
            print(f"\n... [{len(result.stdout) - 1000} more characters in {output_file}]")

        # Evaluate against success criteria
        print(f"\n{'='*70}")
        print("SUCCESS CRITERIA EVALUATION:")
        print(f"{'='*70}")

        output_lower = result.stdout.lower()
        criteria_met = []

        for criterion in task_spec['success_criteria']:
            # Simple heuristic: check if key terms appear
            key_terms = criterion.lower().split()[:3]  # First 3 words
            met = any(term in output_lower for term in key_terms)
            criteria_met.append(met)
            print(f"{'✅' if met else '❌'} {criterion}")

        success_rate = sum(criteria_met) / len(criteria_met) * 100
        print(f"\nSuccess rate: {success_rate:.0f}% ({sum(criteria_met)}/{len(criteria_met)})")

        return {
            "task_id": task_spec['id'],
            "success": result.returncode == 0 and success_rate >= 50,
            "duration": duration,
            "output_file": str(output_file),
            "success_rate": success_rate,
            "exit_code": result.returncode
        }

    except subprocess.TimeoutExpired:
        end_time = time.time()
        duration = end_time - start_time

        print(f"\n❌ TIMEOUT after {duration:.1f}s")

        return {
            "task_id": task_spec['id'],
            "success": False,
            "duration": duration,
            "output_file": None,
            "success_rate": 0,
            "exit_code": -1,
            "error": "Timeout"
        }

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()

        return {
            "task_id": task_spec['id'],
            "success": False,
            "duration": 0,
            "output_file": None,
            "success_rate": 0,
            "exit_code": -1,
            "error": str(e)
        }


def main():
    """Run all dogfooding tasks."""

    print("="*70)
    print("ATADO + QWEN DOGFOODING: REAL PRODUCTION TASKS")
    print("="*70)
    print(f"\nTasks to execute: {len(REAL_TASKS)}")
    print(f"Estimated total time (manual): 8-12 hours")
    print(f"Let's see how much time Qwen saves us!\n")

    # Ask for confirmation
    print("Press Enter to start dogfooding, or Ctrl+C to cancel...")
    input()

    results = []

    for i, task_spec in enumerate(REAL_TASKS, 1):
        print(f"\n{'#'*70}")
        print(f"# TASK {i}/{len(REAL_TASKS)}")
        print(f"{'#'*70}\n")

        result = run_dogfooding_task(task_spec)
        results.append(result)

        if i < len(REAL_TASKS):
            print(f"\n⏳ Waiting 5 seconds before next task...")
            time.sleep(5)

    # Final summary
    print(f"\n{'='*70}")
    print("DOGFOODING SUMMARY")
    print(f"{'='*70}")

    successful = [r for r in results if r['success']]
    total_duration = sum(r['duration'] for r in results)

    print(f"\nSuccessful: {len(successful)}/{len(results)} tasks")
    print(f"Total time: {total_duration:.1f}s ({total_duration/60:.1f} minutes)")
    print(f"Average time per task: {total_duration/len(results):.1f}s")

    print(f"\n{'Task':<40} {'Duration':<12} {'Success Rate':<15} {'Status'}")
    print("-" * 70)

    for result in results:
        status = "✅" if result['success'] else "❌"
        print(f"{result['task_id']:<40} {result['duration']:<12.1f} {result.get('success_rate', 0):<15.0f}% {status}")

    if len(successful) == len(results):
        print("\n✅ ALL DOGFOODING TASKS SUCCESSFUL!")
        print("Qwen + ATADO is production-ready for real development work.")
    else:
        print(f"\n⚠️ {len(results) - len(successful)} task(s) need review")
        print("Check output files for details.")

    print(f"\n📁 All outputs saved to: dogfooding_results/")

    return 0 if len(successful) >= len(results) * 0.75 else 1


if __name__ == "__main__":
    sys.exit(main())
