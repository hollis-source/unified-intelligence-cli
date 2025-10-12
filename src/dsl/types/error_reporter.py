"""Enhanced Error Reporting for DSL Type System

Provides rich, user-friendly error messages for type checking failures,
with contextual information and actionable hints for fixing issues.

Clean Code principles:
- Meaningful error messages that explain WHAT went wrong and HOW to fix it
- Single Responsibility: Only handles error formatting and reporting
- No business logic: Pure presentation layer for type errors

Story: Story 1, Phase 5 - Error Reporting & Integration
"""

from typing import Optional, List
from dataclasses import dataclass
from src.dsl.types.type_system import Type, TypeMismatchError


@dataclass
class ErrorHint:
    """
    Actionable hint for fixing a type error.

    Attributes:
        message: Description of how to fix the error
        example: Optional example code showing the fix
    """
    message: str
    example: Optional[str] = None


def format_type_error(
    error: TypeMismatchError,
    source_location: Optional[str] = None
) -> str:
    """
    Format a TypeMismatchError with rich context and hints.

    Transforms cryptic type errors into user-friendly messages with:
    - Clear explanation of what went wrong
    - Source location context
    - Actionable hints for fixing

    Args:
        error: The type mismatch error to format
        source_location: Optional source code location (e.g., "line 42")

    Returns:
        Formatted error message with context and hints

    Example:
        error = TypeMismatchError(
            expected=MonomorphicType("String"),
            got=MonomorphicType("Int"),
            context="composition g ∘ f"
        )
        formatted = format_type_error(error, "line 15")
        # Returns multi-line error with hints
    """
    lines = ["Type Error"]

    if source_location:
        lines.append(f"  at {source_location}")

    if error.context:
        lines.append(f"  in {error.context}")

    lines.append("")
    lines.append(f"  Expected: {error.expected}")
    lines.append(f"  Got:      {error.got}")
    lines.append("")

    # Add hints
    hints = generate_hints(error)
    if hints:
        lines.append("  Hints:")
        for hint in hints:
            lines.append(f"    • {hint.message}")
            if hint.example:
                lines.append(f"      Example: {hint.example}")

    return "\n".join(lines)


def generate_hints(error: TypeMismatchError) -> List[ErrorHint]:
    """
    Generate actionable hints for fixing a type error.

    Analyzes the type mismatch and provides context-specific suggestions
    for how to resolve it.

    Args:
        error: The type mismatch error

    Returns:
        List of hints for fixing the error
    """
    hints = []

    # Hint for composition type mismatches
    if "composition" in (error.context or "").lower():
        hints.append(ErrorHint(
            message="In composition g ∘ f, the output type of f must match the input type of g",
            example="If f: A → B and g: C → D, you need B = C"
        ))
        hints.append(ErrorHint(
            message="Check that you have the right order: g ∘ f means 'f then g'",
        ))

    # Hint for function application
    if "application" in (error.context or "").lower():
        hints.append(ErrorHint(
            message="Check that the argument type matches the function's input type",
        ))

    # Hint for product types
    if "product" in (error.context or "").lower():
        hints.append(ErrorHint(
            message="In parallel composition f × g, both functions execute concurrently on their respective inputs",
            example="If f: A → B and g: C → D, then f × g: (A × C) → (B × D)"
        ))

    # Generic hint for type variables
    expected_str = str(error.expected)
    got_str = str(error.got)

    if expected_str != got_str:
        hints.append(ErrorHint(
            message=f"Try converting {got_str} to {expected_str}, or update your type annotations",
        ))

    return hints


def format_composition_error(
    left_fn: str,
    right_fn: str,
    left_type: Type,
    right_type: Type,
    mismatch_point: str
) -> str:
    """
    Format a composition-specific error with visual diagram.

    Args:
        left_fn: Name of left function (g in g ∘ f)
        right_fn: Name of right function (f in g ∘ f)
        left_type: Type of left function
        right_type: Type of right function
        mismatch_point: Description of where types don't match

    Returns:
        Formatted error with ASCII art diagram

    Example:
        error = format_composition_error(
            "analyze", "fetch",
            FunctionType(String, Bool),
            FunctionType(Unit, Int),
            "output of fetch (Int) doesn't match input of analyze (String)"
        )
    """
    lines = [
        "Composition Type Error",
        "",
        f"  Cannot compose: {left_fn} ∘ {right_fn}",
        "",
        "  Type flow:",
        f"    {right_fn}: {right_type}",
        f"    {left_fn}:  {left_type}",
        "",
        f"  ✗ {mismatch_point}",
        "",
        "  Hints:",
        "    • In g ∘ f, output of f must match input of g",
        "    • Order matters: g ∘ f means 'execute f first, then g'",
    ]

    return "\n".join(lines)


def format_validation_summary(
    errors: List[str],
    warnings: List[str]
) -> str:
    """
    Format a summary of validation errors and warnings.

    Args:
        errors: List of error messages
        warnings: List of warning messages

    Returns:
        Formatted summary

    Example:
        summary = format_validation_summary(
            errors=["Type mismatch in composition"],
            warnings=["Unused variable 'x'"]
        )
    """
    lines = ["Validation Summary"]
    lines.append("")

    if errors:
        lines.append(f"  Errors ({len(errors)}):")
        for i, error in enumerate(errors, 1):
            lines.append(f"    {i}. {error}")
        lines.append("")

    if warnings:
        lines.append(f"  Warnings ({len(warnings)}):")
        for i, warning in enumerate(warnings, 1):
            lines.append(f"    {i}. {warning}")
        lines.append("")

    if not errors and not warnings:
        lines.append("  ✓ No errors or warnings")
    elif errors:
        lines.append(f"  ✗ Found {len(errors)} error(s)")
    else:
        lines.append(f"  ⚠ Found {len(warnings)} warning(s)")

    return "\n".join(lines)


class ErrorAccumulator:
    """
    Accumulates multiple errors and warnings during type checking.

    Allows collecting all type errors in a workflow before reporting,
    rather than failing on the first error.

    Clean Code: Single Responsibility - only accumulates errors
    """

    def __init__(self):
        """Initialize empty error accumulator."""
        self.errors: List[str] = []
        self.warnings: List[str] = []

    def add_error(self, message: str) -> None:
        """Add an error message."""
        self.errors.append(message)

    def add_warning(self, message: str) -> None:
        """Add a warning message."""
        self.warnings.append(message)

    def has_errors(self) -> bool:
        """Check if any errors were accumulated."""
        return len(self.errors) > 0

    def has_warnings(self) -> bool:
        """Check if any warnings were accumulated."""
        return len(self.warnings) > 0

    def get_summary(self) -> str:
        """Get formatted summary of all errors and warnings."""
        return format_validation_summary(self.errors, self.warnings)

    def clear(self) -> None:
        """Clear all accumulated errors and warnings."""
        self.errors.clear()
        self.warnings.clear()
