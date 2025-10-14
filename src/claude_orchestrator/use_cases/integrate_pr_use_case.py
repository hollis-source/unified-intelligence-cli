"""IntegratePRUseCase - Integrates (merges) Pull Requests.

Orchestrates validation, review, and merge for complete PR integration.

Clean Architecture: Use Case layer (business logic)
SOLID: SRP - Single responsibility for PR integration orchestration
"""

from typing import Optional
from src.claude_orchestrator.interfaces.pr_integrator import IPRIntegrator
from src.claude_orchestrator.entities.pull_request import PullRequest
from src.claude_orchestrator.entities.integration_result import (
    IntegrationResult,
    IntegrationStatus,
    MergeStrategy,
)
from src.claude_orchestrator.entities.validation_result import ValidationResult
from src.claude_orchestrator.entities.pull_request import ReviewResult


class IntegratePRUseCase:
    """
    Use case for integrating (merging) Pull Requests.

    Ensures PR passes all gates before merging:
    1. Validation (tests, coverage, conflicts)
    2. Review (code quality, security)
    3. Integration (merge)

    Usage:
        use_case = IntegratePRUseCase(
            pr_integrator=GitHubPRIntegrator(),
        )

        result = use_case.execute(
            pr=pull_request,
            validation_result=validation_result,
            review_result=review_result,
            merge_strategy=MergeStrategy.SQUASH,
            require_review_approval=True,
        )

        if result.is_successful():
            print(f"PR merged! Commit: {result.merge_commit_sha}")
    """

    def __init__(
        self,
        pr_integrator: IPRIntegrator,
    ):
        """
        Initialize use case.

        Args:
            pr_integrator: PR integrator (GitHub, GitLab, etc.)
        """
        self.pr_integrator = pr_integrator

    def execute(
        self,
        pr: PullRequest,
        validation_result: Optional[ValidationResult] = None,
        review_result: Optional[ReviewResult] = None,
        merge_strategy: MergeStrategy = MergeStrategy.SQUASH,
        require_validation: bool = True,
        require_review_approval: bool = False,
        delete_branch: bool = True,
    ) -> IntegrationResult:
        """
        Integrate Pull Request (validate → review → merge).

        Args:
            pr: Pull Request to integrate
            validation_result: Validation result (from Phase 8B)
            review_result: Review result (from Phase 8A)
            merge_strategy: Strategy for merge
            require_validation: Require validation to pass
            require_review_approval: Require review approval
            delete_branch: Delete PR branch after merge

        Returns:
            IntegrationResult with merge outcome
        """
        print(f"[IntegratePR] Integrating PR #{pr.number}: {pr.title}")
        print(f"[IntegratePR] Branch: {pr.branch} → {pr.base_branch}")
        print(f"[IntegratePR] Merge strategy: {merge_strategy.value}")

        # Gate 1: Validation check
        if require_validation:
            if validation_result is None:
                print(f"[IntegratePR] ❌ Validation required but not provided")
                return IntegrationResult.create(
                    pr_number=pr.number,
                    status=IntegrationStatus.SKIPPED,
                    merge_strategy=merge_strategy,
                    base_branch=pr.base_branch,
                    pr_branch=pr.branch,
                    message="Integration skipped: validation required but not provided",
                )

            if not validation_result.is_valid():
                failed_checks = validation_result.get_failed_checks()
                print(
                    f"[IntegratePR] ❌ Validation failed: {len(failed_checks)} check(s) failed"
                )
                for check in failed_checks:
                    print(f"[IntegratePR]    - {check.check_type.value}: {check.message}")

                return IntegrationResult.create(
                    pr_number=pr.number,
                    status=IntegrationStatus.SKIPPED,
                    merge_strategy=merge_strategy,
                    base_branch=pr.base_branch,
                    pr_branch=pr.branch,
                    message=f"Integration skipped: validation failed ({len(failed_checks)} checks)",
                )

            print(f"[IntegratePR] ✅ Validation passed ({validation_result.passed_checks} checks)")

        # Gate 2: Review approval check
        if require_review_approval:
            if review_result is None:
                print(f"[IntegratePR] ❌ Review approval required but not provided")
                return IntegrationResult.create(
                    pr_number=pr.number,
                    status=IntegrationStatus.SKIPPED,
                    merge_strategy=merge_strategy,
                    base_branch=pr.base_branch,
                    pr_branch=pr.branch,
                    message="Integration skipped: review approval required but not provided",
                )

            if not review_result.is_approved():
                print(f"[IntegratePR] ❌ Review not approved: {review_result.outcome.value}")
                print(f"[IntegratePR]    Issues: {len(review_result.issues)}")
                print(f"[IntegratePR]    Security concerns: {len(review_result.security_concerns)}")

                return IntegrationResult.create(
                    pr_number=pr.number,
                    status=IntegrationStatus.SKIPPED,
                    merge_strategy=merge_strategy,
                    base_branch=pr.base_branch,
                    pr_branch=pr.branch,
                    message=f"Integration skipped: review outcome = {review_result.outcome.value}",
                )

            print(f"[IntegratePR] ✅ Review approved by {review_result.reviewer}")

        # Gate 3: Check if can merge
        print(f"[IntegratePR] Checking if PR can be merged...")
        if not self.pr_integrator.can_merge(pr):
            print(f"[IntegratePR] ❌ PR cannot be merged (blocked by GitHub checks or permissions)")
            return IntegrationResult.create(
                pr_number=pr.number,
                status=IntegrationStatus.BLOCKED,
                merge_strategy=merge_strategy,
                base_branch=pr.base_branch,
                pr_branch=pr.branch,
                message="Integration blocked: PR cannot be merged (GitHub checks or permissions)",
            )

        print(f"[IntegratePR] ✅ PR can be merged")

        # All gates passed - proceed with merge
        print(f"[IntegratePR] All gates passed, merging PR...")
        result = self.pr_integrator.merge_pr(
            pr=pr,
            merge_strategy=merge_strategy,
            delete_branch=delete_branch,
        )

        # Log result
        if result.is_successful():
            print(f"[IntegratePR] ✅ PR MERGED SUCCESSFULLY")
            print(f"[IntegratePR]    Commit: {result.merge_commit_sha}")
            print(f"[IntegratePR]    Time: {result.integration_time_seconds:.1f}s")
        else:
            print(f"[IntegratePR] ❌ MERGE FAILED: {result.message}")

        return result
