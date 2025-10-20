"""IntegrationResult Entity.

Represents the result of PR integration (merge) operation.
Contains merge outcome, strategy used, and post-merge status.

Clean Architecture: Core entity (immutable, no dependencies)
SOLID: SRP - single responsibility for integration result representation
"""

from dataclasses import dataclass
from typing import Dict, Optional, Any
from datetime import datetime
from enum import Enum


class IntegrationStatus(Enum):
    """PR integration status."""

    SUCCESS = "success"  # Successfully merged
    FAILED = "failed"  # Merge failed
    SKIPPED = "skipped"  # Merge skipped (validation/review failed)
    BLOCKED = "blocked"  # Merge blocked (permissions, protection rules)


class MergeStrategy(Enum):
    """Git merge strategy."""

    MERGE = "merge"  # Standard merge (preserves all commits)
    SQUASH = "squash"  # Squash merge (single commit)
    REBASE = "rebase"  # Rebase merge (linear history)


@dataclass(frozen=True)
class IntegrationResult:
    """
    Result of PR integration (merge) operation.

    Contains merge outcome, commit information, and status.

    Example:
        result = IntegrationResult.create(
            pr_number=123,
            status=IntegrationStatus.SUCCESS,
            merge_strategy=MergeStrategy.SQUASH,
            merge_commit_sha="abc123",
            message="Merged PR #123: Add new feature",
        )

        if result.is_successful():
            print(f"PR merged! Commit: {result.merge_commit_sha}")
    """

    # Identity
    pr_number: int
    integrated_at: datetime

    # Status
    status: IntegrationStatus
    message: str  # Human-readable result message

    # Merge details
    merge_strategy: MergeStrategy
    merge_commit_sha: Optional[str]  # Commit SHA after merge (None if failed)
    base_branch: str
    pr_branch: str

    # Metadata
    integration_time_seconds: float
    merged_by: str  # Who/what performed the merge

    @staticmethod
    def create(
        pr_number: int,
        status: IntegrationStatus,
        merge_strategy: MergeStrategy,
        base_branch: str,
        pr_branch: str,
        message: str,
        merge_commit_sha: Optional[str] = None,
        integration_time_seconds: float = 0.0,
        merged_by: str = "claude-orchestrator",
    ) -> "IntegrationResult":
        """
        Factory method to create IntegrationResult.

        Args:
            pr_number: PR number
            status: Integration status
            merge_strategy: Strategy used for merge
            base_branch: Target branch
            pr_branch: Source branch
            message: Result message
            merge_commit_sha: Merge commit SHA (if successful)
            integration_time_seconds: Time taken to integrate
            merged_by: Who performed the merge

        Returns:
            IntegrationResult
        """
        return IntegrationResult(
            pr_number=pr_number,
            integrated_at=datetime.now(),
            status=status,
            message=message,
            merge_strategy=merge_strategy,
            merge_commit_sha=merge_commit_sha,
            base_branch=base_branch,
            pr_branch=pr_branch,
            integration_time_seconds=integration_time_seconds,
            merged_by=merged_by,
        )

    def is_successful(self) -> bool:
        """Check if integration was successful."""
        return self.status == IntegrationStatus.SUCCESS

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "pr_number": self.pr_number,
            "integrated_at": self.integrated_at.isoformat(),
            "status": self.status.value,
            "message": self.message,
            "merge_strategy": self.merge_strategy.value,
            "merge_commit_sha": self.merge_commit_sha,
            "base_branch": self.base_branch,
            "pr_branch": self.pr_branch,
            "integration_time_seconds": self.integration_time_seconds,
            "merged_by": self.merged_by,
        }
