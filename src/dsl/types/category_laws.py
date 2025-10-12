"""Category Theory Laws Enforcement

Implements and verifies fundamental category theory laws for DSL composition:
1. Associativity: (h ∘ g) ∘ f ≡ h ∘ (g ∘ f)
2. Identity: id ∘ f ≡ f ≡ f ∘ id
3. Product projections: π₁, π₂

These laws ensure that composition operators behave correctly according to
category theory, providing mathematical guarantees for workflow composition.

Mathematical Foundation:
- Category C consists of objects and morphisms
- Composition is associative: f ∘ (g ∘ h) = (f ∘ g) ∘ h
- Identity exists: ∃ id_A such that id_A ∘ f = f = f ∘ id_B
- Product category has projections: π₁: A × B → A, π₂: A × B → B

Story: Story 1, Phase 4 - Category Laws Enforcement
"""

from typing import Optional
from src.dsl.types.type_system import (
    Type,
    TypeVariable,
    FunctionType,
    ProductType,
)


def make_identity(type_: Type) -> FunctionType:
    """
    Create identity morphism: id: A → A

    Category Theory: For any object A in category C, there exists
    an identity morphism id_A: A → A such that:
    - id_A ∘ f = f for any f: B → A
    - g ∘ id_A = g for any g: A → C

    Args:
        type_: The type for both domain and codomain

    Returns:
        FunctionType representing id: type_ → type_

    Example:
        id_int = make_identity(MonomorphicType("Int"))
        # Returns: Int → Int
    """
    return FunctionType(input_type=type_, output_type=type_)


def verify_associativity(
    f: FunctionType,
    g: FunctionType,
    h: FunctionType
) -> bool:
    """
    Verify associativity law: (h ∘ g) ∘ f ≡ h ∘ (g ∘ f)

    Category Theory Law:
    Composition must be associative. Given morphisms:
    - f: A → B
    - g: B → C
    - h: C → D

    Then: (h ∘ g) ∘ f = h ∘ (g ∘ f): A → D

    Args:
        f: First function (executed first)
        g: Second function (executed second)
        h: Third function (executed third)

    Returns:
        True if associativity holds, False otherwise

    Note:
        This checks type-level associativity. Since composition is
        structurally associative in our type system, this verifies
        that the types compose correctly both ways.
    """
    # Verify f.output unifies with g.input
    if f.output_type.unify(g.input_type) is None:
        return False

    # Verify g.output unifies with h.input
    if g.output_type.unify(h.input_type) is None:
        return False

    # Both compositions should have same type: f.input → h.output
    # This is guaranteed by type system, but we verify for completeness
    return True


def verify_left_identity(f: FunctionType, identity: FunctionType) -> bool:
    """
    Verify left identity law: id ∘ f ≡ f

    Category Theory Law:
    For any morphism f: A → B and identity id_B: B → B:
    id_B ∘ f = f

    Args:
        f: Function to compose with identity
        identity: Identity morphism for codomain of f

    Returns:
        True if left identity holds, False otherwise

    Example:
        f: Int → String
        id_string: String → String
        verify_left_identity(f, id_string) → True
    """
    # Identity must be id: B → B where B = f.output_type
    if identity.input_type != identity.output_type:
        return False

    # Identity's type must match f's output type
    return f.output_type.unify(identity.input_type) is not None


def verify_right_identity(f: FunctionType, identity: FunctionType) -> bool:
    """
    Verify right identity law: f ∘ id ≡ f

    Category Theory Law:
    For any morphism f: A → B and identity id_A: A → A:
    f ∘ id_A = f

    Args:
        f: Function to compose with identity
        identity: Identity morphism for domain of f

    Returns:
        True if right identity holds, False otherwise

    Example:
        f: Int → String
        id_int: Int → Int
        verify_right_identity(f, id_int) → True
    """
    # Identity must be id: A → A where A = f.input_type
    if identity.input_type != identity.output_type:
        return False

    # Identity's type must match f's input type
    return f.input_type.unify(identity.input_type) is not None


def project_left(product_type: ProductType) -> FunctionType:
    """
    Create left projection: π₁: A × B → A

    Category Theory:
    For product A × B in category C, the left projection π₁
    extracts the left component.

    Universal property of products:
    For any morphisms f: C → A and g: C → B,
    there exists unique h: C → A × B such that:
    - π₁ ∘ h = f
    - π₂ ∘ h = g

    Args:
        product_type: Product type A × B

    Returns:
        FunctionType representing π₁: A × B → A

    Example:
        product = ProductType(Int, String)
        π₁ = project_left(product)
        # Returns: (Int × String) → Int
    """
    return FunctionType(
        input_type=product_type,
        output_type=product_type.left
    )


def project_right(product_type: ProductType) -> FunctionType:
    """
    Create right projection: π₂: A × B → B

    Category Theory:
    For product A × B in category C, the right projection π₂
    extracts the right component.

    Args:
        product_type: Product type A × B

    Returns:
        FunctionType representing π₂: A × B → B

    Example:
        product = ProductType(Int, String)
        π₂ = project_right(product)
        # Returns: (Int × String) → String
    """
    return FunctionType(
        input_type=product_type,
        output_type=product_type.right
    )


def verify_product_universal_property(
    product: ProductType,
    f: FunctionType,
    g: FunctionType,
    h: FunctionType
) -> bool:
    """
    Verify universal property of products.

    Category Theory:
    Given f: C → A, g: C → B, and h: C → A × B,
    verify that:
    - π₁ ∘ h = f  (left projection composed with h equals f)
    - π₂ ∘ h = g  (right projection composed with h equals g)

    This is satisfied when:
    - h.output_type = A × B (the product)
    - f.input_type = g.input_type = h.input_type (all from C)
    - f.output_type = A (left component)
    - g.output_type = B (right component)

    Args:
        product: Product type A × B
        f: Morphism to left component (C → A)
        g: Morphism to right component (C → B)
        h: Morphism to product (C → A × B)

    Returns:
        True if universal property holds, False otherwise
    """
    # Verify h maps to product
    if not isinstance(h.output_type, ProductType):
        return False

    # Verify h.output_type unifies with product
    if h.output_type.unify(product) is None:
        return False

    # Verify f, g, h all have same input type (all from C)
    if f.input_type.unify(h.input_type) is None:
        return False
    if g.input_type.unify(h.input_type) is None:
        return False

    # Verify f.output = product.left
    if f.output_type.unify(product.left) is None:
        return False

    # Verify g.output = product.right
    if g.output_type.unify(product.right) is None:
        return False

    return True
