"""Tests for WorkflowExecutionResult validation (Sprint 5 P1-1).

Validates output integrity checks prevent silent failures and data corruption.

Test Coverage:
- Success with valid result (passes)
- Success with None result (fails with ValueError)
- Failure with None result (passes - expected)
- JSON-serializable results (passes)
- Non-JSON-serializable results (warns but passes)
- Logging behavior verification
"""

import pytest
import json
import logging
from unittest.mock import Mock

from src.dsl.use_cases.lifecycle_executor import WorkflowExecutionResult
from src.entity.lifecycle import Lifecycle


class TestWorkflowExecutionResultValidation:
    """Test suite for WorkflowExecutionResult validation."""

    def test_success_with_valid_result_passes(self):
        """Successful workflow with non-None result should pass validation."""
        lifecycle = Lifecycle()
        result = WorkflowExecutionResult(
            success=True,
            result={"status": "completed", "tasks": 5},
            lifecycle=lifecycle,
            execution_time=1.5,
            phases_completed=["PLAN", "VERIFY", "DECOMPOSE", "EXECUTE"]
        )

        assert result.success is True
        assert result.result == {"status": "completed", "tasks": 5}

    def test_success_with_none_result_raises_error(self):
        """Successful workflow with None result should raise ValueError."""
        lifecycle = Lifecycle()

        with pytest.raises(ValueError) as exc_info:
            WorkflowExecutionResult(
                success=True,
                result=None,  # Invalid: success=True requires non-None result
                lifecycle=lifecycle,
                execution_time=1.5,
                phases_completed=["PLAN", "VERIFY"]
            )

        assert "Result validation failed" in str(exc_info.value)
        assert "success=True" in str(exc_info.value)
        assert "must have non-None result" in str(exc_info.value)

    def test_failure_with_none_result_passes(self):
        """Failed workflow with None result should pass validation (expected behavior)."""
        lifecycle = Lifecycle()
        result = WorkflowExecutionResult(
            success=False,
            result=None,  # Valid: failures can have None result
            lifecycle=lifecycle,
            execution_time=0.5,
            phases_completed=["PLAN", "VERIFY"],
            error="Validation failed"
        )

        assert result.success is False
        assert result.result is None
        assert result.error == "Validation failed"

    def test_json_serializable_result_passes(self):
        """Result with JSON-serializable data should pass without warnings."""
        lifecycle = Lifecycle()
        json_data = {
            "tasks": ["task1", "task2"],
            "count": 2,
            "metrics": {"duration": 1.5, "success_rate": 0.95}
        }

        result = WorkflowExecutionResult(
            success=True,
            result=json_data,
            lifecycle=lifecycle,
            execution_time=1.5,
            phases_completed=["PLAN", "VERIFY", "DECOMPOSE", "EXECUTE"]
        )

        # Verify it's actually JSON-serializable
        json_str = json.dumps(result.result)
        assert json.loads(json_str) == json_data

    def test_non_json_serializable_result_warns(self, caplog):
        """Result with non-JSON-serializable data should warn but not fail."""
        lifecycle = Lifecycle()

        # Custom class that's not JSON-serializable
        class CustomResult:
            def __init__(self, value):
                self.value = value

        with caplog.at_level(logging.WARNING):
            result = WorkflowExecutionResult(
                success=True,
                result=CustomResult("test"),
                lifecycle=lifecycle,
                execution_time=1.5,
                phases_completed=["PLAN", "VERIFY", "DECOMPOSE", "EXECUTE"]
            )

        # Should create result (not fail)
        assert result.success is True
        assert isinstance(result.result, CustomResult)

        # Should log warning
        assert any("not JSON-serializable" in record.message for record in caplog.records)

    def test_string_result_is_valid(self):
        """Simple string result should be valid and JSON-serializable."""
        lifecycle = Lifecycle()
        result = WorkflowExecutionResult(
            success=True,
            result="workflow completed successfully",
            lifecycle=lifecycle,
            execution_time=1.0,
            phases_completed=["PLAN", "VERIFY", "DECOMPOSE", "EXECUTE"]
        )

        assert result.success is True
        assert result.result == "workflow completed successfully"
        # Verify JSON-serializable
        assert json.dumps(result.result) == '"workflow completed successfully"'

    def test_list_result_is_valid(self):
        """List result should be valid and JSON-serializable."""
        lifecycle = Lifecycle()
        result = WorkflowExecutionResult(
            success=True,
            result=["task1", "task2", "task3"],
            lifecycle=lifecycle,
            execution_time=2.0,
            phases_completed=["PLAN", "VERIFY", "DECOMPOSE", "EXECUTE"]
        )

        assert result.success is True
        assert len(result.result) == 3
        # Verify JSON-serializable
        json_str = json.dumps(result.result)
        assert json.loads(json_str) == ["task1", "task2", "task3"]

    def test_nested_dict_result_is_valid(self):
        """Nested dictionary result should be valid and JSON-serializable."""
        lifecycle = Lifecycle()
        result = WorkflowExecutionResult(
            success=True,
            result={
                "workflow": {
                    "name": "test_workflow",
                    "tasks": [
                        {"id": "task1", "status": "completed"},
                        {"id": "task2", "status": "completed"}
                    ]
                },
                "metrics": {
                    "total_time": 5.2,
                    "task_count": 2
                }
            },
            lifecycle=lifecycle,
            execution_time=5.2,
            phases_completed=["PLAN", "VERIFY", "DECOMPOSE", "EXECUTE", "COMPLETE"]
        )

        assert result.success is True
        # Verify JSON-serializable
        json_str = json.dumps(result.result)
        assert "test_workflow" in json_str

    def test_validation_logging_debug_level(self, caplog):
        """Validation should log at debug level for successful validations."""
        lifecycle = Lifecycle()

        with caplog.at_level(logging.DEBUG):
            result = WorkflowExecutionResult(
                success=True,
                result={"data": "test"},
                lifecycle=lifecycle,
                execution_time=1.0,
                phases_completed=["PLAN", "VERIFY", "DECOMPOSE", "EXECUTE"]
            )

        # Should log validation success at DEBUG level
        debug_messages = [r.message for r in caplog.records if r.levelname == "DEBUG"]
        assert any("Result validation passed" in msg for msg in debug_messages)

    def test_validation_logging_error_level(self, caplog):
        """Validation should log at error level for critical failures."""
        lifecycle = Lifecycle()

        with caplog.at_level(logging.ERROR):
            try:
                WorkflowExecutionResult(
                    success=True,
                    result=None,
                    lifecycle=lifecycle,
                    execution_time=1.0,
                    phases_completed=["PLAN"]
                )
            except ValueError:
                pass  # Expected

        # Should log error before raising ValueError
        error_messages = [r.message for r in caplog.records if r.levelname == "ERROR"]
        assert any("Result validation failed" in msg for msg in error_messages)

    def test_empty_dict_result_is_valid(self):
        """Empty dictionary result should be valid (edge case)."""
        lifecycle = Lifecycle()
        result = WorkflowExecutionResult(
            success=True,
            result={},
            lifecycle=lifecycle,
            execution_time=0.1,
            phases_completed=["PLAN", "VERIFY", "DECOMPOSE", "EXECUTE"]
        )

        assert result.success is True
        assert result.result == {}

    def test_empty_list_result_is_valid(self):
        """Empty list result should be valid (edge case)."""
        lifecycle = Lifecycle()
        result = WorkflowExecutionResult(
            success=True,
            result=[],
            lifecycle=lifecycle,
            execution_time=0.1,
            phases_completed=["PLAN", "VERIFY", "DECOMPOSE", "EXECUTE"]
        )

        assert result.success is True
        assert result.result == []

    def test_zero_result_is_valid(self):
        """Zero/false-y values should be valid (not confused with None)."""
        lifecycle = Lifecycle()

        # Test with 0
        result = WorkflowExecutionResult(
            success=True,
            result=0,
            lifecycle=lifecycle,
            execution_time=0.5,
            phases_completed=["PLAN", "VERIFY", "DECOMPOSE", "EXECUTE"]
        )
        assert result.result == 0

        # Test with False
        result = WorkflowExecutionResult(
            success=True,
            result=False,
            lifecycle=lifecycle,
            execution_time=0.5,
            phases_completed=["PLAN", "VERIFY", "DECOMPOSE", "EXECUTE"]
        )
        assert result.result is False

        # Test with empty string
        result = WorkflowExecutionResult(
            success=True,
            result="",
            lifecycle=lifecycle,
            execution_time=0.5,
            phases_completed=["PLAN", "VERIFY", "DECOMPOSE", "EXECUTE"]
        )
        assert result.result == ""
