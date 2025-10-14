"""TaskContext Entity.

Represents snapshot of codebase context used for task generation.
Includes git state, test results, coverage, active goals.

Clean Architecture: Core entity (immutable, no dependencies)
SOLID: SRP - single responsibility for context representation
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Any
from datetime import datetime


@dataclass(frozen=True)
class TaskContext:
    """
    Snapshot of codebase context for task generation.

    Contains all information needed to generate next task:
    - Recent git commits
    - Test results and coverage
    - Active goals and priorities
    - Open PRs and issues

    Example:
        context = TaskContext.create(
            snapshot_time=datetime.now(),
            recent_commits=["abc123", "def456"],
            test_pass_rate=0.95,
            coverage_percentage=82.3,
            active_goals=["test-coverage-95", "optimize-performance"],
        )
    """

    # Timestamp
    snapshot_time: datetime

    # Git context
    recent_commits: List[str]  # Last N commit SHAs
    modified_files: List[str]  # Files changed in recent commits
    current_branch: str

    # Test context
    test_pass_rate: float  # 0.0-1.0
    test_failures: List[Dict[str, Any]]  # Failed test details
    coverage_percentage: float  # 0.0-100.0

    # Goal context
    active_goals: List[str]  # IDs of active goals
    goal_progress: Dict[str, float]  # Goal ID -> progress %

    # Additional context
    open_prs: int = 0
    pending_reviews: int = 0

    @staticmethod
    def create(
        snapshot_time: datetime,
        recent_commits: List[str],
        modified_files: List[str],
        current_branch: str,
        test_pass_rate: float,
        test_failures: Optional[List[Dict[str, Any]]] = None,
        coverage_percentage: float = 0.0,
        active_goals: Optional[List[str]] = None,
        goal_progress: Optional[Dict[str, float]] = None,
        open_prs: int = 0,
        pending_reviews: int = 0,
    ) -> "TaskContext":
        """Factory method to create TaskContext."""
        return TaskContext(
            snapshot_time=snapshot_time,
            recent_commits=recent_commits,
            modified_files=modified_files,
            current_branch=current_branch,
            test_pass_rate=test_pass_rate,
            test_failures=test_failures or [],
            coverage_percentage=coverage_percentage,
            active_goals=active_goals or [],
            goal_progress=goal_progress or {},
            open_prs=open_prs,
            pending_reviews=pending_reviews,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "snapshot_time": self.snapshot_time.isoformat(),
            "recent_commits": self.recent_commits,
            "modified_files": self.modified_files,
            "current_branch": self.current_branch,
            "test_pass_rate": self.test_pass_rate,
            "test_failures": self.test_failures,
            "coverage_percentage": self.coverage_percentage,
            "active_goals": self.active_goals,
            "goal_progress": self.goal_progress,
            "open_prs": self.open_prs,
            "pending_reviews": self.pending_reviews,
        }
