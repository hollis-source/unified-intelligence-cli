"""Typed Data Wrapper for Runtime Type Validation.

Wraps runtime data with type information for validation at composition boundaries.
Enables runtime type checking to complement static type inference.

Clean Architecture: Entity layer (domain model)
SOLID: SRP - only wraps data with type information

Story: Sprint 2, Phase 3 - Runtime Integration
"""

from dataclasses import dataclass
from typing import Any, Optional
from src.dsl.types.type_system import Type


@dataclass
class TypedData:
    """
    Wraps runtime data with type information.

    Used during workflow execution to carry both the data and its type,
    enabling runtime validation at composition boundaries.

    Attributes:
        value: The actual runtime data
        type_info: Type signature of the data
        source: Optional source task/function name for debugging

    Example:
        data = TypedData(
            value={"commits": [...]},
            type_info=MonomorphicType("CommitData"),
            source="get_recent_commits"
        )
    """
    value: Any
    type_info: Type
    source: Optional[str] = None

    def __repr__(self) -> str:
        """Get string representation."""
        if self.source:
            return f"TypedData(value={self.value!r}, type={self.type_info}, source={self.source})"
        return f"TypedData(value={self.value!r}, type={self.type_info})"

    def __str__(self) -> str:
        """Get readable string representation."""
        return f"{self.value} :: {self.type_info}"


def wrap_if_needed(value: Any, type_info: Optional[Type] = None, source: Optional[str] = None) -> Any:
    """
    Wrap value in TypedData if not already wrapped.

    Args:
        value: Value to wrap
        type_info: Type signature (if None, returns unwrapped value)
        source: Optional source for debugging

    Returns:
        TypedData if type_info provided, otherwise original value

    Example:
        wrapped = wrap_if_needed(42, MonomorphicType("Int"), "computation")
    """
    # Already wrapped
    if isinstance(value, TypedData):
        return value

    # No type info - return unwrapped
    if type_info is None:
        return value

    # Wrap with type info
    return TypedData(value=value, type_info=type_info, source=source)


def unwrap_if_needed(value: Any) -> Any:
    """
    Unwrap TypedData to get raw value.

    Args:
        value: Value to unwrap (TypedData or raw value)

    Returns:
        Raw value

    Example:
        raw = unwrap_if_needed(typed_data)  # Returns underlying value
    """
    if isinstance(value, TypedData):
        return value.value
    return value
