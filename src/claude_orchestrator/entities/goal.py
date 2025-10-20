"""Goal Entity.

Represents a high-level objective in priorities.yaml (not specific tasks).
Goals are strategic (e.g., "95% coverage"), tasks are tactical (e.g., "add tests to parser.py").

Clean Architecture: Core entity (immutable, no dependencies)
SOLID: SRP - single responsibility for goal representation
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional, Dict, Any
from datetime import datetime


class GoalType(str, Enum):
    """Types of goals."""

    COVERAGE = "coverage"  # Test coverage goal
    PERFORMANCE = "performance"  # Performance optimization goal
    FEATURE = "feature"  # Feature implementation goal
    REFACTOR = "refactor"  # Code refactoring goal
    DOCUMENTATION = "documentation"  # Documentation goal
    TESTING = "testing"  # Testing infrastructure goal


class GoalStatus(str, Enum):
    """Status of a goal."""

    ACTIVE = "active"  # Currently being worked on
    COMPLETED = "completed"  # Goal achieved
    BLOCKED = "blocked"  # Blocked by dependency
    DEPRECATED = "deprecated"  # No longer relevant


@dataclass(frozen=True)
class Goal:
    """
    Represents a high-level strategic goal.

    Goals define "what" we want to achieve (95% coverage),
    while tasks define "how" (add tests to specific files).

    Example:
        goal = Goal.create(
            id="test-coverage-95",
            title="Achieve 95% Test Coverage",
            description="Increase coverage from 82% to 95%",
            goal_type=GoalType.COVERAGE,
            priority="P1",
            target_metric="coverage_percentage",
            target_value=95.0,
            current_value=82.0,
        )
    """

    # Identity
    id: str
    title: str
    description: str

    # Classification
    goal_type: GoalType
    priority: str  # P0, P1, P2, P3

    # Metrics
    target_metric: Optional[str] = None
    target_value: Optional[float] = None
    current_value: Optional[float] = None

    # State
    status: GoalStatus = GoalStatus.ACTIVE

    # Timestamps
    created_at: datetime = None
    completed_at: Optional[datetime] = None

    def __post_init__(self):
        """Set created_at if not provided."""
        if self.created_at is None:
            object.__setattr__(self, "created_at", datetime.now())

    @staticmethod
    def create(
        id: str,
        title: str,
        description: str,
        goal_type: GoalType,
        priority: str,
        target_metric: Optional[str] = None,
        target_value: Optional[float] = None,
        current_value: Optional[float] = None,
        status: GoalStatus = GoalStatus.ACTIVE,
        completed_at: Optional[datetime] = None,
    ) -> "Goal":
        """Factory method to create Goal."""
        return Goal(
            id=id,
            title=title,
            description=description,
            goal_type=goal_type,
            priority=priority,
            target_metric=target_metric,
            target_value=target_value,
            current_value=current_value,
            status=status,
            completed_at=completed_at,
        )

    def progress_percentage(self) -> Optional[float]:
        """Calculate progress as percentage of target."""
        if self.target_value is None or self.current_value is None:
            return None
        return (self.current_value / self.target_value) * 100.0

    def is_achieved(self) -> bool:
        """Check if goal has reached target."""
        if self.target_value is None or self.current_value is None:
            return False
        return self.current_value >= self.target_value

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "goal_type": self.goal_type.value,
            "priority": self.priority,
            "target_metric": self.target_metric,
            "target_value": self.target_value,
            "current_value": self.current_value,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }
