import pytest
from dataclasses import dataclass
from src.dsl.entities.literal import Literal


class TestLiteral:
    """Pytest tests for Literal entity.

    These tests verify Literal correctly wraps terminal values
    (strings, task names, identifiers) in the DSL AST.
    """

    def test_creation_with_string(self):
        """Test creation of Literal with string value."""
        lit = Literal("task_name")
        assert lit is not None
        assert lit.value == "task_name"

    def test_creation_with_number(self):
        """Test creation of Literal with numeric value."""
        lit = Literal(42)
        assert lit is not None
        assert lit.value == 42

    def test_creation_with_none(self):
        """Test creation of Literal with None value."""
        lit = Literal(None)
        assert lit is not None
        assert lit.value is None

    def test_immutability(self):
        """Test that Literal is immutable (frozen dataclass)."""
        lit = Literal("immutable")

        # Attempt to mutate should raise an error
        with pytest.raises(AttributeError):
            lit.value = "new_value"

    def test_equality(self):
        """Test equality based on value."""
        lit1 = Literal("test")
        lit2 = Literal("test")
        lit3 = Literal("different")

        # Dataclass provides automatic equality
        assert lit1 == lit2
        assert lit1 != lit3

    def test_equality_different_types(self):
        """Test equality with different value types."""
        lit_str = Literal("42")
        lit_int = Literal(42)

        # Different types should not be equal
        assert lit_str != lit_int

    def test_repr(self):
        """Test repr shows value."""
        lit = Literal("task_name")
        repr_str = repr(lit)

        assert "Literal" in repr_str
        assert "task_name" in repr_str

    def test_value_accessor(self):
        """Test value accessor."""
        lit = Literal("test_value")
        assert lit.value == "test_value"

    def test_accept_visitor_pattern(self):
        """Test accept method for visitor pattern."""
        lit = Literal("test")

        # Mock visitor
        class MockVisitor:
            def visit_literal(self, node):
                return f"visited: {node.value}"

        visitor = MockVisitor()
        result = lit.accept(visitor)
        assert result == "visited: test"
