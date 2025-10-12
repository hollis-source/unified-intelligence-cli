"""Unit tests for SQLiteStateRepository.

Tests persistence, versioning, and retrieval of project state using SQLite.
"""

import pytest
import sqlite3
from pathlib import Path
from datetime import datetime

from src.project_builder.state.repository import SQLiteStateRepository
from src.interfaces import ProjectState, TaskStatus
from src.entities.htn.htn_node import HTNNode


class TestSQLiteStateRepositoryInitialization:
    """Tests for repository initialization."""

    def test_init_creates_database_file(self, tmp_path):
        """Test that initialization creates database file."""
        # Arrange
        db_path = tmp_path / "test.db"

        # Act
        repo = SQLiteStateRepository(str(db_path))

        # Assert
        assert db_path.exists()
        assert repo.db_path == db_path

    def test_init_creates_parent_directories(self, tmp_path):
        """Test that initialization creates parent directories if missing."""
        # Arrange
        db_path = tmp_path / "nested" / "dirs" / "test.db"

        # Act
        repo = SQLiteStateRepository(str(db_path))

        # Assert
        assert db_path.exists()
        assert db_path.parent.exists()

    def test_init_creates_schema(self, tmp_path):
        """Test that initialization creates database schema."""
        # Arrange
        db_path = tmp_path / "test.db"

        # Act
        repo = SQLiteStateRepository(str(db_path))

        # Assert - Check table exists
        with sqlite3.connect(db_path) as conn:
            cursor = conn.execute("""
                SELECT name FROM sqlite_master
                WHERE type='table' AND name='project_states'
            """)
            tables = cursor.fetchall()

        assert len(tables) == 1
        assert tables[0][0] == "project_states"

    def test_init_creates_indexes(self, tmp_path):
        """Test that initialization creates database indexes."""
        # Arrange
        db_path = tmp_path / "test.db"

        # Act
        repo = SQLiteStateRepository(str(db_path))

        # Assert - Check indexes exist
        with sqlite3.connect(db_path) as conn:
            cursor = conn.execute("""
                SELECT name FROM sqlite_master
                WHERE type='index'
            """)
            indexes = {row[0] for row in cursor.fetchall()}

        assert "idx_project_id" in indexes
        assert "idx_last_updated" in indexes

    def test_init_is_idempotent(self, tmp_path):
        """Test that multiple initializations don't cause errors."""
        # Arrange
        db_path = tmp_path / "test.db"

        # Act - Initialize twice
        repo1 = SQLiteStateRepository(str(db_path))
        repo2 = SQLiteStateRepository(str(db_path))

        # Assert - No errors, database still usable
        root = HTNNode(task_id="root", description="Root")
        state = ProjectState(
            project_id="test",
            htn_graph=root,
            task_status={"root": TaskStatus.PENDING},
            world_state={}
        )
        repo2.save(state)


class TestSQLiteStateRepositorySave:
    """Tests for saving project state."""

    def test_save_persists_state(self, tmp_path):
        """Test that save persists state to database."""
        # Arrange
        db_path = tmp_path / "test.db"
        repo = SQLiteStateRepository(str(db_path))

        root = HTNNode(task_id="root", description="Root task")
        state = ProjectState(
            project_id="test-project",
            htn_graph=root,
            task_status={"root": TaskStatus.PENDING},
            world_state={"key": "value"},
            version=1
        )

        # Act
        repo.save(state)

        # Assert - Verify data in database
        with sqlite3.connect(db_path) as conn:
            cursor = conn.execute("""
                SELECT project_id, version FROM project_states
                WHERE project_id = ?
            """, ("test-project",))
            row = cursor.fetchone()

        assert row is not None
        assert row[0] == "test-project"
        assert row[1] == 1

    def test_save_serializes_htn_graph(self, tmp_path):
        """Test that save correctly serializes HTN graph with pickle."""
        # Arrange
        db_path = tmp_path / "test.db"
        repo = SQLiteStateRepository(str(db_path))

        task1 = HTNNode(task_id="task1", description="Task 1")
        root = HTNNode(
            task_id="root",
            description="Root",
            subtasks=[task1],
            preconditions={"req": True},
            effects={"result": "done"}
        )

        state = ProjectState(
            project_id="test-project",
            htn_graph=root,
            task_status={"root": TaskStatus.PENDING, "task1": TaskStatus.PENDING},
            world_state={}
        )

        # Act
        repo.save(state)

        # Assert - Load and verify HTN structure
        loaded_state = repo.load("test-project")
        assert loaded_state.htn_graph.task_id == "root"
        assert loaded_state.htn_graph.description == "Root"
        assert len(loaded_state.htn_graph.subtasks) == 1
        assert loaded_state.htn_graph.subtasks[0].task_id == "task1"
        assert loaded_state.htn_graph.preconditions == {"req": True}
        assert loaded_state.htn_graph.effects == {"result": "done"}

    def test_save_serializes_task_status(self, tmp_path):
        """Test that save correctly serializes task status dictionary."""
        # Arrange
        db_path = tmp_path / "test.db"
        repo = SQLiteStateRepository(str(db_path))

        root = HTNNode(task_id="root", description="Root")
        state = ProjectState(
            project_id="test-project",
            htn_graph=root,
            task_status={
                "task1": TaskStatus.COMPLETED,
                "task2": TaskStatus.PENDING,
                "task3": TaskStatus.FAILED
            },
            world_state={}
        )

        # Act
        repo.save(state)

        # Assert - Load and verify task status
        loaded_state = repo.load("test-project")
        assert loaded_state.task_status["task1"] == TaskStatus.COMPLETED
        assert loaded_state.task_status["task2"] == TaskStatus.PENDING
        assert loaded_state.task_status["task3"] == TaskStatus.FAILED

    def test_save_serializes_world_state(self, tmp_path):
        """Test that save correctly serializes world state dictionary."""
        # Arrange
        db_path = tmp_path / "test.db"
        repo = SQLiteStateRepository(str(db_path))

        root = HTNNode(task_id="root", description="Root")
        state = ProjectState(
            project_id="test-project",
            htn_graph=root,
            task_status={"root": TaskStatus.PENDING},
            world_state={
                "file_path": "/opt/app.py",
                "lines_of_code": 42,
                "tests_passed": True,
                "config": {"debug": False}
            }
        )

        # Act
        repo.save(state)

        # Assert - Load and verify world state
        loaded_state = repo.load("test-project")
        assert loaded_state.world_state["file_path"] == "/opt/app.py"
        assert loaded_state.world_state["lines_of_code"] == 42
        assert loaded_state.world_state["tests_passed"] is True
        assert loaded_state.world_state["config"] == {"debug": False}

    def test_save_creates_new_version(self, tmp_path):
        """Test that saving same project_id creates new version."""
        # Arrange
        db_path = tmp_path / "test.db"
        repo = SQLiteStateRepository(str(db_path))

        root = HTNNode(task_id="root", description="Root")
        state_v1 = ProjectState(
            project_id="test-project",
            htn_graph=root,
            task_status={"root": TaskStatus.PENDING},
            world_state={},
            version=1
        )
        state_v2 = ProjectState(
            project_id="test-project",
            htn_graph=root,
            task_status={"root": TaskStatus.COMPLETED},
            world_state={"result": "done"},
            version=2
        )

        # Act
        repo.save(state_v1)
        repo.save(state_v2)

        # Assert - Both versions exist
        versions = repo.get_all_versions("test-project")
        assert len(versions) == 2
        assert versions == [1, 2]

    def test_save_replaces_existing_version(self, tmp_path):
        """Test that saving same version replaces existing data (INSERT OR REPLACE)."""
        # Arrange
        db_path = tmp_path / "test.db"
        repo = SQLiteStateRepository(str(db_path))

        root = HTNNode(task_id="root", description="Root")
        state_v1_first = ProjectState(
            project_id="test-project",
            htn_graph=root,
            task_status={"root": TaskStatus.PENDING},
            world_state={"attempt": "first"},
            version=1
        )
        state_v1_second = ProjectState(
            project_id="test-project",
            htn_graph=root,
            task_status={"root": TaskStatus.COMPLETED},
            world_state={"attempt": "second"},
            version=1
        )

        # Act
        repo.save(state_v1_first)
        repo.save(state_v1_second)

        # Assert - Only one version 1, with latest data
        versions = repo.get_all_versions("test-project")
        assert len(versions) == 1
        loaded = repo.load("test-project", version=1)
        assert loaded.world_state["attempt"] == "second"
        assert loaded.task_status["root"] == TaskStatus.COMPLETED


class TestSQLiteStateRepositoryLoad:
    """Tests for loading project state."""

    def test_load_retrieves_latest_version_by_default(self, tmp_path):
        """Test that load without version parameter retrieves latest version."""
        # Arrange
        db_path = tmp_path / "test.db"
        repo = SQLiteStateRepository(str(db_path))

        root = HTNNode(task_id="root", description="Root")
        state_v1 = ProjectState(
            project_id="test-project",
            htn_graph=root,
            task_status={"root": TaskStatus.PENDING},
            world_state={"version": "v1"},
            version=1
        )
        state_v3 = ProjectState(
            project_id="test-project",
            htn_graph=root,
            task_status={"root": TaskStatus.COMPLETED},
            world_state={"version": "v3"},
            version=3
        )

        repo.save(state_v1)
        repo.save(state_v3)

        # Act
        loaded = repo.load("test-project")

        # Assert
        assert loaded.version == 3
        assert loaded.world_state["version"] == "v3"

    def test_load_retrieves_specific_version(self, tmp_path):
        """Test that load with version parameter retrieves that specific version."""
        # Arrange
        db_path = tmp_path / "test.db"
        repo = SQLiteStateRepository(str(db_path))

        root = HTNNode(task_id="root", description="Root")
        state_v1 = ProjectState(
            project_id="test-project",
            htn_graph=root,
            task_status={"root": TaskStatus.PENDING},
            world_state={"version": "v1"},
            version=1
        )
        state_v2 = ProjectState(
            project_id="test-project",
            htn_graph=root,
            task_status={"root": TaskStatus.COMPLETED},
            world_state={"version": "v2"},
            version=2
        )

        repo.save(state_v1)
        repo.save(state_v2)

        # Act
        loaded = repo.load("test-project", version=1)

        # Assert
        assert loaded.version == 1
        assert loaded.world_state["version"] == "v1"

    def test_load_raises_for_nonexistent_project(self, tmp_path):
        """Test that load raises ValueError for nonexistent project."""
        # Arrange
        db_path = tmp_path / "test.db"
        repo = SQLiteStateRepository(str(db_path))

        # Act & Assert
        with pytest.raises(ValueError, match="Project 'nonexistent' not found"):
            repo.load("nonexistent")

    def test_load_raises_for_nonexistent_version(self, tmp_path):
        """Test that load raises ValueError for nonexistent version."""
        # Arrange
        db_path = tmp_path / "test.db"
        repo = SQLiteStateRepository(str(db_path))

        root = HTNNode(task_id="root", description="Root")
        state = ProjectState(
            project_id="test-project",
            htn_graph=root,
            task_status={"root": TaskStatus.PENDING},
            world_state={},
            version=1
        )
        repo.save(state)

        # Act & Assert
        with pytest.raises(ValueError, match="Project 'test-project' not found"):
            repo.load("test-project", version=999)

    def test_load_preserves_timestamps(self, tmp_path):
        """Test that load correctly deserializes timestamps."""
        # Arrange
        db_path = tmp_path / "test.db"
        repo = SQLiteStateRepository(str(db_path))

        root = HTNNode(task_id="root", description="Root")
        original_time = datetime(2025, 10, 12, 14, 30, 0)
        state = ProjectState(
            project_id="test-project",
            htn_graph=root,
            task_status={"root": TaskStatus.PENDING},
            world_state={},
            version=1,
            last_updated=original_time
        )

        # Act
        repo.save(state)
        loaded = repo.load("test-project")

        # Assert
        assert loaded.last_updated == original_time


class TestSQLiteStateRepositoryExists:
    """Tests for checking project existence."""

    def test_exists_returns_true_for_existing_project(self, tmp_path):
        """Test that exists returns True for saved project."""
        # Arrange
        db_path = tmp_path / "test.db"
        repo = SQLiteStateRepository(str(db_path))

        root = HTNNode(task_id="root", description="Root")
        state = ProjectState(
            project_id="test-project",
            htn_graph=root,
            task_status={"root": TaskStatus.PENDING},
            world_state={}
        )
        repo.save(state)

        # Act
        exists = repo.exists("test-project")

        # Assert
        assert exists is True

    def test_exists_returns_false_for_nonexistent_project(self, tmp_path):
        """Test that exists returns False for nonexistent project."""
        # Arrange
        db_path = tmp_path / "test.db"
        repo = SQLiteStateRepository(str(db_path))

        # Act
        exists = repo.exists("nonexistent")

        # Assert
        assert exists is False


class TestSQLiteStateRepositoryDelete:
    """Tests for deleting project state."""

    def test_delete_removes_project(self, tmp_path):
        """Test that delete removes all versions of project."""
        # Arrange
        db_path = tmp_path / "test.db"
        repo = SQLiteStateRepository(str(db_path))

        root = HTNNode(task_id="root", description="Root")
        state_v1 = ProjectState(
            project_id="test-project",
            htn_graph=root,
            task_status={"root": TaskStatus.PENDING},
            world_state={},
            version=1
        )
        state_v2 = ProjectState(
            project_id="test-project",
            htn_graph=root,
            task_status={"root": TaskStatus.COMPLETED},
            world_state={},
            version=2
        )

        repo.save(state_v1)
        repo.save(state_v2)

        # Act
        repo.delete("test-project")

        # Assert
        assert repo.exists("test-project") is False
        with pytest.raises(ValueError, match="not found"):
            repo.load("test-project")

    def test_delete_is_idempotent(self, tmp_path):
        """Test that deleting nonexistent project doesn't raise error."""
        # Arrange
        db_path = tmp_path / "test.db"
        repo = SQLiteStateRepository(str(db_path))

        # Act & Assert - No error
        repo.delete("nonexistent")

    def test_delete_only_removes_target_project(self, tmp_path):
        """Test that delete only removes specified project, not others."""
        # Arrange
        db_path = tmp_path / "test.db"
        repo = SQLiteStateRepository(str(db_path))

        root = HTNNode(task_id="root", description="Root")
        state1 = ProjectState(
            project_id="project1",
            htn_graph=root,
            task_status={"root": TaskStatus.PENDING},
            world_state={}
        )
        state2 = ProjectState(
            project_id="project2",
            htn_graph=root,
            task_status={"root": TaskStatus.PENDING},
            world_state={}
        )

        repo.save(state1)
        repo.save(state2)

        # Act
        repo.delete("project1")

        # Assert
        assert repo.exists("project1") is False
        assert repo.exists("project2") is True


class TestSQLiteStateRepositoryVersionManagement:
    """Tests for version management methods."""

    def test_get_all_versions_returns_sorted_list(self, tmp_path):
        """Test that get_all_versions returns versions in ascending order."""
        # Arrange
        db_path = tmp_path / "test.db"
        repo = SQLiteStateRepository(str(db_path))

        root = HTNNode(task_id="root", description="Root")
        for version in [3, 1, 2]:  # Save in non-sequential order
            state = ProjectState(
                project_id="test-project",
                htn_graph=root,
                task_status={"root": TaskStatus.PENDING},
                world_state={},
                version=version
            )
            repo.save(state)

        # Act
        versions = repo.get_all_versions("test-project")

        # Assert
        assert versions == [1, 2, 3]

    def test_get_all_versions_returns_empty_for_nonexistent(self, tmp_path):
        """Test that get_all_versions returns empty list for nonexistent project."""
        # Arrange
        db_path = tmp_path / "test.db"
        repo = SQLiteStateRepository(str(db_path))

        # Act
        versions = repo.get_all_versions("nonexistent")

        # Assert
        assert versions == []

    def test_get_latest_version_returns_max_version(self, tmp_path):
        """Test that get_latest_version returns highest version number."""
        # Arrange
        db_path = tmp_path / "test.db"
        repo = SQLiteStateRepository(str(db_path))

        root = HTNNode(task_id="root", description="Root")
        for version in [1, 5, 3]:
            state = ProjectState(
                project_id="test-project",
                htn_graph=root,
                task_status={"root": TaskStatus.PENDING},
                world_state={},
                version=version
            )
            repo.save(state)

        # Act
        latest = repo.get_latest_version("test-project")

        # Assert
        assert latest == 5

    def test_get_latest_version_returns_none_for_nonexistent(self, tmp_path):
        """Test that get_latest_version returns None for nonexistent project."""
        # Arrange
        db_path = tmp_path / "test.db"
        repo = SQLiteStateRepository(str(db_path))

        # Act
        latest = repo.get_latest_version("nonexistent")

        # Assert
        assert latest is None


class TestSQLiteStateRepositoryEdgeCases:
    """Tests for edge cases and error handling."""

    def test_handles_empty_world_state(self, tmp_path):
        """Test that repository handles empty world state."""
        # Arrange
        db_path = tmp_path / "test.db"
        repo = SQLiteStateRepository(str(db_path))

        root = HTNNode(task_id="root", description="Root")
        state = ProjectState(
            project_id="test-project",
            htn_graph=root,
            task_status={"root": TaskStatus.PENDING},
            world_state={}
        )

        # Act
        repo.save(state)
        loaded = repo.load("test-project")

        # Assert
        assert loaded.world_state == {}

    def test_handles_large_world_state(self, tmp_path):
        """Test that repository handles large world state."""
        # Arrange
        db_path = tmp_path / "test.db"
        repo = SQLiteStateRepository(str(db_path))

        root = HTNNode(task_id="root", description="Root")
        large_content = "x" * 100000  # 100KB of data
        state = ProjectState(
            project_id="test-project",
            htn_graph=root,
            task_status={"root": TaskStatus.PENDING},
            world_state={"large_file": large_content}
        )

        # Act
        repo.save(state)
        loaded = repo.load("test-project")

        # Assert
        assert loaded.world_state["large_file"] == large_content

    def test_handles_special_characters_in_state(self, tmp_path):
        """Test that repository handles special characters in state data."""
        # Arrange
        db_path = tmp_path / "test.db"
        repo = SQLiteStateRepository(str(db_path))

        root = HTNNode(task_id="root", description="Root")
        special_content = "Hello 'world' \"quoted\" \n\t\r special: {}[]"
        state = ProjectState(
            project_id="test-project",
            htn_graph=root,
            task_status={"root": TaskStatus.PENDING},
            world_state={"content": special_content}
        )

        # Act
        repo.save(state)
        loaded = repo.load("test-project")

        # Assert
        assert loaded.world_state["content"] == special_content

    def test_handles_unicode_in_state(self, tmp_path):
        """Test that repository handles Unicode characters."""
        # Arrange
        db_path = tmp_path / "test.db"
        repo = SQLiteStateRepository(str(db_path))

        root = HTNNode(task_id="root", description="Root")
        unicode_content = "Hello 世界 🎉 مرحبا"
        state = ProjectState(
            project_id="test-project",
            htn_graph=root,
            task_status={"root": TaskStatus.PENDING},
            world_state={"content": unicode_content}
        )

        # Act
        repo.save(state)
        loaded = repo.load("test-project")

        # Assert
        assert loaded.world_state["content"] == unicode_content
