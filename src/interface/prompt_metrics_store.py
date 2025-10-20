"""
Prompt metrics store interface and DTOs (Phase 4: SurrealDB Metrics Integration).

Clean Architecture: Interface layer
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, Optional, Dict, Any
from datetime import datetime, timezone


@dataclass
class PromptMetrics:
    """Prompt quality metrics record."""
    timestamp: str
    domain: str
    agent_type: str
    template_used: bool
    validation_score: float
    specificity: float
    clarity: float
    completeness: bool
    task_success: Optional[bool] = None
    metadata: Optional[Dict[str, Any]] = None

    @staticmethod
    def now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()


class IPromptMetricsStore(Protocol):
    """Protocol for storing prompt metrics (adapter implementations will persist or cache)."""

    def log(self, metrics: PromptMetrics) -> None:
        """Persist a metrics record (fire-and-forget)."""
        ...

    def health(self) -> bool:
        """Return True if the store is ready to accept writes."""
        ...

