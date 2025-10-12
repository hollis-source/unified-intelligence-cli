"""Typed Interpreter with Runtime Type Validation.

Extends Interpreter to validate types at composition boundaries during execution.
Uses type environment from WorkflowValidator to ensure runtime type safety.

Clean Architecture: Use Case layer (orchestrates execution + validation)
SOLID: SRP - adds runtime validation, OCP - extends Interpreter behavior

Story: Sprint 2, Phase 3 - Runtime Integration
"""

import asyncio
from typing import Any, Optional
from src.dsl.use_cases.interpreter import Interpreter, TaskExecutor
from src.dsl.use_cases.typed_data import TypedData, wrap_if_needed, unwrap_if_needed
from src.dsl.types.type_checker import TypeEnvironment
from src.dsl.types.type_system import FunctionType, TypeMismatchError
from src.dsl.entities.literal import Literal
from src.dsl.entities.composition import Composition
from src.dsl.entities.product import Product
from src.dsl.entities.functor import Functor


class RuntimeTypeError(Exception):
    """Raised when runtime type validation fails."""
    pass


class TypedInterpreter(Interpreter):
    """
    Interpreter with runtime type validation at composition boundaries.

    Extends base Interpreter to validate types during execution, catching
    type errors that may occur due to:
    - Incorrect task implementations
    - Data corruption
    - Type environment mismatches

    Uses TypedData wrappers to carry type information through the execution pipeline.

    Clean Architecture:
    - Use Case layer (execution orchestration)
    - Depends on TypeEnvironment (types) and TaskExecutor (adapters)
    - No framework dependencies

    Example:
        # Validate workflow first
        validator = WorkflowValidator()
        report = validator.validate_file("workflow.ct")

        if report.success:
            # Execute with runtime validation
            executor = CLITaskExecutor()
            interpreter = TypedInterpreter(
                task_executor=executor,
                type_env=report.type_environment,
                strict=True
            )
            result = await interpreter.execute(ast)
    """

    def __init__(
        self,
        task_executor: TaskExecutor,
        type_env: Optional[TypeEnvironment] = None,
        strict: bool = False
    ):
        """
        Initialize typed interpreter.

        Args:
            task_executor: Task executor implementation
            type_env: Type environment from validation (optional)
            strict: If True, raise errors on type mismatches (default: False = warnings)
        """
        super().__init__(task_executor)
        self.type_env = type_env or TypeEnvironment()
        self.strict = strict
        self.validation_errors = []
        self.validation_warnings = []

    async def execute(self, ast_node, input_data: Any = None) -> Any:
        """
        Execute AST with optional runtime type validation.

        Args:
            ast_node: Root AST node to execute
            input_data: Optional input data

        Returns:
            Execution result (may be TypedData if type environment available)

        Raises:
            RuntimeTypeError: If strict mode and type mismatch occurs
        """
        # Clear previous validation results
        self.validation_errors = []
        self.validation_warnings = []

        # Execute with parent implementation
        result = await super().execute(ast_node, input_data)

        return result

    async def visit_literal(self, node: Literal) -> Any:
        """
        Execute literal task and wrap result with type information.

        Args:
            node: Literal node

        Returns:
            TypedData if type environment has type info, else raw result
        """
        # Execute task
        result = await self.task_executor.execute_task(node.value, unwrap_if_needed(self._current_input))

        # Look up type in environment
        type_info = self.type_env.lookup(node.value)

        if type_info is None:
            # No type info - return unwrapped result
            self.validation_warnings.append(
                f"No type annotation for task '{node.value}' - skipping runtime validation"
            )
            return result

        # Wrap result with type info for downstream validation
        # If type is function A -> B and we have input, extract output type B
        if isinstance(type_info, FunctionType):
            output_type = type_info.output_type
            return wrap_if_needed(result, output_type, source=node.value)
        else:
            # Non-function type (shouldn't happen for tasks, but handle gracefully)
            return wrap_if_needed(result, type_info, source=node.value)

    async def visit_composition(self, node: Composition) -> Any:
        """
        Execute composition with runtime type validation.

        Validates that the output type of right matches input type of left
        at the composition boundary.

        Args:
            node: Composition node

        Returns:
            Composition result (TypedData if type info available)

        Raises:
            RuntimeTypeError: If strict mode and type mismatch
        """
        # Execute right first
        right_result = await self.execute(node.right, self._current_input)

        # Validate composition boundary if both sides have type info
        if isinstance(right_result, TypedData):
            # Get left's type signature
            left_type = self._get_node_type(node.left)

            if left_type and isinstance(left_type, FunctionType):
                # Validate: right's output type should match left's input type
                try:
                    self._validate_composition_boundary(
                        right_output_type=right_result.type_info,
                        left_input_type=left_type.input_type,
                        right_source=right_result.source,
                        left_source=self._get_node_name(node.left)
                    )
                except RuntimeTypeError as e:
                    if self.strict:
                        raise
                    else:
                        self.validation_warnings.append(str(e))

        # Execute left with right's result
        left_result = await self.execute(node.left, right_result)

        return left_result

    async def visit_product(self, node: Product) -> Any:
        """
        Execute product with runtime type validation and tuple input unpacking.

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

        # Execute both sides in parallel with their respective inputs
        left_result, right_result = await asyncio.gather(
            self.execute(node.left, left_input),
            self.execute(node.right, right_input)
        )

        # For product, we don't validate compatibility (categorical product)
        # Just return combined results
        return (left_result, right_result)

    async def visit_functor(self, node: Functor) -> Any:
        """
        Execute functor with runtime type validation.

        Args:
            node: Functor node

        Returns:
            Expression result
        """
        # Execute expression
        result = await self.execute(node.expression, self._current_input)

        # Look up functor type in environment
        functor_type = self.type_env.lookup(node.name)

        if functor_type and isinstance(result, TypedData):
            # Wrap result with functor's type if available
            if isinstance(functor_type, FunctionType):
                return wrap_if_needed(
                    unwrap_if_needed(result),
                    functor_type.output_type,
                    source=node.name
                )

        return result

    def _get_node_type(self, node) -> Optional[Any]:
        """
        Get type signature for an AST node.

        Args:
            node: AST node

        Returns:
            Type signature if available, None otherwise
        """
        if isinstance(node, Literal):
            return self.type_env.lookup(node.value)
        elif isinstance(node, Functor):
            return self.type_env.lookup(node.name)
        # For compositions/products, type would be inferred
        return None

    def _get_node_name(self, node) -> str:
        """
        Get readable name for an AST node.

        Args:
            node: AST node

        Returns:
            Node name for error messages
        """
        if isinstance(node, Literal):
            return node.value
        elif isinstance(node, Functor):
            return node.name
        elif isinstance(node, Composition):
            return f"({self._get_node_name(node.left)} ∘ {self._get_node_name(node.right)})"
        elif isinstance(node, Product):
            return f"({self._get_node_name(node.left)} × {self._get_node_name(node.right)})"
        return str(node)

    def _validate_composition_boundary(
        self,
        right_output_type,
        left_input_type,
        right_source: Optional[str],
        left_source: Optional[str]
    ) -> None:
        """
        Validate type compatibility at composition boundary.

        Args:
            right_output_type: Output type from right side
            left_input_type: Input type expected by left side
            right_source: Source of right side (for error messages)
            left_source: Source of left side (for error messages)

        Raises:
            RuntimeTypeError: If types don't match
        """
        # Check if types are compatible
        # For now, use simple equality check
        # TODO: Could use more sophisticated subtyping/polymorphism
        if str(right_output_type) != str(left_input_type):
            error_msg = (
                f"Runtime type mismatch at composition boundary:\n"
                f"  Right side '{right_source or '?'}' produces: {right_output_type}\n"
                f"  Left side '{left_source or '?'}' expects: {left_input_type}\n"
                f"  Types must match for valid composition"
            )

            self.validation_errors.append(error_msg)
            raise RuntimeTypeError(error_msg)

    def has_validation_errors(self) -> bool:
        """Check if runtime validation found errors."""
        return len(self.validation_errors) > 0

    def has_validation_warnings(self) -> bool:
        """Check if runtime validation found warnings."""
        return len(self.validation_warnings) > 0

    def get_validation_summary(self) -> str:
        """
        Get formatted summary of runtime validation results.

        Returns:
            Formatted summary string
        """
        lines = ["Runtime Type Validation Summary"]
        lines.append("=" * 60)
        lines.append("")

        if not self.has_validation_errors() and not self.has_validation_warnings():
            lines.append("✓ No runtime type issues detected")
            return "\n".join(lines)

        if self.validation_errors:
            lines.append(f"Errors: {len(self.validation_errors)}")
            for i, error in enumerate(self.validation_errors, 1):
                lines.append(f"\n{i}. {error}")
            lines.append("")

        if self.validation_warnings:
            lines.append(f"Warnings: {len(self.validation_warnings)}")
            for i, warning in enumerate(self.validation_warnings, 1):
                lines.append(f"  {i}. {warning}")

        return "\n".join(lines)
