import pytest
from dataclasses import dataclass
from src.dsl.entities.composition import Composition
from src.dsl.entities.ast_node import ASTNode


# Mock ASTNode for testing
@dataclass(frozen=True)
class MockASTNode(ASTNode):
    """Mock ASTNode implementation for testing."""
    name: str = "mock"

    def accept(self, visitor):
        """Mock accept implementation."""
        return visitor.visit_mock(self)


class TestComposition:
    """Pytest tests for Composition entity.

    These tests verify Composition correctly composes two ASTNode instances
    following CT semantics (right-to-left composition).
    """

    def test_creation(self):
        """Test creation of Composition instance."""
        left = MockASTNode("left")
        right = MockASTNode("right")

        comp = Composition(left=left, right=right)
        assert comp is not None

    def test_immutability(self):
        """Test that Composition is immutable (frozen dataclass)."""
        left = MockASTNode("left")
        right = MockASTNode("right")

        comp = Composition(left=left, right=right)

        # Attempt to mutate should raise an error
        with pytest.raises(AttributeError):
            comp.left = MockASTNode("new")

    def test_repr(self):
        """Test that repr shows '(left ∘ right)' format."""
        left = MockASTNode("left")
        right = MockASTNode("right")

        comp = Composition(left=left, right=right)
        # Expected repr format
        assert "∘" in repr(comp)
        assert "left" in repr(comp)
        assert "right" in repr(comp)

    def test_left_accessor(self):
        """Test left accessor."""
        left = MockASTNode("left")
        right = MockASTNode("right")

        comp = Composition(left=left, right=right)
        assert comp.left == left

    def test_right_accessor(self):
        """Test right accessor."""
        left = MockASTNode("left")
        right = MockASTNode("right")

        comp = Composition(left=left, right=right)
        assert comp.right == right

    def test_type_validation_left(self):
        """Test type validation for left (must be ASTNode)."""
        with pytest.raises(TypeError, match="left must be an instance of ASTNode"):
            Composition(left="not_astnode", right=MockASTNode("right"))

    def test_type_validation_right(self):
        """Test type validation for right (must be ASTNode)."""
        with pytest.raises(TypeError, match="right must be an instance of ASTNode"):
            Composition(left=MockASTNode("left"), right="not_astnode")

    def test_creation_with_invalid_types(self):
        """Test creation fails with invalid types."""
        with pytest.raises(TypeError):
            Composition(left=123, right="invalid")

    def test_equality(self):
        """Test equality based on left and right."""
        left1 = MockASTNode("left")
        right1 = MockASTNode("right")
        comp1 = Composition(left=left1, right=right1)

        left2 = MockASTNode("left")
        right2 = MockASTNode("right")
        comp2 = Composition(left=left2, right=right2)

        # Dataclass provides automatic equality
        assert comp1 == comp2
        assert comp1 != Composition(left=MockASTNode("different"), right=right1)
