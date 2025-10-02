"""DSL Parser using Lark.

Clean Architecture: Adapter layer (external Lark dependency).
SOLID: SRP - only parses DSL text to AST, DIP - depends on entity abstractions.
"""

import os
from pathlib import Path
from lark import Lark, Transformer, Token
from src.dsl.entities.literal import Literal
from src.dsl.entities.composition import Composition
from src.dsl.entities.product import Product
from src.dsl.entities.functor import Functor


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

    def bind_expr(self, items):
        """Transform bind expression (currently returns composition for simplicity)."""
        # Lark parses binary operators as: [left, operator, right]
        # TODO: Implement proper Bind AST node when needed
        # For now, treat as composition
        left = self._ensure_ast_node(items[0])
        right = self._ensure_ast_node(items[2]) if len(items) > 2 else self._ensure_ast_node(items[1])
        return Composition(left=left, right=right)

    def definition(self, items):
        """Transform functor definition to Functor entity."""
        name = items[0].value if isinstance(items[0], Token) else items[0]
        expression = self._ensure_ast_node(items[1])
        return Functor(name=name, expression=expression)

    def program(self, items):
        """Transform program (list of statements)."""
        # If single statement, return it directly
        if len(items) == 1:
            return items[0]
        # Multiple statements: return list or last statement
        # For simplicity, return last statement (can be enhanced)
        return items[-1]


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
            parser='lalr',  # Fast LALR parser
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
