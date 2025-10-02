"""AST Node base class for CT DSL.

Clean Architecture: Entity layer (no external dependencies).
SOLID: Single Responsibility - represents AST node abstraction.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class ASTNode(ABC):
    """
    Abstract base class for AST nodes in the DSL.

    This class follows the frozen dataclass pattern to ensure immutability.
    It provides automatic __repr__ and __eq__ methods via dataclass.
    Subclasses must implement the accept method for visitor pattern support.

    Clean Code principles:
    - Small and focused (SRP)
    - Immutable (frozen=True)
    - Self-documenting name
    - No side effects

    Example:
        @dataclass(frozen=True)
        class Composition(ASTNode):
            left: ASTNode
            right: ASTNode

            def accept(self, visitor):
                return visitor.visit_composition(self)
    """

    @abstractmethod
    def accept(self, visitor):
        """
        Visitor pattern hook for traversing AST.

        Args:
            visitor: A visitor object implementing visit_* methods for each node type.

        Returns:
            Result of the visitor's processing.
        """
        pass
