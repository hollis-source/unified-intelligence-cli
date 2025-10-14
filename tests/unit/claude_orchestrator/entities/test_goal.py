"""Unit tests for Goal entity.

Tests the immutable Goal entity which represents high-level objectives
in the priorities.yaml file (not specific tasks).

TDD: Test-first approach for Goal entity.
"""

import pytest
from datetime import datetime
from src.claude_orchestrator.entities.goal import Goal, GoalType, GoalStatus


class TestGoalEntity:
    """Test suite for Goal entity."""

    def test_goal_creation_with_all_fields(self):
        """Test creating Goal with all fields specified."""
        goal = Goal.create(
            id="test-coverage-95",
            title="Achieve 95% Test Coverage",
            description="Increase test coverage from current 82% to 95% across all modules",
            goal_type=GoalType.COVERAGE,
            priority="P1",
            target_metric="coverage_percentage",
            target_value=95.0,
            current_value=82.0,
        )

        assert goal.id == "test-coverage-95"
        assert goal.title == "Achieve 95% Test Coverage"
        assert goal.goal_type == GoalType.COVERAGE
        assert goal.priority == "P1"
        assert goal.target_metric == "coverage_percentage"
        assert goal.target_value == 95.0
        assert goal.current_value == 82.0
        assert goal.status == GoalStatus.ACTIVE
        assert isinstance(goal.created_at, datetime)

    def test_goal_immutability(self):
        """Test that Goal is immutable (frozen dataclass)."""
        goal = Goal.create(
            id="test-goal",
            title="Test Goal",
            description="Test description",
            goal_type=GoalType.FEATURE,
            priority="P2",
        )

        with pytest.raises(AttributeError):
            goal.title = "Modified Title"

    def test_goal_default_values(self):
        """Test Goal creation with minimal fields (defaults applied)."""
        goal = Goal.create(
            id="minimal-goal",
            title="Minimal Goal",
            description="Minimal description",
            goal_type=GoalType.REFACTOR,
            priority="P3",
        )

        assert goal.status == GoalStatus.ACTIVE
        assert goal.target_metric is None
        assert goal.target_value is None
        assert goal.current_value is None
        assert goal.completed_at is None
        assert isinstance(goal.created_at, datetime)

    def test_goal_progress_calculation(self):
        """Test progress percentage calculation."""
        goal = Goal.create(
            id="progress-test",
            title="Progress Test",
            description="Test progress calculation",
            goal_type=GoalType.COVERAGE,
            priority="P1",
            target_value=100.0,
            current_value=75.0,
        )

        assert goal.progress_percentage() == 75.0

    def test_goal_progress_no_target(self):
        """Test progress returns None when no target defined."""
        goal = Goal.create(
            id="no-target",
            title="No Target Goal",
            description="Goal without target",
            goal_type=GoalType.FEATURE,
            priority="P1",
        )

        assert goal.progress_percentage() is None

    def test_goal_is_achieved_true(self):
        """Test goal achievement detection (reached target)."""
        goal = Goal.create(
            id="achieved-goal",
            title="Achieved Goal",
            description="Goal that met target",
            goal_type=GoalType.PERFORMANCE,
            priority="P1",
            target_value=100.0,
            current_value=100.0,
        )

        assert goal.is_achieved() is True

    def test_goal_is_achieved_false(self):
        """Test goal achievement detection (not reached)."""
        goal = Goal.create(
            id="unachieved-goal",
            title="Unachieved Goal",
            description="Goal not yet met",
            goal_type=GoalType.PERFORMANCE,
            priority="P1",
            target_value=100.0,
            current_value=85.0,
        )

        assert goal.is_achieved() is False

    def test_goal_is_achieved_no_target(self):
        """Test is_achieved returns False when no target defined."""
        goal = Goal.create(
            id="no-target",
            title="No Target Goal",
            description="Goal without target",
            goal_type=GoalType.DOCUMENTATION,
            priority="P2",
        )

        assert goal.is_achieved() is False

    def test_goal_to_dict_serialization(self):
        """Test Goal serialization to dictionary."""
        goal = Goal.create(
            id="serialize-test",
            title="Serialization Test",
            description="Test serialization",
            goal_type=GoalType.COVERAGE,
            priority="P1",
            target_value=95.0,
            current_value=82.0,
        )

        goal_dict = goal.to_dict()

        assert goal_dict["id"] == "serialize-test"
        assert goal_dict["title"] == "Serialization Test"
        assert goal_dict["goal_type"] == "coverage"
        assert goal_dict["priority"] == "P1"
        assert goal_dict["status"] == "active"
        assert goal_dict["target_value"] == 95.0
        assert goal_dict["current_value"] == 82.0
        assert "created_at" in goal_dict

    def test_goal_type_enum_values(self):
        """Test GoalType enum has expected values."""
        assert GoalType.COVERAGE.value == "coverage"
        assert GoalType.PERFORMANCE.value == "performance"
        assert GoalType.FEATURE.value == "feature"
        assert GoalType.REFACTOR.value == "refactor"
        assert GoalType.DOCUMENTATION.value == "documentation"
        assert GoalType.TESTING.value == "testing"

    def test_goal_status_enum_values(self):
        """Test GoalStatus enum has expected values."""
        assert GoalStatus.ACTIVE.value == "active"
        assert GoalStatus.COMPLETED.value == "completed"
        assert GoalStatus.BLOCKED.value == "blocked"
        assert GoalStatus.DEPRECATED.value == "deprecated"

    def test_goal_with_completed_status(self):
        """Test creating goal with completed status and timestamp."""
        completed_time = datetime.now()
        goal = Goal.create(
            id="completed-goal",
            title="Completed Goal",
            description="Already completed",
            goal_type=GoalType.FEATURE,
            priority="P1",
            status=GoalStatus.COMPLETED,
            completed_at=completed_time,
        )

        assert goal.status == GoalStatus.COMPLETED
        assert goal.completed_at == completed_time

    def test_goal_priority_validation(self):
        """Test that priorities follow P0-P3 format."""
        valid_priorities = ["P0", "P1", "P2", "P3"]

        for priority in valid_priorities:
            goal = Goal.create(
                id=f"priority-{priority}",
                title=f"Priority {priority} Goal",
                description="Test priority",
                goal_type=GoalType.FEATURE,
                priority=priority,
            )
            assert goal.priority == priority
