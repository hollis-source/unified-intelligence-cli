"""ReviewPRUseCase - Reviews Pull Request using AI.

Uses IPRReviewer to perform automated code review.

Clean Architecture: Use Case layer (business logic)
SOLID: SRP - Single responsibility for PR review orchestration
"""

from typing import Optional

from src.claude_orchestrator.interfaces.pr_reviewer import (
    IPRReviewer,
    ReviewCriteria,
)
from src.claude_orchestrator.entities.pull_request import (
    PullRequest,
    ReviewResult,
    ReviewOutcome,
)


class ReviewPRUseCase:
    """
    Use case for reviewing Pull Requests.

    Orchestrates AI-powered code review using configured reviewer.

    Usage:
        use_case = ReviewPRUseCase(
            pr_reviewer=AuggiePRReviewer(use_multi_model=True),
        )

        result = use_case.execute(
            pr=pull_request,
            strict=True,
        )

        if result.is_approved():
            print("PR approved!")
        else:
            print(f"Issues: {result.issues}")
    """

    def __init__(
        self,
        pr_reviewer: IPRReviewer,
    ):
        """
        Initialize use case.

        Args:
            pr_reviewer: PR reviewer (auggie or other)
        """
        self.pr_reviewer = pr_reviewer

    def execute(
        self,
        pr: PullRequest,
        strict: bool = True,
        include_suggestions: bool = True,
    ) -> ReviewResult:
        """
        Review Pull Request.

        Args:
            pr: Pull Request to review
            strict: Use strict review criteria
            include_suggestions: Include improvement suggestions

        Returns:
            ReviewResult with outcome and feedback
        """
        print(f"[ReviewPR] Reviewing PR #{pr.number}: {pr.title}")
        print(f"[ReviewPR] Branch: {pr.branch} → {pr.base_branch}")
        print(f"[ReviewPR] Files changed: {len(pr.files_changed)}")

        # Configure review criteria
        if strict:
            criteria = ReviewCriteria(
                check_code_quality=True,
                check_tests=True,
                check_security=True,
                check_documentation=True,
                check_conventions=True,
                check_performance=False,
                min_code_quality_score=80,  # Strict
                min_test_coverage_score=80,
                min_documentation_score=70,
            )
        else:
            criteria = ReviewCriteria(
                min_code_quality_score=60,  # Lenient
                min_test_coverage_score=60,
                min_documentation_score=50,
            )

        # Perform review
        print(f"[ReviewPR] Performing code review...")
        result = self.pr_reviewer.review_pr(
            pr=pr,
            criteria=criteria,
            include_suggestions=include_suggestions,
        )

        # Log results
        print(f"[ReviewPR] Review complete!")
        print(f"[ReviewPR] Outcome: {result.outcome.value}")
        print(f"[ReviewPR] Reviewer: {result.reviewer}")
        print(f"[ReviewPR] Scores: Quality={result.code_quality_score}, " f"Tests={result.test_coverage_score}, Docs={result.documentation_score}")
        print(f"[ReviewPR] Issues found: {len(result.issues)}")
        print(f"[ReviewPR] Suggestions: {len(result.suggestions)}")
        print(f"[ReviewPR] Security concerns: {len(result.security_concerns)}")

        if result.is_approved():
            print(f"[ReviewPR] ✅ PR APPROVED")
        elif result.has_blocking_issues():
            print(f"[ReviewPR] ❌ PR HAS BLOCKING ISSUES")
        else:
            print(f"[ReviewPR] ⚠️  PR NEEDS CHANGES")

        return result
