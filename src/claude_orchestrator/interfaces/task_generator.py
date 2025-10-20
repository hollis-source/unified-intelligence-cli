"""Task Generator Interface.

Abstract interface for generating tasks from context.

Clean Architecture: Interface/Port layer
SOLID: DIP - Depend on abstraction for task generation
"""

from abc import ABC, abstractmethod
from typing import Optional

from src.claude_orchestrator.entities.task_context import TaskContext
from src.claude_orchestrator.entities.generated_task import GeneratedTask
from src.claude_orchestrator.entities.goal import Goal


class ITaskGenerator(ABC):
    """
    Interface for AI-powered task generation.

    Implementations can use:
    - LLM prompting (GPT, Claude)
    - Heuristic rules
    - Hybrid approaches
    """

    @abstractmethod
    def generate_task(
        self,
        context: TaskContext,
        goal: Optional[Goal] = None,
        max_complexity: str = "medium",
    ) -> GeneratedTask:
        """
        Generate next task based on context.

        Args:
            context: Current codebase context
            goal: Optional specific goal to target
            max_complexity: Maximum task complexity ("low", "medium", "high")

        Returns:
            GeneratedTask with instruction and rationale

        Raises:
            TaskGenerationError: If generation fails
        """
        pass


class TaskGenerationError(Exception):
    """Task generation failed."""
    pass
