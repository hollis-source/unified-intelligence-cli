#!/usr/bin/env python3
"""
Agent Metrics Harness
=====================

Executes agent tasks, collects metrics, and tracks performance over time.

Based on: docs/AGENT_METRICS_SYSTEM.md

Usage:
    python scripts/metrics_harness.py --tasks tasks/database/db-01.yaml
    python scripts/metrics_harness.py --tasks tasks/**/*.yaml --output metrics/run1.jsonl
"""

import argparse
import json
import re
import subprocess
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import yaml


# ============================================================================
# Configuration
# ============================================================================

METRICS_DIR = Path("metrics")
METRICS_DIR.mkdir(exist_ok=True)

# Specificity detection: file:line pattern
FILELINE_REGEX = re.compile(r"[A-Za-z0-9_./-]+\.[A-Za-z0-9]{1,6}:\d+")

# Acceptance thresholds per agent
ACCEPTANCE_THRESHOLDS = {
    "python": (6, 6),  # (auto_min, human_min)
    "architect": (5, 7),
    "test": (6, 6),
    "database": (6, 6),
    "devops": (6, 6),
    "qa": (5, 6),  # QA agent - lower auto threshold (diverse task types: BDD, accessibility, UAT, etc.)
}


# ============================================================================
# Core Metrics Functions
# ============================================================================

def load_task(task_path: Path) -> Dict[str, Any]:
    """Load task YAML file."""
    with open(task_path) as f:
        return yaml.safe_load(f)


def run_agent_task(agent: str, prompt: str, timeout: int = 300) -> Dict[str, Any]:
    """
    Execute agent task via CLI.

    Returns:
        {
            "ok": bool,  # Success/failure
            "latency": float,  # Seconds
            "output": str,  # Agent response
            "usage": dict,  # Token usage metadata
            "error": str,  # Error message if failed
        }
    """
    t0 = time.time()

    try:
        # Actual CLI interface (uses team routing to determine agent)
        # Agent type is determined by task content and team-based routing
        # Use venv python (has all dependencies, including tenacity)
        venv_python = Path(__file__).parent.parent / "venv" / "bin" / "python"
        python_cmd = str(venv_python) if venv_python.exists() else "python3"

        cmd = [
            python_cmd, "-m", "src.main",
            "--task", f"[{agent.upper()} AGENT TASK] {prompt}",  # Hint for routing
            "--provider", "granite",  # Use local Granite (better instruction-following than Grok)
            "--routing", "team",  # Team-based routing
            "--agents", "scaled",  # Enable multi-agent team routing
            "--orchestrator", "simple",
            "--collect-metrics",  # Enable metrics collection
            "--timeout", str(timeout)
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout
        )

        latency = time.time() - t0

        # Try to parse stderr for metadata (token usage)
        # Phase 2: JSON is on last line of stderr (may have warnings/logs before it)
        usage = {}
        try:
            if result.stderr:
                # Get last non-empty line (JSON metadata)
                lines = result.stderr.strip().split('\n')
                json_line = lines[-1] if lines else ""
                if json_line:
                    usage = json.loads(json_line)
        except json.JSONDecodeError:
            pass
        except Exception:
            pass

        return {
            "ok": result.returncode == 0,
            "latency": latency,
            "output": result.stdout,
            "usage": usage,
            "error": result.stderr if result.returncode != 0 else None
        }

    except subprocess.TimeoutExpired:
        latency = time.time() - t0
        return {
            "ok": False,
            "latency": latency,
            "output": "",
            "usage": {},
            "error": f"Timeout after {timeout}s"
        }

    except Exception as e:
        latency = time.time() - t0
        return {
            "ok": False,
            "latency": latency,
            "output": "",
            "usage": {},
            "error": str(e)
        }


def run_check(check, output: str) -> bool:
    """
    Execute a single check (string substring, regex, or cmd).

    Args:
        check: str (simple substring check) or dict {"type": "regex|cmd", ...}
        output: Agent output text

    Returns:
        True if check passes
    """
    # Handle simple string checks (substring match)
    if isinstance(check, str):
        return check.lower() in output.lower()

    # Handle dict checks (regex or cmd)
    if not isinstance(check, dict):
        return False

    check_type = check.get("type")

    if check_type == "regex":
        pattern = check.get("pattern", "")
        return bool(re.search(pattern, output, re.MULTILINE | re.DOTALL))

    elif check_type == "cmd":
        cmd = check.get("run", "")
        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, timeout=60)
            return result.returncode == 0
        except Exception:
            return False

    return False


def compute_auto_checks(agent: str, output: str, task_dir: Path) -> float:
    """
    Compute AutoChecks score (0-10) based on agent-specific criteria.

    Phase B: Refined scoring with real checks, no placeholders.
    Weights tuned for consistency and to incentivize specificity.

    Args:
        agent: Agent type (python, architect, test, database, devops)
        output: Agent output text
        task_dir: Task working directory

    Returns:
        Score 0-10 (max: 5pts base + 5pts agent-specific)
    """
    score = 0.0

    # Base quality indicators (max 5 pts)
    if len(output) > 200:
        score += 1.5  # Substantial output (reduced from 2)

    if "```" in output:
        score += 1.5  # Contains code blocks (reduced from 2)

    if is_specific(output):
        score += 2.0  # Has file:line references (INCREASED from 1 - incentivize!)

    # Agent-specific checks (max 5 pts)
    if agent == "python":
        # Code structure (2 pts)
        if "def " in output or "class " in output:
            score += 2.0

        # Type hints (1 pt) - broader detection
        if any(pattern in output for pattern in ["type:", "->", ": str", ": int", ": List", ": Dict"]):
            score += 1.0

        # Documentation (1 pt)
        if '"""' in output or "'''" in output:
            score += 1.0

        # Testing/quality (1 pt)
        if "test_" in output or "assert" in output or "pytest" in output:
            score += 1.0

    elif agent == "architect":
        # Architecture patterns (2 pts)
        if "diagram" in output.lower() or "architecture" in output.lower():
            score += 2.0

        # Decision rationale (1 pt)
        if "decision" in output.lower() or "adr" in output.lower() or "trade-off" in output.lower():
            score += 1.0

        # Components/layers (1 pt)
        if "component" in output.lower() or "layer" in output.lower() or "service" in output.lower():
            score += 1.0

        # Design patterns (1 pt)
        if any(p in output.lower() for p in ["pattern", "solid", "dry", "factory", "adapter", "singleton"]):
            score += 1.0

    elif agent == "test":
        # Test structure (2 pts)
        if "test_" in output or "def test" in output:
            score += 2.0

        # Assertions (1.5 pts)
        if "assert" in output:
            score += 1.5

        # Test framework (0.5 pt)
        if "import pytest" in output or "import unittest" in output:
            score += 0.5

        # Mocking/fixtures (1 pt)
        if any(pattern in output for pattern in ["fixture", "mock", "Mock", "@pytest", "setUp"]):
            score += 1.0

    elif agent == "database":
        # SQL operations (2 pts)
        if any(kw in output for kw in ["CREATE", "SELECT", "INSERT", "UPDATE", "DELETE"]):
            score += 2.0

        # Indexing (1 pt)
        if "INDEX" in output or "index" in output.lower():
            score += 1.0

        # Constraints/keys (1 pt)
        if any(kw in output for kw in ["PRIMARY KEY", "FOREIGN KEY", "UNIQUE", "NOT NULL"]):
            score += 1.0

        # Transactions/performance (1 pt)
        if any(kw in output for kw in ["TRANSACTION", "COMMIT", "ROLLBACK", "EXPLAIN", "optimize"]):
            score += 1.0

    elif agent == "devops":
        # CI/CD config (2 pts)
        if "name:" in output and "run:" in output:
            score += 2.0

        # Pipeline structure (1 pt)
        if "steps:" in output or "jobs:" in output or "stages:" in output:
            score += 1.0

        # Containerization (1 pt)
        if any(kw in output for kw in ["Dockerfile", "docker", "container", "image:"]):
            score += 1.0

        # Orchestration (1 pt)
        if any(kw in output for kw in ["kubernetes", "k8s", "deployment:", "service:", "helm"]):
            score += 1.0

    elif agent == "qa":
        # BDD/Gherkin scenarios (2 pts)
        if "Feature:" in output or "Scenario:" in output:
            score += 2.0

        # Given/When/Then structure (1.5 pts)
        if all(kw in output for kw in ["Given", "When", "Then"]):
            score += 1.5

        # Exploratory testing + Test planning (1.5 pts) - combined for overlap
        if any(kw in output.lower() for kw in ["charter", "explore", "risk", "test plan", "traceability", "coverage"]):
            score += 1.5

        # UAT/persona-based + Accessibility + Cross-browser (2 pts total) - combined coverage indicators
        qa_coverage_count = sum([
            any(kw in output.lower() for kw in ["persona", "user acceptance", "uat"]),
            any(kw in output for kw in ["WCAG", "accessibility", "screen reader", "ARIA"]),
            any(kw in output.lower() for kw in ["browser", "compatibility", "matrix"]),
            "P0" in output or "P1" in output or "P2" in output,  # Priority classification
        ])
        score += min(qa_coverage_count * 0.5, 2.0)  # 0.5 pts each, max 2 pts

        # Comprehensive accessibility testing bonus (1.0 pt)
        # Recognizes deep accessibility coverage (compensates for lack of BDD patterns in accessibility tasks)
        accessibility_indicators = sum([
            "WCAG" in output,
            "accessibility" in output.lower(),
            "screen reader" in output.lower(),
            "ARIA" in output,
            "keyboard" in output.lower(),
        ])
        if accessibility_indicators >= 3:
            score += 1.0  # Comprehensive accessibility coverage

    return min(score, 10.0)


def is_specific(text: str) -> bool:
    """Check if output contains file:line references."""
    return bool(FILELINE_REGEX.search(text or ""))


def estimate_tokens(text: str) -> int:
    """Estimate tokens from text length (rough: 1 token ≈ 4 chars)."""
    return len(text) // 4


def compute_tokens(usage: Dict[str, Any], output: str = "") -> int:
    """Extract total tokens from usage metadata, or estimate from output.

    Args:
        usage: Usage metadata dict with prompt_tokens, completion_tokens, total_tokens
        output: Response text to estimate from if usage is empty

    Returns:
        Token count (actual or estimated)

    Phase 2: Prefer total_tokens (includes system prompts & overhead)
    """
    # Try to get actual token count from usage metadata
    if usage:
        # Prefer total_tokens (most accurate, includes all overhead)
        total = usage.get("total_tokens", 0)
        if total > 0:
            return int(total)

        # Fallback to sum of prompt + completion
        actual = int(usage.get("prompt_tokens", 0) + usage.get("completion_tokens", 0))
        if actual > 0:
            return actual

    # Fallback to estimation from output text
    return estimate_tokens(output) if output else 0


def compute_quality(auto_score: float, human_score: Optional[float]) -> float:
    """Compute quality score: 0.6*auto + 0.4*human."""
    auto10 = max(0, min(10, auto_score))
    hum10 = human_score if human_score is not None else 0
    return 0.6 * auto10 + 0.4 * hum10


def is_completed(agent: str, quality: float, checks_ok: bool, required_checks: str) -> bool:
    """Determine if task is completed based on acceptance criteria."""
    if required_checks == "all" and not checks_ok:
        return False

    auto_min, human_min = ACCEPTANCE_THRESHOLDS.get(agent, (6, 6))
    # For now, use quality score as proxy (proper split would need separate human rating)
    return quality >= max(auto_min, human_min)


# ============================================================================
# Task Execution
# ============================================================================

def execute_task(task_path: Path, verbose: bool = False) -> Dict[str, Any]:
    """Execute single task and collect metrics."""
    task = load_task(task_path)
    task_id = task.get("id", task_path.stem)
    agent = task.get("agent", "unknown")
    prompt = task.get("prompt", "")
    checks = task.get("checks", [])
    acceptance = task.get("acceptance", {})
    required_checks = acceptance.get("required_checks", "all")

    if verbose:
        print(f"\n{'='*70}")
        print(f"Executing: {task_id} (agent: {agent})")
        print(f"{'='*70}")

    # Execute agent task
    result = run_agent_task(agent, prompt)

    if verbose:
        print(f"Status: {'✓ OK' if result['ok'] else '✗ FAILED'}")
        print(f"Latency: {result['latency']:.2f}s")

    # Run checks
    checks_ok = True
    if checks:
        checks_ok = all(run_check(check, result["output"]) for check in checks)
        if verbose:
            print(f"Checks: {'✓ PASS' if checks_ok else '✗ FAIL'}")

    # Compute metrics
    auto_score = compute_auto_checks(agent, result["output"], task_path.parent)
    tokens = compute_tokens(result["usage"], result["output"])
    specific = is_specific(result["output"])
    quality = compute_quality(auto_score, None)  # No human rating yet
    completed = is_completed(agent, quality, checks_ok, required_checks)

    if verbose:
        print(f"AutoChecks: {auto_score:.1f}/10")
        print(f"Quality: {quality:.1f}/10")
        print(f"Tokens: {tokens}")
        print(f"Specific: {specific}")
        print(f"Completed: {completed}")

    # Create record
    record = {
        "timestamp": datetime.now(datetime.UTC).isoformat() if hasattr(datetime, 'UTC') else datetime.utcnow().isoformat(),
        "task_id": task_id,
        "agent": agent,
        "ok": result["ok"],
        "latency": result["latency"],
        "tokens": tokens,
        "specific": specific,
        "auto_score": auto_score,
        "human_score": None,
        "quality": quality,
        "checks_ok": checks_ok,
        "completed": completed,
        "output_length": len(result["output"]),
        "error": result["error"]
    }

    return record


def execute_suite(task_paths: List[Path], output_path: Path, verbose: bool = False) -> List[Dict[str, Any]]:
    """Execute all tasks in suite and collect metrics."""
    records = []

    print(f"\nExecuting {len(task_paths)} tasks...")
    print(f"Output: {output_path}")
    print()

    for i, task_path in enumerate(task_paths, 1):
        print(f"[{i}/{len(task_paths)}] {task_path.name}...", end=" ")
        try:
            record = execute_task(task_path, verbose=verbose)
            records.append(record)
            status = "✓" if record["completed"] else "✗"
            print(f"{status} ({record['latency']:.1f}s, Q={record['quality']:.1f})")
        except Exception as e:
            print(f"✗ ERROR: {e}")
            records.append({
                "timestamp": datetime.now(datetime.UTC).isoformat() if hasattr(datetime, 'UTC') else datetime.utcnow().isoformat(),
                "task_id": task_path.stem,
                "agent": "unknown",
                "ok": False,
                "error": str(e)
            })

    # Write JSONL
    with open(output_path, "a") as f:
        for record in records:
            f.write(json.dumps(record) + "\n")

    return records


# ============================================================================
# Reporting
# ============================================================================

def compute_rollup(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Compute aggregate metrics per agent."""
    by_agent = defaultdict(list)
    for r in records:
        by_agent[r["agent"]].append(r)

    rollup = {}
    for agent, recs in by_agent.items():
        completed_count = sum(1 for r in recs if r.get("completed", False))
        latencies = [r["latency"] for r in recs if "latency" in r]
        tokens_list = [r["tokens"] for r in recs if "tokens" in r]
        specifics = [r["specific"] for r in recs if "specific" in r]
        qualities = [r["quality"] for r in recs if "quality" in r]

        rollup[agent] = {
            "tasks_attempted": len(recs),
            "tasks_completed": completed_count,
            "completion_rate": 100 * completed_count / len(recs) if recs else 0,
            "quality_mean": np.mean(qualities) if qualities else 0,
            "latency_p95": float(np.percentile(latencies, 95)) if latencies else 0,
            "cost_mean_tokens": int(np.mean(tokens_list)) if tokens_list else 0,
            "specificity": 100 * sum(specifics) / len(specifics) if specifics else 0,
        }

    return rollup


def print_rollup(rollup: Dict[str, Any]):
    """Print rollup metrics table."""
    print("\n" + "="*80)
    print("AGENT PERFORMANCE ROLLUP")
    print("="*80)
    print(f"{'Agent':<15} {'Rate':<8} {'Quality':<8} {'P95(s)':<8} {'Tokens':<8} {'Spec%':<8}")
    print("-"*80)

    for agent, metrics in sorted(rollup.items()):
        print(f"{agent:<15} "
              f"{metrics['completion_rate']:>6.1f}% "
              f"{metrics['quality_mean']:>6.1f}/10 "
              f"{metrics['latency_p95']:>6.1f}s "
              f"{metrics['cost_mean_tokens']:>6}t "
              f"{metrics['specificity']:>6.1f}%")

    print("="*80)


# ============================================================================
# CLI
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description="Agent Metrics Harness")
    parser.add_argument("--tasks", required=True, help="Task YAML files (glob pattern)")
    parser.add_argument("--output", default="metrics/run.jsonl", help="Output JSONL path")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    args = parser.parse_args()

    # Find task files
    task_paths = list(Path(".").glob(args.tasks))
    if not task_paths:
        print(f"No tasks found matching: {args.tasks}")
        return 1

    # Execute suite
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    records = execute_suite(task_paths, output_path, verbose=args.verbose)

    # Compute and print rollup
    rollup = compute_rollup(records)
    print_rollup(rollup)

    print(f"\nMetrics saved to: {output_path}")

    return 0


if __name__ == "__main__":
    exit(main())
