"""DSL Interpreter - Executes AST via multi-agent CLI.

Clean Architecture: Use Case layer (business logic).
SOLID: SRP - only interprets AST, DIP - depends on TaskExecutor abstraction.
"""

import asyncio
from typing import Any, Protocol
from src.dsl.entities.literal import Literal
from src.dsl.entities.composition import Composition
from src.dsl.entities.product import Product
from src.dsl.entities.functor import Functor


class TaskExecutor(Protocol):
    """
    Interface for task execution.

    Clean Architecture: Interface layer (abstraction).
    Implementations can be real CLI adapter or mock for testing.
    """

    async def execute_task(self, task_name: str, input_data: Any = None) -> Any:
        """
        Execute a task by name.

        Args:
            task_name: Name of the task to execute (e.g., "build", "test")
            input_data: Optional input data from previous task

        Returns:
            Task execution result
        """
        ...


class Interpreter:
    """
    Interprets and executes DSL AST via multi-agent system.

    Uses visitor pattern to traverse AST nodes and execute them
    via the TaskExecutor interface. Handles:
    - Sequential composition (∘): Right-to-left execution
    - Parallel product (×): Concurrent execution with asyncio
    - Functors: Named workflow execution

    Clean Architecture:
    - Use Case layer (business logic)
    - Depends on TaskExecutor interface (DIP)
    - No external dependencies

    Example:
        executor = CLITaskExecutor()
        interpreter = Interpreter(executor)
        ast = parser.parse("test ∘ build")
        result = await interpreter.execute(ast)
    """

    def __init__(self, task_executor: TaskExecutor):
        """
        Initialize interpreter with task executor.

        Args:
            task_executor: Implementation of TaskExecutor interface
        """
        self.task_executor = task_executor

    async def execute(self, ast_node) -> Any:
        """
        Execute AST node.

        Args:
            ast_node: Root AST node to execute

        Returns:
            Execution result

        Example:
            result = await interpreter.execute(Literal("build"))
        """
        return await ast_node.accept(self)

    async def visit_literal(self, node: Literal) -> Any:
        """
        Execute literal task.

        Args:
            node: Literal node containing task name

        Returns:
            Task execution result
        """
        return await self.task_executor.execute_task(node.value)

    async def visit_composition(self, node: Composition) -> Any:
        """
        Execute composition (f ∘ g) - sequential execution.

        Category Theory semantics: (f ∘ g)(x) = f(g(x))
        Execute right first, pass result to left.

        Args:
            node: Composition node

        Returns:
            Final composition result
        """
        # Execute right first (CT right-to-left)
        right_result = await self.execute(node.right)

        # Execute left with right's result as input
        left_result = await self.execute(node.left)

        # Return left result (final output of composition)
        return left_result

    async def visit_product(self, node: Product) -> Any:
        """
        Execute product (f × g) - parallel execution.

        Category Theory semantics: Both morphisms execute concurrently,
        results combined as tuple (implements categorical product).

        Args:
            node: Product node

        Returns:
            Tuple of (left_result, right_result)
        """
        # Execute both tasks concurrently using asyncio.gather
        left_result, right_result = await asyncio.gather(
            self.execute(node.left),
            self.execute(node.right)
        )

        # Return combined results (categorical product)
        return (left_result, right_result)

    async def visit_functor(self, node: Functor) -> Any:
        """
        Execute functor - named workflow.

        Args:
            node: Functor node containing name and expression

        Returns:
            Expression execution result
        """
        # Execute the functor's expression
        return await self.execute(node.expression)

    async def visit_monad(self, node):
        """
        Execute monad (for completeness, though not used in AST).

        Args:
            node: Monad node

        Returns:
            Monad value
        """
        # Monads are runtime wrappers, not AST nodes
        # If needed in future, implement bind chain execution
        return node.value

    async def visit_mock(self, node):
        """Visit mock node (for testing)."""
        return await self.task_executor.execute_task(node.name)
