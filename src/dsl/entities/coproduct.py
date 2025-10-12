"""Coproduct entity for choice/alternative task execution (f + g).

Clean Architecture: Entity layer.
SOLID: SRP - represents only categorical coproduct, DIP - depends on ASTNode abstraction.

Categorical semantics: Coproduct (sum type) represents choice between alternatives.
In category theory, coproduct is the dual of product, with injections ι₁ and ι₂.

Execution semantics: First-success with short-circuit evaluation.
- Try left first
- If left succeeds → return left result (short-circuit, don't execute right)
- If left fails → try right
- If both fail → return combined error
"""

from dataclasses import dataclass
from src.dsl.entities.ast_node import ASTNode


@dataclass(frozen=True)
class Coproduct(ASTNode):
    """
    Represents the categorical coproduct of two ASTNode instances (f + g).

    Categorical semantics: Choice/alternative execution where left branch is
    tried first, and right branch is tried only if left fails (first-success
    with lazy evaluation). This is the dual of Product (×).

    This differs from Product (parallel) and Composition (sequential):
    - Product (×): Both execute in parallel, results combined
    - Composition (∘): Sequential execution (output of first feeds into second)
    - Coproduct (+): Alternative execution (first success wins)

    Clean Code principles:
    - Single Responsibility: Only handles choice/alternative logic
    - Immutable: frozen=True prevents mutation bugs
    - Type-safe: Validates ASTNode instances in __post_init__
    - Self-documenting: Clear field names, descriptive repr

    Attributes:
        left (ASTNode): The left alternative (tried first).
        right (ASTNode): The right alternative (tried if left fails).

    Example:
        grok_model + qwen_model
        Execution: Try grok first, if it fails/is unavailable, try qwen
        Result: Output from whichever model succeeds first

    Use cases:
        - Fallback strategies: primary + backup
        - Model selection: expensive_accurate + fast_approximate
        - Resource availability: gpu_task + cpu_task
        - Error recovery: risky_operation + safe_default
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
        """Returns the string representation as '(left + right)'."""
        return f"({self.left} + {self.right})"

    def accept(self, visitor):
        """Visitor pattern implementation for Coproduct nodes."""
        return visitor.visit_coproduct(self)
