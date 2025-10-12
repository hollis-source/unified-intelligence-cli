"""State repository implementation using SQLite for persistence.

Provides persistent storage for project state with versioning and history tracking.
"""

import sqlite3
import json
import pickle
from pathlib import Path
from typing import Optional
from datetime import datetime

from src.interfaces import IStateRepository, ProjectState, TaskStatus
from src.entities.htn.htn_node import HTNNode


class SQLiteStateRepository(IStateRepository):
    """SQLite-based repository for project state persistence.

    Stores project state with full history tracking, supporting resumption
    and rollback capabilities.

    Attributes:
        db_path: Path to SQLite database file
    """

    def __init__(self, db_path: str = "data/project_builder_state.db"):
        """Initialize repository with database connection.

        Args:
            db_path: Path to SQLite database file (created if doesn't exist)
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        """Initialize database schema if not exists."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS project_states (
                    project_id TEXT NOT NULL,
                    version INTEGER NOT NULL,
                    htn_graph BLOB NOT NULL,
                    task_status TEXT NOT NULL,
                    world_state TEXT NOT NULL,
                    last_updated TEXT NOT NULL,
                    PRIMARY KEY (project_id, version)
                )
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_project_id
                ON project_states(project_id)
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_last_updated
                ON project_states(last_updated DESC)
            """)

            conn.commit()

    def save(self, state: ProjectState) -> None:
        """Persist project state to SQLite database.

        Args:
            state: Project state to save
        """
        with sqlite3.connect(self.db_path) as conn:
            # Serialize HTN graph using pickle (preserves object structure)
            htn_blob = pickle.dumps(state.htn_graph)

            # Serialize dictionaries to JSON
            task_status_json = json.dumps({
                task_id: status.value
                for task_id, status in state.task_status.items()
            })
            world_state_json = json.dumps(state.world_state)

            conn.execute("""
                INSERT OR REPLACE INTO project_states
                (project_id, version, htn_graph, task_status, world_state, last_updated)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                state.project_id,
                state.version,
                htn_blob,
                task_status_json,
                world_state_json,
                state.last_updated.isoformat()
            ))

            conn.commit()

    def load(self, project_id: str, version: Optional[int] = None) -> ProjectState:
        """Load project state from SQLite database.

        Args:
            project_id: ID of project to load
            version: Specific version to load (None for latest)

        Returns:
            Loaded project state

        Raises:
            ValueError: If project not found
        """
        with sqlite3.connect(self.db_path) as conn:
            if version is None:
                # Load latest version
                cursor = conn.execute("""
                    SELECT version, htn_graph, task_status, world_state, last_updated
                    FROM project_states
                    WHERE project_id = ?
                    ORDER BY version DESC
                    LIMIT 1
                """, (project_id,))
            else:
                # Load specific version
                cursor = conn.execute("""
                    SELECT version, htn_graph, task_status, world_state, last_updated
                    FROM project_states
                    WHERE project_id = ? AND version = ?
                """, (project_id, version))

            row = cursor.fetchone()

            if row is None:
                raise ValueError(f"Project '{project_id}' not found")

            version, htn_blob, task_status_json, world_state_json, last_updated_str = row

            # Deserialize HTN graph
            htn_graph = pickle.loads(htn_blob)

            # Deserialize dictionaries
            task_status = {
                task_id: TaskStatus(status_value)
                for task_id, status_value in json.loads(task_status_json).items()
            }
            world_state = json.loads(world_state_json)
            last_updated = datetime.fromisoformat(last_updated_str)

            return ProjectState(
                project_id=project_id,
                htn_graph=htn_graph,
                task_status=task_status,
                world_state=world_state,
                version=version,
                last_updated=last_updated
            )

    def exists(self, project_id: str) -> bool:
        """Check if project state exists in database.

        Args:
            project_id: ID of project to check

        Returns:
            True if project exists
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT 1 FROM project_states WHERE project_id = ? LIMIT 1
            """, (project_id,))

            return cursor.fetchone() is not None

    def delete(self, project_id: str) -> None:
        """Delete all versions of project state from database.

        Args:
            project_id: ID of project to delete
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                DELETE FROM project_states WHERE project_id = ?
            """, (project_id,))

            conn.commit()

    def get_all_versions(self, project_id: str) -> list[int]:
        """Get list of all version numbers for a project.

        Args:
            project_id: ID of project

        Returns:
            List of version numbers in ascending order
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT version FROM project_states
                WHERE project_id = ?
                ORDER BY version ASC
            """, (project_id,))

            return [row[0] for row in cursor.fetchall()]

    def get_latest_version(self, project_id: str) -> Optional[int]:
        """Get the latest version number for a project.

        Args:
            project_id: ID of project

        Returns:
            Latest version number, or None if project doesn't exist
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT MAX(version) FROM project_states WHERE project_id = ?
            """, (project_id,))

            result = cursor.fetchone()
            return result[0] if result[0] is not None else None
