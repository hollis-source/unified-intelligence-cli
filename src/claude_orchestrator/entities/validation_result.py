"""ValidationResult Entity.

Represents the result of PR validation checks.
Contains outcomes for tests, coverage, conflicts, and build.

Clean Architecture: Core entity (immutable, no dependencies)
SOLID: SRP - single responsibility for validation result representation
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum


class ValidationStatus(Enum):
    """Overall validation status."""

    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"


class CheckType(Enum):
    """Type of validation check."""

    TESTS = "tests"
    COVERAGE = "coverage"
    CONFLICTS = "conflicts"
    BUILD = "build"
    REVIEW = "review"  # From Phase 8A


@dataclass(frozen=True)
class CheckResult:
    """
    Result of a single validation check.

    Example:
        check = CheckResult.create(
            check_type=CheckType.TESTS,
            status=ValidationStatus.PASSED,
            message="All 42 tests passed",
            details={"passed": 42, "failed": 0},
        )
    """

    check_type: CheckType
    status: ValidationStatus
    message: str  # Human-readable result
    details: Dict[str, Any]  # Structured details
    execution_time_seconds: float

    @staticmethod
    def create(
        check_type: CheckType,
        status: ValidationStatus,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        execution_time_seconds: float = 0.0,
    ) -> "CheckResult":
        """Factory method to create CheckResult."""
        return CheckResult(
            check_type=check_type,
            status=status,
            message=message,
            details=details or {},
            execution_time_seconds=execution_time_seconds,
        )

    def passed(self) -> bool:
        """Check if this validation passed."""
        return self.status == ValidationStatus.PASSED


@dataclass(frozen=True)
class ValidationResult:
    """
    Result of complete PR validation.

    Contains results from all validation checks (tests, coverage, conflicts, etc.).

    Example:
        result = ValidationResult.create(
            pr_number=123,
            checks=[test_check, coverage_check, conflict_check],
            overall_status=ValidationStatus.PASSED,
        )

        if result.is_valid():
            print("PR is ready to merge!")
    """

    # Identity
    pr_number: int
    validated_at: datetime

    # Results
    checks: List[CheckResult]  # Individual check results
    overall_status: ValidationStatus  # Combined status

    # Summary
    total_checks: int
    passed_checks: int
    failed_checks: int
    skipped_checks: int

    # Metadata
    total_time_seconds: float
    validator_version: str = "1.0"

    @staticmethod
    def create(
        pr_number: int,
        checks: List[CheckResult],
        overall_status: Optional[ValidationStatus] = None,
    ) -> "ValidationResult":
        """
        Factory method to create ValidationResult.

        Args:
            pr_number: PR number
            checks: List of CheckResult from validators
            overall_status: Override overall status (auto-computed if None)

        Returns:
            ValidationResult
        """
        # Count check statuses
        passed = sum(1 for c in checks if c.status == ValidationStatus.PASSED)
        failed = sum(1 for c in checks if c.status == ValidationStatus.FAILED)
        skipped = sum(1 for c in checks if c.status == ValidationStatus.SKIPPED)

        # Compute overall status if not provided
        if overall_status is None:
            if failed > 0:
                overall_status = ValidationStatus.FAILED
            elif passed == len(checks):
                overall_status = ValidationStatus.PASSED
            else:
                overall_status = ValidationStatus.SKIPPED

        # Total time
        total_time = sum(c.execution_time_seconds for c in checks)

        return ValidationResult(
            pr_number=pr_number,
            validated_at=datetime.now(),
            checks=checks,
            overall_status=overall_status,
            total_checks=len(checks),
            passed_checks=passed,
            failed_checks=failed,
            skipped_checks=skipped,
            total_time_seconds=total_time,
        )

    def is_valid(self) -> bool:
        """Check if PR passed all validation checks."""
        return self.overall_status == ValidationStatus.PASSED

    def get_failed_checks(self) -> List[CheckResult]:
        """Get list of failed checks."""
        return [c for c in self.checks if c.status == ValidationStatus.FAILED]

    def get_check_result(self, check_type: CheckType) -> Optional[CheckResult]:
        """Get result for specific check type."""
        for check in self.checks:
            if check.check_type == check_type:
                return check
        return None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "pr_number": self.pr_number,
            "validated_at": self.validated_at.isoformat(),
            "checks": [
                {
                    "check_type": c.check_type.value,
                    "status": c.status.value,
                    "message": c.message,
                    "details": c.details,
                    "execution_time_seconds": c.execution_time_seconds,
                }
                for c in self.checks
            ],
            "overall_status": self.overall_status.value,
            "total_checks": self.total_checks,
            "passed_checks": self.passed_checks,
            "failed_checks": self.failed_checks,
            "skipped_checks": self.skipped_checks,
            "total_time_seconds": self.total_time_seconds,
            "validator_version": self.validator_version,
        }
