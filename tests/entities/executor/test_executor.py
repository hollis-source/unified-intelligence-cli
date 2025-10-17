"""Unit tests for Executor abstraction.

Tests cover executor interface, local executor implementation,
execution results, and executor pool management.
"""

import pytest
from src.entity.executor import Executor, ExecutorStatus, ExecutionResult
from src.entity.executor.executor import LocalExecutor, ExecutorPool


class MockTask:
    """Mock task for testing."""

    def __init__(self, task_id: str, command: str = None):
        """Initialize mock task."""
        self.entity_id = task_id
        self.command = command


class TestExecutionResult:
    """Test ExecutionResult dataclass."""

    def test_create_successful_result(self):
        """Test creating successful execution result."""
        result = ExecutionResult(
            success=True,
            output={"data": "processed"},
            duration=1.5
        )

        assert result.success is True
        assert result.output == {"data": "processed"}
        assert result.duration == 1.5
        assert result.error is None

    def test_create_failed_result(self):
        """Test creating failed execution result."""
        result = ExecutionResult(
            success=False,
            error="Task failed",
            duration=0.5
        )

        assert result.success is False
        assert result.error == "Task failed"
        assert result.output is None

    def test_result_with_metadata(self):
        """Test execution result with metadata."""
        result = ExecutionResult(
            success=True,
            metadata={"executor": "local", "retries": 0}
        )

        assert result.metadata["executor"] == "local"
        assert result.metadata["retries"] == 0


class TestExecutorBase:
    """Test Executor base class."""

    def test_create_executor(self):
        """Test creating executor with ID and name."""
        # Can't instantiate abstract class directly, use LocalExecutor
        executor = LocalExecutor(executor_id="exec_1", name="Test Executor")

        assert executor.executor_id == "exec_1"
        assert executor.name == "Test Executor"
        assert executor.status == ExecutorStatus.IDLE

    def test_create_executor_without_name(self):
        """Test creating executor without explicit name."""
        executor = LocalExecutor(executor_id="exec_1")

        assert "Executor-exec_1" in executor.name

    def test_get_status(self):
        """Test getting executor status."""
        executor = LocalExecutor(executor_id="exec_1")

        status = executor.get_status()

        assert status == ExecutorStatus.IDLE

    def test_is_available_when_idle(self):
        """Test is_available() returns True when IDLE."""
        executor = LocalExecutor(executor_id="exec_1")

        assert executor.is_available() is True

    def test_is_available_when_busy(self):
        """Test is_available() returns False when BUSY."""
        executor = LocalExecutor(executor_id="exec_1")
        executor.status = ExecutorStatus.BUSY

        assert executor.is_available() is False

    def test_is_busy_when_busy(self):
        """Test is_busy() returns True when BUSY."""
        executor = LocalExecutor(executor_id="exec_1")
        executor.status = ExecutorStatus.BUSY

        assert executor.is_busy() is True

    def test_is_busy_when_idle(self):
        """Test is_busy() returns False when IDLE."""
        executor = LocalExecutor(executor_id="exec_1")

        assert executor.is_busy() is False

    def test_get_current_task_none_when_idle(self):
        """Test get_current_task() returns None when idle."""
        executor = LocalExecutor(executor_id="exec_1")

        assert executor.get_current_task() is None

    def test_get_current_task_when_busy(self):
        """Test get_current_task() returns task ID when busy."""
        executor = LocalExecutor(executor_id="exec_1")
        executor.status = ExecutorStatus.BUSY
        executor.current_task_id = "task_123"

        assert executor.get_current_task() == "task_123"

    def test_get_execution_count_initial(self):
        """Test execution count starts at zero."""
        executor = LocalExecutor(executor_id="exec_1")

        assert executor.get_execution_count() == 0

    def test_set_and_get_metadata(self):
        """Test setting and getting metadata."""
        executor = LocalExecutor(executor_id="exec_1")

        executor.set_metadata("region", "us-west")
        executor.set_metadata("capacity", 10)

        assert executor.get_metadata("region") == "us-west"
        assert executor.get_metadata("capacity") == 10

    def test_get_metadata_with_default(self):
        """Test getting nonexistent metadata with default."""
        executor = LocalExecutor(executor_id="exec_1")

        value = executor.get_metadata("missing", default="default_value")

        assert value == "default_value"


class TestLocalExecutor:
    """Test LocalExecutor implementation."""

    def test_can_execute_callable(self):
        """Test can_execute() with callable task."""
        executor = LocalExecutor(executor_id="exec_1")

        def task_function():
            return "result"

        assert executor.can_execute(task_function) is True

    def test_can_execute_with_command(self):
        """Test can_execute() with task that has command."""
        executor = LocalExecutor(executor_id="exec_1")
        task = MockTask(task_id="task_1", command="echo hello")

        assert executor.can_execute(task) is True

    def test_can_execute_invalid_task(self):
        """Test can_execute() with invalid task."""
        executor = LocalExecutor(executor_id="exec_1")
        task = object()  # Object without command or callable

        assert executor.can_execute(task) is False

    def test_execute_callable_success(self):
        """Test executing callable task successfully."""
        executor = LocalExecutor(executor_id="exec_1")

        def task_function(value=10):
            return value * 2

        result = executor.execute(task_function, value=5)

        assert result.success is True
        assert result.output == 10
        assert result.error is None
        assert executor.execution_count == 1

    def test_execute_with_command(self):
        """Test executing task with command."""
        executor = LocalExecutor(executor_id="exec_1")
        task = MockTask(task_id="task_1", command="echo hello")

        result = executor.execute(task)

        assert result.success is True
        assert "Executed: echo hello" in result.output

    def test_execute_callable_failure(self):
        """Test executing callable that raises exception."""
        executor = LocalExecutor(executor_id="exec_1")

        def failing_task():
            raise ValueError("Task failed")

        result = executor.execute(failing_task)

        assert result.success is False
        assert "Task failed" in result.error
        assert executor.status == ExecutorStatus.FAILED

    def test_execute_updates_status_to_busy(self):
        """Test execute() sets status to BUSY during execution."""
        executor = LocalExecutor(executor_id="exec_1")

        # Task that checks status mid-execution
        statuses = []

        def task():
            statuses.append(executor.status)
            return "done"

        executor.execute(task)

        # Status should have been BUSY during execution
        assert ExecutorStatus.BUSY in statuses

    def test_execute_returns_to_idle_after_success(self):
        """Test execute() returns to IDLE after successful execution."""
        executor = LocalExecutor(executor_id="exec_1")

        result = executor.execute(lambda: "result")

        assert result.success is True
        assert executor.status == ExecutorStatus.IDLE

    def test_execute_increments_count(self):
        """Test execute() increments execution count."""
        executor = LocalExecutor(executor_id="exec_1")

        executor.execute(lambda: "task1")
        executor.execute(lambda: "task2")
        executor.execute(lambda: "task3")

        assert executor.get_execution_count() == 3

    def test_execute_records_duration(self):
        """Test execute() records execution duration."""
        executor = LocalExecutor(executor_id="exec_1")

        result = executor.execute(lambda: "result")

        assert result.duration >= 0

    def test_execute_invalid_task_returns_failure(self):
        """Test executing invalid task returns failure result."""
        executor = LocalExecutor(executor_id="exec_1")
        invalid_task = object()

        result = executor.execute(invalid_task)

        assert result.success is False
        assert "not executable" in result.error

    def test_cancel_current_task(self):
        """Test cancelling currently running task."""
        executor = LocalExecutor(executor_id="exec_1")
        executor.status = ExecutorStatus.BUSY
        executor.current_task_id = "task_123"

        success = executor.cancel("task_123")

        assert success is True
        assert executor.status == ExecutorStatus.IDLE
        assert executor.current_task_id is None

    def test_cancel_different_task(self):
        """Test cancelling different task returns False."""
        executor = LocalExecutor(executor_id="exec_1")
        executor.status = ExecutorStatus.BUSY
        executor.current_task_id = "task_123"

        success = executor.cancel("task_456")

        assert success is False
        assert executor.current_task_id == "task_123"  # Still set


class TestExecutorPool:
    """Test ExecutorPool management."""

    def test_create_empty_pool(self):
        """Test creating empty executor pool."""
        pool = ExecutorPool()

        assert pool.get_executor_count() == 0

    def test_register_executor(self):
        """Test registering executor to pool."""
        pool = ExecutorPool()
        executor = LocalExecutor(executor_id="exec_1")

        pool.register_executor(executor)

        assert pool.get_executor_count() == 1

    def test_register_multiple_executors(self):
        """Test registering multiple executors."""
        pool = ExecutorPool()

        for i in range(3):
            pool.register_executor(LocalExecutor(executor_id=f"exec_{i}"))

        assert pool.get_executor_count() == 3

    def test_get_executor_by_id(self):
        """Test retrieving executor by ID."""
        pool = ExecutorPool()
        executor = LocalExecutor(executor_id="exec_1")
        pool.register_executor(executor)

        retrieved = pool.get_executor("exec_1")

        assert retrieved is executor

    def test_get_nonexistent_executor(self):
        """Test retrieving nonexistent executor returns None."""
        pool = ExecutorPool()

        retrieved = pool.get_executor("missing")

        assert retrieved is None

    def test_unregister_executor(self):
        """Test removing executor from pool."""
        pool = ExecutorPool()
        executor = LocalExecutor(executor_id="exec_1")
        pool.register_executor(executor)

        success = pool.unregister_executor("exec_1")

        assert success is True
        assert pool.get_executor_count() == 0

    def test_unregister_nonexistent_executor(self):
        """Test unregistering nonexistent executor returns False."""
        pool = ExecutorPool()

        success = pool.unregister_executor("missing")

        assert success is False

    def test_get_available_executor_when_available(self):
        """Test finding available executor."""
        pool = ExecutorPool()
        executor = LocalExecutor(executor_id="exec_1")
        pool.register_executor(executor)

        available = pool.get_available_executor()

        assert available is executor

    def test_get_available_executor_when_all_busy(self):
        """Test finding available executor when all busy."""
        pool = ExecutorPool()
        executor = LocalExecutor(executor_id="exec_1")
        executor.status = ExecutorStatus.BUSY
        pool.register_executor(executor)

        available = pool.get_available_executor()

        assert available is None

    def test_get_available_executor_with_task_matching(self):
        """Test finding available executor that can handle task."""
        pool = ExecutorPool()
        executor = LocalExecutor(executor_id="exec_1")
        pool.register_executor(executor)

        def valid_task():
            return "result"

        available = pool.get_available_executor(task=valid_task)

        assert available is executor

    def test_get_available_executor_prefers_capable(self):
        """Test get_available_executor prefers executor capable of task."""
        pool = ExecutorPool()
        exec1 = LocalExecutor(executor_id="exec_1")
        pool.register_executor(exec1)

        task = MockTask(task_id="task_1", command="echo test")

        available = pool.get_available_executor(task=task)

        assert available is exec1

    def test_execute_task_success(self):
        """Test executing task via pool."""
        pool = ExecutorPool()
        executor = LocalExecutor(executor_id="exec_1")
        pool.register_executor(executor)

        result = pool.execute_task(lambda: "result")

        assert result is not None
        assert result.success is True
        assert result.output == "result"

    def test_execute_task_no_available_executor(self):
        """Test executing task when no executor available."""
        pool = ExecutorPool()

        result = pool.execute_task(lambda: "result")

        assert result is None

    def test_get_pool_status_all_idle(self):
        """Test pool status with all executors idle."""
        pool = ExecutorPool()
        pool.register_executor(LocalExecutor(executor_id="exec_1"))
        pool.register_executor(LocalExecutor(executor_id="exec_2"))

        status = pool.get_pool_status()

        assert status["idle"] == 2
        assert status["busy"] == 0

    def test_get_pool_status_mixed(self):
        """Test pool status with mixed executor states."""
        pool = ExecutorPool()

        exec1 = LocalExecutor(executor_id="exec_1")
        exec2 = LocalExecutor(executor_id="exec_2")
        exec2.status = ExecutorStatus.BUSY

        exec3 = LocalExecutor(executor_id="exec_3")
        exec3.status = ExecutorStatus.FAILED

        pool.register_executor(exec1)
        pool.register_executor(exec2)
        pool.register_executor(exec3)

        status = pool.get_pool_status()

        assert status["idle"] == 1
        assert status["busy"] == 1
        assert status["failed"] == 1

    def test_get_pool_status_empty_pool(self):
        """Test pool status for empty pool."""
        pool = ExecutorPool()

        status = pool.get_pool_status()

        assert status["idle"] == 0
        assert status["busy"] == 0


class TestExecutorRepresentation:
    """Test executor string representation."""

    def test_executor_repr(self):
        """Test __repr__() for executor."""
        executor = LocalExecutor(executor_id="exec_1", name="My Executor")

        repr_str = repr(executor)

        assert "LocalExecutor" in repr_str
        assert "exec_1" in repr_str
        assert "My Executor" in repr_str
        assert "IDLE" in repr_str
