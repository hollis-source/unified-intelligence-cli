"""GenerateNextTaskUseCase - Generates next task from context.

Uses ITaskGenerator to create tasks based on analyzed context.

Clean Architecture: Use Case layer (business logic)
SOLID: SRP - Single responsibility for task generation orchestration
"""

from typing import Optional

from src.claude_orchestrator.interfaces.task_generator import ITaskGenerator
from src.claude_orchestrator.interfaces.context_analyzer import IGoalParser
from src.claude_orchestrator.entities.task_context import TaskContext
from src.claude_orchestrator.entities.generated_task import GeneratedTask


class GenerateNextTaskUseCase:
    """
    Use case for generating next task.

    Selects appropriate goal and generates task using generator.

    Usage:
        use_case = GenerateNextTaskUseCase(
            task_generator=HeuristicTaskGenerator(),
            goal_parser=GoalParser(),
        )

        task = use_case.execute(
            context=context,
            priorities_file="priorities.yaml"
        )

        print(f"Next task: {task.instruction[:100]}...")
    """

    def __init__(
        self,
        task_generator: ITaskGenerator,
        goal_parser: IGoalParser,
    ):
        """
        Initialize use case.

        Args:
            task_generator: Task generator (heuristic or LLM)
            goal_parser: Goal parser
        """
        self.task_generator = task_generator
        self.goal_parser = goal_parser

    def execute(
        self,
        context: TaskContext,
        priorities_file: str,
        target_goal_id: Optional[str] = None,
    ) -> GeneratedTask:
        """
        Generate next task based on context.

        Args:
            context: Current codebase context
            priorities_file: Path to priorities.yaml
            target_goal_id: Optional specific goal to target

        Returns:
            GeneratedTask ready for execution
        """
        print("[GenerateTask] Generating next task...")

        # Load goals
        goals = self.goal_parser.get_active_goals(priorities_file)

        # Select target goal
        target_goal = None
        if target_goal_id:
            target_goal = next((g for g in goals if g.id == target_goal_id), None)
        elif goals:
            # Pick highest priority goal
            target_goal = min(goals, key=lambda g: g.priority)

        # Generate task
        task = self.task_generator.generate_task(
            context=context,
            goal=target_goal,
            max_complexity="medium",
            target_goal_id=target_goal_id,
            enable_heuristics=not bool(target_goal_id),  # Disable heuristics if explicit goal
        )

        print(f"[GenerateTask] Generated task: {task.id}")
        print(f"[GenerateTask] Goal: {task.goal_id}")
        print(f"[GenerateTask] Priority: {task.priority}")

        return task
