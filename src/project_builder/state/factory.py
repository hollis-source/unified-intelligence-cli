"""State repository factory for environment-based database selection.

Sprint 1: Production Deployment - SurrealDB Integration
Provides factory pattern for selecting database backend based on environment configuration.

Clean Architecture: Adapter layer factory (infrastructure concern)
SOLID: Factory pattern with dependency inversion, environment-driven configuration
"""

import os
from typing import Optional

from src.interfaces import IStateRepository
from .repository import SQLiteStateRepository
from .surreal_repository import SurrealDBStateRepository


def create_state_repository(
    db_type: Optional[str] = None,
    state_db_path: str = "data/project_builder_state.db"
) -> IStateRepository:
    """Create state repository based on environment configuration.

    Factory pattern for database backend selection. Supports:
    - SQLite: Local development, simple deployments
    - SurrealDB: Production, multi-model capabilities (graph, vector, real-time)

    Environment Variables:
        PB_DB_TYPE: Database type ("sqlite" or "surrealdb", default: "sqlite")

        SurrealDB-specific:
        PB_DB_HOST: SurrealDB host (default: "localhost")
        PB_DB_PORT: SurrealDB port (default: 8000)
        PB_DB_NAMESPACE: SurrealDB namespace (default: "project_builder")
        PB_DB_DATABASE: SurrealDB database (default: "production")
        PB_DB_USER: SurrealDB username (default: "root")
        PB_DB_PASSWORD: SurrealDB password (default: "changeme")

    Args:
        db_type: Override database type (None = use PB_DB_TYPE env var)
        state_db_path: SQLite database path (used if db_type="sqlite")

    Returns:
        IStateRepository implementation (SQLite or SurrealDB)

    Example:
        # Use environment configuration
        repo = create_state_repository()

        # Explicit SQLite
        repo = create_state_repository(db_type="sqlite", state_db_path="custom.db")

        # Explicit SurrealDB
        repo = create_state_repository(db_type="surrealdb")
    """
    # Determine database type from parameter or environment
    selected_db_type = db_type or os.getenv("PB_DB_TYPE", "sqlite").lower()

    if selected_db_type == "surrealdb":
        # Create SurrealDB repository with environment configuration
        return SurrealDBStateRepository(
            host=os.getenv("PB_DB_HOST", "localhost"),
            port=int(os.getenv("PB_DB_PORT", "8000")),
            namespace=os.getenv("PB_DB_NAMESPACE", "project_builder"),
            database=os.getenv("PB_DB_DATABASE", "production"),
            username=os.getenv("PB_DB_USER", "root"),
            password=os.getenv("PB_DB_PASSWORD", "changeme")
        )
    elif selected_db_type == "sqlite":
        # Create SQLite repository with provided path
        return SQLiteStateRepository(db_path=state_db_path)
    else:
        # Invalid database type - raise clear error
        raise ValueError(
            f"Invalid database type: {selected_db_type}. "
            f"Supported types: 'sqlite', 'surrealdb'. "
            f"Set PB_DB_TYPE environment variable or pass db_type parameter."
        )


def get_db_info() -> dict:
    """Get current database configuration information.

    Returns:
        Dictionary with database type and connection details

    Example:
        info = get_db_info()
        print(f"Using {info['type']} database")
        if info['type'] == 'surrealdb':
            print(f"Connected to {info['host']}:{info['port']}")
    """
    db_type = os.getenv("PB_DB_TYPE", "sqlite").lower()

    if db_type == "surrealdb":
        return {
            "type": "surrealdb",
            "host": os.getenv("PB_DB_HOST", "localhost"),
            "port": int(os.getenv("PB_DB_PORT", "8000")),
            "namespace": os.getenv("PB_DB_NAMESPACE", "project_builder"),
            "database": os.getenv("PB_DB_DATABASE", "production"),
            "username": os.getenv("PB_DB_USER", "root")
            # Note: Password not included for security
        }
    else:
        return {
            "type": "sqlite",
            "path": "data/project_builder_state.db"
        }
