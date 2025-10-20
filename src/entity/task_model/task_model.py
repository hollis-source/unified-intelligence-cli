"""Task model entities for hierarchical task management.

Implements Project/Task/Todo hierarchy with recursive decomposition,
following the unified architecture baseline.
"""

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from uuid import uuid4


class TaskStatus(Enum):
    """Status for task entities."""

    PENDING = auto()
    IN_PROGRESS = auto()
    COMPLETED = auto()
    FAILED = auto()
    BLOCKED = auto()


@dataclass
class TaskEntity:
    """Base class for all task entities (Project/Task/Todo).

    Provides common attributes and functionality shared across the hierarchy.

    Attributes:
        entity_id: Unique identifier
        name: Human-readable name
        description: Detailed description
        status: Current status
        parent_id: ID of parent entity (None for root)
        metadata: Additional entity-specific data
        created_at: Creation timestamp
        updated_at: Last update timestamp
    """

    entity_id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    description: str = ""
    status: TaskStatus = TaskStatus.PENDING
    parent_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def update_status(self, new_status: TaskStatus) -> None:
        """Update entity status and timestamp.

        Args:
            new_status: New status to set
        """
        self.status = new_status
        self.updated_at = datetime.utcnow()

    def is_terminal(self) -> bool:
        """Check if entity is in terminal state.

        Returns:
            True if status is COMPLETED or FAILED
        """
        return self.status in [TaskStatus.COMPLETED, TaskStatus.FAILED]

    def is_active(self) -> bool:
        """Check if entity is actively being worked on.

        Returns:
            True if status is IN_PROGRESS
        """
        return self.status == TaskStatus.IN_PROGRESS

    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"{self.__class__.__name__}(id='{self.entity_id[:8]}...', "
            f"name='{self.name}', status={self.status.name})"
        )


@dataclass
class Project(TaskEntity):
    """Top-level project entity.

    A project contains multiple tasks and represents the highest level
    in the task hierarchy. Projects track overall goals and deadlines.

    Attributes:
        tasks: List of child tasks
        goals: Project objectives
        deadline: Optional project deadline
    """

    tasks: List["Task"] = field(default_factory=list)
    goals: List[str] = field(default_factory=list)
    deadline: Optional[datetime] = None

    def add_task(self, task: "Task") -> None:
        """Add a task to this project.

        Args:
            task: Task to add as child
        """
        task.parent_id = self.entity_id
        self.tasks.append(task)

    def get_tasks(self) -> List["Task"]:
        """Get all direct child tasks.

        Returns:
            List of tasks in this project
        """
        return self.tasks.copy()

    def get_all_tasks(self) -> List["Task"]:
        """Get all tasks recursively (including subtasks).

        Returns:
            Flattened list of all tasks and subtasks
        """
        all_tasks = []
        for task in self.tasks:
            all_tasks.append(task)
            all_tasks.extend(task.get_all_subtasks())
        return all_tasks

    def get_task_by_id(self, task_id: str) -> Optional["Task"]:
        """Find task by ID (searches recursively).

        Args:
            task_id: Task identifier to find

        Returns:
            Task if found, None otherwise
        """
        for task in self.tasks:
            if task.entity_id == task_id:
                return task
            # Search subtasks recursively
            found = task.get_subtask_by_id(task_id)
            if found:
                return found
        return None

    def get_completion_percentage(self) -> float:
        """Calculate project completion percentage.

        Returns:
            Percentage of completed tasks (0.0 to 100.0)
        """
        all_tasks = self.get_all_tasks()
        if not all_tasks:
            return 0.0

        completed = sum(1 for task in all_tasks if task.status == TaskStatus.COMPLETED)
        return (completed / len(all_tasks)) * 100.0


@dataclass
class Task(TaskEntity):
    """Mid-level task entity.

    A task can contain todos or subtasks, supporting recursive decomposition.
    Tasks represent decomposable units of work.

    Attributes:
        subtasks: List of child tasks (for recursive decomposition)
        todos: List of atomic todos
        dependencies: IDs of tasks this depends on
        estimated_duration: Estimated time in seconds
    """

    subtasks: List["Task"] = field(default_factory=list)
    todos: List["Todo"] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    estimated_duration: Optional[int] = None

    def add_subtask(self, subtask: "Task") -> None:
        """Add a subtask to this task (recursive decomposition).

        Args:
            subtask: Task to add as child
        """
        subtask.parent_id = self.entity_id
        self.subtasks.append(subtask)

    def add_todo(self, todo: "Todo") -> None:
        """Add a todo to this task.

        Args:
            todo: Todo to add as child
        """
        todo.parent_id = self.entity_id
        self.todos.append(todo)

    def get_subtasks(self) -> List["Task"]:
        """Get direct subtasks.

        Returns:
            List of child tasks
        """
        return self.subtasks.copy()

    def get_todos(self) -> List["Todo"]:
        """Get direct todos.

        Returns:
            List of child todos
        """
        return self.todos.copy()

    def get_all_subtasks(self) -> List["Task"]:
        """Get all subtasks recursively.

        Returns:
            Flattened list of all nested subtasks
        """
        all_subtasks = []
        for subtask in self.subtasks:
            all_subtasks.append(subtask)
            all_subtasks.extend(subtask.get_all_subtasks())
        return all_subtasks

    def get_subtask_by_id(self, task_id: str) -> Optional["Task"]:
        """Find subtask by ID (searches recursively).

        Args:
            task_id: Task identifier to find

        Returns:
            Task if found, None otherwise
        """
        for subtask in self.subtasks:
            if subtask.entity_id == task_id:
                return subtask
            # Search nested subtasks
            found = subtask.get_subtask_by_id(task_id)
            if found:
                return found
        return None

    def is_leaf(self) -> bool:
        """Check if task is a leaf (no subtasks).

        Returns:
            True if task has no subtasks
        """
        return len(self.subtasks) == 0

    def is_composite(self) -> bool:
        """Check if task is composite (has subtasks).

        Returns:
            True if task has subtasks
        """
        return len(self.subtasks) > 0

    def get_depth(self) -> int:
        """Calculate maximum depth of task hierarchy.

        Returns:
            Maximum depth from this task to deepest subtask
        """
        if self.is_leaf():
            return 0
        return 1 + max(subtask.get_depth() for subtask in self.subtasks)

    def has_dependencies(self) -> bool:
        """Check if task has dependencies.

        Returns:
            True if task depends on other tasks
        """
        return len(self.dependencies) > 0


@dataclass
class Todo(TaskEntity):
    """Atomic todo entity (leaf node).

    A todo is an executable unit that cannot be further decomposed.
    Todos represent concrete actions.

    Attributes:
        action: Concrete action to perform
        completed_at: Timestamp when completed
        assignee: Who is responsible
    """

    action: str = ""
    completed_at: Optional[datetime] = None
    assignee: Optional[str] = None

    def complete(self) -> None:
        """Mark todo as completed with timestamp."""
        self.update_status(TaskStatus.COMPLETED)
        self.completed_at = datetime.utcnow()

    def is_completed(self) -> bool:
        """Check if todo is completed.

        Returns:
            True if status is COMPLETED
        """
        return self.status == TaskStatus.COMPLETED


# Type alias for any task entity
AnyTaskEntity = Union[Project, Task, Todo]


def traverse_hierarchy(
    root: AnyTaskEntity,
    visit_fn: Optional[callable] = None
) -> List[AnyTaskEntity]:
    """Traverse task hierarchy depth-first.

    Args:
        root: Root entity to start from
        visit_fn: Optional function to call on each entity

    Returns:
        List of all entities in depth-first order
    """
    result = [root]

    if visit_fn:
        visit_fn(root)

    # Traverse children based on entity type
    if isinstance(root, Project):
        for task in root.tasks:
            result.extend(traverse_hierarchy(task, visit_fn))
    elif isinstance(root, Task):
        for subtask in root.subtasks:
            result.extend(traverse_hierarchy(subtask, visit_fn))
        for todo in root.todos:
            result.append(todo)
            if visit_fn:
                visit_fn(todo)

    return result


def find_entity_by_id(
    root: AnyTaskEntity,
    entity_id: str
) -> Optional[AnyTaskEntity]:
    """Find entity by ID in hierarchy.

    Args:
        root: Root entity to search from
        entity_id: Entity ID to find

    Returns:
        Entity if found, None otherwise
    """
    all_entities = traverse_hierarchy(root)
    for entity in all_entities:
        if entity.entity_id == entity_id:
            return entity
    return None
