"""HeuristicTaskGenerator - Rule-based task generation.

Generates tasks using heuristics and rules based on context analysis.
MVP implementation before full LLM-powered generation.

Clean Architecture: Adapter layer (implements ITaskGenerator)
SOLID: LSP - substitutable for ITaskGenerator
"""

import random
from typing import Optional
from datetime import datetime

from src.claude_orchestrator.interfaces.task_generator import (
    ITaskGenerator,
    TaskGenerationError,
)
from src.claude_orchestrator.entities.task_context import TaskContext
from src.claude_orchestrator.entities.generated_task import GeneratedTask
from src.claude_orchestrator.entities.goal import Goal, GoalType


class HeuristicTaskGenerator(ITaskGenerator):
    """
    Heuristic-based task generator.

    Uses rules to generate tasks:
    1. If coverage < 80% → generate coverage task
    2. If test failures > 0 → generate fix failing tests task
    3. If uncovered files exist → generate test task for specific file
    4. If goal specified → generate task for that goal
    5. Otherwise → general improvement task

    Usage:
        generator = HeuristicTaskGenerator()
        task = generator.generate_task(context, goal=coverage_goal)
        print(task.instruction)
    """

    def generate_task(
        self,
        context: TaskContext,
        goal: Optional[Goal] = None,
        max_complexity: str = "medium",
        target_goal_id: Optional[str] = None,
        enable_heuristics: bool = True,
    ) -> GeneratedTask:
        """
        Generate next task based on context and heuristics.

        Refactored priority order:
        1. Explicit goal targeting (target_goal_id overrides heuristics)
        2. Fix failing tests (critical, always checked)
        3. High-priority explicit goals (critical/high priority)
        4. Heuristics (only if enable_heuristics=True):
           - Coverage goals
           - Low coverage improvements
        5. Medium/low priority goals
        6. General improvements

        Args:
            context: Current codebase context
            goal: Optional specific goal to target
            max_complexity: Maximum task complexity
            target_goal_id: Explicit goal ID to target (overrides heuristics)
            enable_heuristics: Enable heuristic-based task generation

        Returns:
            GeneratedTask with instruction and rationale
        """
        try:
            # Priority 1: Explicit goal targeting (overrides everything except failing tests)
            if target_goal_id and goal and goal.id == target_goal_id:
                # Check for failing tests first (critical)
                if context.test_failures and len(context.test_failures) > 0:
                    return self._generate_fix_tests_task(context)

                # Generate task for explicit goal
                if goal.goal_type == GoalType.COVERAGE:
                    return self._generate_coverage_task(context, goal)
                else:
                    return self._generate_goal_task(context, goal)

            # Priority 2: Fix failing tests (critical, always checked)
            if context.test_failures and len(context.test_failures) > 0:
                return self._generate_fix_tests_task(context)

            # Priority 3: High-priority explicit goals (critical/high)
            if goal and goal.priority in ["critical", "high"]:
                if goal.goal_type == GoalType.COVERAGE:
                    return self._generate_coverage_task(context, goal)
                else:
                    return self._generate_goal_task(context, goal)

            # Priority 4: Heuristics (only if enabled)
            if enable_heuristics:
                # Coverage-specific goals
                if goal and goal.goal_type == GoalType.COVERAGE:
                    return self._generate_coverage_task(context, goal)

                # Low coverage heuristic (only if no explicit goal or goal is low priority)
                if context.coverage_percentage < 80.0:
                    return self._generate_improve_coverage_task(context)

            # Priority 5: Medium/low priority goals
            if goal:
                if goal.goal_type == GoalType.COVERAGE:
                    return self._generate_coverage_task(context, goal)
                else:
                    return self._generate_goal_task(context, goal)

            # Default: General improvement
            return self._generate_general_task(context)

        except Exception as e:
            raise TaskGenerationError(f"Failed to generate task: {e}")

    def _generate_fix_tests_task(self, context: TaskContext) -> GeneratedTask:
        """Generate task to fix failing tests."""
        failure = context.test_failures[0]  # Fix first failure
        test_name = failure.get("test_name", "unknown")

        task_id = f"fix-test-{test_name}-{datetime.now().strftime('%Y%m%d%H%M%S')}"

        instruction = f"""Fix the failing test: {test_name}

Error: {failure.get('error_message', 'See test output')}

Steps:
1. Run the test locally to reproduce the failure
2. Identify the root cause
3. Fix the issue (either fix the code or update the test)
4. Verify the test passes
5. Ensure no other tests break"""

        rationale = f"Test failure detected in {test_name}. Failing tests block progress on other tasks."

        return GeneratedTask.create(
            id=task_id,
            instruction=instruction,
            rationale=rationale,
            goal_id="testing",
            estimated_minutes=30,
            priority="P0",  # High priority
            complexity="medium",
        )

    def _generate_coverage_task(
        self, context: TaskContext, goal: Goal
    ) -> GeneratedTask:
        """Generate task to improve coverage toward goal."""
        current = context.coverage_percentage
        target = goal.target_value or 80.0
        gap = target - current

        # Pick an uncovered file (heuristic: pick from modified files first)
        target_file = None
        if context.modified_files:
            # Prioritize recently modified files
            for f in context.modified_files:
                if f.endswith(".py") and not f.startswith("test_"):
                    target_file = f
                    break

        if not target_file and context.modified_files:
            target_file = context.modified_files[0]

        task_id = f"coverage-{goal.id}-{datetime.now().strftime('%Y%m%d%H%M%S')}"

        if target_file:
            instruction = f"""Add unit tests to improve coverage for: {target_file}

Current coverage: {current:.1f}%
Target coverage: {target:.1f}%
Gap: {gap:.1f}%

Steps:
1. Analyze {target_file} to identify uncovered code paths
2. Write unit tests covering edge cases and main functionality
3. Run tests to verify they pass
4. Check coverage improvement with pytest-cov
5. Aim to get {target_file} to >80% coverage"""

        else:
            instruction = f"""Improve overall test coverage

Current coverage: {current:.1f}%
Target coverage: {target:.1f}%

Steps:
1. Run pytest-cov to identify files with low coverage
2. Pick the file with lowest coverage
3. Write comprehensive unit tests for that file
4. Verify tests pass and coverage improves
5. Repeat until target reached"""

        rationale = f"Coverage is {current:.1f}%, target is {target:.1f}%. Improving test coverage ensures code quality and catches bugs early."

        return GeneratedTask.create(
            id=task_id,
            instruction=instruction,
            rationale=rationale,
            goal_id=goal.id,
            estimated_minutes=45,
            priority=goal.priority,
            complexity="medium",
        )

    def _generate_improve_coverage_task(self, context: TaskContext) -> GeneratedTask:
        """Generate general coverage improvement task."""
        task_id = f"improve-coverage-{datetime.now().strftime('%Y%m%d%H%M%S')}"

        instruction = f"""Improve test coverage (current: {context.coverage_percentage:.1f}%)

Steps:
1. Run: pytest --cov=src --cov-report=term-missing
2. Identify files with <80% coverage
3. Pick the largest uncovered file
4. Write unit tests for uncovered lines
5. Verify tests pass
6. Check coverage improvement"""

        rationale = f"Test coverage is {context.coverage_percentage:.1f}%, below recommended 80%. Better coverage improves code quality."

        return GeneratedTask.create(
            id=task_id,
            instruction=instruction,
            rationale=rationale,
            goal_id="coverage-general",
            estimated_minutes=45,
            priority="P2",
            complexity="medium",
        )

    def _generate_goal_task(self, context: TaskContext, goal: Goal) -> GeneratedTask:
        """Generate task for specific goal."""
        task_id = f"goal-{goal.id}-{datetime.now().strftime('%Y%m%d%H%M%S')}"

        instruction = f"""Work on goal: {goal.title}

Goal: {goal.description}
Type: {goal.goal_type.value}
Priority: {goal.priority}

Steps:
1. Review the goal requirements
2. Identify the next incremental step
3. Implement that step
4. Test your changes
5. Document progress"""

        rationale = f"Active goal: {goal.title}. Current progress: {goal.progress_percentage() or 0:.0f}%"

        return GeneratedTask.create(
            id=task_id,
            instruction=instruction,
            rationale=rationale,
            goal_id=goal.id,
            estimated_minutes=60,
            priority=goal.priority,
            complexity="high",
        )

    def _generate_general_task(self, context: TaskContext) -> GeneratedTask:
        """Generate general improvement task."""
        task_id = f"general-{datetime.now().strftime('%Y%m%d%H%M%S')}"

        # Pick a recently modified file to improve
        target_file = None
        if context.modified_files:
            target_file = context.modified_files[0]

        if target_file:
            instruction = f"""Improve code quality for: {target_file}

Suggested improvements:
1. Add docstrings if missing
2. Add type hints if missing
3. Refactor complex functions (>20 lines)
4. Add error handling
5. Improve variable names"""

        else:
            instruction = """General code quality improvement

Steps:
1. Review recent commits
2. Identify code that needs improvement
3. Pick one file to refactor
4. Apply clean code principles
5. Add tests if needed"""

        rationale = "General code quality improvement to maintain codebase health."

        return GeneratedTask.create(
            id=task_id,
            instruction=instruction,
            rationale=rationale,
            goal_id="code-quality",
            estimated_minutes=30,
            priority="P3",
            complexity="low",
        )
