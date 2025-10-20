"""Adapters for Claude Orchestrator.

Concrete implementations of interfaces (ports).
Swappable implementations for different execution environments.

Clean Architecture: Adapter layer (outermost layer)
SOLID: DIP - adapters implement interfaces, orchestrator depends on interfaces
"""

from src.claude_orchestrator.adapters.single_worker_pool import SingleWorkerPool
from src.claude_orchestrator.adapters.kubernetes_worker_pool import KubernetesWorkerPool

__all__ = [
    "SingleWorkerPool",
    "KubernetesWorkerPool",
]
