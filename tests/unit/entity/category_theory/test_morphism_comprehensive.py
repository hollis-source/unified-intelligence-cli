# tests/unit/entity/category_theory/test_morphism_comprehensive.py
import pytest
from typing import Any, Callable
from src.entity.category_theory.morphism import Morphism, compose_chain
import warnings


@pytest.mark.parametrize("name, source, target, transform, input_val, expected", [
    ("double", "int", "int", lambda x: x * 2, 5, 10),
    ("to_str", "int", "str", lambda x: str(x), 42, "42"),
    ("upper", "str", "str", lambda x: x.upper(), "hello", "HELLO"),
    ("add_one", "float", "float", lambda x: x + 1.0, 3.14, pytest.approx(4.14)),
    ("negate", "bool", "bool", lambda x: not x, True, False),
])
def test_morphism_creation_and_call(name, source, target, transform, input_val, expected):
    """Test Morphism creation with various types and verify __call__ applies transformation correctly."""
    morph = Morphism(name, source, target, transform)
    assert morph.name == name
    assert morph.source == source
    assert morph.target == target
    assert morph.transform is transform
    assert morph(input_val) == expected


def test_morphism_repr():
    """Test string representation of Morphism."""
    morph = Morphism("square", "int", "int", lambda x: x ** 2)
    assert repr(morph) == "Morphism('square': int → int)"


@pytest.mark.parametrize("f_name, f_source, f_target, f_transform, g_name, g_source, g_target, g_transform, input_val, expected_result", [
    ("double", "int", "int", lambda x: x * 2, "to_str", "int", "str", lambda x: str(x), 5, "10"),
    ("add_one", "float", "float", lambda x: x + 1, "square", "float", "float", lambda x: x ** 2, 5, 36.0),  # 5+1=6, 6^2=36
    ("upper", "str", "str", lambda x: x.upper(), "len", "str", "int", lambda x: len(x), "hello", 5),  # "hello".upper()="HELLO", len("HELLO")=5
])
def test_morphism_compose_valid(f_name, f_source, f_target, f_transform, g_name, g_source, g_target, g_transform, input_val, expected_result):
    """Test composing two morphisms with compatible types (f.target == g.source)."""
    f = Morphism(f_name, f_source, f_target, f_transform)
    g = Morphism(g_name, g_source, g_target, g_transform)

    # g ∘ f: f applied first, then g
    composed = g.compose(f)

    assert composed.name == f"{g_name} ∘ {f_name}"
    assert composed.source == f_source
    assert composed.target == g_target
    assert composed(input_val) == expected_result  # Apply composed function


@pytest.mark.parametrize("f_name, f_source, f_target, g_name, g_source, g_target", [
    ("double", "int", "int", "to_str", "str", "str"),  # int != str
    ("upper", "str", "str", "add_one", "int", "int"),   # str != int
    ("square", "float", "float", "len", "str", "int"),  # float != str
])
def test_morphism_compose_invalid_type(f_name, f_source, f_target, g_name, g_source, g_target):
    """Test composing morphisms with incompatible types raises ValueError."""
    f = Morphism(f_name, f_source, f_target, lambda x: x)
    g = Morphism(g_name, g_source, g_target, lambda x: x)

    with pytest.raises(ValueError, match=f"Cannot compose morphisms: target of '{f.name}'"):
        g.compose(f)


def test_morphism_compose_identity_left():
    """Test left identity law: id_B ∘ f = f."""
    f = Morphism("double", "int", "int", lambda x: x * 2)
    id_b = Morphism.create_identity("int")
    
    composed = id_b.compose(f)
    
    assert composed.source == "int"
    assert composed.target == "int"
    assert composed(5) == f(5)  # Same result as original f


def test_morphism_compose_identity_right():
    """Test right identity law: f ∘ id_A = f."""
    f = Morphism("double", "int", "int", lambda x: x * 2)
    id_a = Morphism.create_identity("int")
    
    composed = f.compose(id_a)
    
    assert composed.source == "int"
    assert composed.target == "int"
    assert composed(5) == f(5)  # Same result as original f


def test_morphism_create_identity():
    """Test create_identity() creates correct identity morphism."""
    id_int = Morphism.create_identity("int")
    assert id_int.name == "id_int"
    assert id_int.source == "int"
    assert id_int.target == "int"
    assert id_int(42) == 42
    assert id_int("hello") == "hello"  # Identity works for any type


def test_morphism_identity_deprecated():
    """Test identity() method raises deprecation warning."""
    with pytest.warns(DeprecationWarning, match="identity\\(\\) is deprecated"):
        id_int = Morphism.identity("int")
    assert id_int.name == "id_int"


@pytest.mark.parametrize("f_transform, g_transform, h_transform", [
    (lambda x: x * 2, lambda x: x + 1, lambda x: x ** 2),
    (lambda x: str(x), lambda x: len(x), lambda x: x > 5),
    (lambda x: x.upper(), lambda x: x + "!", lambda x: len(x)),
])
def test_verify_associativity(f_transform, g_transform, h_transform):
    """Test verify_associativity() returns True for valid composition chain."""
    f = Morphism("f", "int", "int", f_transform)
    g = Morphism("g", "int", "int", g_transform)
    h = Morphism("h", "int", "int", h_transform)

    # Test with sample value 3
    # Left: (h ∘ g) ∘ f
    # Right: h ∘ (g ∘ f)
    assert f.verify_associativity(g, h) is True


def test_verify_associativity_invalid_composition():
    """Test verify_associativity() returns False when morphisms are not composable."""
    f = Morphism("f", "int", "str", lambda x: str(x))
    g = Morphism("g", "str", "int", lambda x: len(x))
    h = Morphism("h", "float", "bool", lambda x: x > 0)

    # f.target ("str") != g.source ("str") -> OK, but g.target ("int") != h.source ("float")
    assert f.verify_associativity(g, h) is False


def test_verify_left_identity():
    """Test verify_left_identity() returns True for valid morphism."""
    f = Morphism("double", "int", "int", lambda x: x * 2)
    assert f.verify_left_identity() is True


def test_verify_right_identity():
    """Test verify_right_identity() returns True for valid morphism."""
    f = Morphism("double", "int", "int", lambda x: x * 2)
    assert f.verify_right_identity() is True


def test_verify_left_identity_different_types():
    """Test verify_left_identity() with morphism between different types."""
    f = Morphism("to_str", "int", "str", lambda x: str(x))
    assert f.verify_left_identity() is True


def test_verify_right_identity_different_types():
    """Test verify_right_identity() with morphism between different types."""
    f = Morphism("to_str", "int", "str", lambda x: str(x))
    assert f.verify_right_identity() is True


@pytest.mark.parametrize("morphisms, expected_result", [
    # 2 morphisms
    (
        [
            Morphism("double", "int", "int", lambda x: x * 2),
            Morphism("to_str", "int", "str", lambda x: str(x))
        ],
        "10"
    ),
    # 3 morphisms
    (
        [
            Morphism("add_one", "int", "int", lambda x: x + 1),
            Morphism("double", "int", "int", lambda x: x * 2),
            Morphism("to_str", "int", "str", lambda x: str(x))
        ],
        "6"  # (1+1)*2 = 4 → "4"? Wait: input=1: 1→2→4→"4" → but we need to test with 1
    ),
    # 4 morphisms
    (
        [
            Morphism("add_one", "int", "int", lambda x: x + 1),
            Morphism("square", "int", "int", lambda x: x ** 2),
            Morphism("double", "int", "int", lambda x: x * 2),
            Morphism("to_str", "int", "str", lambda x: str(x))
        ],
        "32"  # input=1: 1→2→4→8→"8"? Let's recalculate: 1→2→4→8→"8" but we expect 8? 
    ),
])
def test_compose_chain(morphisms, expected_result):
    """Test compose_chain() with 2, 3, and 4 morphisms."""
    # We need to use consistent input value
    input_val = 1
    
    # For 2 morphisms: double then to_str: 1→2→"2" → but expected "10" in example? Let's fix test
    # Actually, example in docstring: compose_chain(f, g, h) = h ∘ g ∘ f
    # So: f first, then g, then h
    # For 2 morphisms: [f, g] = g ∘ f
    # So for [double, to_str]: f=double(1)=2, g=to_str(2)="2" → expected "2"
    # But the example above says expected "10" — that was for input 5
    
    # Let's adjust: use input 5 for first test
    f1 = Morphism("double", "int", "int", lambda x: x * 2)
    g1 = Morphism("to_str", "int", "str", lambda x: str(x))
    composed1 = compose_chain(f1, g1)
    assert composed1(5) == "10"
    
    # For 3 morphisms: add_one(1)=2, double(2)=4, to_str(4)="4"
    f2 = Morphism("add_one", "int", "int", lambda x: x + 1)
    g2 = Morphism("double", "int", "int", lambda x: x * 2)
    h2 = Morphism("to_str", "int", "str", lambda x: str(x))
    composed2 = compose_chain(f2, g2, h2)
    assert composed2(1) == "4"
    
    # For 4 morphisms: add_one(1)=2, square(2)=4, double(4)=8, to_str(8)="8"
    f3 = Morphism("add_one", "int", "int", lambda x: x + 1)
    g3 = Morphism("square", "int", "int", lambda x: x ** 2)
    h3 = Morphism("double", "int", "int", lambda x: x * 2)
    i3 = Morphism("to_str", "int", "str", lambda x: str(x))
    composed3 = compose_chain(f3, g3, h3, i3)
    assert composed3(1) == "8"


def test_compose_chain_single():
    """Test compose_chain() with single morphism returns the same morphism."""
    f = Morphism("double", "int", "int", lambda x: x * 2)
    result = compose_chain(f)
    assert result is f  # Should return the same object
    assert result(5) == 10


def test_compose_chain_empty():
    """Test compose_chain() with empty list raises ValueError."""
    with pytest.raises(ValueError, match="Cannot compose empty chain"):
        compose_chain()


def test_compose_chain_three_different_types():
    """Test compose_chain() with three morphisms of different types."""
    f = Morphism("int_to_str", "int", "str", lambda x: str(x))
    g = Morphism("str_to_len", "str", "int", lambda x: len(x))
    h = Morphism("len_to_bool", "int", "bool", lambda x: x > 3)

    composed = compose_chain(f, g, h)
    assert composed.source == "int"
    assert composed.target == "bool"
    assert composed(123) is False  # "123" has len 3 → 3>3 is False
    assert composed(1234) is True  # "1234" has len 4 → 4>3 is True
    assert composed(12) is False   # "12" has len 2 → 2>3 is False


def test_morphism_compose_with_identity_itself():
    """Test composing identity morphism with itself."""
    id_int = Morphism.create_identity("int")
    composed = id_int.compose(id_int)
    assert composed.source == "int"
    assert composed.target == "int"
    assert composed(42) == 42
    assert composed.name == "id_int ∘ id_int"


def test_verify_associativity_with_identity():
    """Test associativity with identity morphism in chain."""
    f = Morphism("double", "int", "int", lambda x: x * 2)
    id_int = Morphism.create_identity("int")
    
    # Test: (id ∘ f) ∘ id == id ∘ (f ∘ id)
    # Both should equal f
    assert f.verify_associativity(id_int, id_int) is True
    assert id_int.verify_associativity(f, id_int) is True
    assert id_int.verify_associativity(id_int, f) is True


def test_compose_chain_long_chain():
    """Test compose_chain() with 5 morphisms."""
    morphisms = [
        Morphism("add_1", "int", "int", lambda x: x + 1),
        Morphism("mul_2", "int", "int", lambda x: x * 2),
        Morphism("sub_1", "int", "int", lambda x: x - 1),
        Morphism("square", "int", "int", lambda x: x ** 2),
        Morphism("to_str", "int", "str", lambda x: str(x))
    ]
    
    composed = compose_chain(*morphisms)
    result = composed(2)  # 2 → 3 → 6 → 5 → 25 → "25"
    assert result == "25"