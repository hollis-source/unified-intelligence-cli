"""Unit tests for Morphism entity.

Tests cover morphism creation, composition, identity laws,
associativity, and category-theoretic properties.
"""

import pytest
from src.entity.category_theory import Morphism
from src.entity.category_theory.morphism import compose_chain


class TestMorphismCreation:
    """Test morphism instantiation and basic operations."""

    def test_create_morphism(self):
        """Test creating a basic morphism."""
        def double(x: int) -> int:
            return x * 2

        morph = Morphism(
            name="double",
            source="int",
            target="int",
            transform=double
        )

        assert morph.name == "double"
        assert morph.source == "int"
        assert morph.target == "int"
        assert morph.transform(5) == 10

    def test_morphism_call_applies_transform(self):
        """Test calling morphism applies transformation."""
        def increment(x: int) -> int:
            return x + 1

        morph = Morphism(
            name="increment",
            source="int",
            target="int",
            transform=increment
        )

        # Should be callable
        result = morph(10)
        assert result == 11

    def test_morphism_with_type_change(self):
        """Test morphism that changes types."""
        def to_string(x: int) -> str:
            return f"value_{x}"

        morph = Morphism(
            name="to_string",
            source="int",
            target="str",
            transform=to_string
        )

        result = morph(42)
        assert result == "value_42"
        assert isinstance(result, str)


class TestMorphismIdentity:
    """Test identity morphism creation and properties."""

    def test_create_identity_morphism(self):
        """Test creating identity morphism."""
        id_int = Morphism.identity("int")

        assert id_int.name == "id_int"
        assert id_int.source == "int"
        assert id_int.target == "int"

    def test_identity_preserves_value(self):
        """Test identity morphism returns input unchanged."""
        id_str = Morphism.identity("str")

        assert id_str("hello") == "hello"
        assert id_str("") == ""
        assert id_str("test123") == "test123"

    def test_identity_different_types(self):
        """Test identity morphisms for different types."""
        id_int = Morphism.identity("int")
        id_str = Morphism.identity("str")
        id_list = Morphism.identity("list")

        assert id_int(100) == 100
        assert id_str("text") == "text"
        assert id_list([1, 2, 3]) == [1, 2, 3]


class TestMorphismComposition:
    """Test morphism composition operations."""

    def test_compose_two_morphisms(self):
        """Test composing two compatible morphisms."""
        def double(x: int) -> int:
            return x * 2

        def increment(x: int) -> int:
            return x + 1

        f = Morphism(name="double", source="int", target="int", transform=double)
        g = Morphism(name="increment", source="int", target="int", transform=increment)

        # Compose: double ∘ increment (increment first, then double)
        composed = f.compose(g)

        # Should apply g first, then f: double(increment(5)) = double(6) = 12
        assert composed(5) == 12
        assert composed.name == "double ∘ increment"
        assert composed.source == "int"
        assert composed.target == "int"

    def test_compose_type_changing_morphisms(self):
        """Test composing morphisms that change types."""
        def to_string(x: int) -> str:
            return str(x)

        def get_length(s: str) -> int:
            return len(s)

        int_to_str = Morphism(
            name="to_str",
            source="int",
            target="str",
            transform=to_string
        )
        str_to_int = Morphism(
            name="length",
            source="str",
            target="int",
            transform=get_length
        )

        # Compose: length ∘ to_str
        composed = str_to_int.compose(int_to_str)

        # 12345 -> "12345" -> 5
        assert composed(12345) == 5
        assert composed.source == "int"
        assert composed.target == "int"

    def test_compose_incompatible_fails(self):
        """Test composing incompatible morphisms raises error."""
        f = Morphism(
            name="f",
            source="str",
            target="int",
            transform=len
        )
        g = Morphism(
            name="g",
            source="int",
            target="bool",
            transform=lambda x: x > 0
        )

        # f: str → int, g: int → bool
        # f.source (str) != g.target (bool), so not composable
        with pytest.raises(ValueError) as exc_info:
            f.compose(g)

        assert "Cannot compose" in str(exc_info.value)

    def test_compose_three_morphisms(self):
        """Test composing a chain of three morphisms."""
        f = Morphism(name="f", source="int", target="int", transform=lambda x: x + 1)
        g = Morphism(name="g", source="int", target="int", transform=lambda x: x * 2)
        h = Morphism(name="h", source="int", target="int", transform=lambda x: x - 3)

        # Compose: h ∘ g ∘ f  (apply f, then g, then h)
        gf = g.compose(f)  # g ∘ f
        hgf = h.compose(gf)  # h ∘ (g ∘ f)

        # Test: f(5) = 6, g(6) = 12, h(12) = 9
        assert hgf(5) == 9


class TestMorphismAssociativity:
    """Test associativity law for morphism composition."""

    def test_associativity_holds(self):
        """Test (h ∘ g) ∘ f = h ∘ (g ∘ f)."""
        f = Morphism(name="f", source="int", target="int", transform=lambda x: x + 1)
        g = Morphism(name="g", source="int", target="int", transform=lambda x: x * 2)
        h = Morphism(name="h", source="int", target="int", transform=lambda x: x - 3)

        # Left association: (h ∘ g) ∘ f
        hg = h.compose(g)
        left = hg.compose(f)

        # Right association: h ∘ (g ∘ f)
        gf = g.compose(f)
        right = h.compose(gf)

        # Both should produce same result for any input
        test_values = [0, 1, 5, 10, 100]
        for val in test_values:
            assert left(val) == right(val)

    def test_verify_associativity_method(self):
        """Test verify_associativity() method."""
        f = Morphism(name="f", source="int", target="int", transform=lambda x: x + 1)
        g = Morphism(name="g", source="int", target="int", transform=lambda x: x * 2)
        h = Morphism(name="h", source="int", target="int", transform=lambda x: x - 3)

        # Should verify associativity holds
        assert f.verify_associativity(g, h) is True

    def test_verify_associativity_incompatible(self):
        """Test verify_associativity() with incompatible morphisms."""
        f = Morphism(name="f", source="str", target="int", transform=len)
        g = Morphism(name="g", source="bool", target="float", transform=float)
        h = Morphism(name="h", source="list", target="str", transform=str)

        # These are not composable: f: str → int, g: bool → float
        # g.source (bool) != f.target (int), so g.compose(f) fails
        assert f.verify_associativity(g, h) is False


class TestMorphismIdentityLaws:
    """Test identity laws for morphism composition."""

    def test_left_identity_law(self):
        """Test id_B ∘ f = f (left identity)."""
        def double(x: int) -> int:
            return x * 2

        f = Morphism(name="double", source="int", target="int", transform=double)
        id_int = Morphism.identity("int")

        # id_int ∘ f should be equivalent to f
        composed = id_int.compose(f)

        test_values = [0, 1, 5, 10, -3]
        for val in test_values:
            assert composed(val) == f(val)

    def test_right_identity_law(self):
        """Test f ∘ id_A = f (right identity)."""
        def triple(x: int) -> int:
            return x * 3

        f = Morphism(name="triple", source="int", target="int", transform=triple)
        id_int = Morphism.identity("int")

        # f ∘ id_int should be equivalent to f
        composed = f.compose(id_int)

        test_values = [0, 1, 5, 10, -3]
        for val in test_values:
            assert composed(val) == f(val)

    def test_verify_left_identity_method(self):
        """Test verify_left_identity() method."""
        f = Morphism(
            name="increment",
            source="int",
            target="int",
            transform=lambda x: x + 1
        )

        assert f.verify_left_identity() is True

    def test_verify_right_identity_method(self):
        """Test verify_right_identity() method."""
        f = Morphism(
            name="double",
            source="int",
            target="int",
            transform=lambda x: x * 2
        )

        assert f.verify_right_identity() is True

    def test_identity_composition_both_sides(self):
        """Test id_B ∘ f ∘ id_A = f."""
        f = Morphism(
            name="square",
            source="int",
            target="int",
            transform=lambda x: x ** 2
        )
        id_int = Morphism.identity("int")

        # Compose with identity on both sides
        composed = id_int.compose(f.compose(id_int))

        test_values = [0, 1, 2, 5, 10]
        for val in test_values:
            assert composed(val) == f(val)


class TestComposeChain:
    """Test compose_chain utility function."""

    def test_compose_chain_single_morphism(self):
        """Test compose_chain with single morphism."""
        f = Morphism(name="f", source="int", target="int", transform=lambda x: x + 1)

        result = compose_chain(f)

        assert result is f

    def test_compose_chain_two_morphisms(self):
        """Test compose_chain with two morphisms."""
        f = Morphism(name="f", source="int", target="int", transform=lambda x: x + 1)
        g = Morphism(name="g", source="int", target="int", transform=lambda x: x * 2)

        # compose_chain(f, g) should apply f first, then g
        result = compose_chain(f, g)

        # f(5) = 6, g(6) = 12
        assert result(5) == 12

    def test_compose_chain_three_morphisms(self):
        """Test compose_chain with three morphisms."""
        f = Morphism(name="f", source="int", target="int", transform=lambda x: x + 1)
        g = Morphism(name="g", source="int", target="int", transform=lambda x: x * 2)
        h = Morphism(name="h", source="int", target="int", transform=lambda x: x - 3)

        # Apply f, then g, then h
        result = compose_chain(f, g, h)

        # f(5) = 6, g(6) = 12, h(12) = 9
        assert result(5) == 9

    def test_compose_chain_type_changes(self):
        """Test compose_chain with type-changing morphisms."""
        int_to_str = Morphism(
            name="to_str",
            source="int",
            target="str",
            transform=str
        )
        str_to_len = Morphism(
            name="length",
            source="str",
            target="int",
            transform=len
        )
        len_to_bool = Morphism(
            name="is_positive",
            source="int",
            target="bool",
            transform=lambda x: x > 0
        )

        result = compose_chain(int_to_str, str_to_len, len_to_bool)

        # 12345 -> "12345" -> 5 -> True
        assert result(12345) is True
        assert result.source == "int"
        assert result.target == "bool"

    def test_compose_chain_empty_raises_error(self):
        """Test compose_chain with no morphisms raises error."""
        with pytest.raises(ValueError) as exc_info:
            compose_chain()

        assert "empty chain" in str(exc_info.value)

    def test_compose_chain_incompatible_raises_error(self):
        """Test compose_chain with incompatible morphisms raises error."""
        f = Morphism(name="f", source="int", target="str", transform=str)
        g = Morphism(name="g", source="bool", target="int", transform=int)

        # f: int → str, g: bool → int
        # g.source (bool) != f.target (str), so not composable
        with pytest.raises(ValueError):
            compose_chain(f, g)


class TestMorphismRepresentation:
    """Test string representation."""

    def test_repr_basic_morphism(self):
        """Test __repr__() for basic morphism."""
        morph = Morphism(
            name="double",
            source="int",
            target="int",
            transform=lambda x: x * 2
        )

        repr_str = repr(morph)

        assert "double" in repr_str
        assert "int" in repr_str
        assert "→" in repr_str

    def test_repr_identity_morphism(self):
        """Test __repr__() for identity morphism."""
        id_str = Morphism.identity("str")

        repr_str = repr(id_str)

        assert "id_str" in repr_str
        assert "str" in repr_str

    def test_repr_composed_morphism(self):
        """Test __repr__() for composed morphism."""
        f = Morphism(name="f", source="int", target="int", transform=lambda x: x + 1)
        g = Morphism(name="g", source="int", target="int", transform=lambda x: x * 2)

        composed = g.compose(f)

        repr_str = repr(composed)

        assert "∘" in repr_str  # Composition symbol
        assert "f" in repr_str
        assert "g" in repr_str


class TestMorphismImmutability:
    """Test that morphisms are immutable."""

    def test_morphism_is_frozen(self):
        """Test that morphism dataclass is frozen."""
        morph = Morphism(
            name="test",
            source="int",
            target="int",
            transform=lambda x: x
        )

        # Should not be able to modify attributes
        with pytest.raises(Exception):  # FrozenInstanceError or AttributeError
            morph.name = "modified"

    def test_composition_creates_new_morphism(self):
        """Test that composition creates new morphism without modifying originals."""
        f = Morphism(name="f", source="int", target="int", transform=lambda x: x + 1)
        g = Morphism(name="g", source="int", target="int", transform=lambda x: x * 2)

        original_f_name = f.name
        original_g_name = g.name

        # Compose
        composed = g.compose(f)

        # Original morphisms should be unchanged
        assert f.name == original_f_name
        assert g.name == original_g_name
        # Composed should be different
        assert composed is not f
        assert composed is not g
