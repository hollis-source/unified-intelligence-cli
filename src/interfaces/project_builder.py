"""Project Builder interfaces for dependency inversion - Clean Architecture.

These interfaces define the contracts for the Agentic Project Builder components,
following the architecture blueprint specifications.
"""

from typing import Protocol, Dict, Any, List
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from src.entities.htn.htn_node import HTNNode


class TaskStatus(Enum):
    """Status of a task in the project execution lifecycle."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class ProjectState:
    """Immutable state snapshot of a project at a specific point in time.

    Attributes:
        project_id: Unique identifier for the project
        htn_graph: The HTN task graph being executed
        task_status: Current status of each task by task_id
        world_state: Current state of the project world (effects applied)
        version: State version number for tracking changes
        last_updated: Timestamp of last state update
    """
    project_id: str
    htn_graph: HTNNode
    task_status: Dict[str, TaskStatus]
    world_state: Dict[str, Any]
    version: int = 1
    last_updated: datetime = None

    def __post_init__(self):
        if self.last_updated is None:
            self.last_updated = datetime.now()

    def copy(self) -> "ProjectState":
        """Create a copy of this state with incremented version."""
        return ProjectState(
            project_id=self.project_id,
            htn_graph=self.htn_graph,
            task_status=self.task_status.copy(),
            world_state=self.world_state.copy(),
            version=self.version + 1,
            last_updated=datetime.now()
        )


@dataclass
class ExecutionResult:
    """Result of executing a single task.

    Attributes:
        task_id: ID of the executed task
        success: Whether execution succeeded
        effects: State changes produced by execution
        error: Error message if execution failed
        metadata: Additional execution data (timing, cost, model used, etc.)
    """
    task_id: str
    success: bool
    effects: Dict[str, Any]
    error: str = ""
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class ProjectResult:
    """Final result of project execution.

    Attributes:
        project_id: Unique identifier for the project
        success: Whether project completed successfully
        artifacts: Dictionary of generated artifacts (file paths, content, etc.)
        execution_time: Total execution time in seconds
        cost: Total cost in dollars
        task_results: Results of individual task executions
        error: Error message if project failed
    """
    project_id: str
    success: bool
    artifacts: Dict[str, Any]
    execution_time: float
    cost: float
    task_results: List[ExecutionResult]
    error: str = ""


class IStateManager(Protocol):
    """Interface for managing project state across execution lifecycle."""

    def initialize(self, project_id: str, htn_graph: HTNNode) -> ProjectState:
        """Initialize state for a new project.

        Args:
            project_id: Unique identifier for the project
            htn_graph: Initial HTN task graph

        Returns:
            Initial project state
        """
        ...

    def get_current_state(self) -> ProjectState:
        """Get the current project state.

        Returns:
            Current project state snapshot
        """
        ...

    def apply_effects(self, effects: Dict[str, Any]) -> None:
        """Apply task effects to current state.

        Args:
            effects: State changes to apply
        """
        ...

    def mark_task_status(self, task_id: str, status: TaskStatus) -> None:
        """Update the status of a specific task.

        Args:
            task_id: ID of the task to update
            status: New status for the task
        """
        ...

    def validate_current_state(self) -> bool:
        """Validate that current state satisfies all pending task preconditions.

        Returns:
            True if state is valid for execution
        """
        ...

    def has_pending_tasks(self) -> bool:
        """Check if there are any pending tasks.

        Returns:
            True if at least one task is pending
        """
        ...

    def finalize_artifacts(self) -> Dict[str, Any]:
        """Finalize and return project artifacts.

        Returns:
            Dictionary of generated artifacts
        """
        ...


class IStateRepository(Protocol):
    """Interface for persisting project state."""

    def save(self, state: ProjectState) -> None:
        """Persist project state to storage.

        Args:
            state: Project state to save
        """
        ...

    def load(self, project_id: str) -> ProjectState:
        """Load project state from storage.

        Args:
            project_id: ID of project to load

        Returns:
            Loaded project state

        Raises:
            ValueError: If project not found
        """
        ...

    def exists(self, project_id: str) -> bool:
        """Check if project state exists in storage.

        Args:
            project_id: ID of project to check

        Returns:
            True if project exists
        """
        ...

    def delete(self, project_id: str) -> None:
        """Delete project state from storage.

        Args:
            project_id: ID of project to delete
        """
        ...


class IProjectOrchestrator(Protocol):
    """Interface for orchestrating project execution lifecycle."""

    async def execute_project(self, goal: str, project_id: str) -> ProjectResult:
        """Execute a project from natural language goal to completion.

        Args:
            goal: Natural language description of project goal
            project_id: Unique identifier for the project

        Returns:
            Final project result with artifacts
        """
        ...

    async def resume_project(self, project_id: str) -> ProjectResult:
        """Resume a previously started project.

        Args:
            project_id: ID of project to resume

        Returns:
            Final project result with artifacts
        """
        ...


class IGoalDecomposer(Protocol):
    """Interface for decomposing natural language goals into HTN graphs."""

    async def decompose_goal(self, goal: str) -> HTNNode:
        """Decompose natural language goal into HTN task graph.

        Args:
            goal: Natural language project goal

        Returns:
            HTN task graph representing the project
        """
        ...


class IHTNDSLTranslator(Protocol):
    """Interface for translating HTN graphs to DSL workflows."""

    def translate(self, htn_graph: HTNNode) -> Any:  # Returns DSLWorkflow
        """Translate HTN task graph to DSL workflow.

        Args:
            htn_graph: HTN task graph to translate

        Returns:
            DSL workflow expression
        """
        ...


class IExecutionCoordinator(Protocol):
    """Interface for coordinating task execution with agents and models."""

    async def execute_workflows(self, workflows: Any, state: ProjectState) -> List[ExecutionResult]:
        """Execute DSL workflows with agent teams and model selection.

        Args:
            workflows: DSL workflow to execute
            state: Current project state

        Returns:
            List of execution results for each task
        """
        ...


class IFeedbackHandler(Protocol):
    """Interface for handling execution failures and replanning."""

    def replan(self, state: ProjectState, failed_tasks: List[ExecutionResult]) -> ProjectState:
        """Generate new plan based on execution failures.

        Args:
            state: Current project state
            failed_tasks: List of tasks that failed

        Returns:
            Updated project state with new plan
        """
        ...
