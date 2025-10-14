"""
Integration tests for DSL Type System - End-to-End Type Checking.

Tests complete type checking workflows:
- Full AST traversal with type inference
- Complex composition validation
- Error reporting and recovery
- Category theory law validation
- Real-world workflow scenarios

Clean Architecture: Integration test layer validating complete use cases.
"""

import pytest
from src.dsl.entities.literal import Literal
from src.dsl.entities.composition import Composition
from src.dsl.entities.product import Product
from src.dsl.entities.duplicate import Duplicate
from src.dsl.entities.functor import Functor
from src.dsl.entities.type_annotation import TypeAnnotation
from src.dsl.types.type_system import (
    TypeVariable,
    FunctionType,
    ProductType,
    Int,
    String,
    Bool,
    FilePath,
    List,
)
from src.dsl.types.type_inference_visitor import TypeInferenceVisitor


class TestEndToEndTypeChecking:
    """Test complete type checking workflows."""

    def test_simple_workflow_type_checking(self):
        """Test type checking a simple workflow."""
        visitor = TypeInferenceVisitor()

        # Define workflow: parse ∘ fetch
        # fetch :: FilePath → String
        # parse :: String → Int
        fetch_type = FunctionType(FilePath, String)
        parse_type = FunctionType(String, Int)

        ann1 = TypeAnnotation("fetch", fetch_type)
        ann2 = TypeAnnotation("parse", parse_type)

        ann1.accept(visitor)
        ann2.accept(visitor)

        # Create composition
        fetch = Literal("fetch")
        parse = Literal("parse")
        workflow = Composition(left=parse, right=fetch)

        # Type check
        result = workflow.accept(visitor)

        # Should infer: FilePath → Int
        assert result == FunctionType(FilePath, Int)
        assert not visitor.has_errors()

    def test_complex_workflow_with_product(self):
        """Test type checking workflow with parallel composition."""
        visitor = TypeInferenceVisitor()

        # Define workflow: (analyze × validate) ∘ (fetch × parse)
        # fetch :: FilePath → String
        # parse :: FilePath → Int
        # analyze :: String → Bool
        # validate :: Int → Bool

        ann1 = TypeAnnotation("fetch", FunctionType(FilePath, String))
        ann2 = TypeAnnotation("parse", FunctionType(FilePath, Int))
        ann3 = TypeAnnotation("analyze", FunctionType(String, Bool))
        ann4 = TypeAnnotation("validate", FunctionType(Int, Bool))

        ann1.accept(visitor)
        ann2.accept(visitor)
        ann3.accept(visitor)
        ann4.accept(visitor)

        # Create workflow
        fetch = Literal("fetch")
        parse = Literal("parse")
        analyze = Literal("analyze")
        validate = Literal("validate")

        # fetch × parse: (FilePath × FilePath) → (String × Int)
        fetch_parse = Product(left=fetch, right=parse)

        # analyze × validate: (String × Int) → (Bool × Bool)
        analyze_validate = Product(left=analyze, right=validate)

        # (analyze × validate) ∘ (fetch × parse)
        workflow = Composition(left=analyze_validate, right=fetch_parse)

        # Type check
        result = workflow.accept(visitor)

        # Should infer: (FilePath × FilePath) → (Bool × Bool)
        expected_input = ProductType(FilePath, FilePath)
        expected_output = ProductType(Bool, Bool)
        expected = FunctionType(expected_input, expected_output)

        assert result == expected
        assert not visitor.has_errors()

    def test_workflow_with_duplicate(self):
        """Test type checking workflow with duplicate operator."""
        visitor = TypeInferenceVisitor()

        # Define workflow: (process × validate) ∘ Δ
        # Δ :: a → (a × a)
        # process :: String → Bool
        # validate :: String → Int

        ann1 = TypeAnnotation("process", FunctionType(String, Bool))
        ann2 = TypeAnnotation("validate", FunctionType(String, Int))

        ann1.accept(visitor)
        ann2.accept(visitor)

        # Create workflow
        dup = Duplicate()
        process = Literal("process")
        validate = Literal("validate")

        # process × validate: (String × String) → (Bool × Int)
        process_validate = Product(left=process, right=validate)

        # (process × validate) ∘ Δ: String → (Bool × Int)
        workflow = Composition(left=process_validate, right=dup)

        # Type check
        result = workflow.accept(visitor)

        # Should infer: String → (Bool × Int)
        expected_output = ProductType(Bool, Int)
        assert isinstance(result, FunctionType)
        assert result.input_type == String
        assert result.output_type == expected_output
        assert not visitor.has_errors()

    def test_functor_definition_and_usage(self):
        """Test type checking functor definition and usage."""
        visitor = TypeInferenceVisitor()

        # Define functor: pipeline = parse ∘ fetch
        # fetch :: FilePath → String
        # parse :: String → Int

        ann1 = TypeAnnotation("fetch", FunctionType(FilePath, String))
        ann2 = TypeAnnotation("parse", FunctionType(String, Int))

        ann1.accept(visitor)
        ann2.accept(visitor)

        # Create functor
        fetch = Literal("fetch")
        parse = Literal("parse")
        comp = Composition(left=parse, right=fetch)
        functor = Functor(name="pipeline", expression=comp)

        # Visit functor
        functor.accept(visitor)

        # Use functor in another composition
        # format :: Int → String
        ann3 = TypeAnnotation("format", FunctionType(Int, String))
        ann3.accept(visitor)

        format_lit = Literal("format")
        pipeline_lit = Literal("pipeline")

        # format ∘ pipeline: FilePath → String
        workflow = Composition(left=format_lit, right=pipeline_lit)

        # Type check
        result = workflow.accept(visitor)

        assert result == FunctionType(FilePath, String)
        assert not visitor.has_errors()

    def test_polymorphic_workflow(self):
        """Test type checking polymorphic workflow."""
        visitor = TypeInferenceVisitor()

        # Define polymorphic functions
        # map :: (a → b) → List[a] → List[b]
        # filter :: (a → Bool) → List[a] → List[a]

        tv_a = TypeVariable("a")
        tv_b = TypeVariable("b")

        map_type = FunctionType(
            FunctionType(tv_a, tv_b),
            FunctionType(List(tv_a), List(tv_b))
        )

        filter_type = FunctionType(
            FunctionType(tv_a, Bool),
            FunctionType(List(tv_a), List(tv_a))
        )

        ann1 = TypeAnnotation("map", map_type)
        ann2 = TypeAnnotation("filter", filter_type)

        ann1.accept(visitor)
        ann2.accept(visitor)

        # Verify types are bound
        assert visitor.type_env.lookup("map") == map_type
        assert visitor.type_env.lookup("filter") == filter_type
        assert not visitor.has_errors()


class TestErrorReporting:
    """Test error reporting and recovery."""

    def test_type_mismatch_error_message(self):
        """Test that type mismatch produces meaningful error message."""
        visitor = TypeInferenceVisitor()

        # Define incompatible functions
        # f :: Int → String
        # g :: Bool → FilePath (Bool ≠ String)

        ann1 = TypeAnnotation("f", FunctionType(Int, String))
        ann2 = TypeAnnotation("g", FunctionType(Bool, FilePath))

        ann1.accept(visitor)
        ann2.accept(visitor)

        # Create invalid composition: g ∘ f
        f = Literal("f")
        g = Literal("g")
        comp = Composition(left=g, right=f)

        # Type check
        result = comp.accept(visitor)

        assert result is None
        assert visitor.has_errors()

        # Check error message contains useful information
        summary = visitor.get_error_summary()
        assert "Type Error" in summary or "error" in summary.lower()

    def test_missing_type_annotation_warning(self):
        """Test that missing type annotations produce warnings."""
        visitor = TypeInferenceVisitor()

        # Create literal without annotation
        lit = Literal("unknown_task")

        # Visit literal
        lit.accept(visitor)

        assert visitor.has_warnings()
        summary = visitor.get_error_summary()
        assert "unknown_task" in summary

    def test_multiple_errors_accumulation(self):
        """Test that multiple errors are accumulated."""
        visitor = TypeInferenceVisitor()

        # Define multiple incompatible compositions
        ann1 = TypeAnnotation("f1", FunctionType(Int, String))
        ann2 = TypeAnnotation("g1", FunctionType(Bool, FilePath))
        ann3 = TypeAnnotation("f2", FunctionType(String, Int))
        ann4 = TypeAnnotation("g2", FunctionType(FilePath, Bool))

        ann1.accept(visitor)
        ann2.accept(visitor)
        ann3.accept(visitor)
        ann4.accept(visitor)

        # Create two invalid compositions
        comp1 = Composition(left=Literal("g1"), right=Literal("f1"))
        comp2 = Composition(left=Literal("g2"), right=Literal("f2"))

        # Type check both
        comp1.accept(visitor)
        comp2.accept(visitor)

        # Should accumulate both errors
        assert visitor.has_errors()
        summary = visitor.get_error_summary()
        # Check for multiple errors
        assert "Errors (2)" in summary or summary.count("Type Error") >= 2 or summary.count("error") >= 2


class TestCategoryTheoryLaws:
    """Test category theory law validation through type checking."""

    def test_composition_associativity(self):
        """Test that composition is associative: (h ∘ g) ∘ f = h ∘ (g ∘ f)."""
        visitor = TypeInferenceVisitor()

        # Define functions
        ann1 = TypeAnnotation("f", FunctionType(Int, String))
        ann2 = TypeAnnotation("g", FunctionType(String, Bool))
        ann3 = TypeAnnotation("h", FunctionType(Bool, FilePath))

        ann1.accept(visitor)
        ann2.accept(visitor)
        ann3.accept(visitor)

        # Create (h ∘ g) ∘ f
        f = Literal("f")
        g = Literal("g")
        h = Literal("h")

        hg = Composition(left=h, right=g)
        hgf_left = Composition(left=hg, right=f)

        # Create h ∘ (g ∘ f)
        gf = Composition(left=g, right=f)
        hgf_right = Composition(left=h, right=gf)

        # Type check both
        result_left = hgf_left.accept(visitor)
        result_right = hgf_right.accept(visitor)

        # Both should have same type: Int → FilePath
        assert result_left == FunctionType(Int, FilePath)
        assert result_right == FunctionType(Int, FilePath)
        assert result_left == result_right
        assert not visitor.has_errors()

    def test_identity_composition(self):
        """Test identity composition: id ∘ f = f = f ∘ id."""
        visitor = TypeInferenceVisitor()

        # Define identity and function
        tv_a = TypeVariable("a")
        identity_type = FunctionType(tv_a, tv_a)
        func_type = FunctionType(Int, String)

        ann1 = TypeAnnotation("id", identity_type)
        ann2 = TypeAnnotation("f", func_type)

        ann1.accept(visitor)
        ann2.accept(visitor)

        # Create id ∘ f
        id_lit = Literal("id")
        f_lit = Literal("f")

        id_f = Composition(left=id_lit, right=f_lit)
        f_id = Composition(left=f_lit, right=id_lit)

        # Type check
        result_left = id_f.accept(visitor)
        result_right = f_id.accept(visitor)

        # Both should preserve function type (after instantiation)
        assert isinstance(result_left, FunctionType)
        assert isinstance(result_right, FunctionType)

    def test_product_bifunctor_law(self):
        """Test product bifunctor law: (f × g) ∘ (h × k) = (f ∘ h) × (g ∘ k)."""
        visitor = TypeInferenceVisitor()

        # Define functions
        ann1 = TypeAnnotation("f", FunctionType(String, Bool))
        ann2 = TypeAnnotation("g", FunctionType(Int, FilePath))
        ann3 = TypeAnnotation("h", FunctionType(FilePath, String))
        ann4 = TypeAnnotation("k", FunctionType(Bool, Int))

        ann1.accept(visitor)
        ann2.accept(visitor)
        ann3.accept(visitor)
        ann4.accept(visitor)

        # Create (f × g) ∘ (h × k)
        f = Literal("f")
        g = Literal("g")
        h = Literal("h")
        k = Literal("k")

        fg = Product(left=f, right=g)
        hk = Product(left=h, right=k)
        left_side = Composition(left=fg, right=hk)

        # Create (f ∘ h) × (g ∘ k)
        fh = Composition(left=f, right=h)
        gk = Composition(left=g, right=k)
        right_side = Product(left=fh, right=gk)

        # Type check both
        result_left = left_side.accept(visitor)
        result_right = right_side.accept(visitor)

        # Both should have same type: (FilePath × Bool) → (Bool × FilePath)
        expected_input = ProductType(FilePath, Bool)
        expected_output = ProductType(Bool, FilePath)
        expected = FunctionType(expected_input, expected_output)

        assert result_left == expected
        assert result_right == expected
        assert not visitor.has_errors()

