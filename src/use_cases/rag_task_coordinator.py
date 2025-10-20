from __future__ import annotations

import logging
import textwrap
import uuid
from typing import List, Optional

import numpy as np

from src.entity import Agent, Task, ExecutionResult, ExecutionStatus, ExecutionContext
from src.interface import IAgentCoordinator, IAgentExecutor, ITaskPlanner, ExecutionPlan

from src.use_cases.task_coordinator import TaskCoordinatorUseCase
from src.adapters.rag.embedding_pipeline import EmbeddingPipeline
from src.adapters.rag.surrealdb_store import SurrealDBStore


class RAGTaskCoordinator(IAgentCoordinator):
    """Decorator over TaskCoordinatorUseCase that captures execution feedback to SurrealDB."""

    def __init__(
        self,
        task_planner: ITaskPlanner,
        agent_executor: IAgentExecutor,
        db_store: SurrealDBStore,
        embedding_pipeline: Optional[EmbeddingPipeline] = None,
        max_retries: int = 3,
        logger: Optional[logging.Logger] = None,
    ):
        self.base = TaskCoordinatorUseCase(task_planner, agent_executor, max_retries, logger)
        self.db = db_store
        self.embedder = embedding_pipeline or EmbeddingPipeline()
        self.logger = logger or logging.getLogger(__name__)

    async def coordinate(
        self,
        tasks: List[Task],
        agents: List[Agent],
        context: Optional[ExecutionContext] = None,
    ) -> List[ExecutionResult]:
        results = await self.base.coordinate(tasks, agents, context)
        await self._capture_patterns(tasks, results)
        return results

    async def coordinate_task(
        self,
        task: Task,
        context: Optional[ExecutionContext] = None,
    ) -> ExecutionResult:
        result = await self.base.coordinate_task(task, context)
        await self._capture_patterns([task], [result])
        return result

    async def _capture_patterns(self, tasks: List[Task], results: List[ExecutionResult]) -> None:
        for task, result in zip(tasks, results):
            try:
                excerpt = self._make_excerpt(result)
                embedding = await self.embedder.embed_text(
                    f"Task: {task.description}\nStatus: {result.status.value}\nOutput: {excerpt}"
                )
                await self.db.store_execution_log(
                    execution_id=str(uuid.uuid4()),
                    task_description=task.description,
                    task_domain=getattr(task, "domain", None),
                    agent_role=result.metadata.get("agent_role") if result.metadata else None,
                    success=(result.status == ExecutionStatus.SUCCESS),
                    status=result.status.value,
                    latency_seconds=float(result.metadata.get("latency_seconds", 0.0)) if result.metadata else 0.0,
                    output_excerpt=excerpt,
                    embedding=embedding,
                    embedding_model=self.embedder.model_id,
                    metadata=result.metadata or {},
                )
            except Exception as e:
                self.logger.warning(f"Failed to capture execution pattern: {e}")

    def _make_excerpt(self, result: ExecutionResult, max_len: int = 500) -> str:
        text = str(result.output) if result.output is not None else ""
        if not text and result.errors:
            text = " | ".join(map(str, result.errors))
        return textwrap.shorten(text, width=max_len, placeholder="...")

