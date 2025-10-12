"""Functor entity for reusable workflow mappings.

Clean Architecture: Entity layer.
SOLID: SRP - represents only functor (structure-preserving map).
"""

from dataclasses import dataclass
from src.dsl.entities.ast_node import ASTNode


@dataclass(frozen=True)
class Functor(ASTNode):
    """
    Represents a functor (reusable workflow mapping) in the DSL.

    Functors are structure-preserving transformations that map workflows
    across different contexts while maintaining composition semantics.

    Category Theory semantics:
    - Maps objects to objects and morphisms to morphisms
    - Preserves composition: F(g ∘ f) = F(g) ∘ F(f)
    - Preserves identity: F(id) = id

    Clean Code principles:
    - Single Responsibility: Only represents functor abstraction
    - Immutable: frozen=True prevents mutation bugs
    - Type-safe: Validates ASTNode instance
    - Self-documenting: Clear field names

    Attributes:
        name (str): The functor identifier (e.g., "ci_pipeline").
        expression (ASTNode): The workflow expression it maps.

    Example:
        # functor ci_pipeline = build ∘ test ∘ deploy
        ci = Functor(
            name="ci_pipeline",
            expression=Composition(
                left=deploy,
                right=Composition(left=test, right=build)
            )
        )
    """
    name: str
    expression: ASTNode

    def __post_init__(self) -> None:
        """
        Validates that name is string and expression is ASTNode.

        Raises:
            TypeError: If name is not str or expression is not ASTNode.
        """
        if not isinstance(self.name, str):
            raise TypeError(f"name must be a string, got {type(self.name).__name__}")
        if not isinstance(self.expression, ASTNode):
            raise TypeError(f"expression must be an instance of ASTNode, got {type(self.expression).__name__}")

    def __repr__(self) -> str:
        """Returns string representation as 'functor name = expression'."""
        return f"Functor(name={self.name!r}, expression={self.expression!r})"

    def accept(self, visitor):
        """Visitor pattern implementation for Functor nodes."""
        return visitor.visit_functor(self)
