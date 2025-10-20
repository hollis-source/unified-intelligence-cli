"""Claude Orchestrator: Autonomous Dynamic Task Orchestration System.

Clean Architecture implementation for autonomous development workflow
where Claude analyzes context, generates tasks, reviews PRs, and integrates
changes without human intervention.

Core Concepts:
- Context-aware task generation (not static queues)
- Autonomous PR review and integration
- Goal-driven (not task-driven) priorities
- Machine-speed feedback loops (<5 min latency)
- Learning from execution patterns

Architecture Layers:
1. Entities - Core domain objects (Goal, TaskContext, GeneratedTask, IntegrationResult)
2. Use Cases - Business logic (AnalyzeContext, GenerateTask, ReviewPR, IntegratePR)
3. Interfaces - Ports for external systems
4. Adapters - Concrete implementations (Git, Pytest, LLM, etc.)
5. Orchestrator - Main coordination loop

SOLID Principles:
- SRP: Each entity has single responsibility
- OCP: Open for extension (new analyzers, generators) via interfaces
- LSP: All adapters substitutable via interfaces
- ISP: Small, focused interfaces
- DIP: Depend on abstractions (interfaces), not concretions

Version: 1.0
Status: Development
"""

__version__ = "1.0.0"
__author__ = "Claude Orchestrator Team"

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
