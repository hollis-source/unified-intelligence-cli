"""
Performance Data Repository - Infrastructure layer implementation.

Clean Architecture: Infrastructure layer implementing core interfaces.
Storage: SQLite for MVP, easily replaceable with PostgreSQL/MongoDB.

DIP Compliance: Implements IPerformanceDataRepository abstraction.
"""

import sqlite3
import asyncio
from typing import List, Optional
from datetime import datetime
from pathlib import Path

from src.routing.adaptive_interfaces import PerformanceLog, IPerformanceDataRepository


class PerformanceDataRepository:
    """
    SQLite-based repository for raw performance logs.

    Clean Architecture: Infrastructure adapter, replaceable without changing core.
    Thread-safe: Uses connection per operation (SQLite recommendation).
    """

    def __init__(self, db_path: str = "data/performance_logs.db"):
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
        Create performance_logs table if not exists.

        Schema:
        - id: Auto-increment primary key
        - model_id: Model identifier (e.g., "qwen3_hf_inference")
        - task_type: Task type (e.g., "code_analysis")
        - latency_ms: Execution latency in milliseconds
        - success: Boolean success flag
        - cost_usd: Cost in USD
        - timestamp: ISO 8601 timestamp
        - task_description: Optional task description for similarity matching
        """
        conn = sqlite3.connect(str(self.db_path))
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS performance_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    model_id TEXT NOT NULL,
                    task_type TEXT NOT NULL,
                    latency_ms REAL NOT NULL,
                    success INTEGER NOT NULL,
                    cost_usd REAL NOT NULL,
                    timestamp TEXT NOT NULL,
                    task_description TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Indexes for fast queries
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_model_task
                ON performance_logs(model_id, task_type)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_timestamp
                ON performance_logs(timestamp)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_model_timestamp
                ON performance_logs(model_id, timestamp)
            """)

            conn.commit()
        finally:
            conn.close()

    async def save_performance_log(self, log: PerformanceLog) -> None:
        """
        Save performance log asynchronously (non-blocking).

        Args:
            log: Performance log to save

        Note: Runs in thread pool to avoid blocking event loop.
        """
        await asyncio.to_thread(self._save_performance_log_sync, log)

    def _save_performance_log_sync(self, log: PerformanceLog) -> None:
        """
        Synchronous save implementation.

        Args:
            log: Performance log to save
        """
        conn = sqlite3.connect(str(self.db_path))
        try:
            conn.execute("""
                INSERT INTO performance_logs
                (model_id, task_type, latency_ms, success, cost_usd, timestamp, task_description)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                log.model_id,
                log.task_type,
                log.latency_ms,
                1 if log.success else 0,
                log.cost_usd,
                log.timestamp.isoformat(),
                log.task_description
            ))
            conn.commit()
        finally:
            conn.close()

    def get_raw_logs_for_time_range(
        self,
        start_time: datetime,
        end_time: datetime,
        model_id: Optional[str] = None,
        task_type: Optional[str] = None
    ) -> List[PerformanceLog]:
        """
        Retrieve raw logs for time range with optional filters.

        Args:
            start_time: Start of time range
            end_time: End of time range
            model_id: Optional filter by model
            task_type: Optional filter by task type

        Returns:
            List of performance logs matching criteria
        """
        conn = sqlite3.connect(str(self.db_path))
        try:
            query = """
                SELECT model_id, task_type, latency_ms, success, cost_usd, timestamp, task_description
                FROM performance_logs
                WHERE timestamp >= ? AND timestamp <= ?
            """
            params = [start_time.isoformat(), end_time.isoformat()]

            if model_id:
                query += " AND model_id = ?"
                params.append(model_id)

            if task_type:
                query += " AND task_type = ?"
                params.append(task_type)

            query += " ORDER BY timestamp DESC"

            cursor = conn.execute(query, params)
            rows = cursor.fetchall()

            return [
                PerformanceLog(
                    model_id=row[0],
                    task_type=row[1],
                    latency_ms=row[2],
                    success=bool(row[3]),
                    cost_usd=row[4],
                    timestamp=datetime.fromisoformat(row[5]),
                    task_description=row[6]
                )
                for row in rows
            ]
        finally:
            conn.close()

    def get_recent_logs(self, limit: int = 1000) -> List[PerformanceLog]:
        """
        Get most recent logs for quick analysis.

        Args:
            limit: Maximum number of logs to retrieve

        Returns:
            List of recent performance logs
        """
        conn = sqlite3.connect(str(self.db_path))
        try:
            cursor = conn.execute("""
                SELECT model_id, task_type, latency_ms, success, cost_usd, timestamp, task_description
                FROM performance_logs
                ORDER BY timestamp DESC
                LIMIT ?
            """, (limit,))
            rows = cursor.fetchall()

            return [
                PerformanceLog(
                    model_id=row[0],
                    task_type=row[1],
                    latency_ms=row[2],
                    success=bool(row[3]),
                    cost_usd=row[4],
                    timestamp=datetime.fromisoformat(row[5]),
                    task_description=row[6]
                )
                for row in rows
            ]
        finally:
            conn.close()

    def get_logs_for_model_task(
        self,
        model_id: str,
        task_type: str,
        limit: Optional[int] = None
    ) -> List[PerformanceLog]:
        """
        Get logs for specific model and task type.

        Args:
            model_id: Model identifier
            task_type: Task type
            limit: Optional limit on number of logs

        Returns:
            List of performance logs
        """
        conn = sqlite3.connect(str(self.db_path))
        try:
            query = """
                SELECT model_id, task_type, latency_ms, success, cost_usd, timestamp, task_description
                FROM performance_logs
                WHERE model_id = ? AND task_type = ?
                ORDER BY timestamp DESC
            """
            params = [model_id, task_type]

            if limit:
                query += " LIMIT ?"
                params.append(limit)

            cursor = conn.execute(query, params)
            rows = cursor.fetchall()

            return [
                PerformanceLog(
                    model_id=row[0],
                    task_type=row[1],
                    latency_ms=row[2],
                    success=bool(row[3]),
                    cost_usd=row[4],
                    timestamp=datetime.fromisoformat(row[5]),
                    task_description=row[6]
                )
                for row in rows
            ]
        finally:
            conn.close()

    def get_stats(self) -> dict:
        """
        Get repository statistics.

        Returns:
            Dict with stats (total_logs, earliest_log, latest_log, etc.)
        """
        conn = sqlite3.connect(str(self.db_path))
        try:
            cursor = conn.execute("""
                SELECT
                    COUNT(*) as total,
                    MIN(timestamp) as earliest,
                    MAX(timestamp) as latest,
                    COUNT(DISTINCT model_id) as num_models,
                    COUNT(DISTINCT task_type) as num_task_types
                FROM performance_logs
            """)
            row = cursor.fetchone()

            return {
                "total_logs": row[0],
                "earliest_log": row[1],
                "latest_log": row[2],
                "num_models": row[3],
                "num_task_types": row[4]
            }
        finally:
            conn.close()
