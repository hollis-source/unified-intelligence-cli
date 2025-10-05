"""Tests for HTNCompiler - DSL AST to HTNNode conversion.

Tests cover compilation of all DSL entities (Literal, Composition, Product, Functor)
to HTNNode trees, preserving composition semantics and structure.
"""

import pytest
from src.dsl.adapters.htn_compiler import HTNCompiler
from src.dsl.entities.literal import Literal
from src.dsl.entities.composition import Composition
from src.dsl.entities.product import Product
from src.dsl.entities.functor import Functor
from src.entities.htn.htn_node import HTNNode


@pytest.fixture
def compiler():
    """Fixture providing HTNCompiler instance."""
    return HTNCompiler()


class TestHTNCompilerLiteral:
    """Tests for Literal compilation."""

    def test_compile_literal_string(self, compiler):
        """Test compiling string literal."""
        literal = Literal(value="build")
        htn = compiler.compile(literal)

        assert isinstance(htn, HTNNode)
        assert htn.task_id == "build"
        assert htn.description == "Execute build"
        assert htn.is_primitive()
        assert len(htn.subtasks) == 0

    def test_compile_literal_numeric(self, compiler):
        """Test compiling numeric literal."""
        literal = Literal(value=42)
        htn = compiler.compile(literal)

        assert htn.task_id == "42"
        assert htn.is_primitive()

    @pytest.mark.parametrize("value", ["task1", "task2", "agent-name", 123, True])
    def test_compile_literal_various_types(self, compiler, value):
        """Parametrized test for various literal values."""
        literal = Literal(value=value)
        htn = compiler.compile(literal)

        assert htn.task_id == str(value)
        assert htn.is_primitive()


class TestHTNCompilerComposition:
    """Tests for Composition compilation."""

    def test_compile_simple_composition(self, compiler):
        """Test compiling simple composition."""
        comp = Composition(
            left=Literal("test"),
            right=Literal("build")
        )
        htn = compiler.compile(comp)

        assert isinstance(htn, HTNNode)
        assert htn.task_id == "composition"
        assert htn.description == "Sequential composition (∘)"
        assert htn.is_compound()
        assert len(htn.subtasks) == 2

    def test_composition_preserves_right_to_left_order(self, compiler):
        """Test that composition preserves right-to-left execution order."""
        comp = Composition(
            left=Literal("last"),
            right=Literal("first")
        )
        htn = compiler.compile(comp)

        # Right executes first, then left
        assert htn.subtasks[0].task_id == "first"
        assert htn.subtasks[1].task_id == "last"

    def test_nested_composition(self, compiler):
        """Test nested composition compilation."""
        inner = Composition(
            left=Literal("C"),
            right=Literal("D")
        )
        outer = Composition(
            left=inner,
            right=Literal("E")
        )
        htn = compiler.compile(outer)

        assert htn.is_compound()
        assert len(htn.subtasks) == 2
        assert htn.subtasks[0].task_id == "E"  # Right (outer)
        assert htn.subtasks[1].task_id == "composition"  # Left (inner comp)
        assert len(htn.subtasks[1].subtasks) == 2
        assert htn.subtasks[1].subtasks[0].task_id == "D"  # Right (inner)
        assert htn.subtasks[1].subtasks[1].task_id == "C"  # Left (inner)

    def test_composition_metadata(self, compiler):
        """Test composition includes correct metadata."""
        comp = Composition(left=Literal("A"), right=Literal("B"))
        htn = compiler.compile(comp)

        assert htn.metadata["operator"] == "∘"
        assert htn.metadata["execution"] == "sequential"


class TestHTNCompilerProduct:
    """Tests for Product compilation."""

    def test_compile_simple_product(self, compiler):
        """Test compiling simple product."""
        prod = Product(
            left=Literal("frontend"),
            right=Literal("backend")
        )
        htn = compiler.compile(prod)

        assert isinstance(htn, HTNNode)
        assert htn.task_id == "product"
        assert htn.description == "Parallel product (×)"
        assert htn.is_compound()
        assert len(htn.subtasks) == 2

    def test_product_subtasks_order(self, compiler):
        """Test product subtasks are in left, right order."""
        prod = Product(
            left=Literal("left_task"),
            right=Literal("right_task")
        )
        htn = compiler.compile(prod)

        assert htn.subtasks[0].task_id == "left_task"
        assert htn.subtasks[1].task_id == "right_task"

    def test_nested_product(self, compiler):
        """Test nested product compilation."""
        inner = Product(
            left=Literal("X"),
            right=Literal("Y")
        )
        outer = Product(
            left=inner,
            right=Literal("Z")
        )
        htn = compiler.compile(outer)

        assert htn.is_compound()
        assert len(htn.subtasks) == 2
        assert htn.subtasks[0].task_id == "product"  # Left (inner)
        assert htn.subtasks[1].task_id == "Z"  # Right
        assert len(htn.subtasks[0].subtasks) == 2

    def test_product_metadata(self, compiler):
        """Test product includes correct metadata."""
        prod = Product(left=Literal("A"), right=Literal("B"))
        htn = compiler.compile(prod)

        assert htn.metadata["operator"] == "×"
        assert htn.metadata["execution"] == "parallel"


class TestHTNCompilerFunctor:
    """Tests for Functor compilation."""

    def test_compile_simple_functor(self, compiler):
        """Test compiling simple functor."""
        functor = Functor(
            name="ci_pipeline",
            expression=Literal("build")
        )
        htn = compiler.compile(functor)

        assert isinstance(htn, HTNNode)
        assert htn.task_id == "ci_pipeline"
        assert htn.description == "Functor: ci_pipeline"
        assert htn.is_compound()
        assert len(htn.subtasks) == 1
        assert htn.subtasks[0].task_id == "build"

    def test_functor_with_composition(self, compiler):
        """Test functor wrapping composition."""
        functor = Functor(
            name="deploy_pipeline",
            expression=Composition(
                left=Literal("deploy"),
                right=Literal("test")
            )
        )
        htn = compiler.compile(functor)

        assert htn.task_id == "deploy_pipeline"
        assert htn.is_compound()
        assert len(htn.subtasks) == 1
        assert htn.subtasks[0].task_id == "composition"

    def test_functor_metadata(self, compiler):
        """Test functor includes correct metadata."""
        functor = Functor(name="test", expression=Literal("task"))
        htn = compiler.compile(functor)

        assert htn.metadata["type"] == "functor"


class TestHTNCompilerMixedStructures:
    """Tests for complex mixed structures."""

    def test_composition_of_products(self, compiler):
        """Test composition containing products."""
        prod1 = Product(left=Literal("A"), right=Literal("B"))
        prod2 = Product(left=Literal("C"), right=Literal("D"))
        comp = Composition(left=prod1, right=prod2)

        htn = compiler.compile(comp)

        assert htn.task_id == "composition"
        assert len(htn.subtasks) == 2
        assert htn.subtasks[0].task_id == "product"  # Right (prod2)
        assert htn.subtasks[1].task_id == "product"  # Left (prod1)

    def test_product_of_compositions(self, compiler):
        """Test product containing compositions."""
        comp1 = Composition(left=Literal("B"), right=Literal("A"))
        comp2 = Composition(left=Literal("D"), right=Literal("C"))
        prod = Product(left=comp1, right=comp2)

        htn = compiler.compile(prod)

        assert htn.task_id == "product"
        assert len(htn.subtasks) == 2
        assert htn.subtasks[0].task_id == "composition"
        assert htn.subtasks[1].task_id == "composition"

    def test_functor_with_complex_expression(self, compiler):
        """Test functor with complex nested expression."""
        expr = Composition(
            left=Product(left=Literal("test"), right=Literal("lint")),
            right=Literal("build")
        )
        functor = Functor(name="ci", expression=expr)

        htn = compiler.compile(functor)

        assert htn.task_id == "ci"
        assert len(htn.subtasks) == 1
        comp_htn = htn.subtasks[0]
        assert comp_htn.task_id == "composition"
        assert len(comp_htn.subtasks) == 2

    def test_deeply_nested_structure(self, compiler):
        """Test deeply nested compilation."""
        # Build: (((A ∘ B) × C) ∘ D)
        inner_comp = Composition(left=Literal("A"), right=Literal("B"))
        prod = Product(left=inner_comp, right=Literal("C"))
        outer_comp = Composition(left=prod, right=Literal("D"))

        htn = compiler.compile(outer_comp)

        # Verify structure
        assert htn.task_id == "composition"
        assert htn.subtasks[0].task_id == "D"  # Right of outer
        assert htn.subtasks[1].task_id == "product"  # Left of outer
        assert len(htn.subtasks[1].subtasks) == 2

    def test_visitor_pattern_recursion(self, compiler):
        """Test visitor pattern handles deep recursion."""
        # Create deeply nested composition
        current = Literal("base")
        for i in range(10):
            current = Composition(
                left=Literal(f"step_{i}"),
                right=current
            )

        htn = compiler.compile(current)

        # Should successfully compile without errors
        assert htn.is_compound()
        # Verify depth
        depth = 0
        node = htn
        while node.is_compound() and node.subtasks:
            depth += 1
            node = node.subtasks[0]  # Follow right branch
        assert depth == 10
