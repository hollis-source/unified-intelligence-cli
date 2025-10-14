"""ValidatePRUseCase - Validates Pull Requests before merge.

Orchestrates multiple validators to check PR quality.

Clean Architecture: Use Case layer (business logic)
SOLID: SRP - Single responsibility for PR validation orchestration
"""

from typing import List, Optional
from src.claude_orchestrator.interfaces.pr_validator import IPRValidator
from src.claude_orchestrator.entities.pull_request import PullRequest
from src.claude_orchestrator.entities.validation_result import (
    ValidationResult,
    ValidationStatus,
)


class ValidatePRUseCase:
    """
    Use case for validating Pull Requests.

    Runs multiple validators (tests, coverage, conflicts) and combines results.

    Usage:
        use_case = ValidatePRUseCase(
            validators=[
                TestPRValidator(),
                CoveragePRValidator(min_coverage_percentage=80.0),
                ConflictPRValidator(),
            ],
        )

        result = use_case.execute(
            pr=pull_request,
            project_path=".",
            fail_fast=True,
        )

        if result.is_valid():
            print("PR is ready to merge!")
        else:
            print(f"Validation failed: {result.get_failed_checks()}")
    """

    def __init__(
        self,
        validators: List[IPRValidator],
    ):
        """
        Initialize use case.

        Args:
            validators: List of validators to run
        """
        self.validators = validators

    def execute(
        self,
        pr: PullRequest,
        project_path: str,
        fail_fast: bool = True,
        skip_checks: Optional[List[str]] = None,
    ) -> ValidationResult:
        """
        Validate Pull Request.

        Args:
            pr: Pull Request to validate
            project_path: Path to project repository
            fail_fast: Stop on first failure (faster)
            skip_checks: List of check names to skip (optional)

        Returns:
            ValidationResult with all check results
        """
        print(f"[ValidatePR] Validating PR #{pr.number}: {pr.title}")
        print(f"[ValidatePR] Branch: {pr.branch} → {pr.base_branch}")
        print(f"[ValidatePR] Running {len(self.validators)} validators...")

        skip_checks = skip_checks or []
        check_results = []

        for i, validator in enumerate(self.validators, 1):
            check_name = validator.get_check_name()

            # Skip if requested
            if check_name in skip_checks:
                print(f"[ValidatePR] [{i}/{len(self.validators)}] Skipping {check_name}")
                continue

            # Run validator
            print(f"[ValidatePR] [{i}/{len(self.validators)}] Running {check_name}...")

            try:
                check_result = validator.validate(pr, project_path)
                check_results.append(check_result)

                # Log result
                status_icon = "✅" if check_result.passed() else "❌"
                print(
                    f"[ValidatePR] [{i}/{len(self.validators)}] {status_icon} {check_name}: "
                    f"{check_result.message}"
                )

                # Fail fast if enabled
                if fail_fast and not check_result.passed():
                    print(
                        f"[ValidatePR] Fail-fast enabled, stopping after first failure"
                    )
                    break

            except Exception as e:
                print(f"[ValidatePR] [{i}/{len(self.validators)}] ⚠️  {check_name} error: {e}")
                # Continue to next validator on error

        # Create validation result
        result = ValidationResult.create(
            pr_number=pr.number,
            checks=check_results,
        )

        # Log summary
        print(f"[ValidatePR] Validation complete!")
        print(f"[ValidatePR] Overall status: {result.overall_status.value}")
        print(
            f"[ValidatePR] Checks: {result.passed_checks}/{result.total_checks} passed"
        )
        print(f"[ValidatePR] Total time: {result.total_time_seconds:.1f}s")

        if result.is_valid():
            print(f"[ValidatePR] ✅ PR IS VALID - Ready to merge")
        else:
            failed_checks = result.get_failed_checks()
            print(f"[ValidatePR] ❌ PR HAS ISSUES - {len(failed_checks)} check(s) failed:")
            for check in failed_checks:
                print(f"[ValidatePR]    - {check.check_type.value}: {check.message}")

        return result
