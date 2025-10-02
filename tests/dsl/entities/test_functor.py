import pytest
from dataclasses import dataclass
from src.dsl.entities.functor import Functor
from src.dsl.entities.ast_node import ASTNode


# Mock ASTNode for testing
@dataclass(frozen=True)
class MockASTNode(ASTNode):
    """Mock ASTNode implementation for testing."""
    name: str = "mock"

    def accept(self, visitor):
        """Mock accept implementation."""
        return visitor.visit_mock(self)


class TestFunctor:
    """Pytest tests for Functor entity.

    These tests verify Functor correctly represents reusable workflow mappings
    following CT semantics (structure-preserving transformations).
    """

    def test_creation(self):
        """Test creation of Functor instance."""
        expr = MockASTNode("workflow")
        functor = Functor(name="ci_pipeline", expression=expr)

        assert functor is not None
        assert functor.name == "ci_pipeline"
        assert functor.expression == expr

    def test_immutability(self):
        """Test that Functor is immutable (frozen dataclass)."""
        expr = MockASTNode("workflow")
        functor = Functor(name="pipeline", expression=expr)

        # Attempt to mutate should raise an error
        with pytest.raises(AttributeError):
            functor.name = "new_name"

        with pytest.raises(AttributeError):
            functor.expression = MockASTNode("new")

    def test_name_accessor(self):
        """Test name accessor."""
        expr = MockASTNode("workflow")
        functor = Functor(name="test_functor", expression=expr)

        assert functor.name == "test_functor"

    def test_expression_accessor(self):
        """Test expression accessor."""
        expr = MockASTNode("workflow")
        functor = Functor(name="pipeline", expression=expr)

        assert functor.expression == expr

    def test_type_validation_expression(self):
        """Test type validation for expression (must be ASTNode)."""
        with pytest.raises(TypeError, match="expression must be an instance of ASTNode"):
            Functor(name="pipeline", expression="not_astnode")

    def test_type_validation_name(self):
        """Test type validation for name (must be str)."""
        with pytest.raises(TypeError, match="name must be a string"):
            Functor(name=123, expression=MockASTNode("workflow"))

    def test_creation_with_invalid_types(self):
        """Test creation fails with invalid types."""
        with pytest.raises(TypeError):
            Functor(name=None, expression="invalid")

    def test_equality(self):
        """Test equality based on name and expression."""
        expr1 = MockASTNode("workflow")
        functor1 = Functor(name="pipeline", expression=expr1)

        expr2 = MockASTNode("workflow")
        functor2 = Functor(name="pipeline", expression=expr2)

        # Dataclass provides automatic equality
        assert functor1 == functor2
        assert functor1 != Functor(name="different", expression=expr1)

    def test_repr(self):
        """Test repr shows name and expression."""
        expr = MockASTNode("workflow")
        functor = Functor(name="ci_pipeline", expression=expr)

        repr_str = repr(functor)
        assert "Functor" in repr_str
        assert "ci_pipeline" in repr_str
        assert "workflow" in repr_str

    def test_accept_visitor_pattern(self):
        """Test accept method for visitor pattern."""
        expr = MockASTNode("workflow")
        functor = Functor(name="pipeline", expression=expr)

        # Mock visitor
        class MockVisitor:
            def visit_functor(self, node):
                return f"visited functor: {node.name}"

        visitor = MockVisitor()
        result = functor.accept(visitor)
        assert result == "visited functor: pipeline"
