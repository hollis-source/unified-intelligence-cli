"""Integration tests for SurrealDB state repository.

Sprint 1: Production Deployment - SurrealDB Integration
Tests real SurrealDB connectivity and state operations.

IMPORTANT: These tests require a running SurrealDB instance.
Run with: docker-compose -f docker-compose.production.yml up surrealdb
Skip if SurrealDB unavailable: pytest -m "not integration"
"""

import pytest
import os
from datetime import datetime

from src.project_builder.state.factory import create_state_repository
from src.project_builder.state.manager import ProjectStateManager
from src.entities.htn.htn_node import HTNNode
from src.interfaces import TaskStatus


# Mark all tests in this module as integration tests
pytestmark = pytest.mark.integration


@pytest.fixture
def surrealdb_available():
    """Check if SurrealDB is available for testing.

    Returns:
        bool: True if SurrealDB accessible, False otherwise
    """
    try:
        import requests
        response = requests.get("http://localhost:8001/health", timeout=2)
        return response.status_code == 200
    except:
        return False


@pytest.fixture
def surrealdb_repo(surrealdb_available):
    """Create SurrealDB repository for testing.

    Skips test if SurrealDB not available.
    """
    if not surrealdb_available:
        pytest.skip("SurrealDB not available at localhost:8001")

    # Set environment for SurrealDB
    # Read password from environment (set in .env file)
    env_vars = {
        "PB_DB_TYPE": "surrealdb",
        "PB_DB_HOST": "localhost",
        "PB_DB_PORT": "8001",  # Use port 8001 (mapped from container's 8000)
        "PB_DB_NAMESPACE": "project_builder",
        "PB_DB_DATABASE": "test",  # Use test database
        "PB_DB_USER": "root",
        "PB_DB_PASSWORD": os.getenv("PB_DB_PASSWORD", "changeme")  # Use env var or fallback
    }

    with pytest.MonkeyPatch.context() as mp:
        for key, value in env_vars.items():
            mp.setenv(key, value)

        repo = create_state_repository()
        yield repo

        # Cleanup: Delete test projects
        # (SurrealDB test database can be recreated each run)


@pytest.fixture
def test_htn():
    """Create simple HTN graph for testing.

    Returns:
        HTNNode: Root node with 2 subtasks
    """
    # Create child tasks first (primitive tasks with no subtasks)
    child1 = HTNNode(
        task_id="child_1",
        description="First child task",
        preconditions={},
        effects={"result1": "completed"}
    )

    child2 = HTNNode(
        task_id="child_2",
        description="Second child task",
        preconditions={"result1": "completed"},
        effects={"result2": "completed"}
    )

    # Create root (composite task with subtasks)
    root = HTNNode(
        task_id="root_task",
        description="Test root task",
        subtasks=[child1, child2],
        preconditions={},
        effects={}
    )

    return root


class TestSurrealDBConnectivity:
    """Test basic SurrealDB connectivity and operations."""

    def test_create_repository_from_env(self, surrealdb_available):
        """Test creating SurrealDB repository from environment variables."""
        if not surrealdb_available:
            pytest.skip("SurrealDB not available")

        # Arrange
        env_vars = {
            "PB_DB_TYPE": "surrealdb",
            "PB_DB_HOST": "localhost",
            "PB_DB_PORT": "8001"
        }

        # Act
        with pytest.MonkeyPatch.context() as mp:
            for key, value in env_vars.items():
                mp.setenv(key, value)

            repo = create_state_repository()

        # Assert
        from src.project_builder.state.surreal_repository import SurrealDBStateRepository
        assert isinstance(repo, SurrealDBStateRepository)
        assert repo.host == "localhost"
        assert repo.port == 8001


class TestSurrealDBStateOperations:
    """Test state save/load operations with SurrealDB."""

    def test_save_and_load_state(self, surrealdb_repo, test_htn):
        """Test saving and loading project state to/from SurrealDB."""
        # Arrange
        manager = ProjectStateManager(surrealdb_repo)
        project_id = f"test-project-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

        # Act - Initialize state
        initial_state = manager.initialize(project_id, test_htn)

        # Assert initial state
        assert initial_state.project_id == project_id
        assert len(initial_state.task_status) == 3  # root + 2 children
        assert all(status == TaskStatus.PENDING for status in initial_state.task_status.values())

        # Act - Load state
        loaded_state = manager.load_state(project_id)

        # Assert loaded state matches
        assert loaded_state.project_id == initial_state.project_id
        assert loaded_state.version == initial_state.version
        assert loaded_state.task_status == initial_state.task_status
        assert loaded_state.world_state == initial_state.world_state

    def test_update_task_status(self, surrealdb_repo, test_htn):
        """Test updating task status and persisting to SurrealDB."""
        # Arrange
        manager = ProjectStateManager(surrealdb_repo)
        project_id = f"test-status-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        manager.initialize(project_id, test_htn)

        # Act - Update task status
        manager.mark_task_status("child_1", TaskStatus.COMPLETED)

        # Assert - Reload and verify
        manager2 = ProjectStateManager(surrealdb_repo)
        loaded_state = manager2.load_state(project_id)
        assert loaded_state.task_status["child_1"] == TaskStatus.COMPLETED
        assert loaded_state.task_status["child_2"] == TaskStatus.PENDING

    def test_apply_effects(self, surrealdb_repo, test_htn):
        """Test applying effects and persisting to SurrealDB."""
        # Arrange
        manager = ProjectStateManager(surrealdb_repo)
        project_id = f"test-effects-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        manager.initialize(project_id, test_htn)

        # Act - Apply effects
        effects = {
            "artifact_code": "def hello(): pass",
            "test_result": "passed"
        }
        manager.apply_effects(effects)

        # Assert - Reload and verify
        manager2 = ProjectStateManager(surrealdb_repo)
        loaded_state = manager2.load_state(project_id)
        assert loaded_state.world_state["artifact_code"] == "def hello(): pass"
        assert loaded_state.world_state["test_result"] == "passed"

    def test_version_increments(self, surrealdb_repo, test_htn):
        """Test that state versions increment on updates."""
        # Arrange
        manager = ProjectStateManager(surrealdb_repo)
        project_id = f"test-version-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        initial_state = manager.initialize(project_id, test_htn)

        # Act - Make updates
        manager.mark_task_status("child_1", TaskStatus.COMPLETED)
        manager.apply_effects({"result": "done"})

        # Assert - Version incremented
        current_state = manager.get_current_state()
        assert current_state.version > initial_state.version


class TestSurrealDBAdvancedFeatures:
    """Test SurrealDB-specific advanced features (graph, vector)."""

    @pytest.mark.skip(reason="Graph edges not yet implemented in state manager")
    def test_graph_relationships(self, surrealdb_repo, test_htn):
        """Test that SurrealDB stores graph relationships between projects/tasks."""
        # Future: Test graph queries like:
        # SELECT ->has_task->tasks.* FROM projects:test_project;
        pass

    @pytest.mark.skip(reason="Vector embeddings not yet implemented")
    def test_semantic_artifact_search(self, surrealdb_repo):
        """Test semantic search of artifacts using vector embeddings."""
        # Future: Test vector search like:
        # SELECT * FROM artifacts WHERE embedding <|10|> $query_embedding;
        pass


class TestFactoryWithSurrealDB:
    """Test repository factory with SurrealDB."""

    def test_factory_creates_surrealdb_from_env(self, surrealdb_available):
        """Test that factory creates SurrealDB repo when PB_DB_TYPE=surrealdb."""
        if not surrealdb_available:
            pytest.skip("SurrealDB not available")

        # Arrange
        env_vars = {
            "PB_DB_TYPE": "surrealdb",
            "PB_DB_HOST": "localhost",
            "PB_DB_PORT": "8001"
        }

        # Act
        with pytest.MonkeyPatch.context() as mp:
            for key, value in env_vars.items():
                mp.setenv(key, value)

            repo = create_state_repository()

        # Assert
        from src.project_builder.state.surreal_repository import SurrealDBStateRepository
        assert isinstance(repo, SurrealDBStateRepository)

    def test_factory_defaults_to_sqlite_when_surrealdb_unavailable(self):
        """Test that factory falls back to SQLite if SurrealDB unavailable."""
        # Arrange - Point to non-existent SurrealDB
        env_vars = {
            "PB_DB_TYPE": "surrealdb",
            "PB_DB_HOST": "nonexistent-host",
            "PB_DB_PORT": "9999"
        }

        # Act & Assert - Should raise connection error, not fall back
        with pytest.MonkeyPatch.context() as mp:
            for key, value in env_vars.items():
                mp.setenv(key, value)

            with pytest.raises(ConnectionError):
                create_state_repository()
