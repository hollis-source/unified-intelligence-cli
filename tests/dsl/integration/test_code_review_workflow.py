"""Integration Test for Multi-Model Code Review Workflow.

Tests end-to-end execution of broadcast composition for parallel AI code review.
Validates timing to prove parallel execution benefit (2x speedup).

Category Theory Validation:
- Broadcast composition: (f × g) ∘ duplicate :: A → (B × D)
- Parallel execution: max(time(f), time(g)) vs time(f) + time(g)
- Type-safe execution with runtime validation

Clean Architecture: Integration test layer
SOLID: Tests verify correct broadcast composition implementation

Sprint: Testing broadcast composition with production use case
Reference: examples/workflows/multi_model_code_review.ct
"""

import pytest
import asyncio
import time
from pathlib import Path

from src.dsl.adapters.parser import Parser
from src.dsl.use_cases import WorkflowValidator, TypedInterpreter
from src.dsl.adapters.cli_task_executor import CLITaskExecutor


class TestCodeReviewWorkflow:
    """
    Integration tests for multi-model code review workflow.

    Tests verify:
    - End-to-end workflow execution (parse → validate → execute)
    - Timing demonstrates parallel execution benefit (~2x speedup)
    - Type-safe execution with broadcast composition
    - All 10 tasks execute correctly with proper data flow
    """

    def setup_method(self):
        """Setup parser, validator, executor for each test."""
        self.parser = Parser()
        self.validator = WorkflowValidator()
        self.executor = CLITaskExecutor()
        self.workflow_path = Path("examples/workflows/multi_model_code_review.ct")

    @pytest.mark.asyncio
    async def test_compliance_pipeline_execution(self):
        """Test compliance pipeline executes end-to-end with correct data flow."""
        # Read and validate workflow
        with open(self.workflow_path, 'r') as f:
            workflow_text = f.read()

        report = self.validator.validate_text(workflow_text)
        assert report.success, f"Workflow validation failed: {report.summary()}"

        # Parse workflow to get compliance_pipeline functor
        ast = self.parser.parse(workflow_text)
        assert ast is not None

        # Find compliance_pipeline functor
        from src.dsl.entities.functor import Functor
        compliance_pipeline = None
        if isinstance(ast, list):
            for node in ast:
                if isinstance(node, Functor) and node.name == "compliance_pipeline":
                    compliance_pipeline = node
                    break

        assert compliance_pipeline is not None, "compliance_pipeline functor not found"

        # Execute workflow
        interpreter = TypedInterpreter(
            task_executor=self.executor,
            type_env=report.type_environment,
            strict=True
        )

        result = await interpreter.execute(compliance_pipeline.expression)

        # Validate result structure (TypedInterpreter returns TypedData)
        from src.dsl.use_cases.typed_data import TypedData
        if isinstance(result, TypedData):
            result_value = result.value
        else:
            result_value = result

        assert isinstance(result_value, dict)
        assert result_value["task"] == "display_report"
        assert result_value["status"] == "success"
        assert result_value["report_type"] == "compliance"
        assert result_value["displayed"] is True

    @pytest.mark.asyncio
    async def test_compliance_pipeline_timing_proves_parallelism(self):
        """
        Test compliance pipeline timing demonstrates parallel execution benefit.

        Expected timing:
        - Parallel (broadcast): ~0.6s (max(0.5s SOLID, 0.6s Security) = 0.6s)
        - Sequential: ~1.1s (0.5s SOLID + 0.6s Security = 1.1s)
        - Speedup: ~1.8x

        Validates broadcast composition provides real performance improvement.
        """
        # Read and validate workflow
        with open(self.workflow_path, 'r') as f:
            workflow_text = f.read()

        report = self.validator.validate_text(workflow_text)
        assert report.success

        # Parse and find compliance_pipeline
        ast = self.parser.parse(workflow_text)
        from src.dsl.entities.functor import Functor
        compliance_pipeline = None
        if isinstance(ast, list):
            for node in ast:
                if isinstance(node, Functor) and node.name == "compliance_pipeline":
                    compliance_pipeline = node
                    break

        assert compliance_pipeline is not None

        # Execute with timing
        interpreter = TypedInterpreter(
            task_executor=self.executor,
            type_env=report.type_environment,
            strict=True
        )

        start_time = time.perf_counter()
        result = await interpreter.execute(compliance_pipeline.expression)
        execution_time = time.perf_counter() - start_time

        # Validate execution succeeded (TypedInterpreter returns TypedData)
        from src.dsl.use_cases.typed_data import TypedData
        if isinstance(result, TypedData):
            result_value = result.value
        else:
            result_value = result

        assert isinstance(result_value, dict)
        assert result_value["status"] == "success"

        # Validate timing proves parallelism
        # Parallel: max(0.5s, 0.6s) = ~0.6s + overhead
        # Sequential would be: 0.5s + 0.6s = ~1.1s + overhead
        # We allow for overhead, so check < 0.9s (well below sequential 1.1s)
        assert execution_time < 0.9, (
            f"Execution took {execution_time:.3f}s, expected < 0.9s for parallel execution. "
            f"Sequential would be ~1.1s. This suggests parallel execution is NOT working."
        )

        # Also verify it's not suspiciously fast (< 0.55s would mean skipping work)
        assert execution_time > 0.55, (
            f"Execution took {execution_time:.3f}s, suspiciously fast. "
            f"Expected ~0.6s for max(0.5s SOLID, 0.6s Security)."
        )

        print(f"\n✓ Parallel execution time: {execution_time:.3f}s (expected ~0.6s)")
        print(f"✓ Sequential would take: ~1.1s")
        print(f"✓ Speedup: ~{1.1/execution_time:.1f}x")

    @pytest.mark.asyncio
    async def test_quality_pipeline_execution(self):
        """Test quality pipeline executes end-to-end with correct data flow."""
        # Read and validate workflow
        with open(self.workflow_path, 'r') as f:
            workflow_text = f.read()

        report = self.validator.validate_text(workflow_text)
        assert report.success

        # Parse workflow to get quality_pipeline functor
        ast = self.parser.parse(workflow_text)
        from src.dsl.entities.functor import Functor
        quality_pipeline = None
        if isinstance(ast, list):
            for node in ast:
                if isinstance(node, Functor) and node.name == "quality_pipeline":
                    quality_pipeline = node
                    break

        assert quality_pipeline is not None, "quality_pipeline functor not found"

        # Execute workflow
        interpreter = TypedInterpreter(
            task_executor=self.executor,
            type_env=report.type_environment,
            strict=True
        )

        result = await interpreter.execute(quality_pipeline.expression)

        # Validate result structure (TypedInterpreter returns TypedData)
        from src.dsl.use_cases.typed_data import TypedData
        if isinstance(result, TypedData):
            result_value = result.value
        else:
            result_value = result

        assert isinstance(result_value, dict)
        assert result_value["task"] == "display_report"
        assert result_value["status"] == "success"
        assert result_value["report_type"] == "quality"
        assert result_value["displayed"] is True

    @pytest.mark.asyncio
    async def test_quality_pipeline_timing_proves_parallelism(self):
        """
        Test quality pipeline timing demonstrates parallel execution benefit.

        Expected timing:
        - Parallel (broadcast): ~0.55s (max(0.55s Performance, 0.45s Coverage) = 0.55s)
        - Sequential: ~1.0s (0.55s Performance + 0.45s Coverage = 1.0s)
        - Speedup: ~1.8x
        """
        # Read and validate workflow
        with open(self.workflow_path, 'r') as f:
            workflow_text = f.read()

        report = self.validator.validate_text(workflow_text)
        assert report.success

        # Parse and find quality_pipeline
        ast = self.parser.parse(workflow_text)
        from src.dsl.entities.functor import Functor
        quality_pipeline = None
        if isinstance(ast, list):
            for node in ast:
                if isinstance(node, Functor) and node.name == "quality_pipeline":
                    quality_pipeline = node
                    break

        assert quality_pipeline is not None

        # Execute with timing
        interpreter = TypedInterpreter(
            task_executor=self.executor,
            type_env=report.type_environment,
            strict=True
        )

        start_time = time.perf_counter()
        result = await interpreter.execute(quality_pipeline.expression)
        execution_time = time.perf_counter() - start_time

        # Validate execution succeeded (TypedInterpreter returns TypedData)
        from src.dsl.use_cases.typed_data import TypedData
        if isinstance(result, TypedData):
            result_value = result.value
        else:
            result_value = result

        assert isinstance(result_value, dict)
        assert result_value["status"] == "success"

        # Validate timing proves parallelism
        # Parallel: max(0.55s, 0.45s) = ~0.55s + overhead
        # Sequential would be: 0.55s + 0.45s = ~1.0s + overhead
        # Check < 0.85s (well below sequential 1.0s)
        assert execution_time < 0.85, (
            f"Execution took {execution_time:.3f}s, expected < 0.85s for parallel execution. "
            f"Sequential would be ~1.0s. This suggests parallel execution is NOT working."
        )

        # Verify not suspiciously fast
        assert execution_time > 0.5, (
            f"Execution took {execution_time:.3f}s, suspiciously fast. "
            f"Expected ~0.55s for max(0.55s Performance, 0.45s Coverage)."
        )

        print(f"\n✓ Parallel execution time: {execution_time:.3f}s (expected ~0.55s)")
        print(f"✓ Sequential would take: ~1.0s")
        print(f"✓ Speedup: ~{1.0/execution_time:.1f}x")

    @pytest.mark.asyncio
    async def test_broadcast_composition_type_safety(self):
        """
        Test broadcast composition maintains type safety throughout execution.

        Validates:
        - Type environment correctly infers broadcast composition types
        - Runtime execution preserves type information
        - Product morphisms properly unpack tuple inputs
        - No type mismatches at composition boundaries
        """
        # Read and validate workflow
        with open(self.workflow_path, 'r') as f:
            workflow_text = f.read()

        report = self.validator.validate_text(workflow_text)

        # Verify type validation succeeded
        assert report.success, f"Type validation failed: {report.summary()}"
        # ValidationReport uses .errors and .warnings lists, not _count attributes
        assert len(report.errors) == 0
        assert len(report.warnings) == 0

        # Verify compliance_pipeline has correct type signature
        # Expected: Unit → Unit (via composition chain)
        compliance_type = report.type_environment.lookup("compliance_pipeline")
        assert compliance_type is not None
        assert str(compliance_type.input_type) == "Unit"
        assert str(compliance_type.output_type) == "Unit"

        # Verify quality_pipeline has correct type signature
        quality_type = report.type_environment.lookup("quality_pipeline")
        assert quality_type is not None
        assert str(quality_type.input_type) == "Unit"
        assert str(quality_type.output_type) == "Unit"

        print(f"\n✓ Type safety validated:")
        print(f"  compliance_pipeline :: {compliance_type}")
        print(f"  quality_pipeline :: {quality_type}")
        print(f"✓ 0 type errors, 0 warnings")
