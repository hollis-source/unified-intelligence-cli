"""Agentic Project Builder - Phase 1 Implementation.

Integrates HTN, DSL, Adaptive Learning, and Multi-Agent Teams for autonomous
project execution from natural language goals.

Phase 1 Components:
- StateManager: SQLite-based state persistence
- GoalDecomposer: Natural language to HTN translation
- HTNDSLTranslator: HTN to DSL workflow conversion
- ProjectOrchestrator: Meta-operational lifecycle coordinator

Phase 2 (Planned):
- ExecutionCoordinator: Agent team routing and model selection
- FeedbackLoopHandler: Failure detection and replanning
- Parallel execution support (Product operator in DSL)
"""

from .orchestrator import ProjectOrchestrator
from .state import ProjectStateManager, SQLiteStateRepository
from .goal_decomposer import GoalDecomposer
from .htn_dsl import HTNDSLTranslator

__all__ = [
    "ProjectOrchestrator",
    "ProjectStateManager",
    "SQLiteStateRepository",
    "GoalDecomposer",
    "HTNDSLTranslator"
]
