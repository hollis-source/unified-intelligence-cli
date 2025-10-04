"""Integration Tests for Type-Safe DSL Workflow Pipeline

Tests complete end-to-end pipeline:
1. Parse .ct workflow files
2. Validate types (pre-execution)
3. Execute with runtime type validation

Clean Architecture: Integration test layer (tests use case orchestration)
SOLID: Tests verify SRP, OCP, DIP compliance across layers

Sprint: Sprint 3, Phase 3 - Integration Testing
"""

import pytest
import asyncio
from pathlib import Path
from typing import Any

from src.dsl.adapters.parser import Parser
from src.dsl.use_cases import (
    WorkflowValidator,
    TypedInterpreter,
    TypedData,
    wrap_if_needed,
)
from src.dsl.types.type_system import MonomorphicType, FunctionType


class MockTypedTaskExecutor:
    """
    Mock task executor that returns TypedData for runtime validation testing.

    Simulates real task execution with type information attached to results.
    """

    def __init__(self):
        """Initialize with type signatures for mock tasks."""
        self.execution_log = []

        # Mock type signatures (matching simple_data_pipeline.ct)
        self.task_types = {
            "fetch_data": FunctionType(
                input_type=MonomorphicType("Unit"),
                output_type=MonomorphicType("RawData")
            ),
            "clean_data": FunctionType(
                input_type=MonomorphicType("RawData"),
                output_type=MonomorphicType("CleanData")
            ),
            "transform_data": FunctionType(
                input_type=MonomorphicType("CleanData"),
                output_type=MonomorphicType("ProcessedData")
            ),
            "save_results": FunctionType(
                input_type=MonomorphicType("ProcessedData"),
                output_type=MonomorphicType("Unit")
            ),
        }

    async def execute_task(self, task_name: str, input_data: Any = None) -> Any:
        """Execute mock task and return TypedData with correct type signature."""
        self.execution_log.append(f"execute: {task_name}")

        # Get output type for this task
        if task_name in self.task_types:
            func_type = self.task_types[task_name]
            output_type = func_type.output_type

            # Create mock result with type information
            result = TypedData(
                value=f"result_{task_name}",
                type_info=output_type,
                source=task_name
            )
            return result

        # Fallback for unknown tasks
        return f"result_{task_name}"


class TestTypeSafeWorkflowIntegration:
    """
    Integration tests for complete type-safe DSL workflow pipeline.

    Tests verify:
    - Parse → Validate → Execute pipeline works end-to-end
    - Type errors caught during validation
    - Runtime type validation catches mismatches
    - Both strict and warning modes work correctly
    """

    def setup_method(self):
        """Setup parser, validator, and mock executor for each test."""
        self.parser = Parser()
        self.validator = WorkflowValidator()
        self.executor = MockTypedTaskExecutor()

    def test_simple_pipeline_validation_success(self):
        """Test simple_data_pipeline.ct validates successfully."""
        # Simple sequential pipeline with correct types
        dsl_text = """
        # Type annotations
        fetch_data :: () -> RawData
        clean_data :: RawData -> CleanData
        transform_data :: CleanData -> ProcessedData
        save_results :: ProcessedData -> ()

        # Sequential pipeline
        pipeline = save_results o transform_data o clean_data o fetch_data
        """

        # Parse
        ast = self.parser.parse(dsl_text)

        # Validate
        from src.dsl.types.type_inference_visitor import TypeInferenceVisitor

        visitor = TypeInferenceVisitor()
        if isinstance(ast, list):
            for statement in ast:
                statement.accept(visitor)
        elif ast is not None:
            ast.accept(visitor)

        # Should have no errors
        assert not visitor.has_errors()

        # Should have type for pipeline
        pipeline_type = visitor.type_env.lookup("pipeline")
        assert pipeline_type is not None

        # Pipeline should be: () -> ()
        assert isinstance(pipeline_type, FunctionType)
        assert pipeline_type.input_type == MonomorphicType("Unit")
        assert pipeline_type.output_type == MonomorphicType("Unit")

    def test_simple_pipeline_validation_type_mismatch(self):
        """Test validation catches type mismatches."""
        # Intentional type error: skip clean_data step
        dsl_text = """
        fetch_data :: () -> RawData
        clean_data :: RawData -> CleanData
        transform_data :: CleanData -> ProcessedData
        save_results :: ProcessedData -> ()

        # ERROR: transform_data expects CleanData, but fetch_data returns RawData
        invalid_pipeline = transform_data o fetch_data
        """

        # Parse
        ast = self.parser.parse(dsl_text)

        # Validate
        from src.dsl.types.type_inference_visitor import TypeInferenceVisitor

        visitor = TypeInferenceVisitor()
        if isinstance(ast, list):
            for statement in ast:
                statement.accept(visitor)
        elif ast is not None:
            ast.accept(visitor)

        # Should have type error
        assert visitor.has_errors()

        # Error should mention type error or mismatch
        error_msg = str(visitor.errors.errors[0]).lower()
        assert "type error" in error_msg or "type mismatch" in error_msg or "cannot compose" in error_msg

    @pytest.mark.asyncio
    async def test_simple_pipeline_execution_success(self):
        """Test simple pipeline executes successfully with runtime validation."""
        # Simple sequential pipeline
        dsl_text = """
        fetch_data :: () -> RawData
        clean_data :: RawData -> CleanData
        transform_data :: CleanData -> ProcessedData
        save_results :: ProcessedData -> ()

        pipeline = save_results o transform_data o clean_data o fetch_data
        """

        # Parse
        ast = self.parser.parse(dsl_text)

        # Validate (pre-execution)
        from src.dsl.types.type_inference_visitor import TypeInferenceVisitor

        visitor = TypeInferenceVisitor()
        if isinstance(ast, list):
            for statement in ast:
                statement.accept(visitor)
        elif ast is not None:
            ast.accept(visitor)
        type_env = visitor.type_env

        # Extract pipeline functor
        from src.dsl.entities.functor import Functor
        pipeline_ast = None
        if isinstance(ast, list):
            for node in ast:
                if isinstance(node, Functor) and node.name == "pipeline":
                    pipeline_ast = node
                    break
        elif isinstance(ast, Functor):
            pipeline_ast = ast

        assert pipeline_ast is not None, "Pipeline functor not found"

        # Execute with TypedInterpreter
        interpreter = TypedInterpreter(
            task_executor=self.executor,
            type_env=type_env,
            strict=True  # Raise errors on type mismatch
        )

        result = await interpreter.execute(pipeline_ast.expression)

        # Verify execution order (right-to-left)
        assert self.executor.execution_log == [
            "execute: fetch_data",
            "execute: clean_data",
            "execute: transform_data",
            "execute: save_results"
        ]

        # Verify no validation errors
        assert len(interpreter.validation_errors) == 0
        assert len(interpreter.validation_warnings) == 0

    @pytest.mark.asyncio
    async def test_sequential_multi_step_execution(self):
        """Test multi-step sequential pipeline with runtime type validation."""
        dsl_text = """
        get_files :: () -> FileList
        analyze_style :: FileList -> StyleReport
        generate_summary :: StyleReport -> Summary
        save_results :: Summary -> ()

        # Multi-step sequential pipeline
        full_workflow = save_results o generate_summary o analyze_style o get_files
        """

        # Add types for tasks
        self.executor.task_types.update({
            "get_files": FunctionType(
                input_type=MonomorphicType("Unit"),
                output_type=MonomorphicType("FileList")
            ),
            "analyze_style": FunctionType(
                input_type=MonomorphicType("FileList"),
                output_type=MonomorphicType("StyleReport")
            ),
            "generate_summary": FunctionType(
                input_type=MonomorphicType("StyleReport"),
                output_type=MonomorphicType("Summary")
            ),
            "save_results": FunctionType(
                input_type=MonomorphicType("Summary"),
                output_type=MonomorphicType("Unit")
            ),
        })

        # Parse
        ast = self.parser.parse(dsl_text)

        # Validate
        from src.dsl.types.type_inference_visitor import TypeInferenceVisitor

        visitor = TypeInferenceVisitor()
        if isinstance(ast, list):
            for statement in ast:
                statement.accept(visitor)
        elif ast is not None:
            ast.accept(visitor)
        type_env = visitor.type_env

        # Should validate successfully
        assert not visitor.has_errors()

        # Extract full_workflow functor
        from src.dsl.entities.functor import Functor
        workflow_ast = None
        if isinstance(ast, list):
            for node in ast:
                if isinstance(node, Functor) and node.name == "full_workflow":
                    workflow_ast = node
                    break

        assert workflow_ast is not None

        # Execute
        interpreter = TypedInterpreter(
            task_executor=self.executor,
            type_env=type_env,
            strict=True  # Strict mode
        )

        result = await interpreter.execute(workflow_ast.expression)

        # Verify all tasks executed in correct order
        assert self.executor.execution_log == [
            "execute: get_files",
            "execute: analyze_style",
            "execute: generate_summary",
            "execute: save_results"
        ]

    @pytest.mark.asyncio
    async def test_workflow_validator_integration(self):
        """Test WorkflowValidator use case with real workflow file."""
        # Create temporary workflow file
        import tempfile

        workflow_content = """
        # Simple data pipeline
        fetch_data :: () -> RawData
        clean_data :: RawData -> CleanData
        save_data :: CleanData -> ()

        # Valid pipeline
        pipeline = save_data o clean_data o fetch_data
        """

        with tempfile.NamedTemporaryFile(mode='w', suffix='.ct', delete=False) as f:
            f.write(workflow_content)
            workflow_path = f.name

        try:
            # Validate file
            report = self.validator.validate_file(workflow_path)

            # Should succeed
            assert report.success
            assert len(report.errors) == 0
            assert report.type_environment is not None

            # Summary should show success
            summary = report.summary()
            assert "PASSED" in summary or "success" in summary.lower()

        finally:
            # Cleanup
            Path(workflow_path).unlink()

    @pytest.mark.asyncio
    async def test_workflow_validator_catches_errors(self):
        """Test WorkflowValidator catches type errors in file."""
        import tempfile

        workflow_content = """
        fetch_data :: () -> RawData
        process_data :: CleanData -> ProcessedData

        # ERROR: Type mismatch (RawData ≠ CleanData)
        invalid = process_data o fetch_data
        """

        with tempfile.NamedTemporaryFile(mode='w', suffix='.ct', delete=False) as f:
            f.write(workflow_content)
            workflow_path = f.name

        try:
            # Validate file
            report = self.validator.validate_file(workflow_path)

            # Should fail
            assert not report.success
            assert len(report.errors) > 0

            # Summary should show errors
            summary = report.summary()
            assert "error" in summary.lower() or "failed" in summary.lower()

        finally:
            # Cleanup
            Path(workflow_path).unlink()

    def test_both_functor_syntax_variants(self):
        """Test both explicit and implicit functor syntax validate correctly."""
        # Both syntaxes should be equivalent
        dsl_text = """
        fetch :: () -> Data
        process :: Data -> Result

        # Explicit syntax
        functor workflow_explicit = process o fetch

        # Implicit syntax
        workflow_implicit = process o fetch
        """

        # Parse
        ast = self.parser.parse(dsl_text)

        # Validate
        from src.dsl.types.type_inference_visitor import TypeInferenceVisitor

        visitor = TypeInferenceVisitor()
        if isinstance(ast, list):
            for statement in ast:
                statement.accept(visitor)
        elif ast is not None:
            ast.accept(visitor)

        # No errors
        assert not visitor.has_errors()

        # Both should have same type: () -> Result
        explicit_type = visitor.type_env.lookup("workflow_explicit")
        implicit_type = visitor.type_env.lookup("workflow_implicit")

        assert explicit_type == implicit_type
        assert isinstance(explicit_type, FunctionType)
        assert explicit_type.input_type == MonomorphicType("Unit")
        assert explicit_type.output_type == MonomorphicType("Result")
