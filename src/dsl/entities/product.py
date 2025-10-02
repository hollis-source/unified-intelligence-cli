"""Product entity for parallel task execution (f × g).

Clean Architecture: Entity layer.
SOLID: SRP - represents only categorical product, DIP - depends on ASTNode abstraction.
"""

from dataclasses import dataclass
from src.dsl.entities.ast_node import ASTNode


@dataclass(frozen=True)
class Product(ASTNode):
    """
    Represents the categorical product of two ASTNode instances (f × g).

    Categorical semantics: Parallel execution where both tasks run
    concurrently and results are combined (universal property of products
    with projections π₁ and π₂).

    This differs from Composition (sequential) - Product enables true
    parallelism with independent task execution.

    Clean Code principles:
    - Single Responsibility: Only handles parallel product
    - Immutable: frozen=True prevents mutation bugs
    - Type-safe: Validates ASTNode instances in __post_init__
    - Self-documenting: Clear field names, descriptive repr

    Attributes:
        left (ASTNode): The left operand (executed in parallel).
        right (ASTNode): The right operand (executed in parallel).

    Example:
        frontend × backend
        Execution: Both run concurrently, results combined
        Result: {frontend: dashboard.html, backend: api.json}
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
        """Returns the string representation as '(left × right)'."""
        return f"({self.left} × {self.right})"

    def accept(self, visitor):
        """Visitor pattern implementation for Product nodes."""
        return visitor.visit_product(self)
