#!/usr/bin/env python3
"""Autonomous Development Companion CLI Tool (Phases A & B)

Clean Architecture-aligned CLI wrapper around the existing AutonomousOrchestrator
stack to enable continuous autonomous development workflows with metrics
persistence.

Phase A: CLI interface + modes (Click)
Phase B: Metrics persistence (JSON at ~/.ui-cli/autonomous_metrics.json)

Notes:
- We do NOT modify orchestrator/use-cases; we compose them here.
- We time phases ourselves (context → generate → execute) to persist metrics.
- Status/reset operate purely on the metrics file.

Dependencies: click, pathlib (standard lib), json, datetime, time

Future (Phase C): rich dashboard + resume state (autonomous_state.json)
"""
from __future__ import annotations

import json
import os
import sys
import time
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

import click
import requests

# Clean Architecture: use existing orchestrator components (entities/use-cases/adapters)
from src.claude_orchestrator.entities.worker import WorkerPoolConfig
from src.claude_orchestrator.adapters.single_worker_pool import SingleWorkerPool
from src.claude_orchestrator.adapters.git_context_analyzer import GitContextAnalyzer
from src.claude_orchestrator.adapters.pytest_analyzer import PytestAnalyzer
from src.claude_orchestrator.adapters.coverage_analyzer import CoverageAnalyzer
from src.claude_orchestrator.adapters.goal_parser import GoalParser
from src.claude_orchestrator.use_cases.analyze_context_use_case import AnalyzeContextUseCase
from src.claude_orchestrator.use_cases.generate_next_task_use_case import (
    GenerateNextTaskUseCase,
)

# Optional to import orchestrator for future use; not required for Phases A/B metrics
# from src.claude_orchestrator.orchestrators.autonomous_orchestrator import AutonomousOrchestrator


# ==============================
# Metrics Persistence (Phase B)
# ==============================

# Dashboard API configuration
DASHBOARD_API_URL = os.environ.get(
    "DASHBOARD_API_URL",
    "http://syd2.jacobhollis.com:8080/api/metrics/iteration"
)
DASHBOARD_API_KEY = os.environ.get(
    "DASHBOARD_API_KEY",
    "auggie-secret-key"
)

@dataclass
class IterationMetrics:
    timestamp: str
    iteration_number: int
    mode: str

    duration_total: float
    duration_context: float
    duration_generation: float
    duration_execution: float

    success: bool
    task_id: Optional[str]
    task_goal: Optional[str]
    task_priority: Optional[str]


class MetricsTracker:
    """Tracks and persists per-iteration and aggregate metrics.

    SRP: single responsibility for metrics collection/persistence.
    DIP: storage location abstracted via path passed at init.
    """

    def __init__(self, path: Optional[Path] = None) -> None:
        self.base_dir = Path(os.path.expanduser("~/.ui-cli"))
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.path = path or (self.base_dir / "autonomous_metrics.json")
        self._data: Dict[str, Any] = {"iterations": [], "aggregate": {}}
        self._load()

    # Public API
    def record_iteration(self, metrics: IterationMetrics) -> None:
        payload = asdict(metrics)
        self._data.setdefault("iterations", []).append(payload)
        self._recompute_aggregates()
        self._save()
        self._post_to_dashboard(payload)

    def reset(self) -> None:
        self._data = {"iterations": [], "aggregate": {}}
        self._save()

    def get_data(self) -> Dict[str, Any]:
        return self._data

    # Internal
    def _load(self) -> None:
        if self.path.exists():
            try:
                self._data = json.loads(self.path.read_text())
            except Exception:
                # corrupt file → reset to empty
                self._data = {"iterations": [], "aggregate": {}}

    def _save(self) -> None:
        self.path.write_text(json.dumps(self._data, indent=2))

    def _recompute_aggregates(self) -> None:
        its: List[Dict[str, Any]] = self._data.get("iterations", [])
        total = len(its)
        success = sum(1 for i in its if i.get("success"))
        by_mode: Dict[str, List[Dict[str, Any]]] = {}
        for it in its:
            by_mode.setdefault(it.get("mode", "unknown"), []).append(it)

        def avg(items: List[Dict[str, Any]], key: str) -> float:
            vals = [float(x.get(key, 0.0) or 0.0) for x in items]
            return (sum(vals) / len(vals)) if items else 0.0

        avg_duration_by_mode = {
            m: avg(v, "duration_total") for m, v in by_mode.items()
        }
        success_rate_by_mode = {
            m: (sum(1 for x in v if x.get("success")) / len(v) if v else 0.0)
            for m, v in by_mode.items()
        }
        tasks_by_goal: Dict[str, int] = {}
        tasks_by_priority: Dict[str, int] = {}
        for it in its:
            g = it.get("task_goal") or "unknown"
            p = it.get("task_priority") or "unknown"
            tasks_by_goal[g] = tasks_by_goal.get(g, 0) + 1
            tasks_by_priority[p] = tasks_by_priority.get(p, 0) + 1

        self._data["aggregate"] = {
            "total_iterations": total,
            "successful": success,
            "failed": total - success,
            "success_rate": (success / total if total else 0.0),
            "avg_duration_by_mode": avg_duration_by_mode,
            "success_rate_by_mode": success_rate_by_mode,
            "tasks_by_goal": tasks_by_goal,
            "tasks_by_priority": tasks_by_priority,
        }

    def _post_to_dashboard(self, metrics: Dict[str, Any]) -> None:
        """POST metrics to unified dashboard API with retry logic.

        Fails silently if dashboard unavailable to not block local metrics.
        Implements exponential backoff: 3 attempts with 1s, 2s, 4s delays.
        Following Clean Architecture: external I/O isolated in adapter layer.
        """
        # Map our modes/priorities to dashboard's expected values
        mode_mapping = {
            "fast": "autonomous",
            "thorough": "execution",
            "full": "validation",
        }
        priority_mapping = {
            "P1": "critical",
            "P2": "high",
            "P3": "medium",
            "P4": "low",
            "critical": "critical",
            "high": "high",
            "medium": "medium",
            "low": "low",
        }

        payload = metrics.copy()
        payload["mode"] = mode_mapping.get(payload.get("mode"), "autonomous")

        # Map priority if present
        if "task_priority" in payload and payload["task_priority"]:
            payload["task_priority"] = priority_mapping.get(
                payload["task_priority"], "medium"
            )

        # Retry logic with exponential backoff
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = requests.post(
                    DASHBOARD_API_URL,
                    json=payload,
                    headers={"X-API-Key": DASHBOARD_API_KEY},
                    timeout=5,
                )
                response.raise_for_status()
                return  # Success - exit
            except requests.exceptions.RequestException as e:
                if attempt < max_retries - 1:
                    # Exponential backoff: 1s, 2s, 4s
                    delay = 2 ** attempt
                    time.sleep(delay)
                else:
                    # Final attempt failed - log but don't fail
                    click.echo(f"[MetricsTracker] Warning: Failed to POST to dashboard after {max_retries} attempts: {e}", err=True)


# ==============================
# Composition (DI) Helpers
# ==============================
@dataclass
class ModeConfig:
    run_tests: bool
    run_coverage: bool


def resolve_mode(mode: str) -> ModeConfig:
    m = mode.lower()
    if m == "fast":
        return ModeConfig(run_tests=False, run_coverage=False)
    if m == "thorough":
        return ModeConfig(run_tests=True, run_coverage=False)
    if m == "full":
        return ModeConfig(run_tests=True, run_coverage=True)
    raise click.BadParameter("mode must be one of: fast, thorough, full")


def build_components(ssh_host: str, working_dir: str, model_name: str) -> Tuple[
    SingleWorkerPool, AnalyzeContextUseCase, GenerateNextTaskUseCase
]:
    worker_config = WorkerPoolConfig(
        pool_type="ssh",
        max_workers=1,
        ssh_host=ssh_host,
        working_dir=working_dir,
        model_name=model_name,
    )
    worker_pool = SingleWorkerPool(worker_config)
    analyze_context = AnalyzeContextUseCase(
        git_analyzer=GitContextAnalyzer(),
        test_analyzer=PytestAnalyzer(),
        coverage_analyzer=CoverageAnalyzer(),
        goal_parser=GoalParser(),
    )
    generate_task = GenerateNextTaskUseCase(
        task_generator=__import__(
            "src.claude_orchestrator.adapters.heuristic_task_generator",
            fromlist=["HeuristicTaskGenerator"],
        ).HeuristicTaskGenerator(),
        goal_parser=GoalParser(),
    )
    return worker_pool, analyze_context, generate_task


# ==============================
# Iteration Runner (Phase A/B)
# ==============================
class DevRunner:
    """Runs a single autonomous iteration with phase timing.

    This replicates the orchestrator's steps to collect per-phase durations and
    task metadata without modifying core code. Keeps responsibilities clear.
    """

    def __init__(
        self,
        worker_pool: SingleWorkerPool,
        analyze_context: AnalyzeContextUseCase,
        generate_task: GenerateNextTaskUseCase,
        project_path: str,
        priorities_file: str,
        target_goal_id: Optional[str] = None,
    ) -> None:
        self.pool = worker_pool
        self.analyze_context = analyze_context
        self.generate_task = generate_task
        self.project_path = project_path
        self.priorities_file = priorities_file
        self.target_goal_id = target_goal_id
        self.iteration_index = 0

    def run_once(self, mode_cfg: ModeConfig) -> Tuple[bool, Dict[str, Any], Dict[str, float]]:
        self.iteration_index += 1
        phase_durations: Dict[str, float] = {
            "context": 0.0,
            "generation": 0.0,
            "execution": 0.0,
        }
        meta: Dict[str, Any] = {
            "task_id": None,
            "task_goal": None,
            "task_priority": None,
        }

        total_start = time.time()

        # 1) Context
        t0 = time.time()
        context = self.analyze_context.execute(
            project_path=self.project_path,
            priorities_file=self.priorities_file,
            run_tests=mode_cfg.run_tests,
            run_coverage=mode_cfg.run_coverage,
            commit_limit=10,
        )
        phase_durations["context"] = time.time() - t0

        # 2) Generate
        t1 = time.time()
        task = self.generate_task.execute(
            context=context,
            priorities_file=self.priorities_file,
            target_goal_id=self.target_goal_id,
        )
        phase_durations["generation"] = time.time() - t1
        meta.update({
            "task_id": getattr(task, "id", None),
            "task_goal": getattr(task, "goal_id", None),
            "task_priority": getattr(task, "priority", None),
        })

        # 3) Execute
        t2 = time.time()
        worker = self.pool.assign_task(task)
        output = self.pool.wait_for_completion(
            worker.id,
            timeout_minutes=getattr(task, "estimated_minutes", 20) + 10,
            poll_interval_seconds=10,
        )
        phase_durations["execution"] = time.time() - t2

        total = time.time() - total_start
        success = int(getattr(output, "exit_code", 1)) == 0

        return success, meta, {
            "duration_total": total,
            "duration_context": phase_durations["context"],
            "duration_generation": phase_durations["generation"],
            "duration_execution": phase_durations["execution"],
        }


# ==============================
# CLI (Phase A)
# ==============================
DEFAULT_SSH_HOST = os.environ.get("AUTONOMOUS_SSH_HOST", "root@208.87.135.78")
DEFAULT_WORKING_DIR = os.environ.get("AUTONOMOUS_WORKING_DIR", "/root")
DEFAULT_MODEL = os.environ.get("AUTONOMOUS_MODEL", "sonnet4")
DEFAULT_PRIORITIES_FILE = os.environ.get("AUTONOMOUS_PRIORITIES", "priorities.yaml")


@click.group()
def cli() -> None:
    """Autonomous Development Companion CLI.

    Examples:
      python autonomous_dev_tool.py run --iterations 5 --mode fast
      python autonomous_dev_tool.py run --continuous --mode thorough
      python autonomous_dev_tool.py status
    """


@cli.command()
@click.option("--iterations", "iterations", type=int, default=1, help="Number of iterations to run")
@click.option(
    "--mode",
    type=click.Choice(["fast", "thorough", "full"], case_sensitive=False),
    default="fast",
    help="Execution mode",
)
@click.option("--continuous", is_flag=True, help="Run continuously until stopped")
@click.option("--target-goal", "target_goal", type=str, default=None, help="Explicit goal ID to target (overrides heuristics)")
@click.option("--ssh-host", default=DEFAULT_SSH_HOST, show_default=True)
@click.option("--working-dir", default=DEFAULT_WORKING_DIR, show_default=True)
@click.option("--model", default=DEFAULT_MODEL, show_default=True)
@click.option("--project-path", default=".", show_default=True)
@click.option("--priorities-file", default=DEFAULT_PRIORITIES_FILE, show_default=True)
def run(iterations: int, mode: str, continuous: bool, target_goal: str, ssh_host: str, working_dir: str, model: str,
        project_path: str, priorities_file: str) -> None:
    """Run autonomous iterations with metrics persistence."""
    mode_cfg = resolve_mode(mode)
    metrics = MetricsTracker()

    pool, analyze_context, generate_task = build_components(
        ssh_host=ssh_host, working_dir=working_dir, model_name=model
    )
    runner = DevRunner(
        worker_pool=pool,
        analyze_context=analyze_context,
        generate_task=generate_task,
        project_path=project_path,
        priorities_file=priorities_file,
        target_goal_id=target_goal,
    )

    click.echo(f"Starting autonomous run | mode={mode} | continuous={continuous} | iterations={iterations}")
    i = 0
    try:
        while True:
            i += 1
            ts = datetime.now().isoformat()
            click.echo("")
            click.echo("=" * 70)
            click.echo(f"Iteration {i} @ {ts}")
            click.echo("=" * 70)

            success, meta, durs = runner.run_once(mode_cfg)

            rec = IterationMetrics(
                timestamp=ts,
                iteration_number=i,
                mode=mode.lower(),
                duration_total=durs["duration_total"],
                duration_context=durs["duration_context"],
                duration_generation=durs["duration_generation"],
                duration_execution=durs["duration_execution"],
                success=bool(success),
                task_id=meta.get("task_id"),
                task_goal=meta.get("task_goal"),
                task_priority=meta.get("task_priority"),
            )
            metrics.record_iteration(rec)

            status = "SUCCESS" if success else "FAILURE"
            click.echo(f"Result: {status} | total={durs['duration_total']:.1f}s")

            if not continuous and i >= iterations:
                break

            # brief pause for readability if continuous
            if continuous:
                time.sleep(3)

    except KeyboardInterrupt:
        click.echo("\nInterrupted by user. Saving metrics and shutting down...")
    finally:
        click.echo("\nRun complete. Current summary:")
        _print_status(metrics.get_data())


@cli.command()
def status() -> None:
    """Show current metrics summary and recent iterations."""
    metrics = MetricsTracker()
    data = metrics.get_data()
    _print_status(data)


@cli.command()
def reset() -> None:
    """Clear metrics history (autonomous_metrics.json)."""
    metrics = MetricsTracker()
    metrics.reset()
    click.echo("Metrics have been reset.")


# ==============================
# Presentation Helpers
# ==============================

def _print_status(data: Dict[str, Any]) -> None:
    agg = data.get("aggregate", {})
    its = data.get("iterations", [])

    click.echo("=" * 70)
    click.echo("STATUS")
    click.echo("=" * 70)
    click.echo(f"Total iterations: {agg.get('total_iterations', 0)}")
    sr = agg.get("success_rate", 0.0)
    click.echo(f"Success rate: {sr*100:.1f}%")

    click.echo("\nAverage duration by mode (s):")
    for mode, val in (agg.get("avg_duration_by_mode", {}) or {}).items():
        click.echo(f"  - {mode}: {val:.1f}")

    click.echo("\nSuccess rate by mode:")
    for mode, val in (agg.get("success_rate_by_mode", {}) or {}).items():
        click.echo(f"  - {mode}: {val*100:.1f}%")

    # Recent iterations
    click.echo("\nRecent iterations:")
    for it in its[-5:]:
        flag = "✓" if it.get("success") else "✗"
        click.echo(
            f"  [{flag}] #{it.get('iteration_number')} {it.get('timestamp')} "
            f"mode={it.get('mode')} total={it.get('duration_total'):.1f}s "
            f"task={str(it.get('task_id'))[:8]} goal={it.get('task_goal')} prio={it.get('task_priority')}"
        )


if __name__ == "__main__":
    cli()

