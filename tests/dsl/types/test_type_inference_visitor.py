"""
Unit tests for DSL Type Inference Visitor - AST Traversal and Type Checking.

Tests visitor pattern for type inference:
- Literal node type lookup
- Composition node validation
- Product node validation
- Duplicate node polymorphic type
- Functor node type binding
- Type annotation processing
- Error accumulation and reporting

Clean Architecture: Test layer validating visitor pattern contracts.
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
)
from src.dsl.types.type_inference_visitor import TypeInferenceVisitor


class TestVisitLiteral:
    """Test visiting literal nodes."""

    def test_visit_literal_with_type_annotation(self):
        """Test visiting literal with existing type annotation."""
        visitor = TypeInferenceVisitor()

        # Add type annotation
        func_type = FunctionType(Int, String)
        visitor.type_env.bind("process", func_type)

        # Visit literal
        literal = Literal("process")
        result = literal.accept(visitor)

        assert result == func_type
        assert not visitor.has_errors()

    def test_visit_literal_without_type_annotation(self):
        """Test visiting literal without type annotation generates warning."""
        visitor = TypeInferenceVisitor()

        # Visit literal without annotation
        literal = Literal("unknown_task")
        result = literal.accept(visitor)

        assert result is None
        assert visitor.has_warnings()
        assert "No type annotation for 'unknown_task'" in visitor.get_error_summary()

    def test_visit_multiple_literals(self):
        """Test visiting multiple literals."""
        visitor = TypeInferenceVisitor()

        # Add type annotations
        visitor.type_env.bind("fetch", FunctionType(FilePath, String))
        visitor.type_env.bind("parse", FunctionType(String, Int))

        # Visit literals
        fetch_lit = Literal("fetch")
        parse_lit = Literal("parse")

        fetch_type = fetch_lit.accept(visitor)
        parse_type = parse_lit.accept(visitor)

        assert fetch_type == FunctionType(FilePath, String)
        assert parse_type == FunctionType(String, Int)


class TestVisitComposition:
    """Test visiting composition nodes."""

    def test_visit_composition_valid(self):
        """Test visiting valid composition."""
        visitor = TypeInferenceVisitor()

        # Add type annotations
        visitor.type_env.bind("f", FunctionType(Int, String))
        visitor.type_env.bind("g", FunctionType(String, Bool))

        # Create composition: g ∘ f
        f = Literal("f")
        g = Literal("g")
        comp = Composition(left=g, right=f)

        # Visit composition
        result = comp.accept(visitor)

        # Should infer: Int → Bool
        assert result == FunctionType(Int, Bool)
        assert not visitor.has_errors()

    def test_visit_composition_type_mismatch(self):
        """Test visiting composition with type mismatch."""
        visitor = TypeInferenceVisitor()

        # Add type annotations with mismatch
        visitor.type_env.bind("f", FunctionType(Int, String))
        visitor.type_env.bind("g", FunctionType(Bool, FilePath))  # Bool ≠ String

        # Create composition: g ∘ f
        f = Literal("f")
        g = Literal("g")
        comp = Composition(left=g, right=f)

        # Visit composition
        result = comp.accept(visitor)

        assert result is None
        assert visitor.has_errors()
        summary = visitor.get_error_summary()
        assert "Type Error" in summary or "Type mismatch" in summary.lower()

    def test_visit_composition_missing_left_type(self):
        """Test visiting composition with missing left type."""
        visitor = TypeInferenceVisitor()

        # Only annotate right side
        visitor.type_env.bind("f", FunctionType(Int, String))

        # Create composition: g ∘ f (g has no type)
        f = Literal("f")
        g = Literal("unknown")
        comp = Composition(left=g, right=f)

        # Visit composition
        result = comp.accept(visitor)

        assert result is None
        assert visitor.has_errors()

    def test_visit_composition_missing_right_type(self):
        """Test visiting composition with missing right type."""
        visitor = TypeInferenceVisitor()

        # Only annotate left side
        visitor.type_env.bind("g", FunctionType(String, Bool))

        # Create composition: g ∘ f (f has no type)
        f = Literal("unknown")
        g = Literal("g")
        comp = Composition(left=g, right=f)

        # Visit composition
        result = comp.accept(visitor)

        assert result is None
        assert visitor.has_errors()

    def test_visit_composition_chain(self):
        """Test visiting chained compositions."""
        visitor = TypeInferenceVisitor()

        # Add type annotations
        visitor.type_env.bind("f", FunctionType(Int, String))
        visitor.type_env.bind("g", FunctionType(String, Bool))
        visitor.type_env.bind("h", FunctionType(Bool, FilePath))

        # Create chain: h ∘ (g ∘ f)
        f = Literal("f")
        g = Literal("g")
        h = Literal("h")

        gf = Composition(left=g, right=f)
        hgf = Composition(left=h, right=gf)

        # Visit composition
        result = hgf.accept(visitor)

        # Should infer: Int → FilePath
        assert result == FunctionType(Int, FilePath)
        assert not visitor.has_errors()

    def test_visit_composition_polymorphic(self):
        """Test visiting composition with polymorphic types."""
        visitor = TypeInferenceVisitor()

        # Add polymorphic type annotations
        tv_a = TypeVariable("a")
        tv_b = TypeVariable("b")
        visitor.type_env.bind("f", FunctionType(tv_a, tv_b))
        visitor.type_env.bind("g", FunctionType(tv_b, Int))

        # Create composition: g ∘ f
        f = Literal("f")
        g = Literal("g")
        comp = Composition(left=g, right=f)

        # Visit composition
        result = comp.accept(visitor)

        # Should infer: a → Int
        assert isinstance(result, FunctionType)
        assert result.output_type == Int


class TestVisitProduct:
    """Test visiting product nodes."""

    def test_visit_product_valid(self):
        """Test visiting valid product."""
        visitor = TypeInferenceVisitor()

        # Add type annotations
        visitor.type_env.bind("f", FunctionType(Int, String))
        visitor.type_env.bind("g", FunctionType(Bool, FilePath))

        # Create product: f × g
        f = Literal("f")
        g = Literal("g")
        prod = Product(left=f, right=g)

        # Visit product
        result = prod.accept(visitor)

        # Should infer: (Int × Bool) → (String × FilePath)
        expected_input = ProductType(Int, Bool)
        expected_output = ProductType(String, FilePath)
        expected = FunctionType(expected_input, expected_output)

        assert result == expected
        assert not visitor.has_errors()

    def test_visit_product_missing_left_type(self):
        """Test visiting product with missing left type."""
        visitor = TypeInferenceVisitor()

        # Only annotate right side
        visitor.type_env.bind("g", FunctionType(Bool, FilePath))

        # Create product: f × g (f has no type)
        f = Literal("unknown")
        g = Literal("g")
        prod = Product(left=f, right=g)

        # Visit product
        result = prod.accept(visitor)

        assert result is None
        assert visitor.has_errors()

    def test_visit_product_missing_right_type(self):
        """Test visiting product with missing right type."""
        visitor = TypeInferenceVisitor()

        # Only annotate left side
        visitor.type_env.bind("f", FunctionType(Int, String))

        # Create product: f × g (g has no type)
        f = Literal("f")
        g = Literal("unknown")
        prod = Product(left=f, right=g)

        # Visit product
        result = prod.accept(visitor)

        assert result is None
        assert visitor.has_errors()

    def test_visit_product_polymorphic(self):
        """Test visiting product with polymorphic types."""
        visitor = TypeInferenceVisitor()

        # Add polymorphic type annotations
        tv_a = TypeVariable("a")
        tv_b = TypeVariable("b")
        visitor.type_env.bind("f", FunctionType(tv_a, tv_b))
        visitor.type_env.bind("g", FunctionType(Int, String))

        # Create product: f × g
        f = Literal("f")
        g = Literal("g")
        prod = Product(left=f, right=g)

        # Visit product
        result = prod.accept(visitor)

        # Should infer: (a × Int) → (b × String)
        assert isinstance(result, FunctionType)
        assert isinstance(result.input_type, ProductType)
        assert isinstance(result.output_type, ProductType)


class TestVisitDuplicate:
    """Test visiting duplicate nodes."""

    def test_visit_duplicate(self):
        """Test visiting duplicate node returns polymorphic type."""
        visitor = TypeInferenceVisitor()

        # Create duplicate node
        dup = Duplicate()

        # Visit duplicate
        result = dup.accept(visitor)

        # Should return: a → (a × a)
        assert isinstance(result, FunctionType)
        assert isinstance(result.input_type, TypeVariable)
        assert isinstance(result.output_type, ProductType)

        # Both sides of product should be same type variable
        assert result.output_type.left == result.input_type
        assert result.output_type.right == result.input_type


class TestVisitFunctor:
    """Test visiting functor nodes."""

    def test_visit_functor_simple(self):
        """Test visiting functor definition."""
        visitor = TypeInferenceVisitor()

        # Add type annotation for expression
        visitor.type_env.bind("task", FunctionType(Int, String))

        # Create functor: workflow = task
        expr = Literal("task")
        functor = Functor(name="workflow", expression=expr)

        # Visit functor
        result = functor.accept(visitor)

        # Should infer type and bind to name
        assert result == FunctionType(Int, String)
        assert visitor.type_env.lookup("workflow") == FunctionType(Int, String)

    def test_visit_functor_composition(self):
        """Test visiting functor with composition expression."""
        visitor = TypeInferenceVisitor()

        # Add type annotations
        visitor.type_env.bind("f", FunctionType(Int, String))
        visitor.type_env.bind("g", FunctionType(String, Bool))

        # Create functor: pipeline = g ∘ f
        f = Literal("f")
        g = Literal("g")
        comp = Composition(left=g, right=f)
        functor = Functor(name="pipeline", expression=comp)

        # Visit functor
        result = functor.accept(visitor)

        # Should infer Int → Bool and bind to pipeline
        assert result == FunctionType(Int, Bool)
        assert visitor.type_env.lookup("pipeline") == FunctionType(Int, Bool)


class TestVisitTypeAnnotation:
    """Test visiting type annotation nodes."""

    def test_visit_type_annotation(self):
        """Test visiting type annotation."""
        visitor = TypeInferenceVisitor()

        # Create type annotation: task :: Int → String
        func_type = FunctionType(Int, String)
        annotation = TypeAnnotation(name="task", type_signature=func_type)

        # Visit annotation
        result = annotation.accept(visitor)

        # Should bind type to name
        assert result == func_type
        assert visitor.type_env.lookup("task") == func_type

    def test_visit_multiple_type_annotations(self):
        """Test visiting multiple type annotations."""
        visitor = TypeInferenceVisitor()

        # Create multiple annotations
        ann1 = TypeAnnotation("f", FunctionType(Int, String))
        ann2 = TypeAnnotation("g", FunctionType(String, Bool))

        # Visit annotations
        ann1.accept(visitor)
        ann2.accept(visitor)

        # Should bind both types
        assert visitor.type_env.lookup("f") == FunctionType(Int, String)
        assert visitor.type_env.lookup("g") == FunctionType(String, Bool)


class TestErrorAccumulation:
    """Test error accumulation and reporting."""

    def test_error_accumulation_multiple_errors(self):
        """Test accumulating multiple type errors."""
        visitor = TypeInferenceVisitor()

        # Add type annotations with mismatches
        visitor.type_env.bind("f", FunctionType(Int, String))
        visitor.type_env.bind("g", FunctionType(Bool, FilePath))  # Mismatch
        visitor.type_env.bind("h", FunctionType(Int, Bool))  # Another mismatch

        # Create compositions with errors
        f = Literal("f")
        g = Literal("g")
        h = Literal("h")

        comp1 = Composition(left=g, right=f)  # Error: String ≠ Bool
        comp2 = Composition(left=h, right=g)  # Error: FilePath ≠ Int

        # Visit both compositions
        comp1.accept(visitor)
        comp2.accept(visitor)

        # Should accumulate both errors
        assert visitor.has_errors()
        summary = visitor.get_error_summary()
        assert "Errors (2)" in summary or summary.count("error") >= 2

    def test_warning_accumulation(self):
        """Test accumulating warnings."""
        visitor = TypeInferenceVisitor()

        # Visit literals without annotations
        lit1 = Literal("unknown1")
        lit2 = Literal("unknown2")

        lit1.accept(visitor)
        lit2.accept(visitor)

        # Should accumulate warnings
        assert visitor.has_warnings()
        summary = visitor.get_error_summary()
        assert "Warnings" in summary or "warning" in summary.lower()

    def test_get_type_environment(self):
        """Test retrieving type environment."""
        visitor = TypeInferenceVisitor()

        # Add type annotations
        visitor.type_env.bind("f", FunctionType(Int, String))

        # Get environment
        env = visitor.get_type_environment()

        assert env.lookup("f") == FunctionType(Int, String)

