"""
Data collection utilities for model training.

Week 9 Phase 1: Capture agent-task interactions for fine-tuning dataset.
Clean Architecture: Utility layer, no business logic coupling.
"""

import json
import uuid
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)


class DataCollector:
    """
    Collects agent execution data for model training.

    Week 9: Passive data collection from production usage.
    Stores interactions in JSONL format (one JSON object per line).

    Schema:
        {
            "id": "uuid",
            "timestamp": "ISO 8601",
            "task": {"task_id": str, "description": str, "priority": int},
            "agent": {"role": str, "capabilities": [str]},
            "llm": {"provider": str, "model": str, "config": {...}},
            "execution": {
                "status": "success|failure",
                "duration_ms": int,
                "input_messages": [...],
                "output": str,
                "errors": [...],
                "error_details": {...}
            },
            "context": {"history_length": int, "orchestrator": str}
        }

    Usage:
        collector = DataCollector(data_dir="data/training")
        collector.log_interaction(
            task=task,
            agent=agent,
            messages=messages,
            output=response,
            status="success",
            duration_ms=1234,
            llm_config=config,
            provider="tongyi"
        )
    """

    def __init__(self, data_dir: str = "data/training", enabled: bool = True):
        """
        Initialize data collector.

        Args:
            data_dir: Directory to store collected data
            enabled: Whether collection is enabled (default: True)
        """
        self.data_dir = Path(data_dir)
        self.enabled = enabled

        if self.enabled:
            # Create data directory if it doesn't exist
            self.data_dir.mkdir(parents=True, exist_ok=True)

            # Create JSONL file with date-based naming
            today = datetime.now().strftime("%Y%m%d")
            self.log_file = self.data_dir / f"interactions_{today}.jsonl"

            logger.info(f"DataCollector initialized: {self.log_file}")

    def log_interaction(
        self,
        task: Any,  # Task entity
        agent: Any,  # Agent entity
        messages: List[Dict[str, str]],
        output: Optional[str],
        status: str,
        duration_ms: int,
        llm_config: Any,  # LLMConfig
        provider: str,
        errors: Optional[List[str]] = None,
        error_details: Optional[Dict[str, Any]] = None,
        orchestrator: str = "simple",
        context_history_length: int = 0
    ) -> None:
        """
        Log a single agent-task interaction.

        Args:
            task: Task entity with task_id, description, priority
            agent: Agent entity with role, capabilities, agent_id
            messages: LLM input messages (system, user, assistant)
            output: LLM output (if success)
            status: Execution status ("success" or "failure")
            duration_ms: Execution duration in milliseconds
            llm_config: LLM configuration (temperature, max_tokens)
            provider: LLM provider name (mock, grok, tongyi)
            errors: Error messages (if failure)
            error_details: Detailed error context (if failure)
            orchestrator: Orchestrator mode (simple, openai-agents)
            context_history_length: Number of history messages in context
        """
        if not self.enabled:
            return

        try:
            # Build interaction record
            record = {
                "id": str(uuid.uuid4()),
                "timestamp": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
                "task": {
                    "task_id": task.task_id,
                    "description": task.description,
                    "priority": getattr(task, "priority", 0)
                },
                "agent": {
                    "role": agent.role,
                    "capabilities": agent.capabilities
                },
                "llm": {
                    "provider": provider,
                    "model": getattr(llm_config, "model", "unknown"),
                    "config": {
                        "temperature": llm_config.temperature,
                        "max_tokens": llm_config.max_tokens
                    }
                },
                "execution": {
                    "status": status,
                    "duration_ms": duration_ms,
                    "input_messages": messages,
                    "output": output,
                    "errors": errors or [],
                    "error_details": error_details
                },
                "context": {
                    "history_length": context_history_length,
                    "orchestrator": orchestrator
                }
            }

            # Append to JSONL file (atomic write)
            with open(self.log_file, 'a') as f:
                f.write(json.dumps(record) + "\n")

            logger.debug(f"Logged interaction {record['id']} for task {task.task_id}")

        except Exception as e:
            # Don't fail execution if logging fails
            logger.error(f"Failed to log interaction: {e}", exc_info=True)

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get collection statistics for current day.

        Returns:
            Stats dict with total_interactions, success_count, failure_count
        """
        if not self.enabled or not self.log_file.exists():
            return {
                "total_interactions": 0,
                "success_count": 0,
                "failure_count": 0,
                "enabled": self.enabled
            }

        try:
            total = 0
            success = 0
            failure = 0

            with open(self.log_file, 'r') as f:
                for line in f:
                    record = json.loads(line)
                    total += 1
                    if record["execution"]["status"] == "success":
                        success += 1
                    else:
                        failure += 1

            return {
                "total_interactions": total,
                "success_count": success,
                "failure_count": failure,
                "success_rate": success / total if total > 0 else 0.0,
                "log_file": str(self.log_file),
                "enabled": self.enabled
            }

        except Exception as e:
            logger.error(f"Failed to get statistics: {e}")
            return {
                "total_interactions": 0,
                "success_count": 0,
                "failure_count": 0,
                "error": str(e),
                "enabled": self.enabled
            }

    def load_interactions(
        self,
        limit: Optional[int] = None,
        status_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Load interactions from current log file.

        Args:
            limit: Maximum number of interactions to load (newest first)
            status_filter: Filter by status ("success" or "failure")

        Returns:
            List of interaction records
        """
        if not self.enabled or not self.log_file.exists():
            return []

        try:
            interactions = []

            with open(self.log_file, 'r') as f:
                for line in f:
                    record = json.loads(line)

                    # Apply status filter
                    if status_filter and record["execution"]["status"] != status_filter:
                        continue

                    interactions.append(record)

            # Return newest first, apply limit
            interactions.reverse()

            if limit:
                interactions = interactions[:limit]

            return interactions

        except Exception as e:
            logger.error(f"Failed to load interactions: {e}")
            return []
