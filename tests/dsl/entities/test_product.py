import pytest
from dataclasses import dataclass
from src.dsl.entities.product import Product
from src.dsl.entities.ast_node import ASTNode


# Mock ASTNode for testing
@dataclass(frozen=True)
class MockASTNode(ASTNode):
    """Mock ASTNode implementation for testing."""
    name: str = "mock"

    def accept(self, visitor):
        """Mock accept implementation."""
        return visitor.visit_mock(self)


class TestProduct:
    """Pytest tests for Product entity.

    These tests verify Product correctly represents parallel execution (×)
    following CT semantics (categorical product with projections).
    """

    def test_creation(self):
        """Test creation of Product instance."""
        left = MockASTNode("task_a")
        right = MockASTNode("task_b")

        product = Product(left=left, right=right)
        assert product is not None

    def test_immutability(self):
        """Test that Product is immutable (frozen dataclass)."""
        left = MockASTNode("task_a")
        right = MockASTNode("task_b")

        product = Product(left=left, right=right)

        # Attempt to mutate should raise an error
        with pytest.raises(AttributeError):
            product.left = MockASTNode("new")

    def test_repr(self):
        """Test that repr shows '(left × right)' format."""
        left = MockASTNode("task_a")
        right = MockASTNode("task_b")

        product = Product(left=left, right=right)
        # Expected repr format with × symbol
        assert "×" in repr(product)
        assert "task_a" in repr(product)
        assert "task_b" in repr(product)

    def test_left_accessor(self):
        """Test left accessor."""
        left = MockASTNode("task_a")
        right = MockASTNode("task_b")

        product = Product(left=left, right=right)
        assert product.left == left

    def test_right_accessor(self):
        """Test right accessor."""
        left = MockASTNode("task_a")
        right = MockASTNode("task_b")

        product = Product(left=left, right=right)
        assert product.right == right

    def test_type_validation_left(self):
        """Test type validation for left (must be ASTNode)."""
        with pytest.raises(TypeError, match="left must be an instance of ASTNode"):
            Product(left="not_astnode", right=MockASTNode("task_b"))

    def test_type_validation_right(self):
        """Test type validation for right (must be ASTNode)."""
        with pytest.raises(TypeError, match="right must be an instance of ASTNode"):
            Product(left=MockASTNode("task_a"), right="not_astnode")

    def test_creation_with_invalid_types(self):
        """Test creation fails with invalid types."""
        with pytest.raises(TypeError):
            Product(left=123, right="invalid")

    def test_equality(self):
        """Test equality based on left and right."""
        left1 = MockASTNode("task_a")
        right1 = MockASTNode("task_b")
        product1 = Product(left=left1, right=right1)

        left2 = MockASTNode("task_a")
        right2 = MockASTNode("task_b")
        product2 = Product(left=left2, right=right2)

        # Dataclass provides automatic equality
        assert product1 == product2
        assert product1 != Product(left=MockASTNode("different"), right=right1)

    def test_accept_visitor_pattern(self):
        """Test accept method for visitor pattern."""
        left = MockASTNode("task_a")
        right = MockASTNode("task_b")
        product = Product(left=left, right=right)

        # Mock visitor
        class MockVisitor:
            def visit_product(self, node):
                return f"visited product: {node.left.name} × {node.right.name}"

        visitor = MockVisitor()
        result = product.accept(visitor)
        assert result == "visited product: task_a × task_b"
