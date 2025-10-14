"""PR Reviewer Interface.

Abstract interface for code review of Pull Requests.

Clean Architecture: Interface/Port layer
SOLID: DIP - Depend on abstraction for code review
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional

from src.claude_orchestrator.entities.pull_request import PullRequest, ReviewResult


@dataclass
class ReviewCriteria:
    """
    Criteria for PR code review.

    Defines what aspects to check during review.
    """

    check_code_quality: bool = True  # SOLID, Clean Code principles
    check_tests: bool = True  # Test coverage and quality
    check_security: bool = True  # Security vulnerabilities
    check_documentation: bool = True  # Docstrings, comments
    check_conventions: bool = True  # Project coding conventions
    check_performance: bool = False  # Performance issues (optional)

    # Scoring thresholds (0-100)
    min_code_quality_score: int = 70
    min_test_coverage_score: int = 70
    min_documentation_score: int = 60


class IPRReviewer(ABC):
    """
    Interface for AI-powered Pull Request review.

    Implementations can use:
    - LLM models (GPT, Claude, etc.)
    - Multi-model consensus
    - Static analysis tools
    - Hybrid approaches
    """

    @abstractmethod
    def review_pr(
        self,
        pr: PullRequest,
        criteria: Optional[ReviewCriteria] = None,
        include_suggestions: bool = True,
    ) -> ReviewResult:
        """
        Review a Pull Request and provide feedback.

        Args:
            pr: Pull Request to review
            criteria: Review criteria (uses defaults if None)
            include_suggestions: Include improvement suggestions (not blocking)

        Returns:
            ReviewResult with outcome, issues, suggestions, and scores

        Raises:
            PRReviewError: If review fails
        """
        pass

    @abstractmethod
    def get_diff(self, pr: PullRequest) -> str:
        """
        Get diff for PR (to feed to reviewer).

        Args:
            pr: Pull Request

        Returns:
            Git diff as string

        Raises:
            PRReviewError: If fetching diff fails
        """
        pass


class PRReviewError(Exception):
    """PR review failed."""

    pass
