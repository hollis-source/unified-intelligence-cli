"""Composition entity for sequential task execution (f ∘ g).

Clean Architecture: Entity layer.
SOLID: SRP - represents only composition, DIP - depends on abstraction (ASTNode).
"""

from dataclasses import dataclass
from src.dsl.entities.ast_node import ASTNode


@dataclass(frozen=True)
class Composition(ASTNode):
    """
    Represents the composition of two ASTNode instances (f ∘ g).

    Categorical semantics: Sequential composition where output of right
    feeds into input of left (right-to-left composition).

    Clean Code principles:
    - Single Responsibility: Only handles composition
    - Immutable: frozen=True prevents mutation bugs
    - Type-safe: Validates ASTNode instances in __post_init__
    - Self-documenting: Clear field names, descriptive repr

    Attributes:
        left (ASTNode): The left operand (executed second).
        right (ASTNode): The right operand (executed first).

    Example:
        test ∘ code ∘ plan
        Execution order: plan → code → test
    """
    left: ASTNode
    right: ASTNode

    def __post_init__(self) -> None:
        """
        Validates that left and right are instances of ASTNode.

        Raises:
            TypeError: If left or right are not ASTNode instances.
        """
        if not isinstance(self.left, ASTNode):
            raise TypeError(f"left must be an instance of ASTNode, got {type(self.left).__name__}")
        if not isinstance(self.right, ASTNode):
            raise TypeError(f"right must be an instance of ASTNode, got {type(self.right).__name__}")

    def __repr__(self) -> str:
        """Returns the string representation as '(left ∘ right)'."""
        return f"({self.left} ∘ {self.right})"

    def accept(self, visitor):
        """Visitor pattern implementation for Composition nodes."""
        return visitor.visit_composition(self)
