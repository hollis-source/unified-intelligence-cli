#!/usr/bin/env python3
"""
End-to-end Category Theory DSL Example.

Demonstrates complete pipeline:
1. Parse DSL text → AST
2. Traverse AST with visitor pattern
3. Mock execution to show workflow structure

Clean Code: Self-documenting example showing DSL in action.
"""

from src.dsl.adapters.parser import Parser
from src.dsl.entities.literal import Literal
from src.dsl.entities.composition import Composition
from src.dsl.entities.product import Product
from src.dsl.entities.functor import Functor


class MockExecutor:
    """
    Mock executor using visitor pattern to traverse AST.

    Demonstrates how an interpreter would execute the DSL
    by visiting each node and performing corresponding actions.
    """

    def __init__(self):
        """Initialize executor with execution log."""
        self.execution_log = []

    def execute(self, ast_node):
        """Execute AST node by visiting it."""
        return ast_node.accept(self)

    def visit_literal(self, node: Literal):
        """Visit literal node (task name)."""
        task = f"Task({node.value})"
        self.execution_log.append(f"Execute: {task}")
        return task

    def visit_composition(self, node: Composition):
        """Visit composition node (f ∘ g) - sequential execution."""
        # CT semantics: (f ∘ g)(x) = f(g(x))
        # Execute right first, then left
        self.execution_log.append("Begin composition (∘)")
        right_result = self.execute(node.right)
        left_result = self.execute(node.left)
        result = f"({left_result} ∘ {right_result})"
        self.execution_log.append(f"Complete composition: {result}")
        return result

    def visit_product(self, node: Product):
        """Visit product node (f × g) - parallel execution."""
        self.execution_log.append("Begin parallel product (×)")
        # In real implementation, would execute in parallel
        left_result = self.execute(node.left)
        right_result = self.execute(node.right)
        result = f"({left_result} × {right_result})"
        self.execution_log.append(f"Complete product: {result}")
        return result

    def visit_functor(self, node: Functor):
        """Visit functor node - workflow mapping."""
        self.execution_log.append(f"Define functor: {node.name}")
        expression_result = self.execute(node.expression)
        result = f"Functor({node.name} = {expression_result})"
        self.execution_log.append(f"Functor defined: {node.name}")
        return result

    def visit_mock(self, node):
        """Visit mock node (for testing)."""
        return f"Mock({node.name})"


def demo_parse_and_execute(dsl_program: str, description: str):
    """
    Parse and execute a DSL program, showing results.

    Args:
        dsl_program: DSL source code
        description: Human-readable description
    """
    print(f"\n{'=' * 70}")
    print(f"Example: {description}")
    print(f"{'=' * 70}")
    print(f"DSL Program:\n{dsl_program}\n")

    # Parse DSL → AST
    parser = Parser()
    ast = parser.parse(dsl_program)
    print(f"Parsed AST: {ast}\n")

    # Execute via visitor pattern
    executor = MockExecutor()
    result = executor.execute(ast)

    print("Execution Log:")
    for log_entry in executor.execution_log:
        print(f"  {log_entry}")

    print(f"\nFinal Result: {result}")


def main():
    """Run all DSL examples."""
    print("=" * 70)
    print("Category Theory DSL - End-to-End Examples")
    print("=" * 70)

    # Example 1: Simple Sequential Composition
    demo_parse_and_execute(
        'test ∘ build',
        "Sequential Composition (test after build)"
    )

    # Example 2: Parallel Execution
    demo_parse_and_execute(
        'frontend × backend',
        "Parallel Execution (frontend and backend concurrently)"
    )

    # Example 3: Complex Nested Expression
    demo_parse_and_execute(
        '(frontend × backend) ∘ integrate',
        "Parallel then Sequential (build frontend & backend, then integrate)"
    )

    # Example 4: Multi-stage Pipeline
    demo_parse_and_execute(
        'deploy ∘ test ∘ build',
        "Multi-stage Pipeline (build → test → deploy)"
    )

    # Example 5: Functor Definition
    demo_parse_and_execute(
        'functor ci_pipeline = deploy ∘ test ∘ build',
        "Functor Definition (reusable CI/CD workflow)"
    )

    # Example 6: Complex Parallel and Sequential
    demo_parse_and_execute(
        '(test_ui × test_api) ∘ (build_ui × build_api) ∘ plan',
        "Full Stack Pipeline (plan → build both → test both)"
    )

    print(f"\n{'=' * 70}")
    print("All examples completed successfully!")
    print("=" * 70)
    print("\nKey Takeaways:")
    print("- DSL text is parsed into immutable AST entities")
    print("- Visitor pattern enables flexible traversal/execution")
    print("- CT semantics: composition (∘) and product (×)")
    print("- Foundation ready for real task orchestration")


if __name__ == "__main__":
    main()
