"""Test PR Validator.

Validates that PR passes all tests.
Reuses PytestAnalyzer from Phase 7.

Clean Architecture: Adapter layer
SOLID: SRP - Single responsibility for test validation
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
from src.claude_orchestrator.adapters.pytest_analyzer import PytestAnalyzer


class TestPRValidator(IPRValidator):
    """
    Validates that PR passes all tests.

    Checks out PR branch, runs pytest, and reports results.
    """

    def __init__(self, timeout_seconds: int = 300, test_path: str = "tests/"):
        """
        Initialize test validator.

        Args:
            timeout_seconds: Timeout for test execution
            test_path: Path to tests directory
        """
        self.timeout_seconds = timeout_seconds
        self.test_path = test_path
        self.pytest_analyzer = PytestAnalyzer(timeout_seconds=timeout_seconds)

    def validate(self, pr: PullRequest, project_path: str) -> CheckResult:
        """
        Validate PR by running tests on PR branch.

        Args:
            pr: Pull Request to validate
            project_path: Path to project

        Returns:
            CheckResult with test results

        Raises:
            PRValidationError: If validation fails to execute
        """
        start_time = datetime.now()

        try:
            # Save current branch
            current_branch = self._get_current_branch(project_path)

            # Checkout PR branch
            self._checkout_branch(project_path, pr.branch)

            # Run tests
            test_results = self.pytest_analyzer.run_tests(
                project_path=project_path, test_path=self.test_path
            )

            # Restore original branch
            self._checkout_branch(project_path, current_branch)

            # Determine status
            if test_results.pass_rate == 1.0:
                status = ValidationStatus.PASSED
                message = f"All {test_results.passed} tests passed"
            else:
                status = ValidationStatus.FAILED
                message = (
                    f"{test_results.failed} of {test_results.total_tests} tests failed "
                    f"(pass rate: {test_results.pass_rate * 100:.1f}%)"
                )

            # Build details
            details = {
                "total_tests": test_results.total_tests,
                "passed": test_results.passed,
                "failed": test_results.failed,
                "pass_rate": test_results.pass_rate,
                "failures": test_results.failures[:5],  # First 5 failures
                "execution_time": test_results.execution_time_seconds,
            }

            execution_time = (datetime.now() - start_time).total_seconds()

            return CheckResult.create(
                check_type=CheckType.TESTS,
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

            raise PRValidationError(f"Test validation failed: {e}")

    def get_check_name(self) -> str:
        """Get check name."""
        return "Test Suite"

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
