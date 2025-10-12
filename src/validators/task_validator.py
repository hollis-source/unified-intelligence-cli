"""
Task validation - Catch errors early with helpful messages.

Discovered via user simulation: empty/invalid tasks show "Unknown error".
This module provides early validation with actionable feedback.

Clean Code: Fail fast with clear messages.
"""

from typing import Optional, Tuple
from src.entities import Task


class ValidationError(Exception):
    """Validation error with user-friendly message and suggestion."""

    def __init__(
        self,
        message: str,
        suggestion: Optional[str] = None,
        field: Optional[str] = None
    ):
        """
        Initialize validation error.

        Args:
            message: User-friendly error message
            suggestion: Actionable suggestion to fix the error
            field: Which field failed validation
        """
        super().__init__(message)
        self.message = message
        self.suggestion = suggestion
        self.field = field


class TaskValidator:
    """
    Validates tasks before execution.

    SRP: Single responsibility - input validation.
    Discovered need via user simulation testing.
    """

    MIN_DESCRIPTION_LENGTH = 3
    MAX_DESCRIPTION_LENGTH = 10000

    @classmethod
    def validate(cls, task: Task) -> Tuple[bool, Optional[ValidationError]]:
        """
        Validate task for execution.

        Args:
            task: Task to validate

        Returns:
            Tuple of (is_valid, error)
            - (True, None) if valid
            - (False, ValidationError) if invalid

        Example:
            >>> task = Task(description="", priority=1)
            >>> is_valid, error = TaskValidator.validate(task)
            >>> print(error.message)
            "Task description cannot be empty"
            >>> print(error.suggestion)
            "Provide a clear task description (e.g., 'Write a Python function to sort a list')"
        """
        # Validate description exists
        if not task.description:
            return False, ValidationError(
                message="Task description cannot be empty",
                suggestion="Provide a clear task description (e.g., 'Write a Python function to sort a list')",
                field="description"
            )

        # Validate description not just whitespace
        if not task.description.strip():
            return False, ValidationError(
                message="Task description cannot be only whitespace",
                suggestion="Provide a meaningful task description with actual content",
                field="description"
            )

        # Validate minimum length
        if len(task.description.strip()) < cls.MIN_DESCRIPTION_LENGTH:
            return False, ValidationError(
                message=f"Task description too short (minimum {cls.MIN_DESCRIPTION_LENGTH} characters)",
                suggestion=f"Provide more detail about what you want to accomplish (current: {len(task.description.strip())} chars)",
                field="description"
            )

        # Validate maximum length
        if len(task.description) > cls.MAX_DESCRIPTION_LENGTH:
            return False, ValidationError(
                message=f"Task description too long (maximum {cls.MAX_DESCRIPTION_LENGTH} characters)",
                suggestion="Break down your task into smaller, focused subtasks",
                field="description"
            )

        # Validate priority is reasonable
        if task.priority < 0:
            return False, ValidationError(
                message="Task priority cannot be negative",
                suggestion="Use priority values from 1 (highest) to 10 (lowest)",
                field="priority"
            )

        if task.priority > 100:
            return False, ValidationError(
                message="Task priority too high (maximum 100)",
                suggestion="Use priority values from 1 (highest) to 10 (lowest)",
                field="priority"
            )

        # All validations passed
        return True, None

    @classmethod
    def validate_or_raise(cls, task: Task) -> None:
        """
        Validate task and raise ValidationError if invalid.

        Convenience method for code that wants exceptions.

        Args:
            task: Task to validate

        Raises:
            ValidationError: If task is invalid

        Example:
            >>> task = Task(description="Write code", priority=1)
            >>> TaskValidator.validate_or_raise(task)  # No exception
            >>> bad_task = Task(description="", priority=1)
            >>> TaskValidator.validate_or_raise(bad_task)  # Raises ValidationError
        """
        is_valid, error = cls.validate(task)
        if not is_valid:
            raise error