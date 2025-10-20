"""Core domain entities for Claude Orchestrator.

Entities are immutable, framework-independent domain objects
with no external dependencies. They represent core business concepts.

Clean Architecture: These are the innermost layer, protected from
framework changes and external concerns.
"""

from src.claude_orchestrator.entities.goal import Goal, GoalType, GoalStatus
from src.claude_orchestrator.entities.task_context import TaskContext
from src.claude_orchestrator.entities.generated_task import GeneratedTask
from src.claude_orchestrator.entities.integration_result import IntegrationResult, IntegrationStatus

__all__ = [
    "Goal",
    "GoalType",
    "GoalStatus",
    "TaskContext",
    "GeneratedTask",
    "IntegrationResult",
    "IntegrationStatus",
]
