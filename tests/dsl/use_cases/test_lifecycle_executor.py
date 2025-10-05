"""Tests for lifecycle-aware DSL workflow executor.

Tests cover lifecycle phases, validation, and error handling.
"""

import pytest
from pathlib import Path
from src.dsl.use_cases.lifecycle_executor import (
    LifecycleWorkflowExecutor,
    ValidationResult,
    WorkflowExecutionResult
)
from src.dsl.entities.literal import Literal
from src.dsl.entities.composition import Composition
from src.dsl.entities.functor import Functor
from src.entities.lifecycle import LifecycleState


class MockTaskExecutor:
    """Mock task executor for testing."""

    async def execute_task(self, task_name: str, input_data=None):
        """Execute mock task."""
        return {"task": task_name, "status": "success", "output": f"Completed {task_name}"}


class MockParser:
    """Mock parser for testing."""

    def __init__(self, ast_to_return):
        """Initialize with AST to return."""
        self.ast_to_return = ast_to_return

    def parse(self, dsl_text: str):
        """Return mock AST."""
        return self.ast_to_return


class TestLifecycleWorkflowExecutor:
    """Test lifecycle executor basic functionality."""

    def test_create_executor_with_defaults(self):
        """Test creating executor with default dependencies."""
        executor = LifecycleWorkflowExecutor()

        assert executor.task_executor is not None
        assert executor.parser is not None

    def test_create_executor_with_custom_dependencies(self):
        """Test creating executor with custom dependencies."""
        task_executor = MockTaskExecutor()
        parser = MockParser(Literal("test"))

        executor = LifecycleWorkflowExecutor(
            task_executor=task_executor,
            parser=parser
        )

        assert executor.task_executor is task_executor
        assert executor.parser is parser


class TestWorkflowFileReading:
    """Test workflow file reading."""

    def test_read_existing_file(self, tmp_path):
        """Test reading existing workflow file."""
        # Create temp workflow file
        workflow_file = tmp_path / "test.ct"
        workflow_file.write_text("functor test = build")

        executor = LifecycleWorkflowExecutor()
        content = executor._read_workflow_file(str(workflow_file))

        assert content == "functor test = build"

    def test_read_nonexistent_file_raises_error(self):
        """Test reading nonexistent file raises FileNotFoundError."""
        executor = LifecycleWorkflowExecutor()

        with pytest.raises(FileNotFoundError):
            executor._read_workflow_file("/nonexistent/file.ct")


class TestWorkflowValidation:
    """Test workflow validation logic."""

    def test_validate_valid_workflow(self):
        """Test validating valid workflow."""
        executor = LifecycleWorkflowExecutor()

        ast = [Functor("test", Literal("build"))]
        symbol_table = {"test": Literal("build")}

        result = executor._validate_workflow(ast, symbol_table)

        assert result.is_valid is True
        assert len(result.issues) == 0
        assert len(result.checks) > 0

    def test_validate_empty_workflow(self):
        """Test validating empty workflow fails."""
        executor = LifecycleWorkflowExecutor()

        result = executor._validate_workflow([], {})

        assert result.is_valid is False
        assert "Empty workflow" in result.issues[0]

    def test_validate_workflow_with_functors(self):
        """Test validation includes functor count."""
        executor = LifecycleWorkflowExecutor()

        ast = [
            Functor("f1", Literal("task1")),
            Functor("f2", Literal("task2"))
        ]
        symbol_table = {"f1": Literal("task1"), "f2": Literal("task2")}

        result = executor._validate_workflow(ast, symbol_table)

        assert result.is_valid is True
        assert any("2 functors" in check for check in result.checks)


class TestSymbolTableExtraction:
    """Test symbol table extraction from AST."""

    def test_extract_from_functor_list(self):
        """Test extracting functors from list."""
        executor = LifecycleWorkflowExecutor()

        ast = [
            Functor("build", Literal("compile")),
            Functor("test", Literal("pytest"))
        ]

        symbol_table = executor._extract_symbol_table(ast)

        assert "build" in symbol_table
        assert "test" in symbol_table
        assert symbol_table["build"].value == "compile"

    def test_extract_from_empty_list(self):
        """Test extracting from empty AST."""
        executor = LifecycleWorkflowExecutor()

        symbol_table = executor._extract_symbol_table([])

        assert symbol_table == {}

    def test_extract_from_non_list(self):
        """Test extracting from non-list AST."""
        executor = LifecycleWorkflowExecutor()

        ast = Literal("test")
        symbol_table = executor._extract_symbol_table(ast)

        assert symbol_table == {}


class TestMainNodeExtraction:
    """Test main executable node extraction."""

    def test_get_main_from_functor_list(self):
        """Test getting last functor as main node."""
        executor = LifecycleWorkflowExecutor()

        f1 = Functor("first", Literal("task1"))
        f2 = Functor("second", Literal("task2"))
        ast = [f1, f2]

        main = executor._get_main_node(ast)

        assert main is f2

    def test_get_main_from_non_list(self):
        """Test getting main from single node."""
        executor = LifecycleWorkflowExecutor()

        node = Literal("task")
        main = executor._get_main_node(node)

        assert main is node

    def test_get_main_from_empty_list(self):
        """Test getting main from empty list returns None."""
        executor = LifecycleWorkflowExecutor()

        main = executor._get_main_node([])

        assert main is None


class TestTaskCounting:
    """Test task counting logic."""

    def test_count_primitive_task(self):
        """Test counting primitive task."""
        executor = LifecycleWorkflowExecutor()

        node = Literal("task")
        count = executor._count_tasks(node)

        assert count == 1

    def test_count_composition(self):
        """Test counting composition."""
        executor = LifecycleWorkflowExecutor()

        node = Composition(Literal("f"), Literal("g"))
        count = executor._count_tasks(node)

        assert count == 2

    def test_count_functor(self):
        """Test counting functor."""
        executor = LifecycleWorkflowExecutor()

        node = Functor("test", Literal("task"))
        count = executor._count_tasks(node)

        assert count == 1


@pytest.mark.asyncio
class TestWorkflowExecution:
    """Test complete workflow execution with lifecycle."""

    async def test_execute_simple_workflow(self, tmp_path):
        """Test executing simple workflow file."""
        # Create workflow file
        workflow_file = tmp_path / "simple.ct"
        workflow_file.write_text("functor main = build")

        # Create executor with mock dependencies
        task_executor = MockTaskExecutor()
        executor = LifecycleWorkflowExecutor(task_executor=task_executor)

        # Execute
        result = await executor.execute_workflow(str(workflow_file))

        assert result.success is True
        assert result.result is not None
        assert result.lifecycle.get_state() == LifecycleState.COMPLETED
        assert "PLAN" in result.phases_completed
        assert "VERIFY" in result.phases_completed
        assert "DECOMPOSE" in result.phases_completed
        assert "EXECUTE" in result.phases_completed

    async def test_execute_nonexistent_file_fails(self):
        """Test executing nonexistent file fails gracefully."""
        executor = LifecycleWorkflowExecutor()

        result = await executor.execute_workflow("/nonexistent/file.ct")

        assert result.success is False
        assert result.error is not None
        assert "not found" in result.error.lower()

    async def test_execute_empty_workflow_fails_validation(self, tmp_path):
        """Test empty workflow fails at VERIFY phase."""
        # Create empty workflow
        workflow_file = tmp_path / "empty.ct"
        workflow_file.write_text("")

        # Mock parser to return empty AST
        parser = MockParser([])
        executor = LifecycleWorkflowExecutor(parser=parser)

        result = await executor.execute_workflow(str(workflow_file))

        assert result.success is False
        assert "VERIFY" in result.phases_completed
        assert "EXECUTE" not in result.phases_completed
        assert "Validation failed" in result.error

    async def test_execution_tracks_time(self, tmp_path):
        """Test execution tracks elapsed time."""
        workflow_file = tmp_path / "test.ct"
        workflow_file.write_text("functor main = task")

        task_executor = MockTaskExecutor()
        executor = LifecycleWorkflowExecutor(task_executor=task_executor)

        result = await executor.execute_workflow(str(workflow_file))

        assert result.execution_time > 0


@pytest.mark.asyncio
class TestLifecyclePhases:
    """Test lifecycle phase progression."""

    async def test_phases_progress_sequentially(self, tmp_path):
        """Test phases execute in correct order."""
        workflow_file = tmp_path / "workflow.ct"
        workflow_file.write_text("functor test = build")

        task_executor = MockTaskExecutor()
        executor = LifecycleWorkflowExecutor(task_executor=task_executor)

        result = await executor.execute_workflow(str(workflow_file))

        # Check phase order
        phases = result.phases_completed
        assert phases.index("PLAN") < phases.index("VERIFY")
        assert phases.index("VERIFY") < phases.index("DECOMPOSE")
        assert phases.index("DECOMPOSE") < phases.index("EXECUTE")

    async def test_failure_stops_progression(self, tmp_path):
        """Test failure at VERIFY stops further phases."""
        workflow_file = tmp_path / "invalid.ct"
        workflow_file.write_text("")

        parser = MockParser([])  # Empty AST fails validation
        executor = LifecycleWorkflowExecutor(parser=parser)

        result = await executor.execute_workflow(str(workflow_file))

        assert "VERIFY" in result.phases_completed
        assert "EXECUTE" not in result.phases_completed
        assert result.lifecycle.get_state() == LifecycleState.FAILED


class TestValidationResult:
    """Test ValidationResult dataclass."""

    def test_create_valid_result(self):
        """Test creating valid validation result."""
        result = ValidationResult(
            is_valid=True,
            issues=[],
            checks=["check1", "check2"]
        )

        assert result.is_valid is True
        assert len(result.issues) == 0
        assert len(result.checks) == 2

    def test_create_invalid_result(self):
        """Test creating invalid validation result."""
        result = ValidationResult(
            is_valid=False,
            issues=["error1", "error2"],
            checks=[]
        )

        assert result.is_valid is False
        assert len(result.issues) == 2


class TestWorkflowExecutionResult:
    """Test WorkflowExecutionResult dataclass."""

    def test_create_success_result(self):
        """Test creating successful execution result."""
        from src.entities.lifecycle import Lifecycle

        lifecycle = Lifecycle()
        # Go through all phases to reach COMPLETED
        lifecycle.plan()
        lifecycle.verify(verification_result=True)
        lifecycle.decompose()
        lifecycle.execute()
        lifecycle.complete()

        result = WorkflowExecutionResult(
            success=True,
            result={"output": "data"},
            lifecycle=lifecycle,
            execution_time=1.5,
            phases_completed=["PLAN", "VERIFY", "DECOMPOSE", "EXECUTE"]
        )

        assert result.success is True
        assert result.error is None
        assert result.execution_time == 1.5

    def test_create_failure_result(self):
        """Test creating failed execution result."""
        from src.entities.lifecycle import Lifecycle

        lifecycle = Lifecycle()
        lifecycle.fail(error="test error")

        result = WorkflowExecutionResult(
            success=False,
            result=None,
            lifecycle=lifecycle,
            execution_time=0.5,
            phases_completed=["PLAN"],
            error="test error"
        )

        assert result.success is False
        assert result.error == "test error"
