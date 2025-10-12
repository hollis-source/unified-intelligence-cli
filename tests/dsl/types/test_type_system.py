"""
Unit tests for DSL Type System - Core Types, Substitution, and Unification.

Tests Hindley-Milner type system components:
- Type entities (TypeVariable, MonomorphicType, FunctionType, ProductType)
- Substitution operations (apply, compose)
- Unification algorithm (Robinson's algorithm)
- Type algebra properties (reflexive, symmetric, transitive)

Clean Architecture: Test layer validating type system contracts.
"""

import pytest
from src.dsl.types.type_system import (
    Type,
    TypeVariable,
    MonomorphicType,
    FunctionType,
    ProductType,
    Substitution,
    TypeMismatchError,
    Unit,
    Int,
    String,
    Bool,
    FilePath,
    List,
    Dict,
)


class TestTypeVariable:
    """Test TypeVariable entity and operations."""

    def test_type_variable_creation(self):
        """Test creating a type variable."""
        tv = TypeVariable("a")
        assert tv.name == "a"
        assert str(tv) == "a"

    def test_type_variable_free_variables(self):
        """Test that type variable returns itself as free variable."""
        tv = TypeVariable("alpha")
        assert tv.free_variables() == {"alpha"}

    def test_type_variable_equality(self):
        """Test type variable structural equality."""
        tv1 = TypeVariable("a")
        tv2 = TypeVariable("a")
        tv3 = TypeVariable("b")

        assert tv1 == tv2
        assert tv1 != tv3
        assert hash(tv1) == hash(tv2)
        assert hash(tv1) != hash(tv3)

    def test_type_variable_unify_reflexive(self):
        """Test unification reflexive property: unify(t, t) = {}."""
        tv = TypeVariable("a")
        subst = tv.unify(tv)

        assert subst is not None
        assert subst.mappings == {}

    def test_type_variable_unify_with_concrete_type(self):
        """Test unifying type variable with concrete type."""
        tv = TypeVariable("a")
        subst = tv.unify(Int)

        assert subst is not None
        assert subst.mappings == {"a": Int}

    def test_type_variable_unify_occurs_check(self):
        """Test occurs check prevents infinite types (α = α → α)."""
        tv = TypeVariable("a")
        func_type = FunctionType(tv, tv)

        # Should fail occurs check
        subst = tv.unify(func_type)
        assert subst is None

    def test_type_variable_apply_substitution(self):
        """Test applying substitution to type variable."""
        tv = TypeVariable("a")
        subst = Substitution({"a": String})

        result = tv.apply_substitution(subst)
        assert result == String

    def test_type_variable_apply_empty_substitution(self):
        """Test applying empty substitution returns original."""
        tv = TypeVariable("a")
        subst = Substitution({})

        result = tv.apply_substitution(subst)
        assert result == tv


class TestMonomorphicType:
    """Test MonomorphicType entity and operations."""

    def test_monomorphic_type_creation(self):
        """Test creating concrete types."""
        assert Int.name == "Int"
        assert String.name == "String"
        assert str(Int) == "Int"

    def test_monomorphic_type_free_variables(self):
        """Test that concrete types have no free variables."""
        assert Int.free_variables() == set()
        assert String.free_variables() == set()

    def test_monomorphic_type_equality(self):
        """Test monomorphic type structural equality."""
        int1 = MonomorphicType("Int")
        int2 = MonomorphicType("Int")
        str_type = MonomorphicType("String")

        assert int1 == int2
        assert int1 != str_type
        assert hash(int1) == hash(int2)

    def test_monomorphic_type_unify_same_type(self):
        """Test unifying identical concrete types."""
        subst = Int.unify(Int)
        assert subst is not None
        assert subst.mappings == {}

    def test_monomorphic_type_unify_different_types(self):
        """Test unifying different concrete types fails."""
        subst = Int.unify(String)
        assert subst is None

    def test_monomorphic_type_unify_with_type_variable(self):
        """Test unifying concrete type with type variable."""
        tv = TypeVariable("a")
        subst = Int.unify(tv)

        assert subst is not None
        assert subst.mappings == {"a": Int}

    def test_parameterized_type_list(self):
        """Test parameterized type List[T]."""
        list_int = List(Int)
        assert str(list_int) == "List[Int]"
        assert list_int.type_params == (Int,)

    def test_parameterized_type_dict(self):
        """Test parameterized type Dict[K, V]."""
        dict_str_int = Dict(String, Int)
        assert str(dict_str_int) == "Dict[String, Int]"
        assert dict_str_int.type_params == (String, Int)

    def test_parameterized_type_free_variables(self):
        """Test free variables in parameterized types."""
        tv = TypeVariable("a")
        list_a = List(tv)

        assert list_a.free_variables() == {"a"}

    def test_parameterized_type_unify(self):
        """Test unifying parameterized types."""
        list_int = List(Int)
        list_str = List(String)

        # Same structure, different params
        subst = list_int.unify(list_str)
        assert subst is None

        # Same structure, same params
        list_int2 = List(Int)
        subst = list_int.unify(list_int2)
        assert subst is not None
        assert subst.mappings == {}

    def test_parameterized_type_unify_with_type_variable(self):
        """Test unifying List[a] with List[Int]."""
        tv = TypeVariable("a")
        list_a = List(tv)
        list_int = List(Int)

        subst = list_a.unify(list_int)
        assert subst is not None
        assert subst.mappings == {"a": Int}


class TestFunctionType:
    """Test FunctionType entity and operations."""

    def test_function_type_creation(self):
        """Test creating function types."""
        func = FunctionType(Int, String)
        assert func.input_type == Int
        assert func.output_type == String
        assert str(func) == "Int → String"

    def test_function_type_nested_repr(self):
        """Test string representation with nested functions."""
        # (Int → String) → Bool
        inner = FunctionType(Int, String)
        outer = FunctionType(inner, Bool)
        assert str(outer) == "(Int → String) → Bool"

    def test_function_type_free_variables(self):
        """Test free variables in function types."""
        tv_a = TypeVariable("a")
        tv_b = TypeVariable("b")
        func = FunctionType(tv_a, tv_b)

        assert func.free_variables() == {"a", "b"}

    def test_function_type_unify_same_signature(self):
        """Test unifying identical function types."""
        func1 = FunctionType(Int, String)
        func2 = FunctionType(Int, String)

        subst = func1.unify(func2)
        assert subst is not None
        assert subst.mappings == {}

    def test_function_type_unify_different_signatures(self):
        """Test unifying different function types fails."""
        func1 = FunctionType(Int, String)
        func2 = FunctionType(String, Int)

        subst = func1.unify(func2)
        assert subst is None

    def test_function_type_unify_polymorphic(self):
        """Test unifying polymorphic function types."""
        # a → b  unifies with  Int → String
        tv_a = TypeVariable("a")
        tv_b = TypeVariable("b")
        poly_func = FunctionType(tv_a, tv_b)
        concrete_func = FunctionType(Int, String)

        subst = poly_func.unify(concrete_func)
        assert subst is not None
        assert subst.mappings == {"a": Int, "b": String}

    def test_function_type_apply_substitution(self):
        """Test applying substitution to function type."""
        tv_a = TypeVariable("a")
        func = FunctionType(tv_a, String)
        subst = Substitution({"a": Int})

        result = func.apply_substitution(subst)
        assert result == FunctionType(Int, String)


class TestProductType:
    """Test ProductType entity and operations."""

    def test_product_type_creation(self):
        """Test creating product types."""
        prod = ProductType(Int, String)
        assert prod.left == Int
        assert prod.right == String
        assert str(prod) == "Int × String"

    def test_product_type_nested_repr(self):
        """Test string representation with nested products."""
        # (Int × String) × Bool
        inner = ProductType(Int, String)
        outer = ProductType(inner, Bool)
        assert str(outer) == "(Int × String) × Bool"

    def test_product_type_free_variables(self):
        """Test free variables in product types."""
        tv_a = TypeVariable("a")
        tv_b = TypeVariable("b")
        prod = ProductType(tv_a, tv_b)

        assert prod.free_variables() == {"a", "b"}

    def test_product_type_unify_same_structure(self):
        """Test unifying identical product types."""
        prod1 = ProductType(Int, String)
        prod2 = ProductType(Int, String)

        subst = prod1.unify(prod2)
        assert subst is not None
        assert subst.mappings == {}

    def test_product_type_unify_different_structure(self):
        """Test unifying different product types fails."""
        prod1 = ProductType(Int, String)
        prod2 = ProductType(String, Int)

        subst = prod1.unify(prod2)
        assert subst is None

    def test_product_type_unify_polymorphic(self):
        """Test unifying polymorphic product types."""
        tv_a = TypeVariable("a")
        tv_b = TypeVariable("b")
        poly_prod = ProductType(tv_a, tv_b)
        concrete_prod = ProductType(Int, String)

        subst = poly_prod.unify(concrete_prod)
        assert subst is not None
        assert subst.mappings == {"a": Int, "b": String}


class TestSubstitution:
    """Test Substitution operations and monoid laws."""

    def test_substitution_creation(self):
        """Test creating substitutions."""
        subst = Substitution({"a": Int, "b": String})
        assert subst.mappings == {"a": Int, "b": String}

    def test_substitution_apply_to_type_variable(self):
        """Test applying substitution to type variable."""
        subst = Substitution({"a": Int})
        tv = TypeVariable("a")

        result = subst.apply(tv)
        assert result == Int

    def test_substitution_identity(self):
        """Test identity substitution (monoid identity)."""
        empty_subst = Substitution({})
        tv = TypeVariable("a")

        result = empty_subst.apply(tv)
        assert result == tv

    def test_substitution_compose(self):
        """Test substitution composition (monoid operation)."""
        # σ₁: a → Int
        subst1 = Substitution({"a": Int})
        # σ₂: b → a
        tv_a = TypeVariable("a")
        subst2 = Substitution({"b": tv_a})

        # σ₂ ∘ σ₁: b → Int (σ₁ applied to σ₂)
        composed = subst1.compose(subst2)

        tv_b = TypeVariable("b")
        result = composed.apply(tv_b)
        assert result == Int

    def test_substitution_compose_associative(self):
        """Test substitution composition is associative."""
        subst1 = Substitution({"a": Int})
        tv_a = TypeVariable("a")
        subst2 = Substitution({"b": tv_a})
        tv_b = TypeVariable("b")
        subst3 = Substitution({"c": tv_b})

        # (σ₃ ∘ σ₂) ∘ σ₁
        left_assoc = (subst3.compose(subst2)).compose(subst1)
        # σ₃ ∘ (σ₂ ∘ σ₁)
        right_assoc = subst3.compose(subst2.compose(subst1))

        tv_c = TypeVariable("c")
        assert left_assoc.apply(tv_c) == right_assoc.apply(tv_c)


class TestUnificationProperties:
    """Test unification algorithm properties."""

    def test_unification_symmetric(self):
        """Test unification is symmetric: unify(t1, t2) = unify(t2, t1)."""
        tv = TypeVariable("a")

        subst1 = tv.unify(Int)
        subst2 = Int.unify(tv)

        assert subst1 is not None
        assert subst2 is not None
        assert subst1.mappings == subst2.mappings

    def test_unification_transitive(self):
        """Test unification transitivity."""
        tv_a = TypeVariable("a")
        tv_b = TypeVariable("b")

        # a unifies with Int
        subst1 = tv_a.unify(Int)
        assert subst1 is not None

        # b unifies with a (after substitution)
        tv_a_sub = tv_a.apply_substitution(subst1)
        subst2 = tv_b.unify(tv_a_sub)
        assert subst2 is not None

        # Compose substitutions
        final_subst = subst2.compose(subst1)

        # Both a and b should map to Int
        assert final_subst.apply(tv_a) == Int
        assert final_subst.apply(tv_b) == Int

