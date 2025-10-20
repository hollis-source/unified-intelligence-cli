"""HTN Compiler - Converts DSL AST to HTNNode tree.

Implements visitor pattern to transform category-theory DSL entities
into Hierarchical Task Network nodes for decomposition and planning.

Clean Architecture: Adapter layer (DSL → HTN conversion).
SOLID: SRP - single responsibility of AST→HTN compilation.
"""

from typing import Any
from src.dsl.entities.literal import Literal
from src.dsl.entities.composition import Composition
from src.dsl.entities.product import Product
from src.dsl.entities.functor import Functor
from src.dsl.entities.ast_node import ASTNode
from src.entity.htn.htn_node import HTNNode


class HTNCompiler:
    """Compiles DSL AST nodes to HTNNode tree using visitor pattern.

    This compiler traverses the DSL abstract syntax tree and produces
    a hierarchical task network that preserves composition semantics:
    - Sequential composition (∘): right-to-left execution order
    - Parallel product (×): concurrent execution
    - Functors: reusable workflow mappings

    Example:
        compiler = HTNCompiler()
        ast = Composition(left=Literal("test"), right=Literal("build"))
        htn = compiler.compile(ast)
        # Result: HTNNode with subtasks [build, test] (right first)
    """

    def compile(self, ast_node: ASTNode) -> HTNNode:
        """Compile AST node to HTNNode tree.

        Uses visitor pattern - delegates to ast_node.accept(self) which
        calls the appropriate visit_* method.

        Args:
            ast_node: AST node to compile (Literal, Composition, Product, or Functor)

        Returns:
            HTNNode: Root of compiled HTN tree

        Example:
            >>> literal = Literal(value="build")
            >>> htn = compiler.compile(literal)
            >>> assert htn.task_id == "build"
        """
        return ast_node.accept(self)

    def visit_literal(self, node: Literal) -> HTNNode:
        """Compile Literal to primitive HTNNode.

        Literals are leaf nodes in the AST and become primitive (non-decomposable)
        tasks in the HTN.

        Args:
            node: Literal node with value

        Returns:
            HTNNode: Primitive task node
        """
        return HTNNode(
            task_id=str(node.value),
            description=f"Execute {node.value}"
        )

    def visit_composition(self, node: Composition) -> HTNNode:
        """Compile Composition to HTNNode with sequential subtasks.

        Preserves composition semantics: (f ∘ g) means execute g first, then f.
        Subtasks are ordered [right, left] to maintain right-to-left execution.

        Args:
            node: Composition node with left and right operands

        Returns:
            HTNNode: Compound task with subtasks in execution order
        """
        # Compile operands recursively
        right_htn = node.right.accept(self)
        left_htn = node.left.accept(self)

        # Create compound node with right-to-left ordering
        return HTNNode(
            task_id="composition",
            description="Sequential composition (∘)",
            subtasks=[right_htn, left_htn],  # right executes first
            metadata={"operator": "∘", "execution": "sequential"}
        )

    def visit_product(self, node: Product) -> HTNNode:
        """Compile Product to HTNNode with parallel subtasks.

        Products represent concurrent execution: (f × g) means execute
        f and g in parallel.

        Args:
            node: Product node with left and right operands

        Returns:
            HTNNode: Compound task with parallel subtasks
        """
        # Compile operands recursively
        left_htn = node.left.accept(self)
        right_htn = node.right.accept(self)

        # Create compound node with parallel semantics
        return HTNNode(
            task_id="product",
            description="Parallel product (×)",
            subtasks=[left_htn, right_htn],
            metadata={"operator": "×", "execution": "parallel"}
        )

    def visit_functor(self, node: Functor) -> HTNNode:
        """Compile Functor to named HTNNode with expression subtask.

        Functors are reusable workflow mappings with named identifiers.
        The functor's expression becomes a subtask of the named node.

        Args:
            node: Functor node with name and expression

        Returns:
            HTNNode: Named task wrapping expression
        """
        # Compile functor expression
        expr_htn = node.expression.accept(self)

        # Create named compound node
        return HTNNode(
            task_id=node.name,
            description=f"Functor: {node.name}",
            subtasks=[expr_htn],
            metadata={"type": "functor"}
        )
