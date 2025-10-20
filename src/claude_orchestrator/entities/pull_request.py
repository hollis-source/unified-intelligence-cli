"""PullRequest Entity.

Represents a GitHub Pull Request for code review and integration.
Contains PR metadata, review status, and validation results.

Clean Architecture: Core entity (immutable, no dependencies)
SOLID: SRP - single responsibility for PR representation
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum


class PRStatus(Enum):
    """Pull Request status."""

    DRAFT = "draft"
    OPEN = "open"
    REVIEW_PENDING = "review_pending"
    REVIEW_APPROVED = "review_approved"
    REVIEW_REJECTED = "review_rejected"
    VALIDATION_PENDING = "validation_pending"
    VALIDATION_PASSED = "validation_passed"
    VALIDATION_FAILED = "validation_failed"
    READY_TO_MERGE = "ready_to_merge"
    MERGED = "merged"
    CLOSED = "closed"


class ReviewOutcome(Enum):
    """Review outcome from code reviewer."""

    APPROVED = "approved"
    REJECTED = "rejected"
    NEEDS_CHANGES = "needs_changes"
    UNCLEAR = "unclear"


@dataclass(frozen=True)
class PullRequest:
    """
    Pull Request entity for code review and integration.

    Represents a GitHub PR with full metadata and review status.

    Example:
        pr = PullRequest.create(
            number=123,
            title="Add unit tests for parser.py",
            branch="feature/parser-tests",
            base_branch="main",
            files_changed=["src/parser.py", "tests/test_parser.py"],
            task_id="task-abc123",
        )
    """

    # Identity
    number: int  # GitHub PR number
    created_at: datetime

    # PR metadata
    title: str
    description: str
    branch: str  # Source branch
    base_branch: str  # Target branch (usually main)
    author: str

    # Changes
    files_changed: List[str]
    additions: int  # Lines added
    deletions: int  # Lines deleted
    commits: int  # Number of commits

    # Status
    status: PRStatus
    url: str  # GitHub PR URL

    # Related task
    task_id: Optional[str]  # Task that created this PR
    goal_id: Optional[str]  # Goal this PR contributes to

    @staticmethod
    def create(
        number: int,
        title: str,
        branch: str,
        base_branch: str = "main",
        description: str = "",
        author: str = "claude-orchestrator",
        files_changed: Optional[List[str]] = None,
        additions: int = 0,
        deletions: int = 0,
        commits: int = 1,
        status: PRStatus = PRStatus.OPEN,
        url: str = "",
        task_id: Optional[str] = None,
        goal_id: Optional[str] = None,
    ) -> "PullRequest":
        """Factory method to create PullRequest."""
        return PullRequest(
            number=number,
            created_at=datetime.now(),
            title=title,
            description=description,
            branch=branch,
            base_branch=base_branch,
            author=author,
            files_changed=files_changed or [],
            additions=additions,
            deletions=deletions,
            commits=commits,
            status=status,
            url=url,
            task_id=task_id,
            goal_id=goal_id,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "number": self.number,
            "created_at": self.created_at.isoformat(),
            "title": self.title,
            "description": self.description,
            "branch": self.branch,
            "base_branch": self.base_branch,
            "author": self.author,
            "files_changed": self.files_changed,
            "additions": self.additions,
            "deletions": self.deletions,
            "commits": self.commits,
            "status": self.status.value,
            "url": self.url,
            "task_id": self.task_id,
            "goal_id": self.goal_id,
        }


@dataclass(frozen=True)
class ReviewResult:
    """
    Result of PR code review.

    Contains review outcome, issues found, suggestions, and reviewer metadata.

    Example:
        result = ReviewResult.create(
            pr_number=123,
            outcome=ReviewOutcome.NEEDS_CHANGES,
            summary="Good implementation, needs tests",
            issues=["Missing tests for error cases", "No docstrings"],
            suggestions=["Add unit tests", "Document public methods"],
            reviewer="auggie-gpt5",
        )
    """

    # Identity
    pr_number: int
    reviewed_at: datetime

    # Review outcome
    outcome: ReviewOutcome
    summary: str  # Brief summary of review

    # Findings
    issues: List[str]  # Problems found (blocking)
    suggestions: List[str]  # Improvements (non-blocking)
    security_concerns: List[str]  # Security issues (critical)

    # Quality scores (0-100)
    code_quality_score: int  # Overall code quality
    test_coverage_score: int  # Test quality
    documentation_score: int  # Documentation quality

    # Reviewer metadata
    reviewer: str  # Reviewer name/model
    confidence: float  # Reviewer confidence (0.0-1.0)
    review_time_seconds: int  # Time spent reviewing

    @staticmethod
    def create(
        pr_number: int,
        outcome: ReviewOutcome,
        summary: str,
        issues: Optional[List[str]] = None,
        suggestions: Optional[List[str]] = None,
        security_concerns: Optional[List[str]] = None,
        code_quality_score: int = 70,
        test_coverage_score: int = 70,
        documentation_score: int = 70,
        reviewer: str = "auggie",
        confidence: float = 0.8,
        review_time_seconds: int = 0,
    ) -> "ReviewResult":
        """Factory method to create ReviewResult."""
        return ReviewResult(
            pr_number=pr_number,
            reviewed_at=datetime.now(),
            outcome=outcome,
            summary=summary,
            issues=issues or [],
            suggestions=suggestions or [],
            security_concerns=security_concerns or [],
            code_quality_score=code_quality_score,
            test_coverage_score=test_coverage_score,
            documentation_score=documentation_score,
            reviewer=reviewer,
            confidence=confidence,
            review_time_seconds=review_time_seconds,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "pr_number": self.pr_number,
            "reviewed_at": self.reviewed_at.isoformat(),
            "outcome": self.outcome.value,
            "summary": self.summary,
            "issues": self.issues,
            "suggestions": self.suggestions,
            "security_concerns": self.security_concerns,
            "code_quality_score": self.code_quality_score,
            "test_coverage_score": self.test_coverage_score,
            "documentation_score": self.documentation_score,
            "reviewer": self.reviewer,
            "confidence": self.confidence,
            "review_time_seconds": self.review_time_seconds,
        }

    def is_approved(self) -> bool:
        """Check if review approves PR."""
        return self.outcome == ReviewOutcome.APPROVED

    def has_blocking_issues(self) -> bool:
        """Check if review has blocking issues."""
        return len(self.issues) > 0 or len(self.security_concerns) > 0
