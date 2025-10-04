"""DSL Parser using Lark.

Clean Architecture: Adapter layer (external Lark dependency).
SOLID: SRP - only parses DSL text to AST, DIP - depends on entity abstractions.

Story: Story 1, Phase 2 - Extended with type annotation parsing
"""

import os
from pathlib import Path
from lark import Lark, Transformer, Token
from src.dsl.entities.literal import Literal
from src.dsl.entities.composition import Composition
from src.dsl.entities.product import Product
from src.dsl.entities.duplicate import Duplicate
from src.dsl.entities.functor import Functor
from src.dsl.entities.type_annotation import TypeAnnotation
from src.dsl.types.type_system import (
    Type,
    TypeVariable,
    MonomorphicType,
    FunctionType,
    ProductType,
)


class ASTTransformer(Transformer):
    """
    Transforms Lark parse tree to CT DSL AST.

    Implements visitor pattern for each grammar rule, converting
    Lark tree nodes to immutable entity dataclasses.

    Clean Code principles:
    - Small, focused transformation methods
    - No side effects
    - Clear naming matching grammar rules
    """

    def _ensure_ast_node(self, item):
        """Ensure item is an ASTNode, converting Tokens if needed."""
        if isinstance(item, Token):
            # Handle raw tokens (identifiers)
            if item.type == 'IDENTIFIER':
                return Literal(item.value)
            elif item.type == 'LITERAL':
                # Remove quotes from string literals
                value = item.value.strip('"').strip("'")
                return Literal(value)
            else:
                # Fallback: convert token value to Literal
                return Literal(item.value)
        # Already transformed to ASTNode
        return item

    def literal(self, items):
        """Transform literal terminal to Literal entity."""
        # Remove quotes from string literals
        value = items[0].value.strip('"').strip("'")
        return Literal(value)

    def identifier(self, items):
        """Transform identifier to Literal entity (task/agent names)."""
        value = items[0].value
        return Literal(value)

    def composition(self, items):
        """Transform composition expression to Composition entity."""
        # Lark parses binary operators as: [left, operator, right]
        # We skip the operator (items[1]) and use left and right
        left = self._ensure_ast_node(items[0])
        right = self._ensure_ast_node(items[2]) if len(items) > 2 else self._ensure_ast_node(items[1])
        return Composition(left=left, right=right)

    def product_expr(self, items):
        """Transform product expression to Product entity."""
        # Lark parses binary operators as: [left, operator, right]
        left = self._ensure_ast_node(items[0])
        right = self._ensure_ast_node(items[2]) if len(items) > 2 else self._ensure_ast_node(items[1])
        return Product(left=left, right=right)

    def broadcast_expr(self, items):
        """Transform broadcast expression to desugared form.

        Desugaring rules:
        - f ** g           → (f × g) ∘ duplicate
        - f ** g ** h      → ((f × g) × h) ∘ duplicate  (left-associative chaining)
        - prev_broadcast ** h → Extract product from prev, extend it

        This provides syntactic sugar for parallel fan-out execution.
        """
        left = self._ensure_ast_node(items[0])
        right = self._ensure_ast_node(items[2]) if len(items) > 2 else self._ensure_ast_node(items[1])

        # Check if left is already a desugared broadcast: (Product) ∘ duplicate
        # If so, extract the product and extend it instead of nesting
        if isinstance(left, Composition):
            # Check if it's a broadcast pattern: product ∘ duplicate
            if isinstance(left.right, Duplicate) and isinstance(left.left, Product):
                # Extract the product and extend it: (prev_product × right) ∘ duplicate
                extended_product = Product(left=left.left, right=right)
                return Composition(left=extended_product, right=Duplicate())

        # Simple case: build product and compose with duplicate
        product = Product(left=left, right=right)
        return Composition(left=product, right=Duplicate())

    def duplicate_expr(self, items):
        """Transform duplicate expression to Duplicate entity."""
        # Duplicate is a nullary operator (no arguments)
        return Duplicate()

    def bind_expr(self, items):
        """Transform bind expression (currently returns composition for simplicity)."""
        # Lark parses binary operators as: [left, operator, right]
        # TODO: Implement proper Bind AST node when needed
        # For now, treat as composition
        left = self._ensure_ast_node(items[0])
        right = self._ensure_ast_node(items[2]) if len(items) > 2 else self._ensure_ast_node(items[1])
        return Composition(left=left, right=right)

    def definition(self, items):
        """
        Transform functor definition to Functor entity.

        Supports both:
        - functor workflow = expr  (explicit, 3 items)
        - workflow = expr          (implicit, 2 items)
        """
        # Handle optional "functor" keyword
        if len(items) == 3:
            # Has "functor" keyword: ["functor", name, expr]
            name = items[1].value if isinstance(items[1], Token) else items[1]
            expression = self._ensure_ast_node(items[2])
        else:
            # No "functor" keyword: [name, expr]
            name = items[0].value if isinstance(items[0], Token) else items[0]
            expression = self._ensure_ast_node(items[1])

        return Functor(name=name, expression=expression)

    def program(self, items):
        """Transform program (list of statements)."""
        # Return list of all statements for programs with multiple statements
        if len(items) == 0:
            return None  # Empty program
        elif len(items) == 1:
            return items[0]  # Single statement - return directly
        else:
            return items  # Multiple statements - return as list

    # Type annotation transformers (Phase 2)

    def type_annotation(self, items):
        """Transform type annotation: name :: Type"""
        # Grammar: IDENTIFIER TYPE_ANNOTATION type_expr
        # items[0] = IDENTIFIER, items[1] = "::", items[2] = type_expr
        name = items[0].value if isinstance(items[0], Token) else items[0]
        type_expr = items[2]  # Type object (skip :: token at items[1])
        return TypeAnnotation(name=name, type_signature=type_expr)

    def function_type(self, items):
        """Transform function type: A -> B"""
        # Grammar: atomic_type ARROW type_expr
        # items[0] = input_type, items[1] = "->", items[2] = output_type
        input_type = items[0]
        output_type = items[2]  # Skip arrow token at items[1]
        return FunctionType(input_type=input_type, output_type=output_type)

    def product_type(self, items):
        """Transform product type: A × B"""
        # Grammar: atomic_type TYPE_PRODUCT_OP atomic_type
        # items[0] = left, items[1] = "×", items[2] = right
        left = items[0]
        right = items[2]  # Skip product operator at items[1]
        return ProductType(left=left, right=right)

    def monomorphic_type(self, items):
        """Transform monomorphic type: Int, String, etc."""
        type_name = items[0].value
        return MonomorphicType(name=type_name)

    def type_variable(self, items):
        """Transform type variable: a, b, c"""
        var_name = items[0].value
        return TypeVariable(name=var_name)

    def type_constructor(self, items):
        """Transform type constructor: List[T], Dict[K, V]"""
        type_name = items[0].value  # E.g., "List", "Dict"
        type_params = items[1]  # List of Type objects
        return MonomorphicType(name=type_name, type_params=tuple(type_params))

    def type_params(self, items):
        """Transform type parameters list"""
        return list(items)  # Items are already transformed Type objects

    def unit_type(self, items):
        """Transform unit type: ()"""
        return MonomorphicType(name="Unit")


class Parser:
    """
    Parses CT DSL text into AST.

    Uses Lark parser with custom transformer to convert
    DSL programs into immutable entity trees.

    Clean Architecture:
    - Adapter layer (external Lark dependency)
    - Depends on entity abstractions (DIP)
    - No business logic (SRP)

    Example:
        parser = Parser()
        ast = parser.parse("build ∘ test")
        # Returns: Composition(left=Literal("build"), right=Literal("test"))
    """

    def __init__(self):
        """Initialize parser with grammar file."""
        grammar_path = Path(__file__).parent / "grammar.lark"
        with open(grammar_path, 'r') as f:
            grammar = f.read()

        self.lark_parser = Lark(
            grammar,
            start='start',
            parser='earley',  # Earley parser handles ambiguous grammars
            ambiguity='resolve',  # Automatically resolve ambiguities
        )
        self.transformer = ASTTransformer()

    def parse(self, dsl_text: str):
        """
        Parse DSL text into AST.

        Args:
            dsl_text (str): DSL program text.

        Returns:
            ASTNode: Root of the AST.

        Raises:
            LarkError: If syntax is invalid.

        Example:
            ast = parser.parse("frontend × backend")
            # Returns: Product(left=Literal("frontend"), right=Literal("backend"))
        """
        # Parse with Lark
        parse_tree = self.lark_parser.parse(dsl_text)

        # Transform to AST
        ast = self.transformer.transform(parse_tree)

        return ast
