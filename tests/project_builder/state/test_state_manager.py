"""Unit tests for ProjectStateManager.

Tests state management operations including initialization, state transitions,
precondition validation, and artifact extraction.
"""

import pytest
from unittest.mock import Mock, MagicMock
from datetime import datetime

from src.project_builder.state.manager import ProjectStateManager
from src.interfaces import ProjectState, TaskStatus
from src.entities.htn.htn_node import HTNNode


class TestProjectStateManagerInitialization:
    """Tests for ProjectStateManager initialization."""

    def test_init_with_repository(self):
        """Test that manager initializes with a repository."""
        # Arrange
        mock_repo = Mock()

        # Act
        manager = ProjectStateManager(mock_repo)

        # Assert
        assert manager.state_repo == mock_repo
        assert manager.current_state is None

    def test_initialize_creates_initial_state(self):
        """Test that initialize creates state with all tasks as PENDING."""
        # Arrange
        mock_repo = Mock()
        manager = ProjectStateManager(mock_repo)

        # Create simple HTN graph: root -> [task1, task2]
        task1 = HTNNode(task_id="task1", description="First task")
        task2 = HTNNode(task_id="task2", description="Second task")
        root = HTNNode(
            task_id="root",
            description="Root task",
            subtasks=[task1, task2]
        )

        # Act
        state = manager.initialize("test-project", root)

        # Assert
        assert state.project_id == "test-project"
        assert state.htn_graph == root
        assert state.version == 1
        assert len(state.task_status) == 3  # root + task1 + task2
        assert state.task_status["root"] == TaskStatus.PENDING
        assert state.task_status["task1"] == TaskStatus.PENDING
        assert state.task_status["task2"] == TaskStatus.PENDING
        assert state.world_state == {}
        assert isinstance(state.last_updated, datetime)
        mock_repo.save.assert_called_once_with(state)

    def test_initialize_with_nested_htn(self):
        """Test initialize with deeply nested HTN graph."""
        # Arrange
        mock_repo = Mock()
        manager = ProjectStateManager(mock_repo)

        # Create nested HTN: root -> task1 -> [task1a, task1b]
        task1a = HTNNode(task_id="task1a", description="Subtask 1a")
        task1b = HTNNode(task_id="task1b", description="Subtask 1b")
        task1 = HTNNode(
            task_id="task1",
            description="Task 1",
            subtasks=[task1a, task1b]
        )
        root = HTNNode(
            task_id="root",
            description="Root",
            subtasks=[task1]
        )

        # Act
        state = manager.initialize("nested-project", root)

        # Assert
        assert len(state.task_status) == 4  # root + task1 + task1a + task1b
        assert all(
            status == TaskStatus.PENDING
            for status in state.task_status.values()
        )


class TestProjectStateManagerStateAccess:
    """Tests for state access methods."""

    def test_get_current_state_returns_state(self):
        """Test that get_current_state returns initialized state."""
        # Arrange
        mock_repo = Mock()
        manager = ProjectStateManager(mock_repo)
        root = HTNNode(task_id="root", description="Root")
        manager.initialize("test-project", root)

        # Act
        state = manager.get_current_state()

        # Assert
        assert state.project_id == "test-project"
        assert state.version == 1

    def test_get_current_state_raises_when_not_initialized(self):
        """Test that get_current_state raises ValueError if not initialized."""
        # Arrange
        mock_repo = Mock()
        manager = ProjectStateManager(mock_repo)

        # Act & Assert
        with pytest.raises(ValueError, match="State not initialized"):
            manager.get_current_state()


class TestProjectStateManagerEffects:
    """Tests for applying effects to state."""

    def test_apply_effects_updates_world_state(self):
        """Test that apply_effects updates world state and increments version."""
        # Arrange
        mock_repo = Mock()
        manager = ProjectStateManager(mock_repo)
        root = HTNNode(task_id="root", description="Root")
        manager.initialize("test-project", root)

        # Act
        effects = {"file_created": "/opt/app.py", "lines_of_code": 42}
        manager.apply_effects(effects)

        # Assert
        state = manager.get_current_state()
        assert state.world_state["file_created"] == "/opt/app.py"
        assert state.world_state["lines_of_code"] == 42
        assert state.version == 2  # Incremented from 1
        assert mock_repo.save.call_count == 2  # Once for init, once for apply

    def test_apply_effects_preserves_existing_state(self):
        """Test that apply_effects preserves existing world state."""
        # Arrange
        mock_repo = Mock()
        manager = ProjectStateManager(mock_repo)
        root = HTNNode(task_id="root", description="Root")
        manager.initialize("test-project", root)
        manager.apply_effects({"key1": "value1"})

        # Act
        manager.apply_effects({"key2": "value2"})

        # Assert
        state = manager.get_current_state()
        assert state.world_state["key1"] == "value1"
        assert state.world_state["key2"] == "value2"
        assert state.version == 3

    def test_apply_effects_raises_when_not_initialized(self):
        """Test that apply_effects raises ValueError if not initialized."""
        # Arrange
        mock_repo = Mock()
        manager = ProjectStateManager(mock_repo)

        # Act & Assert
        with pytest.raises(ValueError, match="State not initialized"):
            manager.apply_effects({"key": "value"})


class TestProjectStateManagerTaskStatus:
    """Tests for task status management."""

    def test_mark_task_status_updates_status(self):
        """Test that mark_task_status updates task status and increments version."""
        # Arrange
        mock_repo = Mock()
        manager = ProjectStateManager(mock_repo)
        task1 = HTNNode(task_id="task1", description="Task 1")
        root = HTNNode(task_id="root", description="Root", subtasks=[task1])
        manager.initialize("test-project", root)

        # Act
        manager.mark_task_status("task1", TaskStatus.COMPLETED)

        # Assert
        state = manager.get_current_state()
        assert state.task_status["task1"] == TaskStatus.COMPLETED
        assert state.task_status["root"] == TaskStatus.PENDING  # Unchanged
        assert state.version == 2
        assert mock_repo.save.call_count == 2

    def test_mark_task_status_raises_for_invalid_task(self):
        """Test that mark_task_status raises ValueError for unknown task_id."""
        # Arrange
        mock_repo = Mock()
        manager = ProjectStateManager(mock_repo)
        root = HTNNode(task_id="root", description="Root")
        manager.initialize("test-project", root)

        # Act & Assert
        with pytest.raises(ValueError, match="Task 'invalid' not found"):
            manager.mark_task_status("invalid", TaskStatus.COMPLETED)

    def test_mark_task_status_raises_when_not_initialized(self):
        """Test that mark_task_status raises ValueError if not initialized."""
        # Arrange
        mock_repo = Mock()
        manager = ProjectStateManager(mock_repo)

        # Act & Assert
        with pytest.raises(ValueError, match="State not initialized"):
            manager.mark_task_status("task1", TaskStatus.COMPLETED)


class TestProjectStateManagerValidation:
    """Tests for state validation."""

    def test_validate_current_state_with_satisfied_preconditions(self):
        """Test that validate returns True when at least one task can proceed."""
        # Arrange
        mock_repo = Mock()
        manager = ProjectStateManager(mock_repo)

        # Task with no preconditions (can always execute)
        task1 = HTNNode(task_id="task1", description="Task 1", preconditions={})
        root = HTNNode(task_id="root", description="Root", subtasks=[task1])
        manager.initialize("test-project", root)

        # Act
        is_valid = manager.validate_current_state()

        # Assert
        assert is_valid is True

    def test_validate_current_state_with_unsatisfied_preconditions(self):
        """Test that validate returns False when no tasks can proceed."""
        # Arrange
        mock_repo = Mock()
        manager = ProjectStateManager(mock_repo)

        # Both tasks have preconditions that are not satisfied
        task1 = HTNNode(
            task_id="task1",
            description="Task 1",
            preconditions={"file_exists": True}
        )
        root = HTNNode(
            task_id="root",
            description="Root",
            subtasks=[task1],
            preconditions={"initialized": True}  # Root also has unsatisfied precondition
        )
        manager.initialize("test-project", root)

        # Act
        is_valid = manager.validate_current_state()

        # Assert
        assert is_valid is False

    def test_validate_current_state_returns_true_when_no_pending(self):
        """Test that validate returns True when no pending tasks remain."""
        # Arrange
        mock_repo = Mock()
        manager = ProjectStateManager(mock_repo)
        task1 = HTNNode(task_id="task1", description="Task 1")
        root = HTNNode(task_id="root", description="Root", subtasks=[task1])
        manager.initialize("test-project", root)

        # Mark all tasks as completed
        manager.mark_task_status("root", TaskStatus.COMPLETED)
        manager.mark_task_status("task1", TaskStatus.COMPLETED)

        # Act
        is_valid = manager.validate_current_state()

        # Assert
        assert is_valid is True

    def test_validate_current_state_raises_when_not_initialized(self):
        """Test that validate raises ValueError if not initialized."""
        # Arrange
        mock_repo = Mock()
        manager = ProjectStateManager(mock_repo)

        # Act & Assert
        with pytest.raises(ValueError, match="State not initialized"):
            manager.validate_current_state()


class TestProjectStateManagerPendingTasks:
    """Tests for pending task checks."""

    def test_has_pending_tasks_returns_true_when_pending(self):
        """Test that has_pending_tasks returns True when tasks are pending."""
        # Arrange
        mock_repo = Mock()
        manager = ProjectStateManager(mock_repo)
        root = HTNNode(task_id="root", description="Root")
        manager.initialize("test-project", root)

        # Act
        has_pending = manager.has_pending_tasks()

        # Assert
        assert has_pending is True

    def test_has_pending_tasks_returns_false_when_all_completed(self):
        """Test that has_pending_tasks returns False when all tasks completed."""
        # Arrange
        mock_repo = Mock()
        manager = ProjectStateManager(mock_repo)
        root = HTNNode(task_id="root", description="Root")
        manager.initialize("test-project", root)
        manager.mark_task_status("root", TaskStatus.COMPLETED)

        # Act
        has_pending = manager.has_pending_tasks()

        # Assert
        assert has_pending is False

    def test_has_pending_tasks_raises_when_not_initialized(self):
        """Test that has_pending_tasks raises ValueError if not initialized."""
        # Arrange
        mock_repo = Mock()
        manager = ProjectStateManager(mock_repo)

        # Act & Assert
        with pytest.raises(ValueError, match="State not initialized"):
            manager.has_pending_tasks()


class TestProjectStateManagerArtifacts:
    """Tests for artifact finalization."""

    def test_finalize_artifacts_extracts_artifact_prefix(self):
        """Test that finalize_artifacts extracts keys with artifact_ prefix."""
        # Arrange
        mock_repo = Mock()
        manager = ProjectStateManager(mock_repo)
        root = HTNNode(task_id="root", description="Root")
        manager.initialize("test-project", root)

        # Add artifacts to world state
        manager.apply_effects({
            "artifact_file": "def hello(): pass",
            "artifact_test": "def test_hello(): pass",
            "other_key": "value"
        })

        # Act
        artifacts = manager.finalize_artifacts()

        # Assert
        assert "file" in artifacts
        assert artifacts["file"] == "def hello(): pass"
        assert "test" in artifacts
        assert artifacts["test"] == "def test_hello(): pass"
        assert "other_key" not in artifacts

    def test_finalize_artifacts_extracts_code_suffix(self):
        """Test that finalize_artifacts extracts keys ending with _code."""
        # Arrange
        mock_repo = Mock()
        manager = ProjectStateManager(mock_repo)
        root = HTNNode(task_id="root", description="Root")
        manager.initialize("test-project", root)

        # Add code artifacts (with substantial content)
        code_content = "x" * 100  # Must be > 50 chars
        manager.apply_effects({
            "implement_function_code": code_content,
            "setup_test": "completed"  # Short, should be skipped
        })

        # Act
        artifacts = manager.finalize_artifacts()

        # Assert
        assert "implement_function_code" in artifacts
        assert artifacts["implement_function_code"] == code_content
        assert "setup_test" not in artifacts  # Too short

    def test_finalize_artifacts_filters_status_flags(self):
        """Test that finalize_artifacts filters out status flags."""
        # Arrange
        mock_repo = Mock()
        manager = ProjectStateManager(mock_repo)
        root = HTNNode(task_id="root", description="Root")
        manager.initialize("test-project", root)

        # Add mix of artifacts and status flags
        code_content = "def hello(): print('world')" * 5  # > 50 chars
        manager.apply_effects({
            "implement_function_code": code_content,
            "task_completed": "completed",
            "validation_passed": "True"
        })

        # Act
        artifacts = manager.finalize_artifacts()

        # Assert
        assert "implement_function_code" in artifacts
        assert "task_completed" not in artifacts
        assert "validation_passed" not in artifacts

    def test_finalize_artifacts_raises_when_not_initialized(self):
        """Test that finalize_artifacts raises ValueError if not initialized."""
        # Arrange
        mock_repo = Mock()
        manager = ProjectStateManager(mock_repo)

        # Act & Assert
        with pytest.raises(ValueError, match="State not initialized"):
            manager.finalize_artifacts()


class TestProjectStateManagerStateLoading:
    """Tests for loading existing state."""

    def test_load_state_restores_state(self):
        """Test that load_state restores state from repository."""
        # Arrange
        mock_repo = Mock()
        manager = ProjectStateManager(mock_repo)

        # Create mock loaded state
        root = HTNNode(task_id="root", description="Root")
        loaded_state = ProjectState(
            project_id="loaded-project",
            htn_graph=root,
            task_status={"root": TaskStatus.COMPLETED},
            world_state={"file": "content"},
            version=5
        )
        mock_repo.load.return_value = loaded_state

        # Act
        state = manager.load_state("loaded-project")

        # Assert
        assert state.project_id == "loaded-project"
        assert state.version == 5
        assert state.task_status["root"] == TaskStatus.COMPLETED
        assert state.world_state["file"] == "content"
        assert manager.current_state == loaded_state
        mock_repo.load.assert_called_once_with("loaded-project")


class TestProjectStateManagerHelperMethods:
    """Tests for internal helper methods."""

    def test_collect_task_ids_flat_graph(self):
        """Test _collect_task_ids with flat (non-nested) graph."""
        # Arrange
        mock_repo = Mock()
        manager = ProjectStateManager(mock_repo)

        task1 = HTNNode(task_id="task1", description="Task 1")
        task2 = HTNNode(task_id="task2", description="Task 2")
        root = HTNNode(task_id="root", description="Root", subtasks=[task1, task2])

        # Act
        task_ids = manager._collect_task_ids(root)

        # Assert
        assert set(task_ids) == {"root", "task1", "task2"}

    def test_collect_task_ids_nested_graph(self):
        """Test _collect_task_ids with deeply nested graph."""
        # Arrange
        mock_repo = Mock()
        manager = ProjectStateManager(mock_repo)

        task1a = HTNNode(task_id="task1a", description="Subtask 1a")
        task1 = HTNNode(task_id="task1", description="Task 1", subtasks=[task1a])
        root = HTNNode(task_id="root", description="Root", subtasks=[task1])

        # Act
        task_ids = manager._collect_task_ids(root)

        # Assert
        assert set(task_ids) == {"root", "task1", "task1a"}

    def test_find_task_in_graph_finds_root(self):
        """Test _find_task_in_graph finds root node."""
        # Arrange
        mock_repo = Mock()
        manager = ProjectStateManager(mock_repo)

        root = HTNNode(task_id="root", description="Root")

        # Act
        found = manager._find_task_in_graph(root, "root")

        # Assert
        assert found is root

    def test_find_task_in_graph_finds_subtask(self):
        """Test _find_task_in_graph finds subtask."""
        # Arrange
        mock_repo = Mock()
        manager = ProjectStateManager(mock_repo)

        task1 = HTNNode(task_id="task1", description="Task 1")
        root = HTNNode(task_id="root", description="Root", subtasks=[task1])

        # Act
        found = manager._find_task_in_graph(root, "task1")

        # Assert
        assert found is task1

    def test_find_task_in_graph_returns_none_when_not_found(self):
        """Test _find_task_in_graph returns None for nonexistent task."""
        # Arrange
        mock_repo = Mock()
        manager = ProjectStateManager(mock_repo)

        root = HTNNode(task_id="root", description="Root")

        # Act
        found = manager._find_task_in_graph(root, "nonexistent")

        # Assert
        assert found is None
