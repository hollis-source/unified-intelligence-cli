"""Conflict PR Validator.

Validates that PR has no merge conflicts with base branch.

Clean Architecture: Adapter layer
SOLID: SRP - Single responsibility for conflict detection
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


class ConflictPRValidator(IPRValidator):
    """
    Validates that PR has no merge conflicts.

    Attempts a test merge with base branch and checks for conflicts.
    """

    def __init__(self, timeout_seconds: int = 60):
        """
        Initialize conflict validator.

        Args:
            timeout_seconds: Timeout for git operations
        """
        self.timeout_seconds = timeout_seconds

    def validate(self, pr: PullRequest, project_path: str) -> CheckResult:
        """
        Validate PR by checking for merge conflicts.

        Args:
            pr: Pull Request to validate
            project_path: Path to project

        Returns:
            CheckResult with conflict check results

        Raises:
            PRValidationError: If validation fails to execute
        """
        start_time = datetime.now()

        try:
            # Save current branch
            current_branch = self._get_current_branch(project_path)

            # Ensure we have latest base branch
            self._fetch_branch(project_path, pr.base_branch)

            # Checkout base branch
            self._checkout_branch(project_path, pr.base_branch)

            # Try to merge PR branch (dry run)
            conflicts = self._check_merge_conflicts(
                project_path, pr.branch, pr.base_branch
            )

            # Restore original branch
            self._checkout_branch(project_path, current_branch)

            # Determine status
            if not conflicts:
                status = ValidationStatus.PASSED
                message = f"No merge conflicts with {pr.base_branch}"
            else:
                status = ValidationStatus.FAILED
                message = (
                    f"Found {len(conflicts)} file(s) with merge conflicts: "
                    f"{', '.join(conflicts[:3])}"
                )
                if len(conflicts) > 3:
                    message += f" and {len(conflicts) - 3} more"

            # Build details
            details = {
                "base_branch": pr.base_branch,
                "pr_branch": pr.branch,
                "conflicts_found": len(conflicts),
                "conflicting_files": conflicts,
            }

            execution_time = (datetime.now() - start_time).total_seconds()

            return CheckResult.create(
                check_type=CheckType.CONFLICTS,
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

            raise PRValidationError(f"Conflict validation failed: {e}")

    def get_check_name(self) -> str:
        """Get check name."""
        return "Merge Conflicts"

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

    def _fetch_branch(self, project_path: str, branch: str) -> None:
        """Fetch latest branch from remote."""
        # Try to fetch (may fail if no remote, which is OK for local testing)
        subprocess.run(
            ["git", "-C", project_path, "fetch", "origin", branch],
            capture_output=True,
            text=True,
            timeout=30,
        )
        # Don't raise error if fetch fails - branch may be local only

    def _check_merge_conflicts(
        self, project_path: str, pr_branch: str, base_branch: str
    ) -> list:
        """
        Check for merge conflicts between branches.

        Args:
            project_path: Path to project
            pr_branch: PR branch
            base_branch: Base branch

        Returns:
            List of conflicting file paths (empty if no conflicts)
        """
        # Try merge with --no-commit and --no-ff (don't actually merge)
        result = subprocess.run(
            ["git", "-C", project_path, "merge", "--no-commit", "--no-ff", pr_branch],
            capture_output=True,
            text=True,
            timeout=self.timeout_seconds,
        )

        # Check for conflicts
        conflicts = []

        if result.returncode != 0:
            # Merge failed - check if due to conflicts
            if "CONFLICT" in result.stdout or "CONFLICT" in result.stderr:
                # Get conflicting files
                status_result = subprocess.run(
                    ["git", "-C", project_path, "diff", "--name-only", "--diff-filter=U"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                if status_result.returncode == 0:
                    conflicts = [
                        f for f in status_result.stdout.strip().split("\n") if f
                    ]

        # Abort merge (clean up)
        subprocess.run(
            ["git", "-C", project_path, "merge", "--abort"],
            capture_output=True,
            timeout=10,
        )

        return conflicts
