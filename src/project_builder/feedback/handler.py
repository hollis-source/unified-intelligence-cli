from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from typing import Dict, List, Any

from src.interfaces import ProjectState, ExecutionResult, TaskStatus


class FailureType(Enum):
    TIMEOUT = auto()
    DEPENDENCY_MISSING = auto()
    MODEL_FAILURE = auto()
    PRECONDITION_VIOLATION = auto()
    RESOURCE_UNAVAILABLE = auto()
    UNKNOWN = auto()

    def __str__(self) -> str:  # for simpler string usage
        return self.name.lower()


class ReplanningStrategy(Enum):
    RETRY_WITH_DIFFERENT_MODEL = auto()
    REORDER_DEPENDENCIES = auto()
    REFINE_DECOMPOSITION = auto()
    FAIL_PROJECT = auto()


@dataclass
class FeedbackLoopHandler:
    max_retries: int = 3

    def __post_init__(self) -> None:
        self.failure_history: Dict[str, List[Dict[str, Any]]] = {}

    # ---- Classification / Analysis -------------------------------------------------
    def _classify_failure(self, result: ExecutionResult) -> FailureType:
        msg = (result.error or "").lower()
        if "timed out" in msg or "timeout" in msg:
            return FailureType.TIMEOUT
        if "dependency" in msg:
            return FailureType.DEPENDENCY_MISSING
        if "quota" in msg or "model" in msg:
            return FailureType.MODEL_FAILURE
        if "precondition" in msg:
            return FailureType.PRECONDITION_VIOLATION
        if "resource" in msg or "unavailable" in msg:
            return FailureType.RESOURCE_UNAVAILABLE
        return FailureType.UNKNOWN

    def _analyze_failures(self, failed_tasks: List[ExecutionResult]) -> Dict[str, Any]:
        failure_types: Dict[str, int] = {}
        affected_models: List[str] = []
        affected_agents: List[str] = []
        error_messages: List[Dict[str, str]] = []
        for r in failed_tasks:
            ftype = str(self._classify_failure(r))
            failure_types[ftype] = failure_types.get(ftype, 0) + 1
            if r.metadata.get("model"):
                affected_models.append(r.metadata["model"])  # type: ignore[index]
            if r.metadata.get("agent"):
                affected_agents.append(r.metadata["agent"])  # type: ignore[index]
            error_messages.append({"task_id": r.task_id, "error": r.error or ""})
        return {
            "total_failures": len(failed_tasks),
            "failure_types": failure_types,
            "affected_models": affected_models,
            "affected_agents": affected_agents,
            "error_messages": error_messages,
        }

    # ---- Strategy selection / application -----------------------------------------
    def _select_replanning_strategy(self, analysis: Dict[str, Any], state: ProjectState) -> ReplanningStrategy:
        total = analysis.get("total_failures", 0)
        types = analysis.get("failure_types", {})
        # If majority dependency
        if types.get("dependency_missing", 0) >= max(1, total // 2):
            return ReplanningStrategy.REORDER_DEPENDENCIES
        if types.get("precondition_violation", 0) >= max(1, total // 2):
            return ReplanningStrategy.REFINE_DECOMPOSITION
        if types.get("model_failure", 0) >= max(1, total // 2) or types.get("timeout", 0) >= max(1, total // 2):
            return ReplanningStrategy.RETRY_WITH_DIFFERENT_MODEL
        # If more than 50% failed tasks overall
        failed_count = sum(1 for s in state.task_status.values() if s == TaskStatus.FAILED)
        total_tasks = len(state.task_status)
        if total_tasks and (failed_count / total_tasks) > 0.5:
            return ReplanningStrategy.FAIL_PROJECT
        return ReplanningStrategy.RETRY_WITH_DIFFERENT_MODEL

    def _apply_strategy(
        self,
        strategy: ReplanningStrategy,
        state: ProjectState,
        failed_tasks: List[ExecutionResult],
        analysis: Dict[str, Any],
    ) -> ProjectState:
        if strategy == ReplanningStrategy.RETRY_WITH_DIFFERENT_MODEL:
            # Reset failed tasks to PENDING
            for r in failed_tasks:
                if r.task_id in state.task_status:
                    state.task_status[r.task_id] = TaskStatus.PENDING
            return state
        if strategy == ReplanningStrategy.REORDER_DEPENDENCIES:
            for r in failed_tasks:
                if r.task_id in state.task_status:
                    state.task_status[r.task_id] = TaskStatus.PENDING
            return state
        if strategy == ReplanningStrategy.REFINE_DECOMPOSITION:
            raise ValueError("Cannot refine decomposition in Phase 2")
        if strategy == ReplanningStrategy.FAIL_PROJECT:
            raise ValueError("Project failed due to too many errors")
        return state

    # ---- Public API ----------------------------------------------------------------
    def replan(self, state: ProjectState, failed_tasks: List[ExecutionResult]) -> ProjectState:
        if not failed_tasks:
            return state
        analysis = self._analyze_failures(failed_tasks)
        strategy = self._select_replanning_strategy(analysis, state)
        new_state = self._apply_strategy(strategy, state, failed_tasks, analysis)
        self._record_failures(failed_tasks, analysis)
        return new_state

    def _record_failures(self, failed_tasks: List[ExecutionResult], analysis: Dict[str, Any]) -> None:
        for r in failed_tasks:
            ftype = self._classify_failure(r)
            entry = {
                "task_id": r.task_id,
                "error": r.error or "",
                "metadata": r.metadata,
                "failure_type": ftype.value,
            }
            self.failure_history.setdefault(r.task_id, []).append(entry)

    def get_failure_statistics(self) -> Dict[str, Any]:
        total = sum(len(v) for v in self.failure_history.values())
        types: Dict[str, int] = {}
        for entries in self.failure_history.values():
            for e in entries:
                # map back to enum string
                try:
                    name = FailureType(e["failure_type"]).name.lower()  # type: ignore[arg-type]
                except Exception:
                    name = "unknown"
                types[name] = types.get(name, 0) + 1
        most_common = None
        if types:
            most_common = max(types.items(), key=lambda kv: kv[1])[0]
        return {
            "total_failures": total,
            "unique_failed_tasks": len(self.failure_history),
            "failure_types": types,
            "most_common_failure": most_common,
        }

