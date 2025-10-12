"""
Model Summary Repository - Infrastructure layer implementation.

Clean Architecture: Infrastructure layer implementing core interfaces.
Storage: SQLite for MVP, easily replaceable with Redis/PostgreSQL.

DIP Compliance: Implements IModelSummaryRepository abstraction.
"""

import sqlite3
from typing import List, Optional
from datetime import datetime
from pathlib import Path

from src.routing.adaptive_interfaces import ModelSummary, IModelSummaryRepository


class ModelSummaryRepository:
    """
    SQLite-based repository for aggregated model summaries.

    Clean Architecture: Infrastructure adapter, replaceable without changing core.
    Stores precomputed summaries for fast selection.
    """

    def __init__(self, db_path: str = "data/model_summaries.db"):
        """
        Initialize repository with database path.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize_schema()

    def _initialize_schema(self) -> None:
        """
        Create model_summaries table if not exists.

        Schema:
        - model_id: Model identifier (composite key with task_type)
        - task_type: Task type (composite key with model_id)
        - avg_latency_ms: Average latency in milliseconds
        - success_rate: Success rate (0.0-1.0)
        - avg_cost_per_task: Average cost per task in USD
        - sample_size: Number of tasks used to compute summary
        - last_updated: ISO 8601 timestamp
        """
        conn = sqlite3.connect(str(self.db_path))
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS model_summaries (
                    model_id TEXT NOT NULL,
                    task_type TEXT NOT NULL,
                    avg_latency_ms REAL NOT NULL,
                    success_rate REAL NOT NULL,
                    avg_cost_per_task REAL NOT NULL,
                    sample_size INTEGER NOT NULL,
                    last_updated TEXT NOT NULL,
                    PRIMARY KEY (model_id, task_type)
                )
            """)

            # Indexes for fast queries
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_task_type
                ON model_summaries(task_type)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_last_updated
                ON model_summaries(last_updated)
            """)

            conn.commit()
        finally:
            conn.close()

    def get_summary_for_task_type(
        self,
        task_type: str,
        model_id: Optional[str] = None
    ) -> List[ModelSummary]:
        """
        Get summaries for a task type.

        Args:
            task_type: Type of task
            model_id: Optional filter by specific model

        Returns:
            List of summaries matching criteria
        """
        conn = sqlite3.connect(str(self.db_path))
        try:
            if model_id:
                query = """
                    SELECT model_id, task_type, avg_latency_ms, success_rate,
                           avg_cost_per_task, sample_size, last_updated
                    FROM model_summaries
                    WHERE task_type = ? AND model_id = ?
                """
                params = [task_type, model_id]
            else:
                query = """
                    SELECT model_id, task_type, avg_latency_ms, success_rate,
                           avg_cost_per_task, sample_size, last_updated
                    FROM model_summaries
                    WHERE task_type = ?
                    ORDER BY success_rate DESC, avg_cost_per_task ASC
                """
                params = [task_type]

            cursor = conn.execute(query, params)
            rows = cursor.fetchall()

            return [
                ModelSummary(
                    model_id=row[0],
                    task_type=row[1],
                    avg_latency_ms=row[2],
                    success_rate=row[3],
                    avg_cost_per_task=row[4],
                    sample_size=row[5],
                    last_updated=datetime.fromisoformat(row[6])
                )
                for row in rows
            ]
        finally:
            conn.close()

    def get_all_summaries(self) -> List[ModelSummary]:
        """
        Get all summaries for global analysis.

        Returns:
            List of all model summaries
        """
        conn = sqlite3.connect(str(self.db_path))
        try:
            cursor = conn.execute("""
                SELECT model_id, task_type, avg_latency_ms, success_rate,
                       avg_cost_per_task, sample_size, last_updated
                FROM model_summaries
                ORDER BY model_id, task_type
            """)
            rows = cursor.fetchall()

            return [
                ModelSummary(
                    model_id=row[0],
                    task_type=row[1],
                    avg_latency_ms=row[2],
                    success_rate=row[3],
                    avg_cost_per_task=row[4],
                    sample_size=row[5],
                    last_updated=datetime.fromisoformat(row[6])
                )
                for row in rows
            ]
        finally:
            conn.close()

    def update_summary(self, summary: ModelSummary) -> None:
        """
        Update or insert a summary (upsert).

        Args:
            summary: Summary to update/insert
        """
        conn = sqlite3.connect(str(self.db_path))
        try:
            conn.execute("""
                INSERT OR REPLACE INTO model_summaries
                (model_id, task_type, avg_latency_ms, success_rate,
                 avg_cost_per_task, sample_size, last_updated)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                summary.model_id,
                summary.task_type,
                summary.avg_latency_ms,
                summary.success_rate,
                summary.avg_cost_per_task,
                summary.sample_size,
                summary.last_updated.isoformat()
            ))
            conn.commit()
        finally:
            conn.close()

    def get_summary(self, model_id: str, task_type: str) -> Optional[ModelSummary]:
        """
        Get specific summary for model and task type.

        Args:
            model_id: Model identifier
            task_type: Task type

        Returns:
            Summary if exists, None otherwise
        """
        conn = sqlite3.connect(str(self.db_path))
        try:
            cursor = conn.execute("""
                SELECT model_id, task_type, avg_latency_ms, success_rate,
                       avg_cost_per_task, sample_size, last_updated
                FROM model_summaries
                WHERE model_id = ? AND task_type = ?
            """, (model_id, task_type))
            row = cursor.fetchone()

            if not row:
                return None

            return ModelSummary(
                model_id=row[0],
                task_type=row[1],
                avg_latency_ms=row[2],
                success_rate=row[3],
                avg_cost_per_task=row[4],
                sample_size=row[5],
                last_updated=datetime.fromisoformat(row[6])
            )
        finally:
            conn.close()

    def delete_summary(self, model_id: str, task_type: str) -> bool:
        """
        Delete a summary.

        Args:
            model_id: Model identifier
            task_type: Task type

        Returns:
            True if deleted, False if not found
        """
        conn = sqlite3.connect(str(self.db_path))
        try:
            cursor = conn.execute("""
                DELETE FROM model_summaries
                WHERE model_id = ? AND task_type = ?
            """, (model_id, task_type))
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    def get_stats(self) -> dict:
        """
        Get repository statistics.

        Returns:
            Dict with stats (total_summaries, num_models, etc.)
        """
        conn = sqlite3.connect(str(self.db_path))
        try:
            cursor = conn.execute("""
                SELECT
                    COUNT(*) as total,
                    COUNT(DISTINCT model_id) as num_models,
                    COUNT(DISTINCT task_type) as num_task_types,
                    AVG(sample_size) as avg_sample_size,
                    MAX(last_updated) as latest_update
                FROM model_summaries
            """)
            row = cursor.fetchone()

            return {
                "total_summaries": row[0],
                "num_models": row[1],
                "num_task_types": row[2],
                "avg_sample_size": row[3] if row[3] else 0,
                "latest_update": row[4]
            }
        finally:
            conn.close()
