"""GitHub PR Integrator Adapter.

Uses GitHub CLI (gh) for PR integration (merging).

Clean Architecture: Adapter layer
SOLID: DIP - Implements IPRIntegrator abstraction
"""

import subprocess
import re
from datetime import datetime
from typing import Optional

from src.claude_orchestrator.interfaces.pr_integrator import (
    IPRIntegrator,
    PRIntegrationError,
)
from src.claude_orchestrator.entities.pull_request import PullRequest
from src.claude_orchestrator.entities.integration_result import (
    IntegrationResult,
    IntegrationStatus,
    MergeStrategy,
)


class GitHubPRIntegrator(IPRIntegrator):
    """
    PR Integrator using GitHub CLI (gh).

    Merges PRs using gh pr merge command with configurable strategies.
    """

    def __init__(self, timeout_seconds: int = 60, working_dir: str = "."):
        """
        Initialize GitHub PR integrator.

        Args:
            timeout_seconds: Timeout for gh commands
            working_dir: Git repository working directory
        """
        self.timeout_seconds = timeout_seconds
        self.working_dir = working_dir

    def merge_pr(
        self,
        pr: PullRequest,
        merge_strategy: MergeStrategy = MergeStrategy.SQUASH,
        delete_branch: bool = True,
    ) -> IntegrationResult:
        """
        Merge PR using gh CLI.

        Args:
            pr: Pull Request to merge
            merge_strategy: Strategy for merge
            delete_branch: Delete PR branch after merge

        Returns:
            IntegrationResult with merge outcome

        Raises:
            PRIntegrationError: If merge fails
        """
        start_time = datetime.now()

        try:
            # Check if can merge
            if not self.can_merge(pr):
                return IntegrationResult.create(
                    pr_number=pr.number,
                    status=IntegrationStatus.BLOCKED,
                    merge_strategy=merge_strategy,
                    base_branch=pr.base_branch,
                    pr_branch=pr.branch,
                    message=f"PR #{pr.number} cannot be merged (blocked by checks or permissions)",
                    integration_time_seconds=0.0,
                )

            # Build gh command
            cmd = ["gh", "pr", "merge", str(pr.number)]

            # Add merge strategy
            if merge_strategy == MergeStrategy.SQUASH:
                cmd.append("--squash")
            elif merge_strategy == MergeStrategy.REBASE:
                cmd.append("--rebase")
            elif merge_strategy == MergeStrategy.MERGE:
                cmd.append("--merge")

            # Add delete branch flag
            if delete_branch:
                cmd.append("--delete-branch")

            # Add auto flag (don't prompt)
            cmd.append("--auto")

            # Execute merge
            result = subprocess.run(
                cmd,
                cwd=self.working_dir,
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
            )

            # Get execution time
            execution_time = (datetime.now() - start_time).total_seconds()

            # Check result
            if result.returncode == 0:
                # Extract merge commit SHA from output
                merge_commit = self._extract_merge_commit(result.stdout)

                return IntegrationResult.create(
                    pr_number=pr.number,
                    status=IntegrationStatus.SUCCESS,
                    merge_strategy=merge_strategy,
                    base_branch=pr.base_branch,
                    pr_branch=pr.branch,
                    message=f"Successfully merged PR #{pr.number} using {merge_strategy.value}",
                    merge_commit_sha=merge_commit,
                    integration_time_seconds=execution_time,
                )
            else:
                # Merge failed
                error_msg = result.stderr or result.stdout
                return IntegrationResult.create(
                    pr_number=pr.number,
                    status=IntegrationStatus.FAILED,
                    merge_strategy=merge_strategy,
                    base_branch=pr.base_branch,
                    pr_branch=pr.branch,
                    message=f"Failed to merge PR #{pr.number}: {error_msg[:200]}",
                    integration_time_seconds=execution_time,
                )

        except subprocess.TimeoutExpired:
            execution_time = (datetime.now() - start_time).total_seconds()
            return IntegrationResult.create(
                pr_number=pr.number,
                status=IntegrationStatus.FAILED,
                merge_strategy=merge_strategy,
                base_branch=pr.base_branch,
                pr_branch=pr.branch,
                message=f"Merge timeout after {self.timeout_seconds}s",
                integration_time_seconds=execution_time,
            )
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            return IntegrationResult.create(
                pr_number=pr.number,
                status=IntegrationStatus.FAILED,
                merge_strategy=merge_strategy,
                base_branch=pr.base_branch,
                pr_branch=pr.branch,
                message=f"Integration error: {str(e)[:200]}",
                integration_time_seconds=execution_time,
            )

    def can_merge(self, pr: PullRequest) -> bool:
        """
        Check if PR can be merged.

        Args:
            pr: Pull Request

        Returns:
            True if mergeable, False otherwise
        """
        try:
            # Check PR status using gh CLI
            cmd = ["gh", "pr", "view", str(pr.number), "--json", "mergeable,mergeStateStatus"]

            result = subprocess.run(
                cmd,
                cwd=self.working_dir,
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode != 0:
                return False

            # Parse JSON output
            import json

            data = json.loads(result.stdout)

            # Check if mergeable
            mergeable = data.get("mergeable", "UNKNOWN")
            merge_state = data.get("mergeStateStatus", "UNKNOWN")

            # PR is mergeable if:
            # 1. mergeable == "MERGEABLE"
            # 2. mergeStateStatus is not "BLOCKED"
            return mergeable == "MERGEABLE" and merge_state != "BLOCKED"

        except Exception as e:
            # If we can't check, assume not mergeable (safe default)
            return False

    def _extract_merge_commit(self, output: str) -> Optional[str]:
        """
        Extract merge commit SHA from gh output.

        Args:
            output: gh command output

        Returns:
            Merge commit SHA or None
        """
        # Try to find commit SHA in output
        # gh outputs: "✓ Merged pull request #123 (abc1234)"
        sha_pattern = r"[0-9a-f]{7,40}"
        match = re.search(sha_pattern, output)

        if match:
            return match.group(0)

        return None
