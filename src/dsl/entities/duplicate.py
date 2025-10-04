"""Duplicate entity for diagonal functor (broadcast semantics).

Mathematical Definition: Δ : A → A × A
Category Theory: Diagonal functor (natural transformation)
Semantics: duplicate(x) = (x, x)

Clean Architecture: Entity layer.
SOLID: SRP - represents only diagonal functor for broadcast composition.
"""

from dataclasses import dataclass
from src.dsl.entities.ast_node import ASTNode


@dataclass(frozen=True)
class Duplicate(ASTNode):
    """
    Represents the diagonal functor (Δ) for broadcast composition.

    Category Theory:
    - Diagonal functor: Δ : A → A × A
    - Natural transformation that duplicates input
    - Enables broadcast semantics: (f × g) ∘ duplicate

    Use Case:
    - Broadcast single input to multiple parallel functions
    - Example: (analyze_style × analyze_security) ∘ duplicate ∘ get_files
    - Type flow: FileList → (FileList × FileList) → (StyleReport × SecurityReport)

    Without duplicate, product composition requires separate inputs:
    - (f × g) : (A × C) → (B × D)  # Two different inputs

    With duplicate, broadcast single input:
    - (f × g) ∘ duplicate : A → (B × C)  # One input, broadcasted

    Clean Code principles:
    - Single Responsibility: Only handles input duplication
    - Immutable: frozen=True prevents mutation bugs
    - Type-safe: Type checker enforces duplicate : a -> (a × a)
    - Self-documenting: Clear mathematical semantics

    Example DSL usage:
        # Explicit broadcast
        parallel = (analyze_style * analyze_security) o duplicate o get_files

        # Type annotation
        duplicate :: a -> (a × a)

    References:
    - docs/PARALLEL_COMPOSITION_SEMANTICS.md
    - Awodey, "Category Theory", Chapter 6 (Products)
    """

    def __repr__(self) -> str:
        """Returns string representation as 'duplicate' or 'Δ'."""
        return "duplicate"

    def accept(self, visitor):
        """Visitor pattern implementation for Duplicate nodes."""
        return visitor.visit_duplicate(self)
