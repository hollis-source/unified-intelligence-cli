"""Literal entity for terminal values in CT DSL.

Clean Architecture: Entity layer.
SOLID: SRP - represents only literal terminal values.
"""

from dataclasses import dataclass
from typing import Any
from src.dsl.entities.ast_node import ASTNode


@dataclass(frozen=True)
class Literal(ASTNode):
    """
    Represents a literal terminal value in the DSL AST.

    Literals are the leaf nodes of the AST, representing concrete values
    like task names, agent identifiers, or parameters.

    Clean Code principles:
    - Single Responsibility: Only wraps literal values
    - Immutable: frozen=True prevents mutation bugs
    - Type-safe: Accepts Any type for flexibility
    - Self-documenting: Clear field names

    Attributes:
        value (Any): The literal value (string, number, etc.).

    Example:
        task_name = Literal("build_frontend")
        agent_id = Literal("frontend-lead")
        param = Literal(42)
    """
    value: Any

    def __repr__(self) -> str:
        """Returns string representation showing value."""
        return f"Literal(value={self.value!r})"

    def accept(self, visitor):
        """Visitor pattern implementation for Literal nodes."""
        return visitor.visit_literal(self)
