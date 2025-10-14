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
from src.claude_orchestrator.adapters.local_worker_pool import LocalWorkerPool
from src.claude_orchestrator.interfaces.worker_pool import IWorkerPool
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
    """Metrics for a single autonomous iteration.

    Captures timing, success status, and task metadata for one iteration.
    Used for both local persistence and dashboard reporting.

    Attributes:
        timestamp: ISO format timestamp of iteration start
        iteration_number: Sequential iteration number
        mode: Execution mode (fast/thorough/full)
        duration_total: Total iteration duration in seconds
        duration_context: Context analysis phase duration
        duration_generation: Task generation phase duration
        duration_execution: Task execution phase duration
        success: Whether iteration completed successfully
        task_id: Generated task ID
        task_goal: Goal ID task contributes to
        task_priority: Task priority (P1/P2/P3/P4)
    """
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
        """Record a completed iteration with metrics.

        Appends metrics to history, recomputes aggregates, saves to disk,
        and posts to dashboard API.

        Args:
            metrics: Iteration metrics to record
        """
        payload = asdict(metrics)
        self._data.setdefault("iterations", []).append(payload)
        self._recompute_aggregates()
        self._save()
        self._post_to_dashboard(payload)

    def reset(self) -> None:
        """Reset all metrics to empty state.

        Clears iteration history and aggregate statistics.
        Saves empty state to disk.
        """
        self._data = {"iterations": [], "aggregate": {}}
        self._save()

    def get_data(self) -> Dict[str, Any]:
        """Get complete metrics data.

        Returns:
            Dictionary with 'iterations' and 'aggregate' keys
        """
        return self._data

    # Internal
    def _load(self) -> None:
        """Load metrics from disk.

        If file doesn't exist or is corrupt, initializes empty data.
        """
        if self.path.exists():
            try:
                self._data = json.loads(self.path.read_text())
            except (json.JSONDecodeError, OSError) as e:
                # Corrupt file → reset to empty
                click.echo(
                    f"[MetricsTracker] Warning: Failed to load metrics file: {e}. "
                    "Resetting to empty.",
                    err=True
                )
                self._data = {"iterations": [], "aggregate": {}}

    def _save(self) -> None:
        """Save metrics to disk.

        Raises:
            OSError: If file write fails
        """
        try:
            self.path.write_text(json.dumps(self._data, indent=2))
        except OSError as e:
            click.echo(
                f"[MetricsTracker] Error: Failed to save metrics: {e}",
                err=True
            )
            raise

    def _calculate_average(self, items: List[Dict[str, Any]], key: str) -> float:
        """Calculate average value for a key across items.

        Args:
            items: List of dictionaries containing metrics
            key: Key to average

        Returns:
            Average value, or 0.0 if items is empty
        """
        if not items:
            return 0.0
        values = [float(item.get(key, 0.0) or 0.0) for item in items]
        return sum(values) / len(values)

    def _group_by_mode(
        self, iterations: List[Dict[str, Any]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Group iterations by execution mode.

        Args:
            iterations: List of iteration metrics

        Returns:
            Dictionary mapping mode to list of iterations
        """
        grouped: Dict[str, List[Dict[str, Any]]] = {}
        for iteration in iterations:
            mode = iteration.get("mode", "unknown")
            grouped.setdefault(mode, []).append(iteration)
        return grouped

    def _count_by_attribute(
        self, iterations: List[Dict[str, Any]], attribute: str
    ) -> Dict[str, int]:
        """Count iterations by attribute value.

        Args:
            iterations: List of iteration metrics
            attribute: Attribute to count by

        Returns:
            Dictionary mapping attribute value to count
        """
        counts: Dict[str, int] = {}
        for iteration in iterations:
            value = iteration.get(attribute) or "unknown"
            counts[value] = counts.get(value, 0) + 1
        return counts

    def _recompute_aggregates(self) -> None:
        """Recompute aggregate statistics from all iterations.

        Calculates:
        - Total/successful/failed counts
        - Success rates overall and by mode
        - Average durations by mode
        - Task counts by goal and priority
        """
        iterations = self._data.get("iterations", [])
        total_count = len(iterations)
        successful_count = sum(1 for it in iterations if it.get("success"))

        # Group by mode for mode-specific metrics
        iterations_by_mode = self._group_by_mode(iterations)

        # Calculate averages and success rates by mode
        avg_duration_by_mode = {
            mode: self._calculate_average(mode_iterations, "duration_total")
            for mode, mode_iterations in iterations_by_mode.items()
        }

        success_rate_by_mode = {
            mode: (
                sum(1 for it in mode_iterations if it.get("success")) / len(mode_iterations)
                if mode_iterations else 0.0
            )
            for mode, mode_iterations in iterations_by_mode.items()
        }

        # Count tasks by goal and priority
        tasks_by_goal = self._count_by_attribute(iterations, "task_goal")
        tasks_by_priority = self._count_by_attribute(iterations, "task_priority")

        self._data["aggregate"] = {
            "total_iterations": total_count,
            "successful": successful_count,
            "failed": total_count - successful_count,
            "success_rate": (successful_count / total_count if total_count else 0.0),
            "avg_duration_by_mode": avg_duration_by_mode,
            "success_rate_by_mode": success_rate_by_mode,
            "tasks_by_goal": tasks_by_goal,
            "tasks_by_priority": tasks_by_priority,
        }

    def _map_mode_to_dashboard(self, mode: str) -> str:
        """Map internal mode to dashboard-expected mode.

        Args:
            mode: Internal mode string

        Returns:
            Dashboard-compatible mode string
        """
        mode_mapping = {
            "fast": "autonomous",
            "thorough": "execution",
            "full": "validation",
        }
        return mode_mapping.get(mode, "autonomous")

    def _map_priority_to_dashboard(self, priority: str) -> str:
        """Map internal priority to dashboard-expected priority.

        Args:
            priority: Internal priority string

        Returns:
            Dashboard-compatible priority string
        """
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
        return priority_mapping.get(priority, "medium")

    def _prepare_dashboard_payload(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare metrics payload for dashboard API.

        Args:
            metrics: Raw metrics dictionary

        Returns:
            Transformed payload for dashboard
        """
        payload = metrics.copy()
        payload["mode"] = self._map_mode_to_dashboard(payload.get("mode", ""))

        if "task_priority" in payload and payload["task_priority"]:
            payload["task_priority"] = self._map_priority_to_dashboard(
                payload["task_priority"]
            )

        return payload

    def _attempt_dashboard_post(self, payload: Dict[str, Any]) -> bool:
        """Attempt single POST to dashboard API.

        Args:
            payload: Metrics payload to send

        Returns:
            True if successful, False otherwise
        """
        try:
            response = requests.post(
                DASHBOARD_API_URL,
                json=payload,
                headers={"X-API-Key": DASHBOARD_API_KEY},
                timeout=5,
            )
            response.raise_for_status()
            return True
        except requests.exceptions.RequestException:
            return False

    def _post_to_dashboard(self, metrics: Dict[str, Any]) -> None:
        """POST metrics to unified dashboard API with retry logic.

        Fails silently if dashboard unavailable to not block local metrics.
        Implements exponential backoff: 3 attempts with 1s, 2s, 4s delays.
        Following Clean Architecture: external I/O isolated in adapter layer.

        Args:
            metrics: Metrics dictionary to send to dashboard
        """
        payload = self._prepare_dashboard_payload(metrics)

        # Retry logic with exponential backoff
        max_retries = 3
        for attempt in range(max_retries):
            if self._attempt_dashboard_post(payload):
                return  # Success

            if attempt < max_retries - 1:
                # Exponential backoff: 1s, 2s, 4s
                delay = 2 ** attempt
                time.sleep(delay)
            else:
                # Final attempt failed - log but don't fail
                click.echo(
                    f"[MetricsTracker] Warning: Failed to POST to dashboard "
                    f"after {max_retries} attempts",
                    err=True
                )


# ==============================
# Composition (DI) Helpers
# ==============================
@dataclass
class ModeConfig:
    """Configuration for execution mode.

    Determines which analysis steps to run during context analysis.

    Attributes:
        run_tests: Whether to run tests (slow)
        run_coverage: Whether to analyze coverage (very slow)
    """
    run_tests: bool
    run_coverage: bool


def resolve_mode(mode: str) -> ModeConfig:
    """Resolve execution mode string to configuration.

    Args:
        mode: Execution mode ("fast", "thorough", or "full")

    Returns:
        ModeConfig with appropriate test/coverage settings

    Raises:
        click.BadParameter: If mode is invalid
    """
    normalized_mode = mode.lower()
    if normalized_mode == "fast":
        return ModeConfig(run_tests=False, run_coverage=False)
    if normalized_mode == "thorough":
        return ModeConfig(run_tests=True, run_coverage=False)
    if normalized_mode == "full":
        return ModeConfig(run_tests=True, run_coverage=True)
    raise click.BadParameter("mode must be one of: fast, thorough, full")


def _create_worker_pool(
    ssh_host: str, working_dir: str, model_name: str, use_local: bool
) -> IWorkerPool:
    """Create worker pool based on execution mode.

    Args:
        ssh_host: SSH host for remote execution
        working_dir: Working directory path
        model_name: Model name to use
        use_local: True for local execution, False for SSH

    Returns:
        Configured worker pool instance
    """
    if use_local:
        config = WorkerPoolConfig(
            pool_type="local",
            max_workers=1,
            working_dir=working_dir,
            model_name=model_name,
        )
        return LocalWorkerPool(config)

    config = WorkerPoolConfig(
        pool_type="ssh",
        max_workers=1,
        ssh_host=ssh_host,
        working_dir=working_dir,
        model_name=model_name,
    )
    return SingleWorkerPool(config)


def _create_use_cases() -> Tuple[AnalyzeContextUseCase, GenerateNextTaskUseCase]:
    """Create use case instances with dependencies.

    Returns:
        Tuple of (analyze_context, generate_task) use cases
    """
    analyze_context = AnalyzeContextUseCase(
        git_analyzer=GitContextAnalyzer(),
        test_analyzer=PytestAnalyzer(),
        coverage_analyzer=CoverageAnalyzer(),
        goal_parser=GoalParser(),
    )

    # Import task generator dynamically to avoid circular imports
    heuristic_module = __import__(
        "src.claude_orchestrator.adapters.heuristic_task_generator",
        fromlist=["HeuristicTaskGenerator"],
    )

    generate_task = GenerateNextTaskUseCase(
        task_generator=heuristic_module.HeuristicTaskGenerator(),
        goal_parser=GoalParser(),
    )

    return analyze_context, generate_task


def build_components(
    ssh_host: str, working_dir: str, model_name: str, local: bool = False
) -> Tuple[IWorkerPool, AnalyzeContextUseCase, GenerateNextTaskUseCase]:
    """Build all components for autonomous execution.

    DIP: Dependency injection - creates and wires all dependencies.
    SRP: Delegates to specialized factory functions.

    Args:
        ssh_host: SSH host for remote execution
        working_dir: Working directory path
        model_name: Model name to use
        local: True for local execution, False for SSH

    Returns:
        Tuple of (worker_pool, analyze_context, generate_task)
    """
    worker_pool = _create_worker_pool(ssh_host, working_dir, model_name, local)
    analyze_context, generate_task = _create_use_cases()
    return worker_pool, analyze_context, generate_task


# ==============================
# Iteration Runner (Phase A/B)
# ==============================
class DevRunner:
    """Runs a single autonomous iteration with phase timing.

    This replicates the orchestrator's steps to collect per-phase durations and
    task metadata without modifying core code. Keeps responsibilities clear.

    SRP: Single responsibility for orchestrating iteration execution.
    DIP: Depends on abstractions (IWorkerPool, use cases).
    """

    def __init__(
        self,
        worker_pool: IWorkerPool,
        analyze_context: AnalyzeContextUseCase,
        generate_task: GenerateNextTaskUseCase,
        project_path: str,
        priorities_file: str,
        target_goal_id: Optional[str] = None,
    ) -> None:
        """Initialize DevRunner with dependencies.

        Args:
            worker_pool: Worker pool for task execution
            analyze_context: Use case for context analysis
            generate_task: Use case for task generation
            project_path: Path to project root
            priorities_file: Path to priorities.yaml
            target_goal_id: Optional specific goal to target
        """
        self.worker_pool = worker_pool
        self.analyze_context_use_case = analyze_context
        self.generate_task_use_case = generate_task
        self.project_path = project_path
        self.priorities_file = priorities_file
        self.target_goal_id = target_goal_id
        self.iteration_index = 0

    def _analyze_context_phase(self, mode_cfg: ModeConfig) -> Tuple[Any, float]:
        """Execute context analysis phase.

        Args:
            mode_cfg: Mode configuration for test/coverage settings

        Returns:
            Tuple of (context, duration_seconds)
        """
        start_time = time.time()
        context = self.analyze_context_use_case.execute(
            project_path=self.project_path,
            priorities_file=self.priorities_file,
            run_tests=mode_cfg.run_tests,
            run_coverage=mode_cfg.run_coverage,
            commit_limit=10,
        )
        duration = time.time() - start_time
        return context, duration

    def _generate_task_phase(self, context: Any) -> Tuple[Any, Dict[str, Any], float]:
        """Execute task generation phase.

        Args:
            context: Task context from analysis phase

        Returns:
            Tuple of (task, metadata, duration_seconds)
        """
        start_time = time.time()
        task = self.generate_task_use_case.execute(
            context=context,
            priorities_file=self.priorities_file,
            target_goal_id=self.target_goal_id,
        )
        duration = time.time() - start_time

        metadata = {
            "task_id": getattr(task, "id", None),
            "task_goal": getattr(task, "goal_id", None),
            "task_priority": getattr(task, "priority", None),
        }
        return task, metadata, duration

    def _execute_task_phase(self, task: Any) -> Tuple[bool, float]:
        """Execute task execution phase.

        Args:
            task: Generated task to execute

        Returns:
            Tuple of (success, duration_seconds)
        """
        start_time = time.time()
        worker = self.worker_pool.assign_task(task)

        timeout_minutes = getattr(task, "estimated_minutes", 20) + 10
        output = self.worker_pool.wait_for_completion(
            worker.id,
            timeout_minutes=timeout_minutes,
            poll_interval_seconds=10,
        )
        duration = time.time() - start_time

        success = int(getattr(output, "exit_code", 1)) == 0
        return success, duration

    def run_once(self, mode_cfg: ModeConfig) -> Tuple[bool, Dict[str, Any], Dict[str, float]]:
        """Run a single autonomous iteration.

        Executes three phases: context analysis, task generation, task execution.
        Times each phase separately for metrics.

        Args:
            mode_cfg: Mode configuration for test/coverage settings

        Returns:
            Tuple of (success, metadata, durations)
            - success: True if task completed successfully
            - metadata: Task metadata (id, goal, priority)
            - durations: Dict with total and per-phase durations
        """
        self.iteration_index += 1
        total_start = time.time()

        # Phase 1: Context Analysis
        context, context_duration = self._analyze_context_phase(mode_cfg)

        # Phase 2: Task Generation
        task, metadata, generation_duration = self._generate_task_phase(context)

        # Phase 3: Task Execution
        success, execution_duration = self._execute_task_phase(task)

        total_duration = time.time() - total_start

        durations = {
            "duration_total": total_duration,
            "duration_context": context_duration,
            "duration_generation": generation_duration,
            "duration_execution": execution_duration,
        }

        return success, metadata, durations


# ==============================
# CLI (Phase A)
# ==============================
DEFAULT_SSH_HOST = os.environ.get("AUTONOMOUS_SSH_HOST", "root@208.87.135.78")
DEFAULT_WORKING_DIR = os.environ.get("AUTONOMOUS_WORKING_DIR", "/root")
DEFAULT_MODEL = os.environ.get("AUTONOMOUS_MODEL", "sonnet4.5")
DEFAULT_PRIORITIES_FILE = os.environ.get("AUTONOMOUS_PRIORITIES", "priorities.yaml")


@click.group()
def cli() -> None:
    """Autonomous Development Companion CLI.

    Examples:
      python autonomous_dev_tool.py run --iterations 5 --mode fast
      python autonomous_dev_tool.py run --continuous --mode thorough
      python autonomous_dev_tool.py status
    """


def _print_iteration_header(iteration_number: int, timestamp: str) -> None:
    """Print iteration header banner.

    Args:
        iteration_number: Current iteration number
        timestamp: ISO format timestamp
    """
    click.echo("")
    click.echo("=" * 70)
    click.echo(f"Iteration {iteration_number} @ {timestamp}")
    click.echo("=" * 70)


def _create_iteration_metrics(
    iteration_number: int,
    timestamp: str,
    mode: str,
    success: bool,
    metadata: Dict[str, Any],
    durations: Dict[str, float],
) -> IterationMetrics:
    """Create IterationMetrics from run results.

    Args:
        iteration_number: Current iteration number
        timestamp: ISO format timestamp
        mode: Execution mode
        success: Whether iteration succeeded
        metadata: Task metadata
        durations: Phase durations

    Returns:
        IterationMetrics instance
    """
    return IterationMetrics(
        timestamp=timestamp,
        iteration_number=iteration_number,
        mode=mode.lower(),
        duration_total=durations["duration_total"],
        duration_context=durations["duration_context"],
        duration_generation=durations["duration_generation"],
        duration_execution=durations["duration_execution"],
        success=bool(success),
        task_id=metadata.get("task_id"),
        task_goal=metadata.get("task_goal"),
        task_priority=metadata.get("task_priority"),
    )


def _should_continue(continuous: bool, current_iteration: int, max_iterations: int) -> bool:
    """Determine if execution should continue.

    Args:
        continuous: Whether running in continuous mode
        current_iteration: Current iteration number
        max_iterations: Maximum iterations to run

    Returns:
        True if should continue, False otherwise
    """
    if continuous:
        return True
    return current_iteration < max_iterations


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
@click.option("--local", is_flag=True, default=True, help="Use local execution (default)")
@click.option("--ssh-host", default=DEFAULT_SSH_HOST, show_default=True, help="SSH host for remote execution")
@click.option("--working-dir", default=DEFAULT_WORKING_DIR, show_default=True)
@click.option("--model", default=DEFAULT_MODEL, show_default=True)
@click.option("--project-path", default=".", show_default=True)
@click.option("--priorities-file", default=DEFAULT_PRIORITIES_FILE, show_default=True)
def run(
    iterations: int,
    mode: str,
    continuous: bool,
    target_goal: Optional[str],
    local: bool,
    ssh_host: str,
    working_dir: str,
    model: str,
    project_path: str,
    priorities_file: str,
) -> None:
    """Run autonomous iterations with metrics persistence.

    Executes development iterations in a loop, collecting metrics for each.
    Supports local or SSH execution, with configurable test/coverage modes.

    Args:
        iterations: Number of iterations to run (ignored if continuous)
        mode: Execution mode (fast/thorough/full)
        continuous: Run continuously until interrupted
        target_goal: Specific goal ID to target
        local: Use local execution
        ssh_host: SSH host for remote execution
        working_dir: Working directory path
        model: Model name to use
        project_path: Project root path
        priorities_file: Path to priorities.yaml
    """
    mode_cfg = resolve_mode(mode)
    metrics = MetricsTracker()

    # Build components with dependency injection
    pool, analyze_context, generate_task = build_components(
        ssh_host=ssh_host, working_dir=working_dir, model_name=model, local=local
    )

    runner = DevRunner(
        worker_pool=pool,
        analyze_context=analyze_context,
        generate_task=generate_task,
        project_path=project_path,
        priorities_file=priorities_file,
        target_goal_id=target_goal,
    )

    # Print startup banner
    execution_type = "LOCAL" if local else f"SSH ({ssh_host})"
    click.echo(
        f"Starting autonomous run | execution={execution_type} | mode={mode} | "
        f"continuous={continuous} | iterations={iterations}"
    )

    iteration_count = 0
    try:
        while _should_continue(continuous, iteration_count, iterations):
            iteration_count += 1
            timestamp = datetime.now().isoformat()

            _print_iteration_header(iteration_count, timestamp)

            # Execute iteration
            success, metadata, durations = runner.run_once(mode_cfg)

            # Record metrics
            iteration_metrics = _create_iteration_metrics(
                iteration_count, timestamp, mode, success, metadata, durations
            )
            metrics.record_iteration(iteration_metrics)

            # Print result
            status = "SUCCESS" if success else "FAILURE"
            click.echo(f"Result: {status} | total={durations['duration_total']:.1f}s")

            # Brief pause for readability in continuous mode
            if continuous:
                time.sleep(3)

    except KeyboardInterrupt:
        click.echo("\nInterrupted by user. Saving metrics and shutting down...")
    finally:
        click.echo("\nRun complete. Current summary:")
        _print_status(metrics.get_data())


@cli.command()
def status() -> None:
    """Show current metrics summary and recent iterations.

    Displays:
    - Total iterations and success rate
    - Average duration by mode
    - Success rate by mode
    - Last 5 iterations with details

    Reads from ~/.ui-cli/autonomous_metrics.json
    """
    metrics = MetricsTracker()
    data = metrics.get_data()
    _print_status(data)


@cli.command()
def reset() -> None:
    """Clear metrics history (autonomous_metrics.json).

    Resets all iteration history and aggregate statistics.
    This action cannot be undone.
    """
    metrics = MetricsTracker()
    metrics.reset()
    click.echo("Metrics have been reset.")


# ==============================
# Presentation Helpers
# ==============================

def _print_aggregate_stats(aggregate: Dict[str, Any]) -> None:
    """Print aggregate statistics.

    Args:
        aggregate: Aggregate metrics dictionary
    """
    click.echo("=" * 70)
    click.echo("STATUS")
    click.echo("=" * 70)
    click.echo(f"Total iterations: {aggregate.get('total_iterations', 0)}")

    success_rate = aggregate.get("success_rate", 0.0)
    click.echo(f"Success rate: {success_rate * 100:.1f}%")


def _print_duration_by_mode(aggregate: Dict[str, Any]) -> None:
    """Print average duration statistics by mode.

    Args:
        aggregate: Aggregate metrics dictionary
    """
    click.echo("\nAverage duration by mode (s):")
    avg_durations = aggregate.get("avg_duration_by_mode", {}) or {}
    for mode, duration in avg_durations.items():
        click.echo(f"  - {mode}: {duration:.1f}")


def _print_success_rate_by_mode(aggregate: Dict[str, Any]) -> None:
    """Print success rate statistics by mode.

    Args:
        aggregate: Aggregate metrics dictionary
    """
    click.echo("\nSuccess rate by mode:")
    success_rates = aggregate.get("success_rate_by_mode", {}) or {}
    for mode, rate in success_rates.items():
        click.echo(f"  - {mode}: {rate * 100:.1f}%")


def _format_iteration_line(iteration: Dict[str, Any]) -> str:
    """Format single iteration for display.

    Args:
        iteration: Iteration metrics dictionary

    Returns:
        Formatted string for display
    """
    flag = "✓" if iteration.get("success") else "✗"
    iteration_num = iteration.get("iteration_number")
    timestamp = iteration.get("timestamp")
    mode = iteration.get("mode")
    duration = iteration.get("duration_total", 0.0)
    task_id = str(iteration.get("task_id", ""))[:8]
    goal = iteration.get("task_goal")
    priority = iteration.get("task_priority")

    return (
        f"  [{flag}] #{iteration_num} {timestamp} "
        f"mode={mode} total={duration:.1f}s "
        f"task={task_id} goal={goal} prio={priority}"
    )


def _print_recent_iterations(iterations: List[Dict[str, Any]], count: int = 5) -> None:
    """Print recent iterations.

    Args:
        iterations: List of all iterations
        count: Number of recent iterations to show
    """
    click.echo("\nRecent iterations:")
    recent = iterations[-count:] if len(iterations) > count else iterations

    for iteration in recent:
        click.echo(_format_iteration_line(iteration))


def _print_status(data: Dict[str, Any]) -> None:
    """Print comprehensive status summary.

    Displays aggregate statistics and recent iterations.
    SRP: Delegates to specialized print functions.

    Args:
        data: Complete metrics data dictionary
    """
    aggregate = data.get("aggregate", {})
    iterations = data.get("iterations", [])

    _print_aggregate_stats(aggregate)
    _print_duration_by_mode(aggregate)
    _print_success_rate_by_mode(aggregate)
    _print_recent_iterations(iterations)


if __name__ == "__main__":
    cli()

