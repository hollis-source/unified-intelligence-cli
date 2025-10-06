"""Agentic Project Builder - Production Implementation.

Integrates HTN, DSL, Adaptive Learning, and Multi-Agent Teams for autonomous
project execution from natural language goals.

Phase 1 Components:
- StateManager: SQLite-based state persistence
- GoalDecomposer: Natural language to HTN translation
- HTNDSLTranslator: HTN to DSL workflow conversion (with parallel support)
- ProjectOrchestrator: Meta-operational lifecycle coordinator

Phase 2 Components:
- ExecutionCoordinator: Agent team routing and model selection
- FeedbackLoopHandler: Failure detection and intelligent replanning

Phase 3 Components:
- CLI Command: Full-featured build-project interface
- Parallel Execution: Automatic dependency-based parallelization
"""

from .orchestrator import ProjectOrchestrator
from .state import ProjectStateManager, SQLiteStateRepository
from .goal_decomposer import GoalDecomposer
from .htn_dsl import HTNDSLTranslator
from .execution import ExecutionCoordinator
from .feedback import FeedbackLoopHandler, FailureType, ReplanningStrategy

__all__ = [
    "ProjectOrchestrator",
    "ProjectStateManager",
    "SQLiteStateRepository",
    "GoalDecomposer",
    "HTNDSLTranslator",
    "ExecutionCoordinator",
    "FeedbackLoopHandler",
    "FailureType",
    "ReplanningStrategy"
]
