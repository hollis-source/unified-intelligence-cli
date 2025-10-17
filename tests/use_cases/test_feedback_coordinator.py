"""Tests for feedback coordinator use case.

Tests feedback-driven replanning with failure classification and strategies.
"""

import pytest
from src.use_cases.feedback_coordinator import (
    FeedbackCoordinatorUseCase,
    FailureType,
    ReplanningStrategy
)
from src.entity.execution import ExecutionResult, ExecutionStatus


def create_failed_result(task_id: str, error: str) -> ExecutionResult:
    """Helper to create failed execution result."""
    return ExecutionResult(
        status=ExecutionStatus.FAILURE,
        output=None,
        errors=[error],
        metadata={"task_id": task_id}
    )


def test_analyze_failures_empty():
    """Test failure analysis with no failures."""
    coordinator = FeedbackCoordinatorUseCase()
    
    analysis = coordinator.analyze_failures([])
    
    assert analysis["total_failures"] == 0
    assert analysis["failure_types"] == {}
    assert analysis["error_messages"] == []
    assert analysis["task_ids"] == []
    assert analysis["recommended_strategy"] is None


def test_analyze_failures_timeout():
    """Test failure analysis with timeout errors."""
    coordinator = FeedbackCoordinatorUseCase()
    
    failed_tasks = [
        create_failed_result("task1", "Task timed out after 60s"),
        create_failed_result("task2", "Execution timeout exceeded")
    ]
    
    analysis = coordinator.analyze_failures(failed_tasks)
    
    assert analysis["total_failures"] == 2
    assert analysis["failure_types"]["TIMEOUT"] == 2
    assert len(analysis["error_messages"]) == 2
    assert "task1" in analysis["task_ids"]
    assert "task2" in analysis["task_ids"]
    assert analysis["recommended_strategy"] == "RETRY_WITH_DIFFERENT_MODEL"


def test_analyze_failures_dependency():
    """Test failure analysis with dependency errors."""
    coordinator = FeedbackCoordinatorUseCase()
    
    failed_tasks = [
        create_failed_result("task1", "Dependency not satisfied"),
        create_failed_result("task2", "Precondition failed: file_exists")
    ]
    
    analysis = coordinator.analyze_failures(failed_tasks)
    
    assert analysis["total_failures"] == 2
    assert analysis["failure_types"]["DEPENDENCY_MISSING"] == 2
    assert analysis["recommended_strategy"] == "REORDER_DEPENDENCIES"


def test_analyze_failures_model():
    """Test failure analysis with model errors."""
    coordinator = FeedbackCoordinatorUseCase()
    
    failed_tasks = [
        create_failed_result("task1", "LLM provider error"),
        create_failed_result("task2", "Model generation failed")
    ]
    
    analysis = coordinator.analyze_failures(failed_tasks)
    
    assert analysis["total_failures"] == 2
    assert analysis["failure_types"]["MODEL_FAILURE"] == 2
    assert analysis["recommended_strategy"] == "RETRY_WITH_DIFFERENT_MODEL"


def test_analyze_failures_validation():
    """Test failure analysis with validation errors."""
    coordinator = FeedbackCoordinatorUseCase()
    
    failed_tasks = [
        create_failed_result("task1", "Validation failed: invalid input"),
        create_failed_result("task2", "Invalid task configuration")
    ]
    
    analysis = coordinator.analyze_failures(failed_tasks)
    
    assert analysis["total_failures"] == 2
    assert analysis["failure_types"]["VALIDATION_ERROR"] == 2
    assert analysis["recommended_strategy"] == "REFINE_DECOMPOSITION"


def test_analyze_failures_resource():
    """Test failure analysis with resource errors."""
    coordinator = FeedbackCoordinatorUseCase()
    
    failed_tasks = [
        create_failed_result("task1", "Resource unavailable"),
        create_failed_result("task2", "Service unavailable")
    ]
    
    analysis = coordinator.analyze_failures(failed_tasks)
    
    assert analysis["total_failures"] == 2
    assert analysis["failure_types"]["RESOURCE_UNAVAILABLE"] == 2
    assert analysis["recommended_strategy"] == "SKIP_TASK"


def test_analyze_failures_mixed():
    """Test failure analysis with mixed error types."""
    coordinator = FeedbackCoordinatorUseCase()
    
    failed_tasks = [
        create_failed_result("task1", "Task timed out"),
        create_failed_result("task2", "Dependency not satisfied"),
        create_failed_result("task3", "Unknown error")
    ]
    
    analysis = coordinator.analyze_failures(failed_tasks)
    
    assert analysis["total_failures"] == 3
    assert analysis["failure_types"]["TIMEOUT"] == 1
    assert analysis["failure_types"]["DEPENDENCY_MISSING"] == 1
    assert analysis["failure_types"]["UNKNOWN"] == 1


def test_should_replan_within_limits():
    """Test replanning approval within limits."""
    coordinator = FeedbackCoordinatorUseCase(max_retries=3)
    
    analysis = {
        "total_failures": 2,
        "recommended_strategy": "RETRY_WITH_SAME_CONFIG"
    }
    
    assert coordinator.should_replan(analysis, attempt_count=1) is True
    assert coordinator.should_replan(analysis, attempt_count=2) is True


def test_should_replan_max_retries_exceeded():
    """Test replanning rejection when max retries exceeded."""
    coordinator = FeedbackCoordinatorUseCase(max_retries=3)
    
    analysis = {
        "total_failures": 2,
        "recommended_strategy": "RETRY_WITH_SAME_CONFIG"
    }
    
    assert coordinator.should_replan(analysis, attempt_count=3) is False


def test_should_replan_max_failures_exceeded():
    """Test replanning rejection when max failures exceeded."""
    coordinator = FeedbackCoordinatorUseCase(max_total_failures=5)
    
    analysis = {
        "total_failures": 6,
        "recommended_strategy": "RETRY_WITH_SAME_CONFIG"
    }
    
    assert coordinator.should_replan(analysis, attempt_count=1) is False


def test_should_replan_fail_project_strategy():
    """Test replanning rejection when strategy is FAIL_PROJECT."""
    coordinator = FeedbackCoordinatorUseCase()
    
    analysis = {
        "total_failures": 2,
        "recommended_strategy": "FAIL_PROJECT"
    }
    
    assert coordinator.should_replan(analysis, attempt_count=1) is False


def test_replan_retry_same_config():
    """Test replanning with retry same config strategy."""
    coordinator = FeedbackCoordinatorUseCase()
    
    failed_tasks = [
        create_failed_result("task1", "Transient error"),
        create_failed_result("task2", "Temporary failure")
    ]
    
    analysis = {
        "total_failures": 2,
        "failure_types": {"UNKNOWN": 2},
        "recommended_strategy": "RETRY_WITH_SAME_CONFIG"
    }
    
    context = {}
    
    plan = coordinator.replan(failed_tasks, analysis, context)
    
    assert plan["strategy"] == "RETRY_WITH_SAME_CONFIG"
    assert len(plan["actions"]) == 2
    assert plan["actions"][0]["type"] == "retry"
    assert plan["actions"][0]["config"] == "same"
    assert "task1" in plan["modified_tasks"]
    assert "task2" in plan["modified_tasks"]


def test_replan_retry_different_model():
    """Test replanning with different model strategy."""
    coordinator = FeedbackCoordinatorUseCase()
    
    failed_tasks = [
        create_failed_result("task1", "Model timeout")
    ]
    
    analysis = {
        "total_failures": 1,
        "failure_types": {"TIMEOUT": 1},
        "recommended_strategy": "RETRY_WITH_DIFFERENT_MODEL"
    }
    
    context = {
        "available_models": ["grok", "granite", "tongyi"],
        "current_model": "grok"
    }
    
    plan = coordinator.replan(failed_tasks, analysis, context)
    
    assert plan["strategy"] == "RETRY_WITH_DIFFERENT_MODEL"
    assert len(plan["actions"]) == 1
    assert plan["actions"][0]["type"] == "retry"
    assert plan["actions"][0]["model"] == "granite"  # Next model


def test_replan_reorder_dependencies():
    """Test replanning with reorder dependencies strategy."""
    coordinator = FeedbackCoordinatorUseCase()
    
    failed_tasks = [
        create_failed_result("task1", "Dependency not satisfied")
    ]
    
    analysis = {
        "total_failures": 1,
        "failure_types": {"DEPENDENCY_MISSING": 1},
        "recommended_strategy": "REORDER_DEPENDENCIES"
    }
    
    context = {}
    
    plan = coordinator.replan(failed_tasks, analysis, context)
    
    assert plan["strategy"] == "REORDER_DEPENDENCIES"
    assert len(plan["actions"]) == 1
    assert plan["actions"][0]["type"] == "reorder"
    assert plan["actions"][0]["action"] == "move_to_end"


def test_replan_skip_task():
    """Test replanning with skip task strategy."""
    coordinator = FeedbackCoordinatorUseCase()
    
    failed_tasks = [
        create_failed_result("task1", "Resource unavailable")
    ]
    
    analysis = {
        "total_failures": 1,
        "failure_types": {"RESOURCE_UNAVAILABLE": 1},
        "recommended_strategy": "SKIP_TASK"
    }
    
    context = {}
    
    plan = coordinator.replan(failed_tasks, analysis, context)
    
    assert plan["strategy"] == "SKIP_TASK"
    assert len(plan["actions"]) == 1
    assert plan["actions"][0]["type"] == "skip"
    assert len(plan["modified_tasks"]) == 0  # No tasks to retry


def test_replan_refine_decomposition_raises():
    """Test replanning with refine decomposition raises (not implemented)."""
    coordinator = FeedbackCoordinatorUseCase()
    
    failed_tasks = [
        create_failed_result("task1", "Validation failed")
    ]
    
    analysis = {
        "total_failures": 1,
        "failure_types": {"VALIDATION_ERROR": 1},
        "recommended_strategy": "REFINE_DECOMPOSITION"
    }
    
    context = {}
    
    with pytest.raises(ValueError, match="Refinement requires re-decomposition"):
        coordinator.replan(failed_tasks, analysis, context)


def test_record_failure():
    """Test failure recording."""
    coordinator = FeedbackCoordinatorUseCase()
    
    coordinator.record_failure("task1", "TIMEOUT", "Task timed out")
    coordinator.record_failure("task1", "TIMEOUT", "Task timed out again")
    coordinator.record_failure("task2", "MODEL_FAILURE", "Model error")
    
    history1 = coordinator.get_failure_history("task1")
    history2 = coordinator.get_failure_history("task2")
    history3 = coordinator.get_failure_history("task3")
    
    assert len(history1) == 2
    assert len(history2) == 1
    assert len(history3) == 0
    
    assert history1[0]["failure_type"] == "TIMEOUT"
    assert history1[0]["error_message"] == "Task timed out"
    assert "timestamp" in history1[0]


def test_get_failure_history_empty():
    """Test getting failure history for task with no failures."""
    coordinator = FeedbackCoordinatorUseCase()
    
    history = coordinator.get_failure_history("nonexistent_task")
    
    assert history == []

