import pytest
from dataclasses import dataclass
from src.dsl.entities.ast_node import ASTNode


# Mock concrete ASTNode for testing
@dataclass(frozen=True)
class MockASTNode(ASTNode):
    """Mock ASTNode implementation for testing."""
    value: str = "test"

    def accept(self, visitor):
        """Mock accept implementation."""
        return visitor.visit_mock(self)


class TestASTNode:
    """Comprehensive pytest tests for ASTNode abstract base class.

    These tests follow TDD: they verify ASTNode provides proper abstraction
    and subclasses inherit frozen dataclass behavior.
    """

    def test_ast_node_is_abstract_base_class(self):
        """Test that ASTNode is an abstract base class and cannot be instantiated directly."""
        with pytest.raises(TypeError, match="Can't instantiate abstract class ASTNode"):
            ASTNode()  # This should raise TypeError due to abstract methods

    def test_repr_method(self):
        """Test the __repr__ method for string representation."""
        node = MockASTNode("test_value")
        # Dataclass provides automatic repr
        assert "MockASTNode" in repr(node)
        assert "test_value" in repr(node)

    def test_equality(self):
        """Test equality (__eq__) between ASTNode instances."""
        node1 = MockASTNode("test")
        node2 = MockASTNode("test")
        node3 = MockASTNode("different")

        # Frozen dataclass provides automatic equality
        assert node1 == node2
        assert node1 != node3
        assert node1 != "not_an_ast_node"

    def test_immutability(self):
        """Test that ASTNode instances are immutable (frozen dataclass behavior)."""
        node = MockASTNode("immutable_value")

        # Frozen dataclass prevents mutation
        with pytest.raises(AttributeError):
            node.value = "new_value"

    def test_equality_with_different_types(self):
        """Test equality with non-ASTNode objects."""
        node = MockASTNode("test")
        assert node != 123
        assert node != None
        assert node != {}

    def test_repr_consistency(self):
        """Test that repr is consistent."""
        node = MockASTNode("test")
        repr_str = repr(node)
        assert isinstance(repr_str, str)
        assert "MockASTNode" in repr_str
