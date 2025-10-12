"""Tests for state repository factory.

Sprint 1: Production Deployment - SurrealDB Integration
Tests environment-based database selection and configuration.
"""

import os
import pytest
from unittest.mock import patch, MagicMock

from src.project_builder.state.factory import create_state_repository, get_db_info
from src.project_builder.state.repository import SQLiteStateRepository
from src.project_builder.state.surreal_repository import SurrealDBStateRepository


class TestCreateStateRepository:
    """Tests for create_state_repository factory function."""

    def test_default_creates_sqlite(self):
        """Test that default behavior creates SQLite repository."""
        # Arrange & Act
        with patch.dict(os.environ, {}, clear=True):
            repo = create_state_repository()

        # Assert
        assert isinstance(repo, SQLiteStateRepository)
        assert repo.db_path.name == "project_builder_state.db"

    def test_explicit_sqlite_creates_sqlite(self):
        """Test explicit SQLite type creates SQLite repository."""
        # Arrange & Act
        repo = create_state_repository(db_type="sqlite", state_db_path="custom.db")

        # Assert
        assert isinstance(repo, SQLiteStateRepository)
        assert str(repo.db_path) == "custom.db"

    def test_env_var_sqlite_creates_sqlite(self):
        """Test PB_DB_TYPE=sqlite environment variable creates SQLite."""
        # Arrange & Act
        with patch.dict(os.environ, {"PB_DB_TYPE": "sqlite"}):
            repo = create_state_repository()

        # Assert
        assert isinstance(repo, SQLiteStateRepository)

    @patch('src.project_builder.state.surreal_repository.requests.Session')
    def test_explicit_surrealdb_creates_surrealdb(self, mock_session):
        """Test explicit SurrealDB type creates SurrealDB repository."""
        # Arrange
        mock_session_instance = MagicMock()
        mock_session_instance.get.return_value.status_code = 200
        mock_session.return_value = mock_session_instance

        # Act
        repo = create_state_repository(db_type="surrealdb")

        # Assert
        assert isinstance(repo, SurrealDBStateRepository)
        assert repo.host == "localhost"
        assert repo.port == 8000
        assert repo.namespace == "project_builder"
        assert repo.database == "production"

    @patch('src.project_builder.state.surreal_repository.requests.Session')
    def test_env_var_surrealdb_creates_surrealdb(self, mock_session):
        """Test PB_DB_TYPE=surrealdb environment variable creates SurrealDB."""
        # Arrange
        mock_session_instance = MagicMock()
        mock_session_instance.get.return_value.status_code = 200
        mock_session.return_value = mock_session_instance

        # Act
        with patch.dict(os.environ, {"PB_DB_TYPE": "surrealdb"}):
            repo = create_state_repository()

        # Assert
        assert isinstance(repo, SurrealDBStateRepository)

    @patch('src.project_builder.state.surreal_repository.requests.Session')
    def test_surrealdb_with_custom_env_vars(self, mock_session):
        """Test SurrealDB creation with custom environment variables."""
        # Arrange
        mock_session_instance = MagicMock()
        mock_session_instance.get.return_value.status_code = 200
        mock_session.return_value = mock_session_instance

        env_vars = {
            "PB_DB_TYPE": "surrealdb",
            "PB_DB_HOST": "custom-host",
            "PB_DB_PORT": "9000",
            "PB_DB_NAMESPACE": "custom_namespace",
            "PB_DB_DATABASE": "custom_db",
            "PB_DB_USER": "custom_user",
            "PB_DB_PASSWORD": "custom_password"
        }

        # Act
        with patch.dict(os.environ, env_vars):
            repo = create_state_repository()

        # Assert
        assert isinstance(repo, SurrealDBStateRepository)
        assert repo.host == "custom-host"
        assert repo.port == 9000
        assert repo.namespace == "custom_namespace"
        assert repo.database == "custom_db"
        assert repo.username == "custom_user"
        assert repo.password == "custom_password"

    def test_invalid_db_type_raises_error(self):
        """Test that invalid database type raises ValueError."""
        # Arrange & Act & Assert
        with pytest.raises(ValueError, match="Invalid database type: invalid"):
            create_state_repository(db_type="invalid")

    def test_case_insensitive_db_type(self):
        """Test that database type is case-insensitive."""
        # Arrange & Act
        with patch.dict(os.environ, {"PB_DB_TYPE": "SQLITE"}):
            repo = create_state_repository()

        # Assert
        assert isinstance(repo, SQLiteStateRepository)

    def test_explicit_type_overrides_env_var(self):
        """Test that explicit db_type parameter overrides environment variable."""
        # Arrange & Act
        with patch.dict(os.environ, {"PB_DB_TYPE": "surrealdb"}):
            repo = create_state_repository(db_type="sqlite")

        # Assert
        assert isinstance(repo, SQLiteStateRepository)


class TestGetDbInfo:
    """Tests for get_db_info configuration information function."""

    def test_default_returns_sqlite_info(self):
        """Test that default returns SQLite database info."""
        # Arrange & Act
        with patch.dict(os.environ, {}, clear=True):
            info = get_db_info()

        # Assert
        assert info["type"] == "sqlite"
        assert "path" in info
        assert info["path"] == "data/project_builder_state.db"

    def test_sqlite_env_returns_sqlite_info(self):
        """Test that PB_DB_TYPE=sqlite returns SQLite info."""
        # Arrange & Act
        with patch.dict(os.environ, {"PB_DB_TYPE": "sqlite"}):
            info = get_db_info()

        # Assert
        assert info["type"] == "sqlite"
        assert "path" in info

    def test_surrealdb_env_returns_surrealdb_info(self):
        """Test that PB_DB_TYPE=surrealdb returns SurrealDB info."""
        # Arrange
        env_vars = {
            "PB_DB_TYPE": "surrealdb",
            "PB_DB_HOST": "test-host",
            "PB_DB_PORT": "8001",
            "PB_DB_NAMESPACE": "test_ns",
            "PB_DB_DATABASE": "test_db",
            "PB_DB_USER": "test_user"
        }

        # Act
        with patch.dict(os.environ, env_vars):
            info = get_db_info()

        # Assert
        assert info["type"] == "surrealdb"
        assert info["host"] == "test-host"
        assert info["port"] == 8001
        assert info["namespace"] == "test_ns"
        assert info["database"] == "test_db"
        assert info["username"] == "test_user"
        assert "password" not in info  # Password should not be exposed

    def test_surrealdb_uses_defaults_when_env_vars_missing(self):
        """Test that SurrealDB info uses defaults when environment variables missing."""
        # Arrange & Act
        with patch.dict(os.environ, {"PB_DB_TYPE": "surrealdb"}):
            info = get_db_info()

        # Assert
        assert info["type"] == "surrealdb"
        assert info["host"] == "localhost"
        assert info["port"] == 8000
        assert info["namespace"] == "project_builder"
        assert info["database"] == "production"
        assert info["username"] == "root"

    def test_info_does_not_expose_password(self):
        """Test that get_db_info does not expose password for security."""
        # Arrange
        env_vars = {
            "PB_DB_TYPE": "surrealdb",
            "PB_DB_PASSWORD": "secret_password"
        }

        # Act
        with patch.dict(os.environ, env_vars):
            info = get_db_info()

        # Assert
        assert "password" not in info
        assert "PB_DB_PASSWORD" not in str(info)
