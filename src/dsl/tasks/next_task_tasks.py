"""Next Task Analysis - Determine immediate implementation priority.

Clean Architecture: Tasks layer for next-step analysis.
SOLID: SRP - each task assesses one aspect of readiness.
"""

import asyncio
from typing import Any, Dict


async def assess_p2_readiness(input_data: Any = None) -> Dict[str, Any]:
    """
    Assess readiness for P2: Testing Infrastructure implementation.

    Analyzes:
    - Current test coverage status
    - DSL runtime test requirements
    - Integration test needs
    - Mock infrastructure availability

    Returns:
        TestingReadiness assessment
    """
    cmd = [
        "./bin/ui-cli",
        "--provider", "auto",
        "--routing", "team",
        "--agents", "scaled",
        "--orchestrator", "simple",
        "--verbose",
        "--timeout", "180",
        "--task",
        "ULTRATHINK: Assess P2 Testing Infrastructure readiness. "
        "Current: 85% coverage (104 tests). New code: DSL runtime (interpreter, "
        "symbol table, CLI integration, 5 tasks). Requirements: pytest-cov setup, "
        "DSL workflow tests, mock CLI adapter, integration tests. "
        "Assess: effort (hours), dependencies, blockers. Output: readiness score + plan."
    ]

    return await _run_cli_task(cmd, "assess_p2_readiness")


async def assess_type_integration(input_data: Any = None) -> Dict[str, Any]:
    """
    Assess readiness for Hindley-Milner type checking integration.

    Analyzes:
    - Current HM implementation status
    - DSL interpreter integration points
    - Runtime type validation needs
    - Category law enforcement

    Returns:
        TypeCheckingReadiness assessment
    """
    cmd = [
        "./bin/ui-cli",
        "--provider", "auto",
        "--routing", "team",
        "--agents", "scaled",
        "--orchestrator", "simple",
        "--verbose",
        "--timeout", "180",
        "--task",
        "ULTRATHINK: Assess Hindley-Milner type integration readiness. "
        "Existing: Sprint 1 Phase 1 complete (HM type system in src/dsl/types/). "
        "DSL runtime: interpreter with symbol table, functor resolution. "
        "Requirements: connect HM to interpreter, runtime type validation, "
        "type error reporting. Assess: complexity, integration points, effort. "
        "Output: readiness score + integration approach."
    ]

    return await _run_cli_task(cmd, "assess_type_integration")


async def assess_syd2_opportunities(input_data: Any = None) -> Dict[str, Any]:
    """
    Assess SYD2 agent enhancement opportunities.

    Analyzes:
    - Current SYD2 performance (3/3 tasks SUCCESS)
    - Pattern detection readiness (need 20+ tasks)
    - Improvement cycle opportunities
    - Metrics analysis enhancements

    Returns:
        SYD2Enhancement opportunities
    """
    cmd = [
        "./bin/ui-cli",
        "--provider", "auto",
        "--routing", "team",
        "--agents", "scaled",
        "--orchestrator", "simple",
        "--verbose",
        "--timeout", "180",
        "--task",
        "ULTRATHINK: Assess SYD2 agent enhancement opportunities. "
        "Status: 100% success rate (3/3 tasks), 24h cycle running, "
        "pattern detection after 20 tasks (~2 hrs). Current: Phase 1-3 complete. "
        "Phase 4 pending: advanced patterns, ML anomalies, predictive issues. "
        "Assess: quick wins vs long-term enhancements, effort, immediate value. "
        "Output: enhancement priorities + ROI."
    ]

    return await _run_cli_task(cmd, "assess_syd2_opportunities")


async def evaluate_technical_debt(input_data: Any = None) -> Dict[str, Any]:
    """
    Evaluate technical debt and refactoring needs.

    Analyzes:
    - Code quality issues
    - Architecture violations
    - Performance bottlenecks
    - Documentation gaps

    Returns:
        DebtAssessment with priorities
    """
    cmd = [
        "./bin/ui-cli",
        "--provider", "auto",
        "--routing", "team",
        "--agents", "scaled",
        "--orchestrator", "simple",
        "--verbose",
        "--timeout", "180",
        "--task",
        "ULTRATHINK: Evaluate technical debt after P0+P1 implementation. "
        "Recent changes: environment wrapper, DSL runtime, output fixes. "
        "Review: code quality, architecture compliance, performance, documentation. "
        "Identify: quick fixes, refactoring needs, optimization opportunities. "
        "Assess: impact if deferred, effort to resolve. Output: debt priorities."
    ]

    return await _run_cli_task(cmd, "evaluate_technical_debt")


async def determine_next_task(input_data: Any = None) -> Dict[str, Any]:
    """
    Determine immediate next implementation task.

    Synthesizes all assessments to identify:
    - Highest priority task
    - Implementation approach
    - Effort estimate
    - Success criteria

    Returns:
        NextTask with concrete plan
    """
    # Extract and flatten analysis results
    if isinstance(input_data, tuple):
        analyses = _flatten_tuple(input_data)
        analyses_text = "\n\n".join([
            f"Assessment {i+1}: {a.get('task', 'unknown')}\n{_format_analysis(a)}"
            for i, a in enumerate(analyses)
        ])
    else:
        analyses_text = str(input_data)

    cmd = [
        "./bin/ui-cli",
        "--provider", "auto",
        "--routing", "team",
        "--agents", "scaled",
        "--orchestrator", "simple",
        "--verbose",
        "--timeout", "300",
        "--task",
        f"ULTRATHINK: Determine immediate next implementation task.\n\n"
        f"Context: P0 (environment) ✅ P1 (DSL runtime) ✅ Fix (truncation) ✅\n"
        f"SYD2 agent: 100% success, 24h validation running\n\n"
        f"Assessments:\n{analyses_text}\n\n"
        f"Requirements:\n"
        f"1. Identify SINGLE highest-priority task (not multiple)\n"
        f"2. Must be implementable in 2-4 hours (quick win)\n"
        f"3. High impact / low risk\n"
        f"4. Builds on P0+P1 success\n"
        f"5. Provides immediate value\n\n"
        f"Output:\n"
        f"- Task name and description\n"
        f"- Implementation approach (Clean Architecture)\n"
        f"- Effort estimate (hours)\n"
        f"- Success criteria (3-5 items)\n"
        f"- Files to create/modify"
    ]

    return await _run_cli_task(cmd, "determine_next_task")


# Helper functions (reuse from priorities_analysis_tasks)

async def _run_cli_task(command: list, task_name: str) -> Dict[str, Any]:
    """Execute CLI command and return parsed result."""
    try:
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
    """Flatten nested tuple structure."""
    result = []
    for item in t:
        if isinstance(item, tuple):
            result.extend(_flatten_tuple(item))
        else:
            result.append(item)
    return result


def _format_analysis(analysis: Any) -> str:
    """Format analysis result."""
    if isinstance(analysis, dict):
        if 'output' in analysis:
            # Truncate long outputs for context
            output = analysis['output']
            if len(output) > 500:
                return output[:250] + "\n...\n" + output[-250:]
            return output
        else:
            import json
            return json.dumps(analysis, indent=2)
    else:
        return str(analysis)
