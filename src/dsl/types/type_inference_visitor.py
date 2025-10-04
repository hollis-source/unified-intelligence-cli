"""Type Inference Visitor for DSL AST

Implements the visitor pattern to walk DSL AST and perform type inference
and checking. Collects type annotations, builds type environment, and validates
compositions according to category theory laws.

Clean Architecture: Use Case layer (coordinates type checking)
SOLID: SRP - only responsible for type inference traversal

Story: Sprint 2, Phase 1 - Parser Integration
"""

from typing import Optional
from src.dsl.entities.ast_node import ASTNode
from src.dsl.entities.literal import Literal
from src.dsl.entities.composition import Composition
from src.dsl.entities.product import Product
from src.dsl.entities.duplicate import Duplicate
from src.dsl.entities.functor import Functor
from src.dsl.entities.type_annotation import TypeAnnotation
from src.dsl.types.type_system import (
    Type,
    TypeVariable,
    FunctionType,
    ProductType,
    TypeMismatchError,
)
from src.dsl.types.type_checker import (
    TypeEnvironment,
    check_composition,
    check_product,
)
from src.dsl.types.error_reporter import (
    ErrorAccumulator,
    format_type_error,
)


class TypeInferenceVisitor:
    """
    Visitor for type inference and checking on DSL AST.

    Walks the AST in a single pass, collecting type annotations
    and validating compositions. Accumulates errors for batch reporting.

    Usage:
        visitor = TypeInferenceVisitor()
        ast.accept(visitor)
        if visitor.has_errors():
            print(visitor.get_error_summary())

    Clean Code: Single Responsibility - only AST traversal and type checking
    """

    def __init__(self):
        """Initialize visitor with empty type environment."""
        self.type_env = TypeEnvironment()
        self.errors = ErrorAccumulator()

    def visit_literal(self, node: Literal) -> Optional[Type]:
        """
        Visit a literal node (task/function name).

        Args:
            node: Literal AST node

        Returns:
            Type signature if found in environment, None otherwise
        """
        # Look up type in environment
        type_sig = self.type_env.lookup(node.value)

        if type_sig is None:
            self.errors.add_warning(
                f"No type annotation for '{node.value}'"
            )

        return type_sig

    def visit_composition(self, node: Composition) -> Optional[Type]:
        """
        Visit a composition node (g ∘ f).

        Validates that the composition is well-typed according to
        category theory: output of f must match input of g.

        Args:
            node: Composition AST node

        Returns:
            Composed function type if valid, None if error
        """
        # Visit children to get their types
        left_type = node.left.accept(self)
        right_type = node.right.accept(self)

        # If either child has no type, cannot check composition
        if left_type is None or right_type is None:
            self.errors.add_error(
                f"Cannot infer types for composition: {node}"
            )
            return None

        # Both must be function types
        if not isinstance(left_type, FunctionType):
            self.errors.add_error(
                f"Left side of composition must be function, got {left_type}"
            )
            return None

        if not isinstance(right_type, FunctionType):
            self.errors.add_error(
                f"Right side of composition must be function, got {right_type}"
            )
            return None

        # Check composition using type checker
        try:
            result_type = check_composition(left_type, right_type)
            return result_type
        except TypeMismatchError as e:
            # Format error with context
            error_msg = format_type_error(
                e,
                source_location=f"composition at {node}"
            )
            self.errors.add_error(error_msg)
            return None

    def visit_product(self, node: Product) -> Optional[Type]:
        """
        Visit a product node (f × g).

        Validates parallel composition, creating product type
        (A × C) → (B × D) from f: A → B and g: C → D.

        Args:
            node: Product AST node

        Returns:
            Product function type if valid, None if error
        """
        # Visit children to get their types
        left_type = node.left.accept(self)
        right_type = node.right.accept(self)

        # If either child has no type, cannot check product
        if left_type is None or right_type is None:
            self.errors.add_error(
                f"Cannot infer types for product: {node}"
            )
            return None

        # Both must be function types
        if not isinstance(left_type, FunctionType):
            self.errors.add_error(
                f"Left side of product must be function, got {left_type}"
            )
            return None

        if not isinstance(right_type, FunctionType):
            self.errors.add_error(
                f"Right side of product must be function, got {right_type}"
            )
            return None

        # Check product using type checker
        result_type = check_product(left_type, right_type)
        return result_type

    def visit_duplicate(self, node: Duplicate) -> Optional[Type]:
        """
        Visit a duplicate node (diagonal functor Δ).

        Returns the polymorphic type signature: a -> (a × a)
        This enables broadcast semantics for parallel composition.

        Args:
            node: Duplicate AST node

        Returns:
            Polymorphic function type: a -> (a × a)
        """
        # Duplicate has polymorphic type: a -> (a × a)
        # Use a fresh type variable for polymorphism
        type_var = TypeVariable(name="a")
        product_type = ProductType(left=type_var, right=type_var)
        return FunctionType(input_type=type_var, output_type=product_type)

    def visit_functor(self, node: Functor) -> Optional[Type]:
        """
        Visit a functor definition (functor name = expression).

        Infers the type of the expression and binds it to the name.

        Args:
            node: Functor AST node

        Returns:
            Type of the functor expression
        """
        # Visit expression to infer its type
        expr_type = node.expression.accept(self)

        if expr_type is not None:
            # Bind the functor name to its type
            self.type_env.bind(node.name, expr_type)

        return expr_type

    def visit_type_annotation(self, node: TypeAnnotation) -> Optional[Type]:
        """
        Visit a type annotation (name :: Type).

        Adds the type binding to the environment for later lookups.

        Args:
            node: TypeAnnotation AST node

        Returns:
            The annotated type
        """
        # Bind name to type in environment
        self.type_env.bind(node.name, node.type_signature)
        return node.type_signature

    def has_errors(self) -> bool:
        """Check if any errors were accumulated."""
        return self.errors.has_errors()

    def has_warnings(self) -> bool:
        """Check if any warnings were accumulated."""
        return self.errors.has_warnings()

    def get_error_summary(self) -> str:
        """Get formatted summary of all errors and warnings."""
        return self.errors.get_summary()

    def get_type_environment(self) -> TypeEnvironment:
        """Get the built type environment."""
        return self.type_env
