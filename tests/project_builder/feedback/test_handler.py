"""Tests for FeedbackLoopHandler - Failure detection and replanning.

Tests cover:
- Failure classification (timeout, dependency, model, precondition, resource)
- Replanning strategy selection
- State updates after replanning
- Failure history tracking
- Max retry limits
"""

import pytest
from unittest.mock import Mock

from src.project_builder.feedback.handler import (
    FeedbackLoopHandler,
    FailureType,
    ReplanningStrategy
)
from src.interfaces import ProjectState, ExecutionResult, TaskStatus
from src.entity.htn.htn_node import HTNNode


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def handler():
    """Create FeedbackLoopHandler with default settings."""
    return FeedbackLoopHandler(max_retries=3)


@pytest.fixture
def sample_state():
    """Create sample ProjectState."""
    htn_graph = HTNNode(
        task_id="root",
        description="Root task",
        subtasks=[
            HTNNode(task_id="task1", description="Task 1"),
            HTNNode(task_id="task2", description="Task 2"),
            HTNNode(task_id="task3", description="Task 3")
        ]
    )
    
    state = Mock(spec=ProjectState)
    state.project_id = "test-project"
    state.htn_graph = htn_graph
    state.world_state = {}
    state.task_status = {
        "task1": TaskStatus.COMPLETED,
        "task2": TaskStatus.FAILED,
        "task3": TaskStatus.PENDING
    }
    state.copy = Mock(return_value=state)
    
    return state


@pytest.fixture
def timeout_failure():
    """Create timeout failure result."""
    return ExecutionResult(
        task_id="task1",
        success=False,
        effects={},
        error="Task timed out after 120 seconds",
        metadata={"model": "qwen3", "agent": "Backend Engineer"}
    )


@pytest.fixture
def dependency_failure():
    """Create dependency failure result."""
    return ExecutionResult(
        task_id="task2",
        success=False,
        effects={},
        error="Dependency missing: required file not found",
        metadata={"model": "qwen3", "agent": "Backend Engineer"}
    )


@pytest.fixture
def model_failure():
    """Create model failure result."""
    return ExecutionResult(
        task_id="task3",
        success=False,
        effects={},
        error="Model generation failed: quota exceeded",
        metadata={"model": "gpt-4", "agent": "Frontend Engineer"}
    )


@pytest.fixture
def precondition_failure():
    """Create precondition violation failure."""
    return ExecutionResult(
        task_id="task4",
        success=False,
        effects={},
        error="Preconditions not satisfied: file_path required",
        metadata={"model": "qwen3", "agent": "Backend Engineer"}
    )


# ============================================================================
# Test Classes
# ============================================================================

class TestFeedbackLoopHandlerInit:
    """Tests for FeedbackLoopHandler initialization."""
    
    def test_init_default_max_retries(self):
        """Test initialization with default max_retries."""
        handler = FeedbackLoopHandler()
        assert handler.max_retries == 3
    
    def test_init_custom_max_retries(self):
        """Test initialization with custom max_retries."""
        handler = FeedbackLoopHandler(max_retries=5)
        assert handler.max_retries == 5
    
    def test_init_empty_failure_history(self, handler):
        """Test that failure history is initialized empty."""
        assert handler.failure_history == {}


class TestFailureClassification:
    """Tests for failure type classification."""
    
    def test_classify_timeout_failure(self, handler, timeout_failure):
        """Test classification of timeout failures."""
        failure_type = handler._classify_failure(timeout_failure)
        assert failure_type == FailureType.TIMEOUT
    
    def test_classify_dependency_failure(self, handler, dependency_failure):
        """Test classification of dependency failures."""
        failure_type = handler._classify_failure(dependency_failure)
        assert failure_type == FailureType.DEPENDENCY_MISSING
    
    def test_classify_model_failure(self, handler, model_failure):
        """Test classification of model failures."""
        failure_type = handler._classify_failure(model_failure)
        assert failure_type == FailureType.MODEL_FAILURE
    
    def test_classify_precondition_failure(self, handler, precondition_failure):
        """Test classification of precondition violations."""
        failure_type = handler._classify_failure(precondition_failure)
        assert failure_type == FailureType.PRECONDITION_VIOLATION
    
    def test_classify_resource_unavailable(self, handler):
        """Test classification of resource unavailable failures."""
        failure = ExecutionResult(
            task_id="task1",
            success=False,
            effects={},
            error="Resource unavailable: database connection failed",
            metadata={}
        )
        
        failure_type = handler._classify_failure(failure)
        assert failure_type == FailureType.RESOURCE_UNAVAILABLE
    
    def test_classify_unknown_failure(self, handler):
        """Test classification of unknown failures."""
        failure = ExecutionResult(
            task_id="task1",
            success=False,
            effects={},
            error="Something went wrong",
            metadata={}
        )
        
        failure_type = handler._classify_failure(failure)
        assert failure_type == FailureType.UNKNOWN


class TestFailureAnalysis:
    """Tests for failure analysis."""
    
    def test_analyze_failures_counts_total(
        self,
        handler,
        timeout_failure,
        dependency_failure
    ):
        """Test that failure analysis counts total failures."""
        failed_tasks = [timeout_failure, dependency_failure]
        
        analysis = handler._analyze_failures(failed_tasks)
        
        assert analysis["total_failures"] == 2
    
    def test_analyze_failures_groups_by_type(
        self,
        handler,
        timeout_failure,
        model_failure
    ):
        """Test that failures are grouped by type."""
        failed_tasks = [timeout_failure, model_failure]
        
        analysis = handler._analyze_failures(failed_tasks)
        
        assert analysis["failure_types"]["timeout"] == 1
        assert analysis["failure_types"]["model_failure"] == 1
    
    def test_analyze_failures_tracks_affected_models(
        self,
        handler,
        timeout_failure,
        model_failure
    ):
        """Test that affected models are tracked."""
        failed_tasks = [timeout_failure, model_failure]
        
        analysis = handler._analyze_failures(failed_tasks)
        
        assert "qwen3" in analysis["affected_models"]
        assert "gpt-4" in analysis["affected_models"]
    
    def test_analyze_failures_tracks_affected_agents(
        self,
        handler,
        timeout_failure,
        model_failure
    ):
        """Test that affected agents are tracked."""
        failed_tasks = [timeout_failure, model_failure]
        
        analysis = handler._analyze_failures(failed_tasks)
        
        assert "Backend Engineer" in analysis["affected_agents"]
        assert "Frontend Engineer" in analysis["affected_agents"]
    
    def test_analyze_failures_collects_error_messages(
        self,
        handler,
        timeout_failure
    ):
        """Test that error messages are collected."""
        failed_tasks = [timeout_failure]
        
        analysis = handler._analyze_failures(failed_tasks)
        
        assert len(analysis["error_messages"]) == 1
        assert analysis["error_messages"][0]["task_id"] == "task1"
        assert "timed out" in analysis["error_messages"][0]["error"].lower()


class TestReplanningStrategySelection:
    """Tests for replanning strategy selection."""
    
    def test_select_strategy_for_dependency_failures(
        self,
        handler,
        sample_state
    ):
        """Test strategy selection for majority dependency failures."""
        analysis = {
            "total_failures": 2,
            "failure_types": {
                "dependency_missing": 2
            }
        }
        
        strategy = handler._select_replanning_strategy(analysis, sample_state)
        
        assert strategy == ReplanningStrategy.REORDER_DEPENDENCIES
    
    def test_select_strategy_for_precondition_violations(
        self,
        handler,
        sample_state
    ):
        """Test strategy selection for precondition violations."""
        analysis = {
            "total_failures": 2,
            "failure_types": {
                "precondition_violation": 2
            }
        }
        
        strategy = handler._select_replanning_strategy(analysis, sample_state)
        
        assert strategy == ReplanningStrategy.REFINE_DECOMPOSITION
    
    def test_select_strategy_for_model_failures(
        self,
        handler,
        sample_state
    ):
        """Test strategy selection for model failures."""
        analysis = {
            "total_failures": 3,
            "failure_types": {
                "model_failure": 2,
                "unknown": 1
            }
        }
        
        strategy = handler._select_replanning_strategy(analysis, sample_state)
        
        assert strategy == ReplanningStrategy.RETRY_WITH_DIFFERENT_MODEL
    
    def test_select_strategy_for_timeout_failures(
        self,
        handler,
        sample_state
    ):
        """Test strategy selection for timeout failures."""
        analysis = {
            "total_failures": 3,
            "failure_types": {
                "timeout": 2,
                "unknown": 1
            }
        }
        
        strategy = handler._select_replanning_strategy(analysis, sample_state)
        
        assert strategy == ReplanningStrategy.RETRY_WITH_DIFFERENT_MODEL
    
    def test_select_strategy_fails_project_on_too_many_failures(
        self,
        handler,
        sample_state
    ):
        """Test that project fails when too many tasks fail."""
        # More than 50% of tasks failed
        sample_state.task_status = {
            "task1": TaskStatus.FAILED,
            "task2": TaskStatus.FAILED,
            "task3": TaskStatus.PENDING
        }
        
        analysis = {
            "total_failures": 2,
            "failure_types": {
                "unknown": 2
            }
        }
        
        strategy = handler._select_replanning_strategy(analysis, sample_state)
        
        assert strategy == ReplanningStrategy.FAIL_PROJECT


class TestReplanningStrategyApplication:
    """Tests for applying replanning strategies."""
    
    def test_apply_retry_with_different_model(
        self,
        handler,
        sample_state,
        model_failure
    ):
        """Test applying RETRY_WITH_DIFFERENT_MODEL strategy."""
        strategy = ReplanningStrategy.RETRY_WITH_DIFFERENT_MODEL
        failed_tasks = [model_failure]
        analysis = {}
        
        new_state = handler._apply_strategy(
            strategy,
            sample_state,
            failed_tasks,
            analysis
        )
        
        # Failed task should be reset to PENDING
        assert new_state.task_status["task3"] == TaskStatus.PENDING
    
    def test_apply_reorder_dependencies(
        self,
        handler,
        sample_state,
        dependency_failure
    ):
        """Test applying REORDER_DEPENDENCIES strategy."""
        strategy = ReplanningStrategy.REORDER_DEPENDENCIES
        failed_tasks = [dependency_failure]
        analysis = {}
        
        new_state = handler._apply_strategy(
            strategy,
            sample_state,
            failed_tasks,
            analysis
        )
        
        # Failed task should be reset to PENDING
        assert new_state.task_status["task2"] == TaskStatus.PENDING
    
    def test_apply_refine_decomposition_raises_error(
        self,
        handler,
        sample_state,
        precondition_failure
    ):
        """Test that REFINE_DECOMPOSITION raises error (not implemented in Phase 2)."""
        strategy = ReplanningStrategy.REFINE_DECOMPOSITION
        failed_tasks = [precondition_failure]
        analysis = {}
        
        with pytest.raises(ValueError) as exc_info:
            handler._apply_strategy(
                strategy,
                sample_state,
                failed_tasks,
                analysis
            )
        
        assert "Cannot refine decomposition" in str(exc_info.value)
    
    def test_apply_fail_project(
        self,
        handler,
        sample_state,
        timeout_failure
    ):
        """Test applying FAIL_PROJECT strategy."""
        strategy = ReplanningStrategy.FAIL_PROJECT
        failed_tasks = [timeout_failure]
        analysis = {}
        
        with pytest.raises(ValueError) as exc_info:
            handler._apply_strategy(
                strategy,
                sample_state,
                failed_tasks,
                analysis
            )
        
        assert "Project failed" in str(exc_info.value)


class TestReplanMethod:
    """Tests for the main replan method."""

    def test_replan_with_no_failures(self, handler, sample_state):
        """Test that replan returns state unchanged when no failures."""
        failed_tasks = []

        result = handler.replan(sample_state, failed_tasks)

        assert result == sample_state

    def test_replan_analyzes_failures(
        self,
        handler,
        sample_state,
        timeout_failure
    ):
        """Test that replan analyzes failures."""
        failed_tasks = [timeout_failure]

        result = handler.replan(sample_state, failed_tasks)

        # Should return updated state
        assert result is not None

    def test_replan_selects_strategy(
        self,
        handler,
        sample_state,
        model_failure
    ):
        """Test that replan selects appropriate strategy."""
        failed_tasks = [model_failure]

        result = handler.replan(sample_state, failed_tasks)

        # Should reset failed task to PENDING
        assert result.task_status["task3"] == TaskStatus.PENDING

    def test_replan_records_failures(
        self,
        handler,
        sample_state,
        timeout_failure
    ):
        """Test that replan records failures in history."""
        failed_tasks = [timeout_failure]

        handler.replan(sample_state, failed_tasks)

        # Failure should be recorded
        assert "task1" in handler.failure_history
        assert len(handler.failure_history["task1"]) == 1


class TestFailureHistoryTracking:
    """Tests for failure history tracking."""

    def test_record_failures_adds_to_history(
        self,
        handler,
        timeout_failure
    ):
        """Test that failures are added to history."""
        failed_tasks = [timeout_failure]
        analysis = {}

        handler._record_failures(failed_tasks, analysis)

        assert "task1" in handler.failure_history
        assert len(handler.failure_history["task1"]) == 1

    def test_record_failures_preserves_metadata(
        self,
        handler,
        timeout_failure
    ):
        """Test that failure metadata is preserved."""
        failed_tasks = [timeout_failure]
        analysis = {}

        handler._record_failures(failed_tasks, analysis)

        failure_record = handler.failure_history["task1"][0]
        assert failure_record["error"] == timeout_failure.error
        assert failure_record["metadata"] == timeout_failure.metadata
        assert failure_record["failure_type"] == FailureType.TIMEOUT.value

    def test_record_failures_accumulates_multiple_failures(
        self,
        handler,
        timeout_failure
    ):
        """Test that multiple failures for same task are accumulated."""
        failed_tasks = [timeout_failure]
        analysis = {}

        # Record twice
        handler._record_failures(failed_tasks, analysis)
        handler._record_failures(failed_tasks, analysis)

        assert len(handler.failure_history["task1"]) == 2

    def test_get_failure_statistics_empty(self, handler):
        """Test failure statistics when no failures recorded."""
        stats = handler.get_failure_statistics()

        assert stats["total_failures"] == 0
        assert stats["unique_failed_tasks"] == 0
        assert stats["failure_types"] == {}
        assert stats["most_common_failure"] is None

    def test_get_failure_statistics_with_failures(
        self,
        handler,
        timeout_failure,
        model_failure
    ):
        """Test failure statistics with recorded failures."""
        handler._record_failures([timeout_failure], {})
        handler._record_failures([model_failure], {})

        stats = handler.get_failure_statistics()

        assert stats["total_failures"] == 2
        assert stats["unique_failed_tasks"] == 2
        assert "timeout" in stats["failure_types"]
        assert "model_failure" in stats["failure_types"]

    def test_get_failure_statistics_most_common(
        self,
        handler,
        timeout_failure
    ):
        """Test identification of most common failure type."""
        # Record multiple timeout failures
        handler._record_failures([timeout_failure], {})
        handler._record_failures([timeout_failure], {})

        stats = handler.get_failure_statistics()

        assert stats["most_common_failure"] == "timeout"


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_replan_with_empty_error_message(
        self,
        handler,
        sample_state
    ):
        """Test handling of failure with empty error message."""
        failure = ExecutionResult(
            task_id="task1",
            success=False,
            effects={},
            error="",
            metadata={}
        )

        result = handler.replan(sample_state, [failure])

        # Should still work, classifying as UNKNOWN
        assert result is not None

    def test_replan_with_missing_metadata(
        self,
        handler,
        sample_state
    ):
        """Test handling of failure with missing metadata."""
        failure = ExecutionResult(
            task_id="task1",
            success=False,
            effects={},
            error="Failed",
            metadata={}
        )

        result = handler.replan(sample_state, [failure])

        assert result is not None

    def test_apply_strategy_with_nonexistent_task(
        self,
        handler,
        sample_state
    ):
        """Test applying strategy when task doesn't exist in state."""
        failure = ExecutionResult(
            task_id="nonexistent",
            success=False,
            effects={},
            error="Failed",
            metadata={}
        )

        strategy = ReplanningStrategy.RETRY_WITH_DIFFERENT_MODEL

        # Should not raise error
        result = handler._apply_strategy(
            strategy,
            sample_state,
            [failure],
            {}
        )

        assert result is not None

    def test_failure_analysis_with_multiple_same_type(
        self,
        handler
    ):
        """Test failure analysis with multiple failures of same type."""
        failures = [
            ExecutionResult(
                task_id=f"task{i}",
                success=False,
                effects={},
                error="Task timed out",
                metadata={}
            )
            for i in range(5)
        ]

        analysis = handler._analyze_failures(failures)

        assert analysis["total_failures"] == 5
        assert analysis["failure_types"]["timeout"] == 5


class TestIntegrationScenarios:
    """Integration tests for realistic failure scenarios."""

    def test_replan_cascade_dependency_failures(
        self,
        handler,
        sample_state
    ):
        """Test replanning for cascading dependency failures."""
        failures = [
            ExecutionResult(
                task_id="task1",
                success=False,
                effects={},
                error="Dependency missing: file not found",
                metadata={}
            ),
            ExecutionResult(
                task_id="task2",
                success=False,
                effects={},
                error="Dependency missing: task1 output required",
                metadata={}
            )
        ]

        result = handler.replan(sample_state, failures)

        # Should select REORDER_DEPENDENCIES strategy
        assert result.task_status["task1"] == TaskStatus.PENDING
        assert result.task_status["task2"] == TaskStatus.PENDING

    def test_replan_mixed_failure_types(
        self,
        handler,
        sample_state,
        timeout_failure,
        model_failure
    ):
        """Test replanning with mixed failure types."""
        failures = [timeout_failure, model_failure]

        result = handler.replan(sample_state, failures)

        # Should select appropriate strategy based on analysis
        assert result is not None

    def test_replan_progressive_failures(
        self,
        handler,
        sample_state
    ):
        """Test multiple replan calls with progressive failures."""
        failure1 = ExecutionResult(
            task_id="task1",
            success=False,
            effects={},
            error="Timeout",
            metadata={}
        )

        # First replan
        result1 = handler.replan(sample_state, [failure1])
        assert "task1" in handler.failure_history

        # Second replan with same task
        result2 = handler.replan(result1, [failure1])

        # Should accumulate failures
        assert len(handler.failure_history["task1"]) == 2
