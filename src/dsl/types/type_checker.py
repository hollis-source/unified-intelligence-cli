"""Type Checker with Composition Validation

Implements type checking for DSL composition operators (∘, ×) with
category-theoretic guarantees. Validates that morphism composition
preserves types at compile time.

Mathematical Foundation:
- Sequential composition (g ∘ f): Requires codomain(f) = domain(g)
- Parallel composition (f × g): Product in category of types
- Type inference: Hindley-Milner algorithm for polymorphic types

Story: Story 1, Phase 3 - Composition Operators
"""

from typing import Dict, Optional
from src.dsl.types.type_system import (
    Type,
    FunctionType,
    ProductType,
    TypeMismatchError,
)


class TypeEnvironment:
    """
    Type environment for storing and looking up type annotations.

    Maintains a mapping from function/task names to their type signatures,
    enabling type checking of compositions.

    Clean Code: SRP - only manages type bindings
    """

    def __init__(self):
        """Initialize empty type environment."""
        self.bindings: Dict[str, Type] = {}

    def bind(self, name: str, type_sig: Type) -> None:
        """
        Bind a name to a type signature.

        Args:
            name: Function/task identifier
            type_sig: Type signature (usually FunctionType)
        """
        self.bindings[name] = type_sig

    def lookup(self, name: str) -> Optional[Type]:
        """
        Look up type signature for a name.

        Args:
            name: Function/task identifier

        Returns:
            Type signature if found, None otherwise
        """
        return self.bindings.get(name)

    def __repr__(self) -> str:
        """String representation of type environment."""
        items = [f"{name} :: {typ}" for name, typ in self.bindings.items()]
        return f"TypeEnv({', '.join(items)})"


def check_composition(g: FunctionType, f: FunctionType) -> FunctionType:
    """
    Type check sequential composition: g ∘ f

    Category Theory Law:
    If f: A → B and g: B → C, then g ∘ f: A → C

    Type Checking:
    - f.output must unify with g.input
    - Result type: A → C where A = f.input, C = g.output

    Args:
        g: Left function (executed second)
        f: Right function (executed first)

    Returns:
        Composed function type: f.input → g.output

    Raises:
        TypeMismatchError: If f.output doesn't unify with g.input

    Example:
        f: Int → String
        g: String → Bool
        g ∘ f: Int → Bool ✓

        f: Int → String
        g: Bool → Float
        g ∘ f: Type error (String ≠ Bool)
    """
    # Unify f's output with g's input
    subst = f.output_type.unify(g.input_type)

    if subst is None:
        raise TypeMismatchError(
            expected=g.input_type,
            got=f.output_type,
            context=f"composition {g} ∘ {f}"
        )

    # Apply substitution to result type
    result = FunctionType(
        input_type=f.input_type,
        output_type=g.output_type
    )
    return result.apply_substitution(subst)


def check_product(f: FunctionType, g: FunctionType) -> FunctionType:
    """
    Type check parallel composition: f × g

    Category Theory:
    If f: A → B and g: C → D, then f × g: (A × C) → (B × D)

    Product type semantics:
    - Both functions execute concurrently
    - Input is a product: (A × C)
    - Output is a product: (B × D)

    Args:
        f: Left function
        g: Right function

    Returns:
        Product function type: (A × C) → (B × D)

    Example:
        f: Int → String
        g: Bool → Float
        f × g: (Int × Bool) → (String × Float) ✓
    """
    input_product = ProductType(left=f.input_type, right=g.input_type)
    output_product = ProductType(left=f.output_type, right=g.output_type)

    return FunctionType(
        input_type=input_product,
        output_type=output_product
    )
