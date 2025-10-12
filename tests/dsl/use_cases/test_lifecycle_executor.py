"""Tests for lifecycle-aware DSL workflow executor.

Tests cover lifecycle phases, validation, and error handling.

P1-2: Updated to provide explicit dependencies (task_executor, parser) per DIP.
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
from src.dsl.adapters.parser import Parser
from src.dsl.adapters.cli_task_executor import CLITaskExecutor


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


# P1-2: Helper to create executor with defaults for tests
def create_test_executor(task_executor=None, parser=None):
    """Create lifecycle executor with test defaults.

    P1-2: Since LifecycleWorkflowExecutor no longer provides defaults,
    this helper provides them for test convenience while maintaining DIP.

    Args:
        task_executor: Optional task executor (defaults to MockTaskExecutor)
        parser: Optional parser (defaults to MockParser with Literal("test"))

    Returns:
        LifecycleWorkflowExecutor instance with explicit dependencies
    """
    task_executor = task_executor or MockTaskExecutor()
    parser = parser or MockParser(Literal("test"))
    return LifecycleWorkflowExecutor(task_executor=task_executor, parser=parser)


class TestLifecycleWorkflowExecutor:
    """Test lifecycle executor basic functionality."""

    def test_create_executor_with_defaults(self):
        """Test creating executor with explicit default dependencies.

        P1-2: Defaults are no longer provided by executor - composition root
        (test setup) provides them explicitly per Dependency Inversion Principle.
        """
        # P1-2: Explicitly provide dependencies instead of relying on defaults
        task_executor = MockTaskExecutor()
        parser = MockParser(Literal("test"))

        executor = LifecycleWorkflowExecutor(
            task_executor=task_executor,
            parser=parser
        )

        assert executor.task_executor is task_executor
        assert executor.parser is parser

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

        executor = create_test_executor()
        content = executor._read_workflow_file(str(workflow_file))

        assert content == "functor test = build"

    def test_read_nonexistent_file_raises_error(self):
        """Test reading nonexistent file raises FileNotFoundError."""
        executor = create_test_executor()

        with pytest.raises(FileNotFoundError):
            executor._read_workflow_file("/nonexistent/file.ct")


class TestWorkflowValidation:
    """Test workflow validation logic."""

    def test_validate_valid_workflow(self):
        """Test validating valid workflow."""
        executor = create_test_executor()

        ast = [Functor("test", Literal("build"))]
        symbol_table = {"test": Literal("build")}

        result = executor._validate_workflow(ast, symbol_table)

        assert result.is_valid is True
        assert len(result.issues) == 0
        assert len(result.checks) > 0

    def test_validate_empty_workflow(self):
        """Test validating empty workflow fails."""
        executor = create_test_executor()

        result = executor._validate_workflow([], {})

        assert result.is_valid is False
        assert "Empty workflow" in result.issues[0]

    def test_validate_workflow_with_functors(self):
        """Test validation includes functor count."""
        executor = create_test_executor()

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
        executor = create_test_executor()

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
        executor = create_test_executor()

        symbol_table = executor._extract_symbol_table([])

        assert symbol_table == {}

    def test_extract_from_non_list(self):
        """Test extracting from non-list AST."""
        executor = create_test_executor()

        ast = Literal("test")
        symbol_table = executor._extract_symbol_table(ast)

        assert symbol_table == {}


class TestMainNodeExtraction:
    """Test main executable node extraction."""

    def test_get_main_from_functor_list(self):
        """Test getting last functor as main node."""
        executor = create_test_executor()

        f1 = Functor("first", Literal("task1"))
        f2 = Functor("second", Literal("task2"))
        ast = [f1, f2]

        main = executor._get_main_node(ast)

        assert main is f2

    def test_get_main_from_non_list(self):
        """Test getting main from single node."""
        executor = create_test_executor()

        node = Literal("task")
        main = executor._get_main_node(node)

        assert main is node

    def test_get_main_from_empty_list(self):
        """Test getting main from empty list returns None."""
        executor = create_test_executor()

        main = executor._get_main_node([])

        assert main is None


class TestTaskCounting:
    """Test task counting logic."""

    def test_count_primitive_task(self):
        """Test counting primitive task."""
        executor = create_test_executor()

        node = Literal("task")
        count = executor._count_tasks(node)

        assert count == 1

    def test_count_composition(self):
        """Test counting composition."""
        executor = create_test_executor()

        node = Composition(Literal("f"), Literal("g"))
        count = executor._count_tasks(node)

        assert count == 2

    def test_count_functor(self):
        """Test counting functor."""
        executor = create_test_executor()

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
        executor = LifecycleWorkflowExecutor(task_executor=task_executor, parser=Parser())

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
        executor = create_test_executor()

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
        executor = LifecycleWorkflowExecutor(task_executor=MockTaskExecutor(), parser=parser)

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
        executor = LifecycleWorkflowExecutor(task_executor=task_executor, parser=Parser())

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
        executor = LifecycleWorkflowExecutor(task_executor=task_executor, parser=Parser())

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
        executor = LifecycleWorkflowExecutor(task_executor=MockTaskExecutor(), parser=parser)

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


@pytest.mark.asyncio
class TestResultValidation:
    """Test P1-1 output validation functionality."""

    def test_validate_none_result_fails(self):
        """Test that None result fails validation."""
        executor = create_test_executor()

        is_valid = executor._validate_result(None, verbose=False)

        assert is_valid is False

    def test_validate_dict_with_failed_status_fails(self):
        """Test that dict with FAILED status fails validation."""
        executor = create_test_executor()

        result = {
            'status': 'FAILED',
            'output': None,
            'error': 'Task execution failed',
            'metadata': {}
        }

        is_valid = executor._validate_result(result, verbose=False)

        assert is_valid is False

    def test_validate_dict_with_success_status_passes(self):
        """Test that dict with SUCCESS status and output passes validation."""
        executor = create_test_executor()

        result = {
            'status': 'SUCCESS',
            'output': 'Task completed successfully',
            'metadata': {}
        }

        is_valid = executor._validate_result(result, verbose=False)

        assert is_valid is True

    def test_validate_dict_with_success_but_none_output_warns(self):
        """Test that dict with SUCCESS status but None output logs warning but passes."""
        executor = create_test_executor()

        result = {
            'status': 'SUCCESS',
            'output': None,
            'metadata': {}
        }

        # This should pass (some workflows may have no output)
        # but should log a warning
        is_valid = executor._validate_result(result, verbose=False)

        assert is_valid is True  # Passes but warns

    def test_validate_non_dict_result_passes(self):
        """Test that non-dict, non-None result passes validation."""
        executor = create_test_executor()

        # String result
        is_valid = executor._validate_result("string result", verbose=False)
        assert is_valid is True

        # List result
        is_valid = executor._validate_result(["item1", "item2"], verbose=False)
        assert is_valid is True

        # Object result
        is_valid = executor._validate_result(Literal("test"), verbose=False)
        assert is_valid is True

    async def test_execute_workflow_fails_when_interpreter_returns_none(self, tmp_path):
        """Test that workflow execution fails when interpreter returns None."""
        # Create workflow file
        workflow_file = tmp_path / "test.ct"
        workflow_file.write_text("functor main = task")

        # Create mock task executor that returns None
        class NoneReturningExecutor:
            async def execute_task(self, task_name: str, input_data=None):
                return None  # Simulate silent failure

        executor = LifecycleWorkflowExecutor(
            task_executor=NoneReturningExecutor(),
            parser=Parser()
        )

        result = await executor.execute_workflow(str(workflow_file))

        # Should fail validation
        assert result.success is False
        assert "validation failed" in result.error.lower()
        assert "EXECUTE" in result.phases_completed

    async def test_execute_workflow_fails_when_interpreter_returns_failed_status(self, tmp_path):
        """Test that workflow execution fails when interpreter returns FAILED status."""
        # Create workflow file
        workflow_file = tmp_path / "test.ct"
        workflow_file.write_text("functor main = task")

        # Create mock task executor that returns FAILED status
        class FailedStatusExecutor:
            async def execute_task(self, task_name: str, input_data=None):
                return {
                    'status': 'FAILED',
                    'output': None,
                    'error': 'Task execution failed',
                    'metadata': {}
                }

        executor = LifecycleWorkflowExecutor(
            task_executor=FailedStatusExecutor(),
            parser=Parser()
        )

        result = await executor.execute_workflow(str(workflow_file))

        # Should fail validation
        assert result.success is False
        assert "validation failed" in result.error.lower()
        assert "EXECUTE" in result.phases_completed
