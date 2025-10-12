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


def check_coproduct(f: FunctionType, g: FunctionType) -> FunctionType:
    """
    Type check coproduct (choice/alternative): f + g

    DSL Semantics (first-success with lazy evaluation):
    - Try f first with input
    - If f succeeds, return f's result (short-circuit)
    - If f fails, try g with same input
    - Result type must be consistent

    Type Checking:
    - Both functions must accept same input type (they receive same input)
    - Both functions must produce same output type (for type safety)
    - If f: A → B and g: A → B, then f + g: A → B

    Args:
        f: Left alternative (tried first)
        g: Right alternative (tried if left fails)

    Returns:
        Coproduct function type with unified input/output types

    Raises:
        TypeMismatchError: If input or output types don't unify

    Example:
        f: String → Int (primary model)
        g: String → Int (backup model)
        f + g: String → Int ✓

        f: String → Int
        g: Bool → Float
        f + g: Type error (input types don't match)
    """
    # Unify input types (both receive same input)
    input_subst = f.input_type.unify(g.input_type)
    if input_subst is None:
        raise TypeMismatchError(
            expected=f.input_type,
            got=g.input_type,
            context=f"coproduct {f} + {g} - input types must match"
        )

    # Unify output types (result type must be consistent)
    output_subst = f.output_type.unify(g.output_type)
    if output_subst is None:
        raise TypeMismatchError(
            expected=f.output_type,
            got=g.output_type,
            context=f"coproduct {f} + {g} - output types must match"
        )

    # Compose substitutions and apply to result type
    combined_subst = output_subst.compose(input_subst)

    result = FunctionType(
        input_type=f.input_type,
        output_type=f.output_type
    )
    return result.apply_substitution(combined_subst)
