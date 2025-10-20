"""AnalyzeContextUseCase - Orchestrates context analysis.

Coordinates all context analyzers to build complete TaskContext.

Clean Architecture: Use Case layer (business logic)
SOLID: SRP - Single responsibility for context analysis orchestration
"""

from datetime import datetime
from typing import Optional

from src.claude_orchestrator.interfaces.context_analyzer import (
    IGitAnalyzer,
    ITestAnalyzer,
    ICoverageAnalyzer,
    IGoalParser,
)
from src.claude_orchestrator.entities.task_context import TaskContext


class AnalyzeContextUseCase:
    """
    Use case for analyzing codebase context.

    Orchestrates:
    - Git analysis (recent commits, modified files)
    - Test analysis (pass rate, failures)
    - Coverage analysis (coverage %, uncovered files)
    - Goal analysis (active goals, progress)

    Usage:
        use_case = AnalyzeContextUseCase(
            git_analyzer=GitContextAnalyzer(),
            test_analyzer=PytestAnalyzer(),
            coverage_analyzer=CoverageAnalyzer(),
            goal_parser=GoalParser(),
        )

        context = use_case.execute(
            project_path="/path/to/project",
            priorities_file="priorities.yaml"
        )

        print(f"Coverage: {context.coverage_percentage}%")
        print(f"Active goals: {len(context.active_goals)}")
    """

    def __init__(
        self,
        git_analyzer: IGitAnalyzer,
        test_analyzer: ITestAnalyzer,
        coverage_analyzer: ICoverageAnalyzer,
        goal_parser: IGoalParser,
    ):
        """
        Initialize use case with analyzers.

        Args:
            git_analyzer: Git repository analyzer
            test_analyzer: Test execution analyzer
            coverage_analyzer: Coverage analyzer
            goal_parser: Goal parser
        """
        self.git_analyzer = git_analyzer
        self.test_analyzer = test_analyzer
        self.coverage_analyzer = coverage_analyzer
        self.goal_parser = goal_parser

    def execute(
        self,
        project_path: str,
        priorities_file: str,
        run_tests: bool = False,
        run_coverage: bool = False,
        commit_limit: int = 10,
    ) -> TaskContext:
        """
        Analyze full codebase context.

        Args:
            project_path: Path to project root
            priorities_file: Path to priorities.yaml
            run_tests: Whether to run tests (slow, default False for speed)
            run_coverage: Whether to analyze coverage (VERY slow, default False)
            commit_limit: Number of recent commits to analyze

        Returns:
            TaskContext with complete analysis
        """
        print("[AnalyzeContext] Starting context analysis...")

        # 1. Analyze git
        print("[AnalyzeContext] Analyzing git...")
        git_info = self.git_analyzer.analyze(project_path, commit_limit=commit_limit)

        # 2. Run tests (optional, can be slow)
        test_pass_rate = 1.0
        test_failures = []
        if run_tests:
            print("[AnalyzeContext] Running tests...")
            try:
                test_results = self.test_analyzer.run_tests(project_path)
                test_pass_rate = test_results.pass_rate
                test_failures = test_results.failures
                print(
                    f"[AnalyzeContext] Tests: {test_results.passed}/{test_results.total_tests} passed"
                )
            except Exception as e:
                print(f"[AnalyzeContext] Test analysis failed: {e}")
                # Continue with defaults

        # 3. Analyze coverage (optional, VERY slow)
        coverage_percentage = 0.0
        if run_coverage:
            print("[AnalyzeContext] Analyzing coverage...")
            try:
                coverage_results = self.coverage_analyzer.analyze_coverage(project_path)
                coverage_percentage = coverage_results.overall_percentage
                print(f"[AnalyzeContext] Coverage: {coverage_percentage}%")
            except Exception as e:
                print(f"[AnalyzeContext] Coverage analysis failed: {e}")
                # Continue with default
        else:
            print("[AnalyzeContext] Skipping coverage analysis (disabled for speed)")

        # 4. Load goals
        print("[AnalyzeContext] Loading goals...")
        active_goals = []
        goal_progress = {}
        try:
            goals = self.goal_parser.get_active_goals(priorities_file)
            active_goals = [g.id for g in goals]
            goal_progress = {
                g.id: g.progress_percentage() or 0.0 for g in goals if g.progress_percentage() is not None
            }
            print(f"[AnalyzeContext] Found {len(active_goals)} active goals")
        except Exception as e:
            print(f"[AnalyzeContext] Goal parsing failed: {e}")
            # Continue with empty goals

        # 5. Build TaskContext
        context = TaskContext.create(
            snapshot_time=datetime.now(),
            recent_commits=[c["sha"] for c in git_info.recent_commits],
            modified_files=git_info.modified_files,
            current_branch=git_info.current_branch,
            test_pass_rate=test_pass_rate,
            test_failures=test_failures,
            coverage_percentage=coverage_percentage,
            active_goals=active_goals,
            goal_progress=goal_progress,
        )

        print("[AnalyzeContext] Context analysis complete")
        return context
