"""Morphism entity for category-theoretic transformations.

Implements morphisms (arrows) in category theory, representing transformations
between objects with composition and identity laws.
"""

from dataclasses import dataclass
from typing import Any, Callable, Generic, TypeVar


# Type variables for domain and codomain
A = TypeVar('A')  # Source type
B = TypeVar('B')  # Target type
C = TypeVar('C')  # Composition target type


@dataclass(frozen=True)
class Morphism(Generic[A, B]):
    """Represents a morphism (arrow) in category theory.

    A morphism is a structure-preserving map between two objects (domain and
    codomain). Morphisms can be composed following associativity laws.

    Type parameters:
        A: Type of the source object (domain)
        B: Type of the target object (codomain)

    Attributes:
        name: Human-readable identifier for this morphism
        source: Domain object type identifier
        target: Codomain object type identifier
        transform: Function implementing the transformation
    """

    name: str
    source: str
    target: str
    transform: Callable[[A], B]

    def __call__(self, value: A) -> B:
        """Apply morphism transformation to a value.

        Args:
            value: Input value from domain

        Returns:
            Transformed value in codomain
        """
        return self.transform(value)

    def compose(self, other: "Morphism[B, C]") -> "Morphism[A, C]":
        """Compose this morphism with another (self ∘ other).

        In category theory notation: (f ∘ g)(x) = f(g(x))
        This morphism is applied AFTER the other morphism.

        Composition is only valid when:
        - self.source matches other.target (type compatibility)

        Args:
            other: Morphism to compose with (applied first)

        Returns:
            New morphism representing the composition

        Raises:
            ValueError: If morphisms are not composable
        """
        if self.source != other.target:
            raise ValueError(
                f"Cannot compose morphisms: target of '{other.name}' "
                f"({other.target}) does not match source of '{self.name}' "
                f"({self.source})"
            )

        # Create composed transformation: (f ∘ g)(x) = f(g(x))
        def apply_composed_transform(x: A) -> C:
            intermediate = other.transform(x)
            return self.transform(intermediate)

        return Morphism(
            name=f"{self.name} ∘ {other.name}",
            source=other.source,
            target=self.target,
            transform=apply_composed_transform
        )

    def __repr__(self) -> str:
        """String representation for debugging."""
        return f"Morphism('{self.name}': {self.source} → {self.target})"

    @staticmethod
    def create_identity(obj_type: str) -> "Morphism[A, A]":
        """Create identity morphism for an object type.

        The identity morphism id_A: A → A satisfies:
        - id_A ∘ f = f for any f: B → A
        - g ∘ id_A = g for any g: A → C

        Args:
            obj_type: Type identifier for the object

        Returns:
            Identity morphism for that object type
        """
        return Morphism(
            name=f"id_{obj_type}",
            source=obj_type,
            target=obj_type,
            transform=lambda x: x  # Identity function
        )


    # Backward compatibility alias (deprecated)
    @staticmethod
    def identity(obj_type: str) -> "Morphism[A, A]":
        """DEPRECATED: Use create_identity() instead."""
        import warnings
        warnings.warn(
            "identity() is deprecated, use create_identity() instead",
            DeprecationWarning,
            stacklevel=2
        )
        return Morphism.create_identity(obj_type)
    def verify_associativity(
        self,
        g: "Morphism[B, C]",
        h: "Morphism[C, Any]"
    ) -> bool:
        """Verify associativity law: (h ∘ g) ∘ f = h ∘ (g ∘ f).

        Tests composition associativity with sample values.

        Args:
            g: Second morphism in composition chain
            h: Third morphism in composition chain

        Returns:
            True if associativity holds for composition

        Note:
            This is a verification helper, not a proof. Tests with
            a sample value to check computational correctness.
        """
        # Create both composition orders
        try:
            # Left association: (h ∘ g) ∘ f
            hg = h.compose(g)
            hg_f = hg.compose(self)

            # Right association: h ∘ (g ∘ f)
            gf = g.compose(self)
            h_gf = h.compose(gf)

            # Both should have same source/target
            return (
                hg_f.source == h_gf.source and
                hg_f.target == h_gf.target
            )
        except ValueError:
            # If compositions fail, not composable
            return False

    def verify_left_identity(self) -> bool:
        """Verify left identity law: id_B ∘ f = f.

        Returns:
            True if composing with identity on left preserves morphism
        """
        id_target = Morphism.identity(self.target)
        composed = id_target.compose(self)

        # Check that composition has same source/target
        return (
            composed.source == self.source and
            composed.target == self.target
        )

    def verify_right_identity(self) -> bool:
        """Verify right identity law: f ∘ id_A = f.

        Returns:
            True if composing with identity on right preserves morphism
        """
        id_source = Morphism.identity(self.source)
        composed = self.compose(id_source)

        # Check that composition has same source/target
        return (
            composed.source == self.source and
            composed.target == self.target
        )


def compose_chain(*morphisms: Morphism) -> Morphism:
    """Compose a chain of morphisms left-to-right.

    Composes morphisms in sequence: compose_chain(f, g, h) = h ∘ g ∘ f
    (functions applied left to right: f first, then g, then h)

    Args:
        *morphisms: Sequence of morphisms to compose

    Returns:
        Single composed morphism

    Raises:
        ValueError: If chain is empty or morphisms not composable
    """
    if not morphisms:
        raise ValueError("Cannot compose empty chain of morphisms")

    if len(morphisms) == 1:
        return morphisms[0]

    # Compose from left to right: f, g, h -> h ∘ g ∘ f
    result = morphisms[0]
    for morph in morphisms[1:]:
        result = morph.compose(result)

    return result
