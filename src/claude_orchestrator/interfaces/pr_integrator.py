"""PR Integrator Interface.

Abstract interface for PR integration (merging).

Clean Architecture: Interface/Port layer
SOLID: DIP - Depend on abstraction for integration
"""

from abc import ABC, abstractmethod
from src.claude_orchestrator.entities.pull_request import PullRequest
from src.claude_orchestrator.entities.integration_result import (
    IntegrationResult,
    MergeStrategy,
)


class IPRIntegrator(ABC):
    """
    Interface for PR integration (merging).

    Implementations can use:
    - GitHub CLI (gh)
    - GitHub API
    - GitLab API
    - Git commands

    Following DIP - depend on abstraction, not concrete implementation.
    """

    @abstractmethod
    def merge_pr(
        self,
        pr: PullRequest,
        merge_strategy: MergeStrategy = MergeStrategy.SQUASH,
        delete_branch: bool = True,
    ) -> IntegrationResult:
        """
        Merge Pull Request.

        Args:
            pr: Pull Request to merge
            merge_strategy: Strategy for merge (squash/merge/rebase)
            delete_branch: Delete PR branch after merge

        Returns:
            IntegrationResult with merge outcome

        Raises:
            PRIntegrationError: If merge fails
        """
        pass

    @abstractmethod
    def can_merge(self, pr: PullRequest) -> bool:
        """
        Check if PR can be merged (permissions, status).

        Args:
            pr: Pull Request

        Returns:
            True if PR can be merged, False otherwise
        """
        pass


class PRIntegrationError(Exception):
    """PR integration failed."""

    pass
