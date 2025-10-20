"""Coverage PR Validator.

Validates that PR maintains coverage threshold.
Reuses CoverageAnalyzer from Phase 7.

Clean Architecture: Adapter layer
SOLID: SRP - Single responsibility for coverage validation
"""

import subprocess
from datetime import datetime
from src.claude_orchestrator.interfaces.pr_validator import IPRValidator, PRValidationError
from src.claude_orchestrator.entities.pull_request import PullRequest
from src.claude_orchestrator.entities.validation_result import (
    CheckResult,
    CheckType,
    ValidationStatus,
)
from src.claude_orchestrator.adapters.coverage_analyzer import CoverageAnalyzer


class CoveragePRValidator(IPRValidator):
    """
    Validates that PR maintains coverage threshold.

    Checks out PR branch, runs coverage analysis, and compares to threshold.
    """

    def __init__(
        self, min_coverage_percentage: float = 80.0, timeout_seconds: int = 300
    ):
        """
        Initialize coverage validator.

        Args:
            min_coverage_percentage: Minimum required coverage (0-100)
            timeout_seconds: Timeout for coverage analysis
        """
        self.min_coverage_percentage = min_coverage_percentage
        self.timeout_seconds = timeout_seconds
        self.coverage_analyzer = CoverageAnalyzer(timeout_seconds=timeout_seconds)

    def validate(self, pr: PullRequest, project_path: str) -> CheckResult:
        """
        Validate PR by checking coverage on PR branch.

        Args:
            pr: Pull Request to validate
            project_path: Path to project

        Returns:
            CheckResult with coverage results

        Raises:
            PRValidationError: If validation fails to execute
        """
        start_time = datetime.now()

        try:
            # Save current branch
            current_branch = self._get_current_branch(project_path)

            # Checkout PR branch
            self._checkout_branch(project_path, pr.branch)

            # Run coverage analysis
            coverage_results = self.coverage_analyzer.analyze_coverage(
                project_path=project_path, min_coverage=self.min_coverage_percentage
            )

            # Restore original branch
            self._checkout_branch(project_path, current_branch)

            # Determine status
            if coverage_results.overall_percentage >= self.min_coverage_percentage:
                status = ValidationStatus.PASSED
                message = (
                    f"Coverage {coverage_results.overall_percentage:.1f}% "
                    f"meets threshold {self.min_coverage_percentage:.1f}%"
                )
            else:
                status = ValidationStatus.FAILED
                message = (
                    f"Coverage {coverage_results.overall_percentage:.1f}% "
                    f"below threshold {self.min_coverage_percentage:.1f}%"
                )

            # Build details
            low_coverage_files = {
                file: pct
                for file, pct in coverage_results.files_coverage.items()
                if pct < self.min_coverage_percentage
            }

            details = {
                "overall_percentage": coverage_results.overall_percentage,
                "threshold": self.min_coverage_percentage,
                "files_checked": len(coverage_results.files_coverage),
                "low_coverage_files": low_coverage_files,
                "files_with_uncovered_lines": len(coverage_results.uncovered_lines),
            }

            execution_time = (datetime.now() - start_time).total_seconds()

            return CheckResult.create(
                check_type=CheckType.COVERAGE,
                status=status,
                message=message,
                details=details,
                execution_time_seconds=execution_time,
            )

        except Exception as e:
            # Restore branch on error
            try:
                self._checkout_branch(project_path, current_branch)
            except:
                pass

            raise PRValidationError(f"Coverage validation failed: {e}")

    def get_check_name(self) -> str:
        """Get check name."""
        return "Coverage Check"

    def _get_current_branch(self, project_path: str) -> str:
        """Get current git branch."""
        result = subprocess.run(
            ["git", "-C", project_path, "branch", "--show-current"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            raise PRValidationError(f"Failed to get current branch: {result.stderr}")
        return result.stdout.strip()

    def _checkout_branch(self, project_path: str, branch: str) -> None:
        """Checkout git branch."""
        result = subprocess.run(
            ["git", "-C", project_path, "checkout", branch],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            raise PRValidationError(f"Failed to checkout branch {branch}: {result.stderr}")
