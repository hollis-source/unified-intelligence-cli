# tests/unit/entity/test_execution_comprehensive.py
"""Comprehensive tests for Execution entities."""

import pytest
from src.entity.execution import ExecutionStatus, ExecutionResult, ExecutionContext


# ExecutionStatus Enum Tests

def test_execution_status_values():
    """Test all ExecutionStatus enum values."""
    assert ExecutionStatus.SUCCESS.value == "success"
    assert ExecutionStatus.FAILURE.value == "failure"
    assert ExecutionStatus.PENDING.value == "pending"
    assert ExecutionStatus.RUNNING.value == "running"


def test_execution_status_equality():
    """Test ExecutionStatus enum equality."""
    assert ExecutionStatus.SUCCESS == ExecutionStatus.SUCCESS
    assert ExecutionStatus.SUCCESS != ExecutionStatus.FAILURE


# ExecutionResult Tests

def test_execution_result_creation_minimal():
    """Test ExecutionResult with only required fields."""
    result = ExecutionResult(
        status=ExecutionStatus.SUCCESS,
        output="Task completed"
    )
    assert result.status == ExecutionStatus.SUCCESS
    assert result.output == "Task completed"
    assert result.errors == []
    assert result.metadata == {}
    assert result.error_details is None


def test_execution_result_creation_full():
    """Test ExecutionResult with all fields."""
    error_details = {
        "error_type": "ValidationError",
        "component": "validator",
        "root_cause": "Invalid input",
        "user_message": "Please check your input"
    }

    result = ExecutionResult(
        status=ExecutionStatus.FAILURE,
        output=None,
        errors=["Error 1", "Error 2"],
        metadata={"duration": 5.2, "retries": 3},
        error_details=error_details
    )

    assert result.status == ExecutionStatus.FAILURE
    assert result.output is None
    assert result.errors == ["Error 1", "Error 2"]
    assert result.metadata == {"duration": 5.2, "retries": 3}
    assert result.error_details == error_details


def test_execution_result_success_case():
    """Test successful execution result."""
    result = ExecutionResult(
        status=ExecutionStatus.SUCCESS,
        output={"result": "completed", "data": [1, 2, 3]}
    )
    assert result.status == ExecutionStatus.SUCCESS
    assert result.output == {"result": "completed", "data": [1, 2, 3]}
    assert len(result.errors) == 0


def test_execution_result_failure_with_errors():
    """Test failure result with error messages."""
    result = ExecutionResult(
        status=ExecutionStatus.FAILURE,
        output=None,
        errors=["Connection timeout", "Retry failed"]
    )
    assert result.status == ExecutionStatus.FAILURE
    assert len(result.errors) == 2
    assert "Connection timeout" in result.errors


def test_execution_result_with_error_details():
    """Test ExecutionResult with structured error_details."""
    error_details = {
        "error_type": "ToolError",
        "component": "calculator",
        "input": {"operation": "divide", "x": 10, "y": 0},
        "root_cause": "Division by zero",
        "user_message": "Cannot divide by zero",
        "suggestion": "Please provide a non-zero divisor",
        "context": {"timestamp": "2025-10-14T10:00:00Z"}
    }

    result = ExecutionResult(
        status=ExecutionStatus.FAILURE,
        output=None,
        errors=["Division by zero error"],
        error_details=error_details
    )

    assert result.error_details["error_type"] == "ToolError"
    assert result.error_details["component"] == "calculator"
    assert result.error_details["root_cause"] == "Division by zero"


@pytest.mark.parametrize("status", [
    ExecutionStatus.SUCCESS,
    ExecutionStatus.FAILURE,
    ExecutionStatus.PENDING,
    ExecutionStatus.RUNNING
])
def test_execution_result_all_statuses(status):
    """Test ExecutionResult with all possible statuses."""
    result = ExecutionResult(status=status, output="test")
    assert result.status == status


@pytest.mark.parametrize("output", [
    "string output",
    {"key": "value"},
    [1, 2, 3],
    None,
    42,
    True
])
def test_execution_result_various_output_types(output):
    """Test ExecutionResult with various output types."""
    result = ExecutionResult(status=ExecutionStatus.SUCCESS, output=output)
    assert result.output == output


# ExecutionContext Tests

def test_execution_context_creation_minimal():
    """Test ExecutionContext with only required field."""
    context = ExecutionContext(session_id="session_123")
    assert context.session_id == "session_123"
    assert context.history == []
    assert context.llm_state == {}
    assert context.user_data == {}


def test_execution_context_creation_full():
    """Test ExecutionContext with all fields."""
    history = [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi"}
    ]
    llm_state = {"temperature": 0.7, "model": "gpt-4"}
    user_data = {"user_id": "user_456", "preferences": {"lang": "en"}}

    context = ExecutionContext(
        session_id="session_789",
        history=history,
        llm_state=llm_state,
        user_data=user_data
    )

    assert context.session_id == "session_789"
    assert context.history == history
    assert context.llm_state == llm_state
    assert context.user_data == user_data


def test_execution_context_history_management():
    """Test managing conversation history in ExecutionContext."""
    context = ExecutionContext(session_id="session_001")

    # Add to history
    context.history.append({"role": "user", "content": "First message"})
    context.history.append({"role": "assistant", "content": "Response"})

    assert len(context.history) == 2
    assert context.history[0]["role"] == "user"
    assert context.history[1]["role"] == "assistant"


def test_execution_context_llm_state_updates():
    """Test updating LLM state in ExecutionContext."""
    context = ExecutionContext(session_id="session_002")

    context.llm_state["temperature"] = 0.8
    context.llm_state["max_tokens"] = 2000

    assert context.llm_state["temperature"] == 0.8
    assert context.llm_state["max_tokens"] == 2000


def test_execution_context_user_data_storage():
    """Test storing user data in ExecutionContext."""
    context = ExecutionContext(session_id="session_003")

    context.user_data["user_id"] = "user_123"
    context.user_data["timezone"] = "UTC"

    assert context.user_data["user_id"] == "user_123"
    assert context.user_data["timezone"] == "UTC"


def test_execution_context_independence():
    """Test that ExecutionContext instances are independent."""
    context1 = ExecutionContext(session_id="session_A")
    context2 = ExecutionContext(session_id="session_B")

    context1.history.append({"role": "user", "content": "Message A"})
    context2.history.append({"role": "user", "content": "Message B"})

    assert len(context1.history) == 1
    assert len(context2.history) == 1
    assert context1.history[0]["content"] == "Message A"
    assert context2.history[0]["content"] == "Message B"
