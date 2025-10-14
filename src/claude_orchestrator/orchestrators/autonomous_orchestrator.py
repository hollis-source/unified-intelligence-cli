"""AutonomousOrchestrator - Fully autonomous task execution loop.

Main orchestrator that combines context analysis, task generation, and execution.
This is the complete Phase 7 implementation.

Clean Architecture: Orchestrator coordinates use cases and adapters
SOLID: DIP - Depends on abstractions (use cases, interfaces)
"""

from typing import Optional
import time

from src.claude_orchestrator.interfaces.worker_pool import IWorkerPool
from src.claude_orchestrator.use_cases.analyze_context_use_case import AnalyzeContextUseCase
from src.claude_orchestrator.use_cases.generate_next_task_use_case import GenerateNextTaskUseCase
from src.claude_orchestrator.entities.generated_task import GeneratedTask


class AutonomousOrchestrator:
    """
    Fully autonomous orchestrator with dynamic task generation.

    Loop:
    1. Analyze context (git, tests, coverage, goals)
    2. Generate next task based on context
    3. Execute task via worker pool
    4. Repeat

    Features:
    - Context-aware task generation
    - No static queue (tasks generated dynamically)
    - Adapts to codebase changes
    - Goal-driven priorities

    Usage:
        orchestrator = AutonomousOrchestrator(
            worker_pool=SingleWorkerPool(config),
            analyze_context=AnalyzeContextUseCase(...),
            generate_task=GenerateNextTaskUseCase(...),
            project_path=".",
            priorities_file="priorities.yaml",
        )

        # Run one iteration
        orchestrator.run_iteration()

        # Run N iterations
        orchestrator.run_iterations(count=5)

        # Run until stopped
        orchestrator.run_loop(max_iterations=100)
    """

    def __init__(
        self,
        worker_pool: IWorkerPool,
        analyze_context: AnalyzeContextUseCase,
        generate_task: GenerateNextTaskUseCase,
        project_path: str,
        priorities_file: str,
        target_goal_id: Optional[str] = None,
    ):
        """
        Initialize autonomous orchestrator.

        Args:
            worker_pool: Worker pool for task execution
            analyze_context: Context analysis use case
            generate_task: Task generation use case
            project_path: Path to project root
            priorities_file: Path to priorities.yaml
            target_goal_id: Optional explicit goal to target (overrides heuristics)
        """
        self.pool = worker_pool
        self.analyze_context = analyze_context
        self.generate_task = generate_task
        self.project_path = project_path
        self.priorities_file = priorities_file
        self.target_goal_id = target_goal_id

        self.iteration_count = 0
        self.successful_tasks = 0
        self.failed_tasks = 0
        self.recent_commit_hashes = []  # Track commits for stagnation detection

    def run_iteration(self, run_tests: bool = False, run_coverage: bool = False) -> bool:
        """
        Run one iteration of the autonomous loop.

        Steps:
        1. Analyze context
        2. Generate task
        3. Execute task
        4. Record results

        Args:
            run_tests: Whether to run tests during analysis (slow)
            run_coverage: Whether to analyze coverage (VERY slow, not recommended)

        Returns:
            True if successful, False if failed
        """
        self.iteration_count += 1

        print(f"\n{'='*70}")
        print(f"ITERATION {self.iteration_count}")
        print(f"{'='*70}\n")

        try:
            # 1. Analyze context
            print("[Autonomous] Step 1/3: Analyzing context...")
            context = self.analyze_context.execute(
                project_path=self.project_path,
                priorities_file=self.priorities_file,
                run_tests=run_tests,
                run_coverage=run_coverage,
                commit_limit=10,
            )

            print(f"[Autonomous] Context: {len(context.recent_commits)} commits, "
                  f"{context.coverage_percentage:.1f}% coverage, "
                  f"{len(context.active_goals)} active goals")

            # 2. Generate task
            print("\n[Autonomous] Step 2/3: Generating next task...")
            task = self.generate_task.execute(
                context=context,
                priorities_file=self.priorities_file,
                target_goal_id=self.target_goal_id,
            )

            print(f"[Autonomous] Task: {task.instruction[:100]}...")
            print(f"[Autonomous] Estimated: {task.estimated_minutes} minutes")

            # 3. Execute task
            print("\n[Autonomous] Step 3/3: Executing task...")
            worker = self.pool.assign_task(task)
            print(f"[Autonomous] Assigned to worker: {worker.id}")

            output = self.pool.wait_for_completion(
                worker.id,
                timeout_minutes=task.estimated_minutes + 10,  # Buffer
                poll_interval_seconds=10,
            )

            # 4. Record results
            print(f"\n[Autonomous] Task completed: {output.status}")
            print(f"[Autonomous] Exit code: {output.exit_code}")

            if output.exit_code == 0:
                self.successful_tasks += 1
                print("[Autonomous] ✅ Task SUCCEEDED")
            else:
                self.failed_tasks += 1
                print("[Autonomous] ❌ Task FAILED")

            if output.pr_url:
                print(f"[Autonomous] PR: {output.pr_url}")

            # Track commit for stagnation detection
            self._track_iteration_commit()

            return output.exit_code == 0

        except Exception as e:
            print(f"\n[Autonomous] ❌ Iteration FAILED: {e}")
            self.failed_tasks += 1
            return False

    def run_iterations(
        self,
        count: int,
        run_tests: bool = False,
        run_coverage: bool = False,
        delay_seconds: int = 5,
    ) -> dict:
        """
        Run N iterations of the autonomous loop.

        Args:
            count: Number of iterations to run
            run_tests: Whether to run tests during analysis
            run_coverage: Whether to analyze coverage (VERY slow)
            delay_seconds: Delay between iterations

        Returns:
            dict with execution statistics
        """
        print(f"\n[Autonomous] Starting {count} autonomous iterations...\n")

        for i in range(count):
            success = self.run_iteration(run_tests=run_tests, run_coverage=run_coverage)

            if i < count - 1:  # Don't delay after last iteration
                print(f"\n[Autonomous] Waiting {delay_seconds}s before next iteration...")
                time.sleep(delay_seconds)

        return self.get_statistics()

    def run_loop(
        self,
        max_iterations: Optional[int] = None,
        run_tests: bool = False,
        run_coverage: bool = False,
    ) -> dict:
        """
        Run autonomous loop until max_iterations or manual stop.

        Args:
            max_iterations: Maximum iterations (None = infinite)
            run_tests: Whether to run tests during analysis
            run_coverage: Whether to analyze coverage (VERY slow)

        Returns:
            dict with execution statistics
        """
        print(f"\n[Autonomous] Starting autonomous loop...")
        print(f"[Autonomous] Max iterations: {max_iterations or 'infinite'}")
        print(f"[Autonomous] Press Ctrl+C to stop\n")

        try:
            while True:
                if max_iterations and self.iteration_count >= max_iterations:
                    print(f"\n[Autonomous] Reached max iterations ({max_iterations})")
                    break

                self.run_iteration(run_tests=run_tests, run_coverage=run_coverage)

                # Check for stagnation (no new commits in last 3 iterations)
                if self._detect_stagnation(threshold=3):
                    print(f"\n[Autonomous] ⚠️  Stagnation detected: No new commits in last 3 iterations")
                    print(f"[Autonomous] Goal appears complete. Stopping autonomous loop.")
                    break

                # Brief pause between iterations
                time.sleep(5)

        except KeyboardInterrupt:
            print("\n\n[Autonomous] Stopped by user (Ctrl+C)")

        return self.get_statistics()

    def get_statistics(self) -> dict:
        """
        Get execution statistics.

        Returns:
            dict with stats
        """
        success_rate = (
            self.successful_tasks / self.iteration_count
            if self.iteration_count > 0
            else 0.0
        )

        stats = {
            "total_iterations": self.iteration_count,
            "successful_tasks": self.successful_tasks,
            "failed_tasks": self.failed_tasks,
            "success_rate": success_rate,
        }

        print(f"\n{'='*70}")
        print("STATISTICS")
        print(f"{'='*70}")
        print(f"Total iterations: {stats['total_iterations']}")
        print(f"Successful tasks: {stats['successful_tasks']}")
        print(f"Failed tasks: {stats['failed_tasks']}")
        print(f"Success rate: {stats['success_rate']*100:.1f}%")
        print(f"{'='*70}\n")

        return stats

    def _track_iteration_commit(self) -> None:
        """Track latest commit hash for stagnation detection."""
        try:
            import subprocess
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=self.project_path,
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                commit_hash = result.stdout.strip()
                self.recent_commit_hashes.append(commit_hash)
                # Keep only last 5 commits for stagnation detection
                if len(self.recent_commit_hashes) > 5:
                    self.recent_commit_hashes.pop(0)
        except Exception:
            # If git fails, just skip tracking
            pass

    def _detect_stagnation(self, threshold: int = 3) -> bool:
        """
        Detect if work has stagnated (no new commits in last N iterations).

        Args:
            threshold: Number of iterations with same commit to consider stagnation

        Returns:
            True if stagnated, False otherwise
        """
        if len(self.recent_commit_hashes) < threshold:
            return False

        # Check if last N commits are all the same
        last_n = self.recent_commit_hashes[-threshold:]
        return len(set(last_n)) == 1

    def shutdown(self) -> None:
        """Shutdown orchestrator and worker pool."""
        print("[Autonomous] Shutting down...")
        self.pool.shutdown()
        stats = self.get_statistics()
        print("[Autonomous] Shutdown complete")
