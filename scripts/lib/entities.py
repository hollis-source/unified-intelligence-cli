"""
Core entities for release automation.

Following Clean Architecture: entities are at the center,
framework-independent business objects.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class CheckStatus(Enum):
    """Status of a pre-release check."""
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"


class ReleaseStage(Enum):
    """Stages of the release process."""
    PREFLIGHT = "preflight"
    TAGGING = "tagging"
    PUBLISHING = "publishing"
    VERIFICATION = "verification"
    COMPLETE = "complete"


@dataclass
class Check:
    """Represents a single pre-release check."""
    name: str
    description: str
    status: CheckStatus = CheckStatus.PENDING
    error_message: Optional[str] = None
    required: bool = True
    
    def mark_passed(self) -> None:
        """Mark check as passed."""
        self.status = CheckStatus.PASSED
        self.error_message = None
    
    def mark_failed(self, error: str) -> None:
        """Mark check as failed."""
        self.status = CheckStatus.FAILED
        self.error_message = error
    
    def mark_skipped(self, reason: str) -> None:
        """Mark check as skipped."""
        self.status = CheckStatus.SKIPPED
        self.error_message = f"Skipped: {reason}"
    
    @property
    def passed(self) -> bool:
        """Check if this check passed."""
        return self.status == CheckStatus.PASSED
    
    @property
    def failed(self) -> bool:
        """Check if this check failed."""
        return self.status == CheckStatus.FAILED


@dataclass
class Release:
    """Represents a software release."""
    version: str
    tag_name: str
    branch: str = "master"
    stage: ReleaseStage = ReleaseStage.PREFLIGHT
    checks: list[Check] = None
    
    def __post_init__(self):
        if self.checks is None:
            self.checks = []
    
    @property
    def all_checks_passed(self) -> bool:
        """Check if all required checks passed."""
        return all(
            check.passed or (not check.required)
            for check in self.checks
        )
    
    @property
    def failed_checks(self) -> list[Check]:
        """Get list of failed checks."""
        return [check for check in self.checks if check.failed and check.required]
    
    def advance_stage(self) -> None:
        """Move to next stage."""
        stages = list(ReleaseStage)
        current_idx = stages.index(self.stage)
        if current_idx < len(stages) - 1:
            self.stage = stages[current_idx + 1]


@dataclass
class Secret:
    """Represents a configuration secret."""
    name: str
    description: str
    required: bool = True
    value: Optional[str] = None
    is_set: bool = False
    
    @property
    def missing(self) -> bool:
        """Check if required secret is missing."""
        return self.required and not self.is_set
