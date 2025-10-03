"""TypeAnnotation entity for DSL type system integration.

Clean Architecture: Entity layer (domain model).
SOLID: SRP - represents only type annotations, DIP - depends on type system abstractions.

Story: Story 1, Phase 2 - AST Integration
"""

from dataclasses import dataclass
from src.dsl.entities.ast_node import ASTNode
from src.dsl.types.type_system import Type


@dataclass(frozen=True)
class TypeAnnotation(ASTNode):
    """
    Represents a type annotation in the DSL: name :: Type

    Associates a function/task name with its type signature,
    enabling compile-time type checking of workflow compositions.

    Category Theory semantics:
    - Declares the domain and codomain of a morphism
    - Enables verification that g ∘ f is well-typed

    Clean Code principles:
    - Single Responsibility: Only represents type annotations
    - Immutable: frozen=True prevents mutation bugs
    - Type-safe: Validates Type instance

    Attributes:
        name (str): The function/task identifier
        type_signature (Type): The type from type_system.py

    Example:
        # fetch_commits :: () -> List[Commit]
        TypeAnnotation(
            name="fetch_commits",
            type_signature=FunctionType(
                input_type=Unit,
                output_type=List(MonomorphicType("Commit"))
            )
        )
    """
    name: str
    type_signature: Type

    def __post_init__(self) -> None:
        """
        Validates that name is string and type_signature is Type.

        Raises:
            TypeError: If name is not str or type_signature is not Type.
        """
        if not isinstance(self.name, str):
            raise TypeError(f"name must be a string, got {type(self.name).__name__}")
        if not isinstance(self.type_signature, Type):
            raise TypeError(
                f"type_signature must be an instance of Type, "
                f"got {type(self.type_signature).__name__}"
            )

    def __repr__(self) -> str:
        """Returns string representation as 'name :: type_signature'."""
        return f"{self.name} :: {self.type_signature}"

    def accept(self, visitor):
        """Visitor pattern implementation for TypeAnnotation nodes."""
        return visitor.visit_type_annotation(self)
