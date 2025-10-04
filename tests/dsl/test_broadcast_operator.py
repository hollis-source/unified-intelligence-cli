"""Unit Tests for Broadcast Operator `**`.

Tests the N-ary broadcast operator desugaring and chaining.

Category Theory: Tests diagonal functor syntactic sugar
Clean Architecture: Test layer
SOLID: SRP - only tests broadcast operator parsing and desugaring

Sprint: N-ary broadcast operator implementation
"""

import pytest
from src.dsl.adapters.parser import Parser
from src.dsl.entities.composition import Composition
from src.dsl.entities.product import Product
from src.dsl.entities.duplicate import Duplicate
from src.dsl.entities.literal import Literal


class TestBroadcastOperator:
    """Test broadcast operator ** desugaring."""

    def setup_method(self):
        """Setup parser for each test."""
        self.parser = Parser()

    def test_binary_broadcast(self):
        """Test binary broadcast: f ** g desugars to (f × g) ∘ duplicate"""
        ast = self.parser.parse("f ** g")

        # Should desugar to: (f × g) ∘ duplicate
        assert isinstance(ast, Composition)
        assert isinstance(ast.left, Product)
        assert isinstance(ast.right, Duplicate)

        # Verify product contains f and g
        assert isinstance(ast.left.left, Literal)
        assert ast.left.left.value == "f"
        assert isinstance(ast.left.right, Literal)
        assert ast.left.right.value == "g"

    def test_ternary_broadcast(self):
        """Test ternary broadcast: f ** g ** h desugars to ((f × g) × h) ∘ duplicate"""
        ast = self.parser.parse("f ** g ** h")

        # Should desugar to: ((f × g) × h) ∘ duplicate
        assert isinstance(ast, Composition)
        assert isinstance(ast.left, Product)
        assert isinstance(ast.right, Duplicate)

        # Verify nested product structure: (left: (f × g), right: h)
        outer_product = ast.left
        assert isinstance(outer_product.left, Product)  # Inner product (f × g)
        assert isinstance(outer_product.right, Literal)
        assert outer_product.right.value == "h"

        # Verify inner product: (f × g)
        inner_product = outer_product.left
        assert isinstance(inner_product.left, Literal)
        assert inner_product.left.value == "f"
        assert isinstance(inner_product.right, Literal)
        assert inner_product.right.value == "g"

    def test_quaternary_broadcast(self):
        """Test quaternary broadcast: f ** g ** h ** k desugars to (((f × g) × h) × k) ∘ duplicate"""
        ast = self.parser.parse("f ** g ** h ** k")

        # Should desugar to: (((f × g) × h) × k) ∘ duplicate
        assert isinstance(ast, Composition)
        assert isinstance(ast.left, Product)
        assert isinstance(ast.right, Duplicate)

        # Verify outermost product: (...) × k
        p3 = ast.left
        assert isinstance(p3.left, Product)  # ((f × g) × h)
        assert isinstance(p3.right, Literal)
        assert p3.right.value == "k"

        # Verify middle product: (f × g) × h
        p2 = p3.left
        assert isinstance(p2.left, Product)  # (f × g)
        assert isinstance(p2.right, Literal)
        assert p2.right.value == "h"

        # Verify innermost product: f × g
        p1 = p2.left
        assert isinstance(p1.left, Literal)
        assert p1.left.value == "f"
        assert isinstance(p1.right, Literal)
        assert p1.right.value == "g"

    def test_broadcast_in_composition(self):
        """Test broadcast as part of larger composition: (f ** g) ∘ h"""
        ast = self.parser.parse("(f ** g) o h")

        # Should parse as: composition(broadcast(f, g), h)
        # broadcast(f, g) = (f × g) ∘ duplicate
        # Final: ((f × g) ∘ duplicate) ∘ h

        assert isinstance(ast, Composition)
        # Left side should be the broadcast composition
        assert isinstance(ast.left, Composition)
        assert isinstance(ast.left.left, Product)
        assert isinstance(ast.left.right, Duplicate)
        # Right side should be h
        assert isinstance(ast.right, Literal)
        assert ast.right.value == "h"

    def test_broadcast_vs_product(self):
        """Test that ** and × are different operators"""
        broadcast_ast = self.parser.parse("f ** g")
        product_ast = self.parser.parse("f * g")

        # Broadcast should have duplicate composition
        assert isinstance(broadcast_ast, Composition)
        assert isinstance(broadcast_ast.right, Duplicate)

        # Product should just be a product
        assert isinstance(product_ast, Product)
        assert not isinstance(product_ast, Composition)
