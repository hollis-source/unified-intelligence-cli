"""Context Analyzer Interfaces.

Abstract interfaces for analyzing codebase context (git, tests, coverage, goals).
Used by AnalyzeContextUseCase to gather information for task generation.

Clean Architecture: Interface/Port layer
SOLID: ISP - Focused interfaces, DIP - Depend on abstractions
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from datetime import datetime

from src.claude_orchestrator.entities.task_context import TaskContext
from src.claude_orchestrator.entities.goal import Goal


@dataclass
class GitInfo:
    """Information from git analysis."""
    recent_commits: List[Dict[str, str]]  # [{sha, author, message, date}]
    modified_files: List[str]
    current_branch: str
    uncommitted_changes: bool
    total_commits: int


@dataclass
class TestResults:
    """Results from test execution."""
    total_tests: int
    passed: int
    failed: int
    skipped: int
    pass_rate: float  # 0.0-1.0
    failures: List[Dict[str, str]]  # [{test_name, error_message}]
    execution_time_seconds: float


@dataclass
class CoverageResults:
    """Results from coverage analysis."""
    overall_percentage: float  # 0.0-100.0
    files_coverage: Dict[str, float]  # {file_path: coverage_percent}
    uncovered_lines: Dict[str, List[int]]  # {file_path: [line_numbers]}
    total_lines: int
    covered_lines: int


class IGitAnalyzer(ABC):
    """
    Interface for git repository analysis.

    Analyzes git history, current state, and provides context
    for task generation decisions.
    """

    @abstractmethod
    def analyze(self, repo_path: str, commit_limit: int = 10) -> GitInfo:
        """
        Analyze git repository.

        Args:
            repo_path: Path to git repository
            commit_limit: Number of recent commits to analyze

        Returns:
            GitInfo with repository state

        Raises:
            GitAnalysisError: If analysis fails
        """
        pass

    @abstractmethod
    def get_modified_files_since(self, repo_path: str, since: datetime) -> List[str]:
        """
        Get files modified since a specific time.

        Args:
            repo_path: Path to git repository
            since: DateTime to check from

        Returns:
            List of modified file paths
        """
        pass


class ITestAnalyzer(ABC):
    """
    Interface for test execution and analysis.

    Runs tests and captures results for task generation.
    """

    @abstractmethod
    def run_tests(self, project_path: str, test_path: Optional[str] = None) -> TestResults:
        """
        Run tests and capture results.

        Args:
            project_path: Path to project root
            test_path: Optional specific test path (file or directory)

        Returns:
            TestResults with execution summary

        Raises:
            TestAnalysisError: If test execution fails
        """
        pass

    @abstractmethod
    def get_failed_tests(self, project_path: str) -> List[Dict[str, str]]:
        """
        Get list of failed tests with details.

        Args:
            project_path: Path to project root

        Returns:
            List of failed test details
        """
        pass


class ICoverageAnalyzer(ABC):
    """
    Interface for code coverage analysis.

    Runs coverage tools and identifies gaps for task generation.
    """

    @abstractmethod
    def analyze_coverage(self, project_path: str, min_coverage: float = 80.0) -> CoverageResults:
        """
        Analyze code coverage.

        Args:
            project_path: Path to project root
            min_coverage: Minimum acceptable coverage percentage

        Returns:
            CoverageResults with coverage details

        Raises:
            CoverageAnalysisError: If coverage analysis fails
        """
        pass

    @abstractmethod
    def get_uncovered_files(self, project_path: str) -> List[str]:
        """
        Get list of files with low coverage.

        Args:
            project_path: Path to project root

        Returns:
            List of file paths with <80% coverage
        """
        pass


class IGoalParser(ABC):
    """
    Interface for parsing and managing goals.

    Reads priorities.yaml and provides goal information.
    """

    @abstractmethod
    def load_goals(self, priorities_file: str) -> List[Goal]:
        """
        Load goals from priorities.yaml.

        Args:
            priorities_file: Path to priorities.yaml

        Returns:
            List of Goal entities

        Raises:
            GoalParseError: If parsing fails
        """
        pass

    @abstractmethod
    def get_active_goals(self, priorities_file: str) -> List[Goal]:
        """
        Get only active goals (not completed/deprecated).

        Args:
            priorities_file: Path to priorities.yaml

        Returns:
            List of active Goal entities
        """
        pass

    @abstractmethod
    def update_goal_progress(
        self, priorities_file: str, goal_id: str, current_value: float
    ) -> None:
        """
        Update goal progress.

        Args:
            priorities_file: Path to priorities.yaml
            goal_id: Goal ID to update
            current_value: New current value

        Raises:
            GoalUpdateError: If update fails
        """
        pass


# Exceptions

class ContextAnalysisError(Exception):
    """Base exception for context analysis errors."""
    pass


class GitAnalysisError(ContextAnalysisError):
    """Git analysis failed."""
    pass


class TestAnalysisError(ContextAnalysisError):
    """Test analysis failed."""
    pass


class CoverageAnalysisError(ContextAnalysisError):
    """Coverage analysis failed."""
    pass


class GoalParseError(ContextAnalysisError):
    """Goal parsing failed."""
    pass


class GoalUpdateError(ContextAnalysisError):
    """Goal update failed."""
    pass
