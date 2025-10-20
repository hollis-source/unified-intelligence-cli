"""
Unit tests for DSL Type Checker - Composition Validation.

Tests type checking for DSL composition operators:
- Sequential composition (g ∘ f) validation
- Parallel composition (f × g) validation
- Type environment management
- Type mismatch error handling

Clean Architecture: Test layer validating type checking contracts.
"""

import pytest
from src.dsl.types.type_system import (
    TypeVariable,
    MonomorphicType,
    FunctionType,
    ProductType,
    TypeMismatchError,
    Int,
    String,
    Bool,
    FilePath,
)
from src.dsl.types.type_checker import (
    TypeEnvironment,
    check_composition,
    check_product,
)


class TestTypeEnvironment:
    """Test TypeEnvironment for managing type bindings."""

    def test_type_environment_creation(self):
        """Test creating empty type environment."""
        env = TypeEnvironment()
        assert env.bindings == {}

    def test_type_environment_bind(self):
        """Test binding names to types."""
        env = TypeEnvironment()
        func_type = FunctionType(Int, String)

        env.bind("process", func_type)
        assert env.bindings["process"] == func_type

    def test_type_environment_lookup_existing(self):
        """Test looking up existing type binding."""
        env = TypeEnvironment()
        func_type = FunctionType(String, Bool)

        env.bind("validate", func_type)
        result = env.lookup("validate")

        assert result == func_type

    def test_type_environment_lookup_missing(self):
        """Test looking up non-existent binding returns None."""
        env = TypeEnvironment()
        result = env.lookup("nonexistent")
        assert result is None

    def test_type_environment_multiple_bindings(self):
        """Test managing multiple type bindings."""
        env = TypeEnvironment()

        env.bind("fetch", FunctionType(FilePath, String))
        env.bind("parse", FunctionType(String, Int))
        env.bind("format", FunctionType(Int, String))

        assert len(env.bindings) == 3
        assert env.lookup("fetch") == FunctionType(FilePath, String)
        assert env.lookup("parse") == FunctionType(String, Int)

    def test_type_environment_repr(self):
        """Test string representation of type environment."""
        env = TypeEnvironment()
        env.bind("f", FunctionType(Int, String))

        repr_str = repr(env)
        assert "f :: Int → String" in repr_str


class TestCheckComposition:
    """Test sequential composition type checking (g ∘ f)."""

    def test_check_composition_valid_simple(self):
        """Test valid composition with matching types."""
        # f: Int → String
        f = FunctionType(Int, String)
        # g: String → Bool
        g = FunctionType(String, Bool)

        # g ∘ f: Int → Bool
        result = check_composition(g, f)

        assert result == FunctionType(Int, Bool)

    def test_check_composition_valid_chain(self):
        """Test composition chain with multiple steps."""
        # f: Int → String
        f = FunctionType(Int, String)
        # g: String → Bool
        g = FunctionType(String, Bool)
        # h: Bool → FilePath
        h = FunctionType(Bool, FilePath)

        # h ∘ g: String → FilePath
        hg = check_composition(h, g)
        assert hg == FunctionType(String, FilePath)

        # (h ∘ g) ∘ f: Int → FilePath
        result = check_composition(hg, f)
        assert result == FunctionType(Int, FilePath)

    def test_check_composition_type_mismatch(self):
        """Test composition with type mismatch raises error."""
        # f: Int → String
        f = FunctionType(Int, String)
        # g: Bool → FilePath (input doesn't match f's output)
        g = FunctionType(Bool, FilePath)

        # g ∘ f should fail: String ≠ Bool
        with pytest.raises(TypeMismatchError) as exc_info:
            check_composition(g, f)

        error = exc_info.value
        assert error.expected == Bool
        assert error.got == String
        assert "composition" in error.context

    def test_check_composition_polymorphic_types(self):
        """Test composition with polymorphic types."""
        # f: a → b
        tv_a = TypeVariable("a")
        tv_b = TypeVariable("b")
        f = FunctionType(tv_a, tv_b)

        # g: b → c
        tv_c = TypeVariable("c")
        g = FunctionType(tv_b, tv_c)

        # g ∘ f: a → c
        result = check_composition(g, f)

        # Result should have input type 'a' and output type 'c'
        assert isinstance(result.input_type, TypeVariable)
        assert isinstance(result.output_type, TypeVariable)

    def test_check_composition_instantiate_polymorphic(self):
        """Test composition instantiates polymorphic types."""
        # f: Int → a (polymorphic output)
        tv_a = TypeVariable("a")
        f = FunctionType(Int, tv_a)

        # g: String → Bool (concrete)
        g = FunctionType(String, Bool)

        # g ∘ f: Int → Bool (instantiates a = String)
        result = check_composition(g, f)

        assert result.input_type == Int
        assert result.output_type == Bool

    def test_check_composition_identity_type(self):
        """Test composition with identity function type."""
        # id: a → a
        tv_a = TypeVariable("a")
        identity = FunctionType(tv_a, tv_a)

        # f: Int → String
        f = FunctionType(Int, String)

        # id ∘ f: Int → String (left identity)
        result_left = check_composition(identity, f)
        # Result should be equivalent to f after substitution
        assert result_left.input_type == Int

        # f ∘ id: Int → String (right identity)
        result_right = check_composition(f, identity)
        assert result_right.output_type == String

    def test_check_composition_product_types(self):
        """Test composition with product types."""
        # f: (Int × String) → Bool
        input_prod = ProductType(Int, String)
        f = FunctionType(input_prod, Bool)

        # g: Bool → FilePath
        g = FunctionType(Bool, FilePath)

        # g ∘ f: (Int × String) → FilePath
        result = check_composition(g, f)

        assert result.input_type == input_prod
        assert result.output_type == FilePath

    def test_check_composition_nested_functions(self):
        """Test composition with higher-order function types."""
        # f: Int → (String → Bool)
        inner_func = FunctionType(String, Bool)
        f = FunctionType(Int, inner_func)

        # g: (String → Bool) → FilePath
        g = FunctionType(inner_func, FilePath)

        # g ∘ f: Int → FilePath
        result = check_composition(g, f)

        assert result.input_type == Int
        assert result.output_type == FilePath


class TestCheckProduct:
    """Test parallel composition type checking (f × g)."""

    def test_check_product_valid_simple(self):
        """Test valid product composition."""
        # f: Int → String
        f = FunctionType(Int, String)
        # g: Bool → FilePath
        g = FunctionType(Bool, FilePath)

        # f × g: (Int × Bool) → (String × FilePath)
        result = check_product(f, g)

        expected_input = ProductType(Int, Bool)
        expected_output = ProductType(String, FilePath)

        assert result.input_type == expected_input
        assert result.output_type == expected_output

    def test_check_product_same_types(self):
        """Test product of functions with same types."""
        # f: Int → String
        f = FunctionType(Int, String)
        # g: Int → String
        g = FunctionType(Int, String)

        # f × g: (Int × Int) → (String × String)
        result = check_product(f, g)

        expected_input = ProductType(Int, Int)
        expected_output = ProductType(String, String)

        assert result.input_type == expected_input
        assert result.output_type == expected_output

    def test_check_product_polymorphic_types(self):
        """Test product with polymorphic types."""
        # f: a → b
        tv_a = TypeVariable("a")
        tv_b = TypeVariable("b")
        f = FunctionType(tv_a, tv_b)

        # g: c → d
        tv_c = TypeVariable("c")
        tv_d = TypeVariable("d")
        g = FunctionType(tv_c, tv_d)

        # f × g: (a × c) → (b × d)
        result = check_product(f, g)

        assert isinstance(result.input_type, ProductType)
        assert isinstance(result.output_type, ProductType)

    def test_check_product_nested_products(self):
        """Test product with nested product types."""
        # f: (Int × String) → Bool
        input_prod = ProductType(Int, String)
        f = FunctionType(input_prod, Bool)

        # g: FilePath → (Bool × Int)
        output_prod = ProductType(Bool, Int)
        g = FunctionType(FilePath, output_prod)

        # f × g: ((Int × String) × FilePath) → (Bool × (Bool × Int))
        result = check_product(f, g)

        expected_input = ProductType(input_prod, FilePath)
        expected_output = ProductType(Bool, output_prod)

        assert result.input_type == expected_input
        assert result.output_type == expected_output

    def test_check_product_identity_functions(self):
        """Test product of identity functions."""
        # id_a: a → a
        tv_a = TypeVariable("a")
        id_a = FunctionType(tv_a, tv_a)

        # id_b: b → b
        tv_b = TypeVariable("b")
        id_b = FunctionType(tv_b, tv_b)

        # id_a × id_b: (a × b) → (a × b)
        result = check_product(id_a, id_b)

        assert isinstance(result.input_type, ProductType)
        assert isinstance(result.output_type, ProductType)

    def test_check_product_higher_order_functions(self):
        """Test product with higher-order function types."""
        # f: Int → (String → Bool)
        inner_func = FunctionType(String, Bool)
        f = FunctionType(Int, inner_func)

        # g: Bool → FilePath
        g = FunctionType(Bool, FilePath)

        # f × g: (Int × Bool) → ((String → Bool) × FilePath)
        result = check_product(f, g)

        expected_input = ProductType(Int, Bool)
        expected_output = ProductType(inner_func, FilePath)

        assert result.input_type == expected_input
        assert result.output_type == expected_output


class TestCompositionProductInteraction:
    """Test interaction between composition and product operators."""

    def test_composition_of_products(self):
        """Test composing product functions: (h × k) ∘ (f × g)."""
        # f: Int → String
        f = FunctionType(Int, String)
        # g: Bool → FilePath
        g = FunctionType(Bool, FilePath)

        # f × g: (Int × Bool) → (String × FilePath)
        fg = check_product(f, g)

        # h: String → Int
        h = FunctionType(String, Int)
        # k: FilePath → Bool
        k = FunctionType(FilePath, Bool)

        # h × k: (String × FilePath) → (Int × Bool)
        hk = check_product(h, k)

        # (h × k) ∘ (f × g): (Int × Bool) → (Int × Bool)
        result = check_composition(hk, fg)

        expected_input = ProductType(Int, Bool)
        expected_output = ProductType(Int, Bool)

        assert result.input_type == expected_input
        assert result.output_type == expected_output

    def test_product_of_compositions(self):
        """Test product of composed functions: (g ∘ f) × (k ∘ h)."""
        # f: Int → String
        f = FunctionType(Int, String)
        # g: String → Bool
        g = FunctionType(String, Bool)

        # g ∘ f: Int → Bool
        gf = check_composition(g, f)

        # h: FilePath → Int
        h = FunctionType(FilePath, Int)
        # k: Int → String
        k = FunctionType(Int, String)

        # k ∘ h: FilePath → String
        kh = check_composition(k, h)

        # (g ∘ f) × (k ∘ h): (Int × FilePath) → (Bool × String)
        result = check_product(gf, kh)

        expected_input = ProductType(Int, FilePath)
        expected_output = ProductType(Bool, String)

        assert result.input_type == expected_input
        assert result.output_type == expected_output

