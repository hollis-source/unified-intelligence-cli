"""
Core Type System with Hindley-Milner Type Inference

Implements type algebra for DSL workflow composition with category-theoretic
guarantees. Based on Robinson's unification algorithm and Damas-Milner type
inference.

Mathematical Foundation:
- Types form a category where objects are types and morphisms are functions
- Composition of morphisms preserves types: g ∘ f valid iff codomain(f) = domain(g)
- Product types enable parallel composition: f × g valid for any f, g

References:
- Damas, L., & Milner, R. (1982). Principal type-schemes for functional programs.
- Robinson, J. A. (1965). A machine-oriented logic based on the resolution principle.
- Pierce, B. C. (2002). Types and Programming Languages.

Story: Story 1, Phase 1 - Type System Foundation
"""

from abc import ABC, abstractmethod
from typing import Dict, Optional, Set, List
from dataclasses import dataclass


class TypeMismatchError(Exception):
    """Raised when types cannot be unified during composition checking"""
    def __init__(self, expected: 'Type', got: 'Type', context: str = ""):
        self.expected = expected
        self.got = got
        self.context = context
        super().__init__(
            f"Type mismatch{f' in {context}' if context else ''}: "
            f"expected {expected}, got {got}"
        )


@dataclass(frozen=True)
class Substitution:
    """
    Type substitution: mapping from type variables to types.

    Category theory: Substitution is a morphism in the category of types.
    Composition of substitutions forms a monoid.
    """
    mappings: Dict[str, 'Type']

    def apply(self, type_: 'Type') -> 'Type':
        """Apply substitution to a type"""
        return type_.apply_substitution(self)

    def compose(self, other: 'Substitution') -> 'Substitution':
        """
        Compose substitutions (monoid operation).

        (σ₂ ∘ σ₁)(α) = σ₂(σ₁(α))
        """
        new_mappings = {
            var: self.apply(typ)
            for var, typ in other.mappings.items()
        }
        new_mappings.update(self.mappings)
        return Substitution(new_mappings)


class Type(ABC):
    """
    Base class for all types in the DSL type system.

    Category Theory:
    - Types are objects in a category
    - FunctionType represents morphisms: A → B
    - Composition of FunctionTypes must satisfy category laws
    """

    @abstractmethod
    def free_variables(self) -> Set[str]:
        """Return set of free type variables"""
        pass

    @abstractmethod
    def apply_substitution(self, subst: Substitution) -> 'Type':
        """Apply substitution to this type"""
        pass

    @abstractmethod
    def unify(self, other: 'Type') -> Optional[Substitution]:
        """
        Robinson's unification algorithm.

        Returns substitution σ such that σ(self) = σ(other),
        or None if types cannot be unified.

        Properties:
        - Reflexive: ∀ t: unify(t, t) = {}
        - Symmetric: unify(t1, t2) = unify(t2, t1)
        - Transitive: If σ₁ = unify(t1, t2) and σ₂ = unify(σ₁(t2), t3)
                     then σ₂ ∘ σ₁ = unify(t1, t3)
        """
        pass

    @abstractmethod
    def __str__(self) -> str:
        """Human-readable type representation"""
        pass

    @abstractmethod
    def __eq__(self, other) -> bool:
        """Structural equality check"""
        pass

    @abstractmethod
    def __hash__(self) -> int:
        """Hash for type caching"""
        pass


@dataclass(frozen=True)
class TypeVariable(Type):
    """
    Type variable (e.g., 'a', 'b' in ∀a.a→a).

    Represents polymorphic types that can be instantiated
    to any concrete type during unification.
    """
    name: str

    def free_variables(self) -> Set[str]:
        return {self.name}

    def apply_substitution(self, subst: Substitution) -> Type:
        return subst.mappings.get(self.name, self)

    def unify(self, other: Type) -> Optional[Substitution]:
        if isinstance(other, TypeVariable) and self.name == other.name:
            return Substitution({})  # Same variable, no substitution needed

        if self.name in other.free_variables():
            # Occurs check: prevent infinite types (e.g., α = α → α)
            return None

        return Substitution({self.name: other})

    def __str__(self) -> str:
        return self.name

    def __eq__(self, other) -> bool:
        return isinstance(other, TypeVariable) and self.name == other.name

    def __hash__(self) -> int:
        return hash(("TypeVariable", self.name))


@dataclass(frozen=True)
class MonomorphicType(Type):
    """
    Concrete type with no type variables (e.g., Int, String, List[Commit]).

    Category theory: Objects in the category of types.
    """
    name: str
    type_params: tuple = ()  # For parameterized types like List[T]

    def free_variables(self) -> Set[str]:
        fv = set()
        for param in self.type_params:
            if isinstance(param, Type):
                fv.update(param.free_variables())
        return fv

    def apply_substitution(self, subst: Substitution) -> Type:
        if not self.type_params:
            return self
        new_params = tuple(
            param.apply_substitution(subst) if isinstance(param, Type) else param
            for param in self.type_params
        )
        return MonomorphicType(self.name, new_params)

    def unify(self, other: Type) -> Optional[Substitution]:
        if isinstance(other, TypeVariable):
            return other.unify(self)

        if not isinstance(other, MonomorphicType):
            return None

        if self.name != other.name:
            return None

        if len(self.type_params) != len(other.type_params):
            return None

        # Unify type parameters recursively
        subst = Substitution({})
        for p1, p2 in zip(self.type_params, other.type_params):
            if isinstance(p1, Type) and isinstance(p2, Type):
                p1_sub = p1.apply_substitution(subst)
                p2_sub = p2.apply_substitution(subst)
                next_subst = p1_sub.unify(p2_sub)
                if next_subst is None:
                    return None
                subst = next_subst.compose(subst)

        return subst

    def __str__(self) -> str:
        if not self.type_params:
            return self.name
        params_str = ", ".join(str(p) for p in self.type_params)
        return f"{self.name}[{params_str}]"

    def __eq__(self, other) -> bool:
        return (isinstance(other, MonomorphicType) and
                self.name == other.name and
                self.type_params == other.type_params)

    def __hash__(self) -> int:
        return hash(("MonomorphicType", self.name, self.type_params))


@dataclass(frozen=True)
class FunctionType(Type):
    """
    Function type: A → B

    Category Theory:
    - FunctionTypes are morphisms in the category of types
    - Composition: (B → C) ∘ (A → B) = (A → C)
    - Identity: id :: A → A satisfies id ∘ f = f = f ∘ id

    For type checking composition g ∘ f:
    - f.output must unify with g.input
    - Result type: FunctionType(f.input, g.output)
    """
    input_type: Type
    output_type: Type

    def free_variables(self) -> Set[str]:
        return self.input_type.free_variables() | self.output_type.free_variables()

    def apply_substitution(self, subst: Substitution) -> Type:
        return FunctionType(
            self.input_type.apply_substitution(subst),
            self.output_type.apply_substitution(subst)
        )

    def unify(self, other: Type) -> Optional[Substitution]:
        if isinstance(other, TypeVariable):
            return other.unify(self)

        if not isinstance(other, FunctionType):
            return None

        # Unify input types
        input_subst = self.input_type.unify(other.input_type)
        if input_subst is None:
            return None

        # Apply substitution and unify output types
        self_out = self.output_type.apply_substitution(input_subst)
        other_out = other.output_type.apply_substitution(input_subst)
        output_subst = self_out.unify(other_out)

        if output_subst is None:
            return None

        return output_subst.compose(input_subst)

    def __str__(self) -> str:
        # Add parentheses for nested function types
        input_str = (f"({self.input_type})" if isinstance(self.input_type, FunctionType)
                     else str(self.input_type))
        return f"{input_str} → {self.output_type}"

    def __eq__(self, other) -> bool:
        return (isinstance(other, FunctionType) and
                self.input_type == other.input_type and
                self.output_type == other.output_type)

    def __hash__(self) -> int:
        return hash(("FunctionType", self.input_type, self.output_type))


@dataclass(frozen=True)
class ProductType(Type):
    """
    Product type for parallel composition: A × B

    Category Theory:
    - Product in the category of types
    - Has projections π₁: (A × B) → A and π₂: (A × B) → B
    - Universal property: For any C with f: C → A and g: C → B,
      there exists unique h: C → (A × B) such that π₁ ∘ h = f and π₂ ∘ h = g

    Used for parallel workflow composition:
    If f: A → B and g: C → D, then f × g: (A × C) → (B × D)
    """
    left: Type
    right: Type

    def free_variables(self) -> Set[str]:
        return self.left.free_variables() | self.right.free_variables()

    def apply_substitution(self, subst: Substitution) -> Type:
        return ProductType(
            self.left.apply_substitution(subst),
            self.right.apply_substitution(subst)
        )

    def unify(self, other: Type) -> Optional[Substitution]:
        if isinstance(other, TypeVariable):
            return other.unify(self)

        if not isinstance(other, ProductType):
            return None

        # Unify left components
        left_subst = self.left.unify(other.left)
        if left_subst is None:
            return None

        # Apply substitution and unify right components
        self_right = self.right.apply_substitution(left_subst)
        other_right = other.right.apply_substitution(left_subst)
        right_subst = self_right.unify(other_right)

        if right_subst is None:
            return None

        return right_subst.compose(left_subst)

    def __str__(self) -> str:
        # Add parentheses for nested products
        left_str = (f"({self.left})" if isinstance(self.left, (FunctionType, ProductType))
                    else str(self.left))
        right_str = (f"({self.right})" if isinstance(self.right, (FunctionType, ProductType))
                     else str(self.right))
        return f"{left_str} × {right_str}"

    def __eq__(self, other) -> bool:
        return (isinstance(other, ProductType) and
                self.left == other.left and
                self.right == other.right)

    def __hash__(self) -> int:
        return hash(("ProductType", self.left, self.right))


# Common type constants for convenience
Unit = MonomorphicType("()")
Int = MonomorphicType("Int")
String = MonomorphicType("String")
Bool = MonomorphicType("Bool")
FilePath = MonomorphicType("FilePath")

def List(elem_type: Type) -> MonomorphicType:
    """List[T] type constructor"""
    return MonomorphicType("List", (elem_type,))

def Dict(key_type: Type, value_type: Type) -> MonomorphicType:
    """Dict[K, V] type constructor"""
    return MonomorphicType("Dict", (key_type, value_type))
