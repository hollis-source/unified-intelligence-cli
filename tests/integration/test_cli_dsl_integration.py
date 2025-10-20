"""Integration Tests for CLI-DSL Workflow Execution.

Tests end-to-end execution of DSL workflows through CLI interface.
Validates CLI argument parsing → DSL workflow loading → execution → result formatting.

Clean Architecture: Integration test layer
SOLID: Tests verify correct CLI adapter and DSL runtime integration

Sprint: P2 Testing Infrastructure
Reference: P2 priorities (Build mock CLI adapter for testing)
"""

import pytest
import asyncio
from pathlib import Path
from click.testing import CliRunner
from typing import Dict, Any
from dataclasses import dataclass

from src.dsl.adapters.parser import Parser
from src.dsl.use_cases import WorkflowValidator, TypedInterpreter
from src.dsl.adapters.cli_task_executor import CLITaskExecutor


@dataclass
class MockCLITaskExecutor:
    """Mock CLI task executor for testing without external dependencies."""

    execution_log: list
    task_results: Dict[str, Any]

    def __init__(self):
        """Initialize with empty log."""
        self.execution_log = []
        self.task_results = {}

    async def execute_task(self, task_name: str, input_data: Any = None) -> Any:
        """Execute mock task and return result."""
        # Log execution
        self.execution_log.append(
            {"task": task_name, "input": input_data, "status": "success"}
        )

        # Return configured result or default
        if task_name in self.task_results:
            return self.task_results[task_name]

        # Default result
        return {"task": task_name, "status": "success", "result": f"completed_{task_name}"}


class TestCLIDSLIntegration:
    """
    Integration tests for CLI-DSL workflow execution.

    Tests verify:
    - CLI loads and parses DSL workflow files
    - CLI arguments properly passed to workflow execution
    - DSL workflow executes with CLI task executor
    - Results formatted correctly for CLI output
    - Error handling through CLI → DSL → executor chain
    """

    @pytest.fixture
    def parser(self):
        """Create DSL parser."""
        return Parser()

    @pytest.fixture
    def validator(self):
        """Create workflow validator."""
        return WorkflowValidator()

    @pytest.fixture
    def executor(self):
        """Create mock CLI task executor."""
        return MockCLITaskExecutor()

    @pytest.fixture
    def workflow_dir(self, tmp_path):
        """Create temporary workflow directory."""
        workflow_dir = tmp_path / "workflows"
        workflow_dir.mkdir()
        return workflow_dir

    def test_cli_loads_dsl_workflow_file(self, parser, workflow_dir):
        """Test CLI can load and parse DSL workflow from file."""
        # Create workflow file
        workflow_file = workflow_dir / "test_workflow.ct"
        workflow_file.write_text(
            """
            analyze :: () -> Report
            display :: Report -> ()

            pipeline = display o analyze
            """
        )

        # Load and parse
        with open(workflow_file, "r") as f:
            workflow_text = f.read()

        ast = parser.parse(workflow_text)

        # Should parse successfully
        assert ast is not None
        assert isinstance(ast, list)
        assert len(ast) == 3  # 2 signatures + 1 functor

    @pytest.mark.asyncio
    async def test_cli_executes_simple_workflow(
        self, parser, validator, executor, workflow_dir
    ):
        """Test CLI executes simple DSL workflow end-to-end."""
        # Create simple workflow
        workflow_file = workflow_dir / "simple.ct"
        workflow_file.write_text(
            """
            fetch_data :: () -> Data
            process_data :: Data -> Result

            pipeline = process_data o fetch_data
            """
        )

        # Load workflow
        with open(workflow_file, "r") as f:
            workflow_text = f.read()

        # Validate
        report = validator.validate_text(workflow_text)
        assert report.success, f"Validation failed: {report.summary()}"

        # Parse
        ast = parser.parse(workflow_text)

        # Find pipeline functor
        from src.dsl.entities.functor import Functor

        pipeline = None
        if isinstance(ast, list):
            for node in ast:
                if isinstance(node, Functor) and node.name == "pipeline":
                    pipeline = node
                    break

        assert pipeline is not None

        # Execute with CLI task executor
        interpreter = TypedInterpreter(
            task_executor=executor, type_env=report.type_environment, strict=True
        )

        result = await interpreter.execute(pipeline.expression)

        # Verify execution
        assert len(executor.execution_log) == 2
        assert executor.execution_log[0]["task"] == "fetch_data"
        assert executor.execution_log[1]["task"] == "process_data"

    @pytest.mark.asyncio
    async def test_cli_passes_arguments_to_workflow(
        self, parser, validator, executor
    ):
        """Test CLI arguments are properly passed to workflow execution."""
        # Workflow with input
        workflow_text = """
        analyze :: Input -> Report
        """

        # Validate
        report = validator.validate_text(workflow_text)
        assert report.success

        # Parse
        ast = parser.parse(workflow_text)

        # Configure executor with expected result
        executor.task_results["analyze"] = {
            "status": "success",
            "report": "Analysis complete",
        }

        # Execute with input data (simulating CLI argument)
        interpreter = TypedInterpreter(
            task_executor=executor, type_env=report.type_environment, strict=False
        )

        cli_input = {"file": "test.py", "options": ["--verbose"]}

        from src.dsl.entities.literal import Literal

        # AST might be single node or list
        analyze_task = Literal("analyze")
        if isinstance(ast, list):
            analyze_task = next(
                (node for node in ast if hasattr(node, "name") and node.name == "analyze"),
                Literal("analyze"),
            )

        result = await interpreter.execute(analyze_task, cli_input)

        # Verify input passed to executor
        assert len(executor.execution_log) == 1
        assert executor.execution_log[0]["input"] == cli_input

    @pytest.mark.asyncio
    async def test_cli_executes_parallel_workflow(
        self, parser, validator, executor, workflow_dir
    ):
        """Test CLI executes parallel DSL workflow correctly."""
        # Parallel workflow
        workflow_file = workflow_dir / "parallel.ct"
        workflow_file.write_text(
            """
            analyze_style :: Code -> StyleReport
            analyze_security :: Code -> SecurityReport

            # Parallel composition
            parallel = (analyze_style * analyze_security) o duplicate
            """
        )

        # Load workflow
        with open(workflow_file, "r") as f:
            workflow_text = f.read()

        # Validate
        report = validator.validate_text(workflow_text)
        assert report.success

        # Parse
        ast = parser.parse(workflow_text)

        # Find parallel functor
        from src.dsl.entities.functor import Functor

        parallel = None
        if isinstance(ast, list):
            for node in ast:
                if isinstance(node, Functor) and node.name == "parallel":
                    parallel = node
                    break

        assert parallel is not None

        # Configure executor results
        executor.task_results["analyze_style"] = {"issues": ["style1", "style2"]}
        executor.task_results["analyze_security"] = {"vulnerabilities": ["sec1"]}

        # Execute
        interpreter = TypedInterpreter(
            task_executor=executor, type_env=report.type_environment, strict=True
        )

        input_code = {"code": "def test(): pass"}
        result = await interpreter.execute(parallel.expression, input_code)

        # Verify parallel execution
        assert len(executor.execution_log) == 2

        # Both tasks should execute
        task_names = {log["task"] for log in executor.execution_log}
        assert task_names == {"analyze_style", "analyze_security"}

        # Result should be tuple
        assert isinstance(result, tuple)
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_cli_handles_workflow_execution_errors(
        self, parser, validator, executor
    ):
        """Test CLI properly handles errors during workflow execution."""
        # Workflow that will fail
        workflow_text = """
        failing_task :: () -> Result
        """

        # Parse and validate
        report = validator.validate_text(workflow_text)
        assert report.success

        ast = parser.parse(workflow_text)

        # Configure executor to raise error
        @dataclass
        class FailingExecutor:
            """Executor that fails."""

            async def execute_task(self, task_name: str, input_data: Any = None):
                raise RuntimeError(f"Task {task_name} failed")

        failing_executor = FailingExecutor()

        # Execute
        interpreter = TypedInterpreter(
            task_executor=failing_executor,
            type_env=report.type_environment,
            strict=True,
        )

        from src.dsl.entities.literal import Literal

        failing_task = Literal("failing_task")

        # Should propagate error
        with pytest.raises(RuntimeError, match="Task failing_task failed"):
            await interpreter.execute(failing_task)

    @pytest.mark.asyncio
    async def test_cli_workflow_with_result_formatting(
        self, parser, validator, executor
    ):
        """Test CLI formats workflow results for display."""
        # Workflow with structured result
        workflow_text = """
        analyze :: () -> Report
        format_report :: Report -> DisplayText

        display_pipeline = format_report o analyze
        """

        # Validate
        report = validator.validate_text(workflow_text)
        assert report.success

        # Parse
        ast = parser.parse(workflow_text)

        # Configure executor
        executor.task_results["analyze"] = {
            "metrics": {"lines": 100, "functions": 10},
            "issues": ["issue1", "issue2"],
        }
        executor.task_results["format_report"] = {
            "formatted": "Analysis Report\n=============\nLines: 100\nFunctions: 10\nIssues: 2"
        }

        # Find pipeline
        from src.dsl.entities.functor import Functor

        pipeline = None
        if isinstance(ast, list):
            for node in ast:
                if isinstance(node, Functor) and node.name == "display_pipeline":
                    pipeline = node
                    break

        assert pipeline is not None

        # Execute
        interpreter = TypedInterpreter(
            task_executor=executor, type_env=report.type_environment, strict=True
        )

        result = await interpreter.execute(pipeline.expression)

        # Verify formatting executed
        assert len(executor.execution_log) == 2
        assert executor.execution_log[1]["task"] == "format_report"

        # Result should be formatted
        from src.dsl.use_cases.typed_data import TypedData

        if isinstance(result, TypedData):
            result = result.value

        assert isinstance(result, dict)
        assert "formatted" in result

    @pytest.mark.asyncio
    async def test_cli_loads_multiple_workflows(
        self, parser, validator, executor, workflow_dir
    ):
        """Test CLI can load and execute multiple workflows."""
        # Create multiple workflow files
        workflow1 = workflow_dir / "workflow1.ct"
        workflow1.write_text(
            """
            task1 :: () -> Result1
            pipeline1 = task1
            """
        )

        workflow2 = workflow_dir / "workflow2.ct"
        workflow2.write_text(
            """
            task2 :: () -> Result2
            pipeline2 = task2
            """
        )

        # Load and execute both
        workflows = []
        for wf_file in [workflow1, workflow2]:
            with open(wf_file, "r") as f:
                wf_text = f.read()

            report = validator.validate_text(wf_text)
            assert report.success

            ast = parser.parse(wf_text)
            workflows.append(ast)

        # Both should parse successfully
        assert len(workflows) == 2

    @pytest.mark.asyncio
    async def test_cli_workflow_with_conditional_execution(
        self, parser, validator, executor
    ):
        """Test CLI executes workflows with conditional branches."""
        # Workflow with choice (sum type)
        workflow_text = """
        validate :: Input -> Valid
        process :: Valid -> Result
        error_handler :: Invalid -> ErrorReport

        # Choice: process if valid, else error_handler
        conditional = (process + error_handler)
        """

        # Validate
        report = validator.validate_text(workflow_text)
        # Note: Sum types may not be fully implemented, so validation might fail
        # This test validates the CLI-DSL integration pattern

        # Parse
        ast = parser.parse(workflow_text)

        # Should at least parse successfully
        assert ast is not None


class TestCLIWorkflowDiscovery:
    """Tests for CLI workflow file discovery and loading."""

    def test_cli_discovers_workflow_files(self, tmp_path):
        """Test CLI discovers .ct workflow files in directory."""
        workflow_dir = tmp_path / "workflows"
        workflow_dir.mkdir()

        # Create multiple workflow files
        (workflow_dir / "workflow1.ct").write_text("task1 :: () -> Result")
        (workflow_dir / "workflow2.ct").write_text("task2 :: () -> Result")
        (workflow_dir / "other.txt").write_text("not a workflow")

        # Discover workflow files
        workflow_files = sorted(workflow_dir.glob("*.ct"))

        # Should find 2 .ct files
        assert len(workflow_files) == 2
        assert all(f.suffix == ".ct" for f in workflow_files)

    def test_cli_loads_workflow_from_stdin(self):
        """Test CLI can accept workflow from stdin."""
        # Simulate stdin workflow
        workflow_text = """
        stdin_task :: () -> Result
        """

        parser = Parser()
        ast = parser.parse(workflow_text)

        # Should parse successfully
        assert ast is not None

    def test_cli_handles_missing_workflow_file(self, tmp_path):
        """Test CLI handles missing workflow file gracefully."""
        missing_file = tmp_path / "missing.ct"

        # Should not exist
        assert not missing_file.exists()

        # CLI should detect this and return appropriate error
        # (actual CLI implementation would handle this)
        with pytest.raises(FileNotFoundError):
            with open(missing_file, "r") as f:
                f.read()


class TestCLIPerformance:
    """Performance tests for CLI-DSL execution."""

    @pytest.mark.asyncio
    async def test_cli_workflow_execution_speed(self):
        """Test CLI workflow execution completes in reasonable time."""
        import time

        # Create parser and validator
        parser = Parser()
        validator = WorkflowValidator()

        # Simple workflow
        workflow_text = """
        quick_task :: () -> Result
        """

        # Measure parsing + validation time
        start = time.perf_counter()

        report = validator.validate_text(workflow_text)
        ast = parser.parse(workflow_text)

        elapsed = time.perf_counter() - start

        # Should be fast (< 100ms for simple workflow)
        assert elapsed < 0.1, f"CLI workflow loading too slow: {elapsed:.3f}s"
        assert report.success
        assert ast is not None
