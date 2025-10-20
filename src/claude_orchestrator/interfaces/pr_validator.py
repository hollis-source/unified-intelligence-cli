"""PR Validator Interface.

Abstract interface for PR validation checks.

Clean Architecture: Interface/Port layer
SOLID: DIP - Depend on abstraction for validation, ISP - Small focused interface
"""

from abc import ABC, abstractmethod
from src.claude_orchestrator.entities.pull_request import PullRequest
from src.claude_orchestrator.entities.validation_result import CheckResult


class IPRValidator(ABC):
    """
    Interface for PR validation checks.

    Each validator performs one specific check:
    - TestPRValidator: Runs tests
    - CoveragePRValidator: Checks coverage
    - ConflictPRValidator: Checks merge conflicts
    - BuildPRValidator: Runs build

    Following ISP (Interface Segregation Principle) - small, focused interface.
    """

    @abstractmethod
    def validate(self, pr: PullRequest, project_path: str) -> CheckResult:
        """
        Validate PR for specific check.

        Args:
            pr: Pull Request to validate
            project_path: Path to project repository

        Returns:
            CheckResult with status and details

        Raises:
            PRValidationError: If validation check fails to execute
        """
        pass

    @abstractmethod
    def get_check_name(self) -> str:
        """
        Get human-readable name of this check.

        Returns:
            Check name (e.g., "Test Suite", "Coverage Check")
        """
        pass


class PRValidationError(Exception):
    """PR validation check failed to execute."""

    pass
