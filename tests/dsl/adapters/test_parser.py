import pytest
from src.dsl.adapters.parser import Parser
from src.dsl.entities.literal import Literal
from src.dsl.entities.composition import Composition
from src.dsl.entities.product import Product
from src.dsl.entities.functor import Functor


class TestParser:
    """Pytest tests for DSL Parser.

    These tests verify the parser correctly converts DSL text to AST
    following the Lark grammar and CT semantics.
    """

    def setup_method(self):
        """Setup parser for each test."""
        self.parser = Parser()

    def test_parse_literal(self):
        """Test parsing a simple literal."""
        dsl = '"task_name"'
        ast = self.parser.parse(dsl)

        assert isinstance(ast, Literal)
        assert ast.value == "task_name"

    def test_parse_identifier(self):
        """Test parsing an identifier."""
        dsl = 'build_frontend'
        ast = self.parser.parse(dsl)

        assert isinstance(ast, Literal)
        assert ast.value == "build_frontend"

    def test_parse_composition(self):
        """Test parsing composition (f ∘ g)."""
        dsl = 'test ∘ build'
        ast = self.parser.parse(dsl)

        assert isinstance(ast, Composition)
        assert isinstance(ast.left, Literal)
        assert isinstance(ast.right, Literal)
        assert ast.left.value == "test"
        assert ast.right.value == "build"

    def test_parse_composition_ascii(self):
        """Test parsing composition with ASCII 'o'."""
        dsl = 'test o build'
        ast = self.parser.parse(dsl)

        assert isinstance(ast, Composition)

    def test_parse_product(self):
        """Test parsing parallel product (f × g)."""
        dsl = 'frontend × backend'
        ast = self.parser.parse(dsl)

        assert isinstance(ast, Product)
        assert isinstance(ast.left, Literal)
        assert isinstance(ast.right, Literal)
        assert ast.left.value == "frontend"
        assert ast.right.value == "backend"

    def test_parse_product_ascii(self):
        """Test parsing product with ASCII '*'."""
        dsl = 'frontend * backend'
        ast = self.parser.parse(dsl)

        assert isinstance(ast, Product)

    def test_parse_functor(self):
        """Test parsing functor definition."""
        dsl = 'functor ci_pipeline = build ∘ test'
        ast = self.parser.parse(dsl)

        assert isinstance(ast, Functor)
        assert ast.name == "ci_pipeline"
        assert isinstance(ast.expression, Composition)

    def test_parse_nested_composition(self):
        """Test parsing nested composition (f ∘ g ∘ h)."""
        dsl = 'deploy ∘ test ∘ build'
        ast = self.parser.parse(dsl)

        # Lark parses right-associative by default: deploy ∘ (test ∘ build)
        # This matches CT semantics where (f ∘ g)(x) = f(g(x))
        assert isinstance(ast, Composition)
        assert isinstance(ast.left, Literal)
        assert ast.left.value == "deploy"
        assert isinstance(ast.right, Composition)
        assert ast.right.left.value == "test"
        assert ast.right.right.value == "build"

    def test_parse_parenthesized_expression(self):
        """Test parsing parenthesized expressions."""
        dsl = '(build ∘ test) × (lint ∘ format)'
        ast = self.parser.parse(dsl)

        assert isinstance(ast, Product)
        assert isinstance(ast.left, Composition)
        assert isinstance(ast.right, Composition)

    def test_parse_complex_program(self):
        """Test parsing complex multi-operator expression."""
        dsl = '(frontend × backend) ∘ integrate'
        ast = self.parser.parse(dsl)

        assert isinstance(ast, Composition)
        # Composition should be: (frontend × backend) ∘ integrate
        # So left = (frontend × backend), right = integrate
        assert isinstance(ast.left, Product)
        assert isinstance(ast.right, Literal)
        assert ast.right.value == "integrate"

    def test_parse_with_whitespace(self):
        """Test parser handles whitespace correctly."""
        dsl = '  build   ∘   test  '
        ast = self.parser.parse(dsl)

        assert isinstance(ast, Composition)

    def test_parse_with_comments(self):
        """Test parser ignores comments."""
        dsl = '''
        # This is a comment
        build ∘ test  # Another comment
        '''
        ast = self.parser.parse(dsl)

        assert isinstance(ast, Composition)

    def test_parse_multiple_statements(self):
        """Test parsing multiple statements separated by semicolons."""
        dsl = 'functor ci = build ∘ test; ci'
        result = self.parser.parse(dsl)

        # Should return list of statements or program node
        assert result is not None

    def test_parse_invalid_syntax(self):
        """Test parser raises error on invalid syntax."""
        dsl = 'build ∘ ∘ test'  # Double operator

        with pytest.raises(Exception):  # Lark raises ParseError or similar
            self.parser.parse(dsl)

    def test_parse_empty_string(self):
        """Test parser handles empty input."""
        dsl = ''

        with pytest.raises(Exception):
            self.parser.parse(dsl)
