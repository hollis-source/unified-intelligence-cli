"""GoalParser Adapter.

Parses and manages goals from priorities.yaml.

Clean Architecture: Adapter layer (implements IGoalParser interface)
SOLID: LSP - substitutable for IGoalParser
"""

import yaml
from typing import List
from pathlib import Path

from src.claude_orchestrator.interfaces.context_analyzer import (
    IGoalParser,
    GoalParseError,
    GoalUpdateError,
)
from src.claude_orchestrator.entities.goal import Goal, GoalType, GoalStatus


class GoalParser(IGoalParser):
    """
    Parser for priorities.yaml goals.

    Reads YAML format and converts to Goal entities.

    Usage:
        parser = GoalParser()
        goals = parser.get_active_goals("priorities.yaml")
        print(f"Active goals: {len(goals)}")
    """

    def load_goals(self, priorities_file: str) -> List[Goal]:
        """
        Load all goals from priorities.yaml.

        Args:
            priorities_file: Path to priorities.yaml

        Returns:
            List of Goal entities
        """
        try:
            if not Path(priorities_file).exists():
                raise GoalParseError(f"File not found: {priorities_file}")

            with open(priorities_file, "r") as f:
                data = yaml.safe_load(f)

            if not data or "priorities" not in data:
                return []

            goals = []
            for priority in data["priorities"]:
                goal = self._parse_goal(priority)
                if goal:
                    goals.append(goal)

            return goals

        except yaml.YAMLError as e:
            raise GoalParseError(f"YAML parsing failed: {e}")
        except Exception as e:
            raise GoalParseError(f"Failed to load goals: {e}")

    def get_active_goals(self, priorities_file: str) -> List[Goal]:
        """
        Get only active goals (not completed/deprecated).

        Args:
            priorities_file: Path to priorities.yaml

        Returns:
            List of active Goal entities
        """
        all_goals = self.load_goals(priorities_file)
        return [
            g
            for g in all_goals
            if g.status
            in [GoalStatus.ACTIVE, GoalStatus.BLOCKED]  # Include blocked
        ]

    def update_goal_progress(
        self, priorities_file: str, goal_id: str, current_value: float
    ) -> None:
        """
        Update goal progress.

        Args:
            priorities_file: Path to priorities.yaml
            goal_id: Goal ID to update
            current_value: New current value
        """
        try:
            with open(priorities_file, "r") as f:
                data = yaml.safe_load(f)

            if not data or "priorities" not in data:
                raise GoalUpdateError("Invalid priorities file format")

            # Find and update goal
            updated = False
            for priority in data["priorities"]:
                if priority.get("id") == goal_id:
                    priority["current_value"] = current_value
                    updated = True
                    break

            if not updated:
                raise GoalUpdateError(f"Goal not found: {goal_id}")

            # Write back
            with open(priorities_file, "w") as f:
                yaml.safe_dump(data, f, default_flow_style=False)

        except yaml.YAMLError as e:
            raise GoalUpdateError(f"YAML writing failed: {e}")
        except Exception as e:
            raise GoalUpdateError(f"Failed to update goal: {e}")

    def _parse_goal(self, priority_data: dict) -> Goal:
        """Parse priority data into Goal entity."""
        try:
            # Map priority type to GoalType
            goal_type_str = priority_data.get("type", "feature")
            goal_type = self._map_goal_type(goal_type_str)

            # Map status
            status_str = priority_data.get("status", "active")
            status = self._map_status(status_str)

            # Extract metrics
            target_metric = priority_data.get("target_metric")
            target_value = priority_data.get("target_value")
            current_value = priority_data.get("current_value")

            # Create goal
            return Goal.create(
                id=priority_data["id"],
                title=priority_data["title"],
                description=priority_data.get("description", ""),
                goal_type=goal_type,
                priority=priority_data.get("priority", "P2"),
                target_metric=target_metric,
                target_value=float(target_value) if target_value else None,
                current_value=float(current_value) if current_value else None,
                status=status,
            )

        except KeyError as e:
            raise GoalParseError(f"Missing required field: {e}")
        except Exception as e:
            raise GoalParseError(f"Failed to parse goal: {e}")

    def _map_goal_type(self, type_str: str) -> GoalType:
        """Map string to GoalType enum."""
        mapping = {
            "coverage": GoalType.COVERAGE,
            "performance": GoalType.PERFORMANCE,
            "feature": GoalType.FEATURE,
            "refactor": GoalType.REFACTOR,
            "documentation": GoalType.DOCUMENTATION,
            "testing": GoalType.TESTING,
        }
        return mapping.get(type_str.lower(), GoalType.FEATURE)

    def _map_status(self, status_str: str) -> GoalStatus:
        """Map string to GoalStatus enum."""
        mapping = {
            "active": GoalStatus.ACTIVE,
            "completed": GoalStatus.COMPLETED,
            "blocked": GoalStatus.BLOCKED,
            "deprecated": GoalStatus.DEPRECATED,
            "in_progress": GoalStatus.ACTIVE,  # Treat as active
        }
        return mapping.get(status_str.lower(), GoalStatus.ACTIVE)
