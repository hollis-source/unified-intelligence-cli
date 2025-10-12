"""Priority Analysis Tasks - Real CLI integration for priorities workflow.

Clean Architecture: Tasks layer (DSL → CLI bridge).
SOLID: SRP - each task maps to specific ULTRATHINK analysis.
"""

import subprocess
import json
from typing import Any, Dict
import asyncio


async def analyze_current_state(input_data: Any = None) -> Dict[str, Any]:
    """
    Analyze current project state using CLI multi-agent orchestration.

    Executes ULTRATHINK analysis of:
    - Recent commits and deployment status
    - Completed work (Sprint 1 Phase 1, Story 2, SYD2)
    - Architecture maturity and technical debt

    Returns:
        StateAnalysis with current project status
    """
    cmd = [
        "./bin/ui-cli",
        "--provider", "auto",
        "--routing", "team",
        "--agents", "scaled",
        "--orchestrator", "simple",
        "--verbose",  # Enable full output display
        "--timeout", "180",
        "--task",
        "ULTRATHINK: Analyze unified-intelligence-cli current state. "
        "Review: recent commits, SYD2 deployment, Sprint 1 Phase 1 completion, "
        "Story 2 research. Assess: architecture quality, technical debt, "
        "production readiness. Output: concise state summary."
    ]

    result = await _run_cli_task(cmd, "analyze_current_state")
    return result


async def assess_dsl_priorities(input_data: Any = None) -> Dict[str, Any]:
    """
    Assess DSL implementation priorities.

    Executes ULTRATHINK analysis of:
    - Existing DSL capabilities (parser, executor, operators)
    - Missing components for workflow execution
    - Integration gaps with type system

    Returns:
        DSLPriorities with recommended enhancements
    """
    cmd = [
        "./bin/ui-cli",
        "--provider", "auto",
        "--routing", "team",
        "--agents", "scaled",
        "--orchestrator", "simple", "--verbose",
        "--timeout", "180",
        "--task",
        "ULTRATHINK: Assess DSL implementation priorities. "
        "Review: src/dsl structure, parser, interpreter, operators. "
        "Identify: missing runtime components, type system integration gaps. "
        "Output: top 3 DSL priorities with business value."
    ]

    result = await _run_cli_task(cmd, "assess_dsl_priorities")
    return result


async def assess_sprint_priorities(input_data: Any = None) -> Dict[str, Any]:
    """
    Evaluate Sprint 1 remaining phases priority order.

    Executes ULTRATHINK analysis of:
    - Sprint 1 phases 2-5 (AST, operators, laws, errors)
    - Dependencies between phases
    - Implementation complexity estimates

    Returns:
        SprintPriorities with recommended phase order
    """
    cmd = [
        "./bin/ui-cli",
        "--provider", "auto",
        "--routing", "team",
        "--agents", "scaled",
        "--orchestrator", "simple", "--verbose",
        "--timeout", "180",
        "--task",
        "ULTRATHINK: Evaluate Sprint 1 phases 2-5 priority order. "
        "Review: docs/SPRINT_1_TYPE_SYSTEM_PLAN.md. Phase 1 complete. "
        "Assess: AST integration, composition operators, category laws, errors. "
        "Output: recommended phase order with rationale."
    ]

    result = await _run_cli_task(cmd, "assess_sprint_priorities")
    return result


async def evaluate_syd2_synergy(input_data: Any = None) -> Dict[str, Any]:
    """
    Analyze SYD2 agent synergy with potential priorities.

    Executes ULTRATHINK analysis of:
    - SYD2 capabilities (task execution, metrics, patterns)
    - Dogfooding opportunities with each priority
    - Feedback quality expectations

    Returns:
        SYD2Synergy with synergy scores for priorities
    """
    cmd = [
        "./bin/ui-cli",
        "--provider", "auto",
        "--routing", "team",
        "--agents", "scaled",
        "--orchestrator", "simple", "--verbose",
        "--timeout", "180",
        "--task",
        "ULTRATHINK: Analyze SYD2 agent synergy with priorities. "
        "SYD2 deployed at syd2.jacobhollis.com: task execution, metrics, "
        "pattern detection, self-improvement. Identify: which priorities benefit "
        "most from SYD2 testing. Output: synergy analysis with recommendations."
    ]

    result = await _run_cli_task(cmd, "evaluate_syd2_synergy")
    return result


async def synthesize_recommendation(input_data: Any = None) -> Dict[str, Any]:
    """
    Synthesize final priority recommendation from all analyses.

    Takes aggregated results from:
    - Current state analysis
    - DSL priorities
    - Sprint priorities
    - SYD2 synergy

    Returns:
        FinalRecommendation with single highest-priority task
    """
    # Extract analysis results from nested tuple structure
    if isinstance(input_data, tuple):
        # Flatten nested tuples from broadcast composition
        analyses = _flatten_tuple(input_data)
        analyses_text = "\n\n".join([
            f"Analysis {i+1}:\n{_format_analysis(a)}"
            for i, a in enumerate(analyses)
        ])
    else:
        analyses_text = str(input_data)

    cmd = [
        "./bin/ui-cli",
        "--provider", "auto",
        "--routing", "team",
        "--agents", "scaled",
        "--orchestrator", "simple", "--verbose",
        "--timeout", "300",
        "--task",
        f"ULTRATHINK: Synthesize final priority recommendation from analyses:\n\n"
        f"{analyses_text}\n\n"
        f"Requirements: Identify top 3 priorities, assess business value + "
        f"dependencies + complexity + SYD2 synergy. Recommend single highest "
        f"priority with implementation approach (Clean Architecture + SOLID). "
        f"Output: structured recommendation with clear rationale."
    ]

    result = await _run_cli_task(cmd, "synthesize_recommendation")
    return result


async def _run_cli_task(command: list, task_name: str) -> Dict[str, Any]:
    """
    Execute CLI command and return parsed result.

    Args:
        command: Command list to execute
        task_name: Name of the task for logging

    Returns:
        Dictionary with task result
    """
    try:
        # Run command asynchronously
        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        stdout, stderr = await process.communicate()

        if process.returncode == 0:
            output = stdout.decode('utf-8')
            return {
                "task": task_name,
                "status": "success",
                "output": output,
                "raw_output": output
            }
        else:
            error = stderr.decode('utf-8')
            return {
                "task": task_name,
                "status": "failed",
                "error": error
            }

    except Exception as e:
        return {
            "task": task_name,
            "status": "failed",
            "error": str(e)
        }


def _flatten_tuple(t: tuple) -> list:
    """
    Flatten nested tuple structure from broadcast composition.

    Args:
        t: Nested tuple from product composition

    Returns:
        Flattened list of elements
    """
    result = []
    for item in t:
        if isinstance(item, tuple):
            result.extend(_flatten_tuple(item))
        else:
            result.append(item)
    return result


def _format_analysis(analysis: Any) -> str:
    """
    Format analysis result for synthesis.

    Args:
        analysis: Analysis result (dict or other)

    Returns:
        Formatted string
    """
    if isinstance(analysis, dict):
        if 'output' in analysis:
            return analysis['output']
        else:
            return json.dumps(analysis, indent=2)
    else:
        return str(analysis)
