"""State manager implementation for project execution lifecycle.

Manages immutable project state with precondition validation and effect application.
"""

from typing import Dict, Any

from src.interfaces import IStateManager, IStateRepository, ProjectState, TaskStatus
from src.entities.htn.htn_node import HTNNode


class ProjectStateManager(IStateManager):
    """Manager for project state across execution lifecycle.

    Maintains immutable state snapshots with versioning, supports precondition
    validation, and tracks task status throughout project execution.

    Attributes:
        state_repo: Repository for state persistence
        current_state: Current project state snapshot
    """

    def __init__(self, state_repo: IStateRepository):
        """Initialize state manager with repository.

        Args:
            state_repo: Repository for persisting state
        """
        self.state_repo = state_repo
        self.current_state: ProjectState = None

    def initialize(self, project_id: str, htn_graph: HTNNode) -> ProjectState:
        """Initialize state for a new project.

        Creates initial state with all tasks marked as PENDING and empty world state.

        Args:
            project_id: Unique identifier for the project
            htn_graph: Initial HTN task graph

        Returns:
            Initial project state
        """
        # Collect all task IDs from HTN graph
        task_ids = self._collect_task_ids(htn_graph)

        # Create initial state
        self.current_state = ProjectState(
            project_id=project_id,
            htn_graph=htn_graph,
            task_status={task_id: TaskStatus.PENDING for task_id in task_ids},
            world_state={},
            version=1
        )

        # Persist initial state
        self.state_repo.save(self.current_state)

        return self.current_state

    def get_current_state(self) -> ProjectState:
        """Get the current project state.

        Returns:
            Current project state snapshot

        Raises:
            ValueError: If state not initialized
        """
        if self.current_state is None:
            raise ValueError("State not initialized. Call initialize() first.")

        return self.current_state

    def apply_effects(self, effects: Dict[str, Any]) -> None:
        """Apply task effects to current state.

        Creates new state version with effects applied, following immutable
        state pattern.

        Args:
            effects: State changes to apply
        """
        if self.current_state is None:
            raise ValueError("State not initialized. Call initialize() first.")

        # Create new state version
        new_state = self.current_state.copy()
        new_state.world_state.update(effects)

        # Update current state and persist
        self.current_state = new_state
        self.state_repo.save(new_state)

    def mark_task_status(self, task_id: str, status: TaskStatus) -> None:
        """Update the status of a specific task.

        Args:
            task_id: ID of the task to update
            status: New status for the task

        Raises:
            ValueError: If task_id not found in state
        """
        if self.current_state is None:
            raise ValueError("State not initialized. Call initialize() first.")

        if task_id not in self.current_state.task_status:
            raise ValueError(f"Task '{task_id}' not found in state")

        # Create new state version with updated task status
        new_state = self.current_state.copy()
        new_state.task_status[task_id] = status

        # Update current state and persist
        self.current_state = new_state
        self.state_repo.save(new_state)

    def validate_current_state(self) -> bool:
        """Validate that current state is viable for execution.

        Phase 1: Checks that at least one pending task has satisfied preconditions.
        Phase 2: Will add more sophisticated validation (circular dependencies, etc.)

        Returns:
            True if state is valid for execution

        Raises:
            ValueError: If state not initialized
        """
        if self.current_state is None:
            raise ValueError("State not initialized. Call initialize() first.")

        # Get all pending tasks
        pending_tasks = [
            task_id
            for task_id, status in self.current_state.task_status.items()
            if status == TaskStatus.PENDING
        ]

        # If no pending tasks, state is valid (all done or failed)
        if not pending_tasks:
            return True

        # Check if at least ONE task can proceed (preconditions satisfied)
        # This ensures we're not in a deadlock state
        for task_id in pending_tasks:
            task_node = self._find_task_in_graph(
                self.current_state.htn_graph,
                task_id
            )

            if task_node is None:
                # Task not found in graph (shouldn't happen)
                continue

            # Check if this task's preconditions are satisfied
            if task_node.check_preconditions(self.current_state.world_state):
                # At least one task can proceed
                return True

        # No tasks can proceed - potential deadlock
        return False

    def has_pending_tasks(self) -> bool:
        """Check if there are any pending tasks.

        Returns:
            True if at least one task is pending

        Raises:
            ValueError: If state not initialized
        """
        if self.current_state is None:
            raise ValueError("State not initialized. Call initialize() first.")

        return any(
            status == TaskStatus.PENDING
            for status in self.current_state.task_status.values()
        )

    def finalize_artifacts(self) -> Dict[str, Any]:
        """Finalize and return project artifacts.

        Extracts artifacts from world state and marks project as completed.

        Returns:
            Dictionary of generated artifacts

        Raises:
            ValueError: If state not initialized
        """
        if self.current_state is None:
            raise ValueError("State not initialized. Call initialize() first.")

        # Extract artifacts from world state
        # Convention: artifacts are stored with "artifact_" prefix OR end with artifact suffixes
        artifacts = {}

        for key, value in self.current_state.world_state.items():
            # Include artifact_* keys (HTN convention)
            if key.startswith("artifact_"):
                artifact_name = key.replace("artifact_", "")
                artifacts[artifact_name] = value

            # Also include keys ending with common artifact suffixes (real execution output)
            elif any(key.endswith(suffix) for suffix in ['_code', '_function', '_test', '_docs', '_output']):
                # Skip if value is just a status flag (completed, True, etc.)
                if isinstance(value, str) and len(value) > 50 and value not in ['completed', 'True', 'False']:
                    # Extract clean name: "implement_add_function_code" -> "add_function_code"
                    artifact_name = key
                    artifacts[artifact_name] = value

        return artifacts

    def load_state(self, project_id: str) -> ProjectState:
        """Load existing project state from repository.

        Args:
            project_id: ID of project to load

        Returns:
            Loaded project state

        Raises:
            ValueError: If project not found
        """
        self.current_state = self.state_repo.load(project_id)
        return self.current_state

    def _collect_task_ids(self, node: HTNNode) -> list[str]:
        """Recursively collect all task IDs from HTN graph.

        Args:
            node: HTN node to start collection from

        Returns:
            List of all task IDs in the graph
        """
        task_ids = [node.task_id]

        for subtask in node.subtasks:
            task_ids.extend(self._collect_task_ids(subtask))

        return task_ids

    def _find_task_in_graph(self, node: HTNNode, task_id: str) -> HTNNode:
        """Recursively find task node by ID in HTN graph.

        Args:
            node: HTN node to start search from
            task_id: ID of task to find

        Returns:
            HTN node with matching task_id, or None if not found
        """
        if node.task_id == task_id:
            return node

        for subtask in node.subtasks:
            found = self._find_task_in_graph(subtask, task_id)
            if found is not None:
                return found

        return None
