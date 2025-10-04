"""DSL Interpreter - Executes AST via multi-agent CLI.

Clean Architecture: Use Case layer (business logic).
SOLID: SRP - only interprets AST, DIP - depends on TaskExecutor abstraction.
"""

import asyncio
from typing import Any, Protocol
from src.dsl.entities.literal import Literal
from src.dsl.entities.composition import Composition
from src.dsl.entities.product import Product
from src.dsl.entities.duplicate import Duplicate
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
        self._current_input = None  # Thread-local input data for visitor pattern

    async def execute(self, ast_node, input_data: Any = None) -> Any:
        """
        Execute AST node with optional input data.

        Args:
            ast_node: Root AST node to execute
            input_data: Optional input data to pass to first task

        Returns:
            Execution result

        Example:
            result = await interpreter.execute(Literal("build"))
            result = await interpreter.execute(ast, input_data={"key": "value"})
        """
        # Store input data for visitor methods to access
        previous_input = self._current_input
        self._current_input = input_data
        try:
            result = await ast_node.accept(self)
            return result
        finally:
            # Restore previous input (for nested executions)
            self._current_input = previous_input

    async def visit_literal(self, node: Literal) -> Any:
        """
        Execute literal task with input data.

        Args:
            node: Literal node containing task name

        Returns:
            Task execution result
        """
        # Pass current input data to task executor
        return await self.task_executor.execute_task(node.value, self._current_input)

    async def visit_composition(self, node: Composition) -> Any:
        """
        Execute composition (f ∘ g) - sequential execution with result propagation.

        Category Theory semantics: (f ∘ g)(x) = f(g(x))
        Execute right first with current input, pass result to left.

        Args:
            node: Composition node

        Returns:
            Final composition result
        """
        # Execute right first (CT right-to-left) with current input
        right_result = await self.execute(node.right, self._current_input)

        # Execute left with right's result as input (propagation!)
        left_result = await self.execute(node.left, right_result)

        # Return left result (final output of composition)
        return left_result

    async def visit_product(self, node: Product) -> Any:
        """
        Execute product (f × g) - parallel execution with tuple input unpacking.

        Category Theory semantics: Product morphism (f × g) :: (A × C) → (B × D)
        - Input: tuple (a, c) where a :: A, c :: C
        - Left function f receives a
        - Right function g receives c
        - Output: tuple (b, d) where b :: B, d :: D

        Args:
            node: Product node

        Returns:
            Tuple of (left_result, right_result)
        """
        # Product morphism requires tuple input (A × C)
        # Unpack tuple to pass correct inputs to each function
        if isinstance(self._current_input, tuple) and len(self._current_input) == 2:
            # Proper product semantics: unpack tuple input
            left_input, right_input = self._current_input
        else:
            # Fallback: broadcast same input to both (for backward compatibility)
            left_input = self._current_input
            right_input = self._current_input

        # Execute both tasks concurrently with their respective inputs
        left_result, right_result = await asyncio.gather(
            self.execute(node.left, left_input),
            self.execute(node.right, right_input)
        )

        # Return combined results (categorical product)
        return (left_result, right_result)

    async def visit_duplicate(self, node: Duplicate) -> Any:
        """
        Execute duplicate (diagonal functor Δ) - broadcasts input to product tuple.

        Category Theory semantics: Δ(x) = (x, x)
        Creates a product tuple from single input for broadcast composition.

        Args:
            node: Duplicate node

        Returns:
            Tuple (input, input)
        """
        # Duplicate current input into product tuple
        return (self._current_input, self._current_input)

    async def visit_functor(self, node: Functor) -> Any:
        """
        Execute functor - named workflow with input propagation.

        Args:
            node: Functor node containing name and expression

        Returns:
            Expression execution result
        """
        # Execute the functor's expression with current input
        return await self.execute(node.expression, self._current_input)

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
        """Visit mock node (for testing) with input propagation."""
        return await self.task_executor.execute_task(node.name, self._current_input)
