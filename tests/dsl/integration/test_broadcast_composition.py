"""Integration Tests for Broadcast Composition with Duplicate Operator

Tests the diagonal functor (Δ) for broadcast semantics in parallel composition.
Validates end-to-end pipeline: parse → type-check → execute.

Mathematical Foundation:
- duplicate :: a -> (a × a)  (diagonal functor)
- (f × g) ∘ duplicate :: A -> (B × D)  (broadcast composition)
- Without duplicate: (f × g) :: (A × C) -> (B × D)  (product morphism)

Clean Architecture: Integration test layer
SOLID: Tests verify correct implementation of diagonal functor

Sprint: Sprint 3, Phase 4 - Broadcast Composition
Reference: docs/PARALLEL_COMPOSITION_SEMANTICS.md
"""

import pytest
import asyncio
from typing import Any

from src.dsl.adapters.parser import Parser
from src.dsl.use_cases import (
    TypedInterpreter,
    TypedData,
)
from src.dsl.types.type_system import (
    MonomorphicType,
    FunctionType,
    ProductType,
    TypeVariable,
)
from src.dsl.types.type_inference_visitor import TypeInferenceVisitor
from src.dsl.entities.duplicate import Duplicate
from src.dsl.entities.functor import Functor


class MockTypedTaskExecutor:
    """Mock task executor for broadcast composition testing."""

    def __init__(self):
        """Initialize with task execution log."""
        self.execution_log = []
        self.task_types = {}

    async def execute_task(self, task_name: str, input_data: Any = None) -> Any:
        """Execute mock task and log input/output."""
        self.execution_log.append({
            'task': task_name,
            'input': input_data
        })

        # Return TypedData with proper type information
        if task_name in self.task_types:
            func_type = self.task_types[task_name]
            output_type = func_type.output_type

            result = TypedData(
                value=f"result_{task_name}",
                type_info=output_type,
                source=task_name
            )
            return result

        # Fallback for unknown tasks
        return f"result_{task_name}"


class TestBroadcastComposition:
    """
    Integration tests for broadcast composition using duplicate operator.

    Tests verify:
    - Parsing duplicate keyword creates Duplicate AST node
    - Type inference returns polymorphic type a -> (a × a)
    - Runtime execution broadcasts input correctly
    - Full broadcast composition (f × g) ∘ duplicate works end-to-end
    """

    def setup_method(self):
        """Setup parser, executor for each test."""
        self.parser = Parser()
        self.executor = MockTypedTaskExecutor()

    def test_parse_duplicate_keyword(self):
        """Test parsing duplicate keyword creates Duplicate AST node."""
        # Parse duplicate keyword
        ast = self.parser.parse("duplicate")

        # Should create Duplicate node, not Literal
        assert isinstance(ast, Duplicate)
        assert str(ast) == "duplicate"

    def test_parse_duplicate_unicode(self):
        """Test parsing Unicode Δ creates Duplicate AST node."""
        # Parse Unicode delta
        ast = self.parser.parse("Δ")

        # Should create Duplicate node
        assert isinstance(ast, Duplicate)

    def test_duplicate_type_inference(self):
        """Test type inference for duplicate returns polymorphic type a -> (a × a)."""
        # Parse duplicate
        ast = self.parser.parse("duplicate")

        # Type inference
        visitor = TypeInferenceVisitor()
        inferred_type = ast.accept(visitor)

        # Should be function type: a -> (a × a)
        assert isinstance(inferred_type, FunctionType)

        # Input should be type variable
        assert isinstance(inferred_type.input_type, TypeVariable)

        # Output should be product type
        assert isinstance(inferred_type.output_type, ProductType)

        # Product should have same type variables on both sides
        product = inferred_type.output_type
        assert product.left == product.right
        assert isinstance(product.left, TypeVariable)

    def test_broadcast_composition_type_inference(self):
        """Test type inference for broadcast composition (f × g) ∘ duplicate."""
        dsl_text = """
        get_files :: () -> FileList
        analyze_style :: FileList -> StyleReport
        analyze_security :: FileList -> SecurityReport

        # Broadcast composition
        parallel = (analyze_style * analyze_security) o duplicate o get_files
        """

        # Parse
        ast = self.parser.parse(dsl_text)

        # Type inference
        visitor = TypeInferenceVisitor()
        if isinstance(ast, list):
            for statement in ast:
                statement.accept(visitor)
        elif ast is not None:
            ast.accept(visitor)

        # Should have no errors
        assert not visitor.has_errors()

        # parallel should have type: () -> (StyleReport × SecurityReport)
        parallel_type = visitor.type_env.lookup("parallel")
        assert parallel_type is not None
        assert isinstance(parallel_type, FunctionType)

        # Input: Unit (from get_files)
        assert parallel_type.input_type == MonomorphicType("Unit")

        # Output: Product of StyleReport × SecurityReport
        assert isinstance(parallel_type.output_type, ProductType)
        assert parallel_type.output_type.left == MonomorphicType("StyleReport")
        assert parallel_type.output_type.right == MonomorphicType("SecurityReport")

    @pytest.mark.asyncio
    async def test_duplicate_runtime_execution(self):
        """Test runtime execution of duplicate broadcasts input correctly."""
        # Parse duplicate
        ast = self.parser.parse("duplicate")

        # Setup type environment
        visitor = TypeInferenceVisitor()
        ast.accept(visitor)
        type_env = visitor.type_env

        # Execute with input data
        interpreter = TypedInterpreter(
            task_executor=self.executor,
            type_env=type_env,
            strict=False  # No strict typing for basic duplicate test
        )

        input_data = {"test": "data"}
        result = await interpreter.execute(ast, input_data)

        # Result should be tuple (input, input)
        assert isinstance(result, tuple)
        assert len(result) == 2
        assert result[0] == input_data
        assert result[1] == input_data
        assert result[0] is result[1]  # Same object reference

    @pytest.mark.asyncio
    async def test_broadcast_composition_runtime_execution(self):
        """Test full broadcast composition (f × g) ∘ duplicate executes correctly."""
        dsl_text = """
        get_files :: () -> FileList
        analyze_style :: FileList -> StyleReport
        analyze_security :: FileList -> SecurityReport

        # Broadcast composition
        parallel = (analyze_style * analyze_security) o duplicate o get_files
        """

        # Setup task types
        self.executor.task_types = {
            "get_files": FunctionType(
                input_type=MonomorphicType("Unit"),
                output_type=MonomorphicType("FileList")
            ),
            "analyze_style": FunctionType(
                input_type=MonomorphicType("FileList"),
                output_type=MonomorphicType("StyleReport")
            ),
            "analyze_security": FunctionType(
                input_type=MonomorphicType("FileList"),
                output_type=MonomorphicType("SecurityReport")
            ),
        }

        # Parse
        ast = self.parser.parse(dsl_text)

        # Type inference
        visitor = TypeInferenceVisitor()
        if isinstance(ast, list):
            for statement in ast:
                statement.accept(visitor)
        elif ast is not None:
            ast.accept(visitor)
        type_env = visitor.type_env

        # Extract parallel functor
        parallel_ast = None
        if isinstance(ast, list):
            for node in ast:
                if isinstance(node, Functor) and node.name == "parallel":
                    parallel_ast = node
                    break

        assert parallel_ast is not None

        # Execute
        interpreter = TypedInterpreter(
            task_executor=self.executor,
            type_env=type_env,
            strict=True
        )

        result = await interpreter.execute(parallel_ast.expression)

        # Verify execution flow:
        # 1. get_files executes first
        # 2. duplicate broadcasts result to tuple
        # 3. analyze_style and analyze_security execute in parallel
        assert len(self.executor.execution_log) == 3

        # First: get_files
        assert self.executor.execution_log[0]['task'] == 'get_files'

        # Next two: analyze_style and analyze_security (order may vary due to parallel execution)
        task_names = {log['task'] for log in self.executor.execution_log[1:]}
        assert task_names == {'analyze_style', 'analyze_security'}

        # Both should receive same input (result from get_files)
        style_input = None
        security_input = None
        for log in self.executor.execution_log[1:]:
            if log['task'] == 'analyze_style':
                style_input = log['input']
            elif log['task'] == 'analyze_security':
                security_input = log['input']

        # Both should have received same input from get_files (broadcast semantics)
        assert style_input is not None
        assert security_input is not None
        # TypedInterpreter unwraps TypedData before passing to executor
        # So inputs are raw strings
        assert style_input == "result_get_files"
        assert security_input == "result_get_files"

        # Result should be tuple of (StyleReport, SecurityReport)
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_broadcast_vs_product_type_signatures(self):
        """Test type signatures differ between broadcast and product composition."""
        dsl_text = """
        f :: A -> B
        g :: A -> D

        # Product morphism: requires two separate inputs (A × A)
        product = f * g

        # Broadcast: uses duplicate to share one input A -> (B × D)
        broadcast = (f * g) o duplicate
        """

        # Parse
        ast = self.parser.parse(dsl_text)

        # Type inference
        visitor = TypeInferenceVisitor()
        if isinstance(ast, list):
            for statement in ast:
                statement.accept(visitor)
        elif ast is not None:
            ast.accept(visitor)

        # Product morphism: (A × A) -> (B × D)
        product_type = visitor.type_env.lookup("product")
        assert isinstance(product_type, FunctionType)
        assert isinstance(product_type.input_type, ProductType)
        assert isinstance(product_type.output_type, ProductType)
        assert product_type.input_type.left == MonomorphicType("A")
        assert product_type.input_type.right == MonomorphicType("A")

        # Broadcast: A -> (B × D)  (single input via duplicate)
        broadcast_type = visitor.type_env.lookup("broadcast")
        assert isinstance(broadcast_type, FunctionType)
        # Input should be A (unified from duplicate's type variable and product's input types)
        assert broadcast_type.input_type == MonomorphicType("A")
        # Output should be product type (B × D)
        assert isinstance(broadcast_type.output_type, ProductType)
        assert broadcast_type.output_type.left == MonomorphicType("B")
        assert broadcast_type.output_type.right == MonomorphicType("D")

    def test_nested_broadcast_composition(self):
        """Test nested broadcast composition for complex workflows."""
        dsl_text = """
        get_data :: () -> Data
        process :: Data -> Processed
        analyze :: Data -> Analysis
        save :: Processed -> ()
        report :: Analysis -> ()

        # Nested broadcast: process data and analyze in parallel, then save/report in parallel
        # (save × report) ∘ (process × analyze) ∘ duplicate ∘ get_data
        nested = (save * report) o (process * analyze) o duplicate o get_data
        """

        # Parse
        ast = self.parser.parse(dsl_text)

        # Type inference
        visitor = TypeInferenceVisitor()
        if isinstance(ast, list):
            for statement in ast:
                statement.accept(visitor)
        elif ast is not None:
            ast.accept(visitor)

        # Should validate successfully
        if visitor.has_errors():
            print("Type errors:", visitor.get_error_summary())

        # nested should have type: () -> (() × ())
        nested_type = visitor.type_env.lookup("nested")
        assert nested_type is not None
        assert isinstance(nested_type, FunctionType)
        assert nested_type.input_type == MonomorphicType("Unit")
        assert isinstance(nested_type.output_type, ProductType)
        assert nested_type.output_type.left == MonomorphicType("Unit")
        assert nested_type.output_type.right == MonomorphicType("Unit")
