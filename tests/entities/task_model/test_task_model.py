"""Unit tests for Task Model entities.

Tests cover Project/Task/Todo entities, hierarchical relationships,
recursive decomposition, and traversal operations.
"""

import pytest
from src.entity.task_model import Project, Task, Todo, TaskStatus
from src.entity.task_model.task_model import traverse_hierarchy, find_entity_by_id


class TestTaskEntityBase:
    """Test base TaskEntity functionality."""

    def test_create_task_with_defaults(self):
        """Test creating task with default values."""
        task = Task(name="Test task")

        assert task.name == "Test task"
        assert task.status == TaskStatus.PENDING
        assert task.parent_id is None
        assert len(task.entity_id) > 0  # UUID generated

    def test_update_status(self):
        """Test updating task status."""
        task = Task(name="Test")
        original_updated = task.updated_at

        task.update_status(TaskStatus.IN_PROGRESS)

        assert task.status == TaskStatus.IN_PROGRESS
        assert task.updated_at >= original_updated

    def test_is_terminal_completed(self):
        """Test is_terminal() for COMPLETED status."""
        task = Task(name="Test", status=TaskStatus.COMPLETED)

        assert task.is_terminal() is True

    def test_is_terminal_failed(self):
        """Test is_terminal() for FAILED status."""
        task = Task(name="Test", status=TaskStatus.FAILED)

        assert task.is_terminal() is True

    def test_is_terminal_non_terminal(self):
        """Test is_terminal() for non-terminal states."""
        for status in [TaskStatus.PENDING, TaskStatus.IN_PROGRESS, TaskStatus.BLOCKED]:
            task = Task(name="Test", status=status)
            assert task.is_terminal() is False

    def test_is_active(self):
        """Test is_active() for IN_PROGRESS status."""
        task = Task(name="Test", status=TaskStatus.IN_PROGRESS)

        assert task.is_active() is True

    def test_is_not_active(self):
        """Test is_active() for other statuses."""
        task = Task(name="Test", status=TaskStatus.PENDING)

        assert task.is_active() is False


class TestProjectEntity:
    """Test Project entity."""

    def test_create_project(self):
        """Test creating project with basic attributes."""
        project = Project(
            name="Build Feature",
            description="Implement new feature",
            goals=["goal1", "goal2"]
        )

        assert project.name == "Build Feature"
        assert project.description == "Implement new feature"
        assert len(project.goals) == 2

    def test_add_task_to_project(self):
        """Test adding task to project."""
        project = Project(name="Project")
        task = Task(name="Task 1")

        project.add_task(task)

        assert len(project.tasks) == 1
        assert task.parent_id == project.entity_id

    def test_add_multiple_tasks(self):
        """Test adding multiple tasks."""
        project = Project(name="Project")

        for i in range(3):
            project.add_task(Task(name=f"Task {i}"))

        assert len(project.tasks) == 3

    def test_get_tasks(self):
        """Test getting direct tasks."""
        project = Project(name="Project")
        task1 = Task(name="Task 1")
        task2 = Task(name="Task 2")

        project.add_task(task1)
        project.add_task(task2)

        tasks = project.get_tasks()

        assert len(tasks) == 2
        assert task1 in tasks
        assert task2 in tasks

    def test_get_all_tasks_recursive(self):
        """Test getting all tasks including subtasks."""
        project = Project(name="Project")
        task1 = Task(name="Task 1")
        subtask = Task(name="Subtask")
        task1.add_subtask(subtask)

        project.add_task(task1)

        all_tasks = project.get_all_tasks()

        assert len(all_tasks) == 2  # task1 + subtask
        assert task1 in all_tasks
        assert subtask in all_tasks

    def test_get_task_by_id(self):
        """Test finding task by ID."""
        project = Project(name="Project")
        task = Task(name="Task 1")
        project.add_task(task)

        found = project.get_task_by_id(task.entity_id)

        assert found is task

    def test_get_task_by_id_in_subtasks(self):
        """Test finding task in subtasks."""
        project = Project(name="Project")
        task = Task(name="Task")
        subtask = Task(name="Subtask")
        task.add_subtask(subtask)
        project.add_task(task)

        found = project.get_task_by_id(subtask.entity_id)

        assert found is subtask

    def test_get_task_by_id_not_found(self):
        """Test finding nonexistent task returns None."""
        project = Project(name="Project")

        found = project.get_task_by_id("nonexistent")

        assert found is None

    def test_get_completion_percentage_empty(self):
        """Test completion percentage with no tasks."""
        project = Project(name="Project")

        assert project.get_completion_percentage() == 0.0

    def test_get_completion_percentage_partial(self):
        """Test completion percentage with partial completion."""
        project = Project(name="Project")
        task1 = Task(name="Task 1", status=TaskStatus.COMPLETED)
        task2 = Task(name="Task 2", status=TaskStatus.PENDING)

        project.add_task(task1)
        project.add_task(task2)

        assert project.get_completion_percentage() == 50.0

    def test_get_completion_percentage_full(self):
        """Test completion percentage at 100%."""
        project = Project(name="Project")
        task1 = Task(name="Task 1", status=TaskStatus.COMPLETED)
        task2 = Task(name="Task 2", status=TaskStatus.COMPLETED)

        project.add_task(task1)
        project.add_task(task2)

        assert project.get_completion_percentage() == 100.0


class TestTaskEntity:
    """Test Task entity."""

    def test_create_task(self):
        """Test creating task with basic attributes."""
        task = Task(
            name="Implement feature",
            description="Add new functionality",
            estimated_duration=3600
        )

        assert task.name == "Implement feature"
        assert task.estimated_duration == 3600

    def test_add_subtask(self):
        """Test adding subtask (recursive decomposition)."""
        task = Task(name="Parent task")
        subtask = Task(name="Subtask")

        task.add_subtask(subtask)

        assert len(task.subtasks) == 1
        assert subtask.parent_id == task.entity_id

    def test_add_todo(self):
        """Test adding todo to task."""
        task = Task(name="Task")
        todo = Todo(name="Fix bug", action="Update code")

        task.add_todo(todo)

        assert len(task.todos) == 1
        assert todo.parent_id == task.entity_id

    def test_get_subtasks(self):
        """Test getting direct subtasks."""
        task = Task(name="Task")
        subtask1 = Task(name="Subtask 1")
        subtask2 = Task(name="Subtask 2")

        task.add_subtask(subtask1)
        task.add_subtask(subtask2)

        subtasks = task.get_subtasks()

        assert len(subtasks) == 2
        assert subtask1 in subtasks

    def test_get_todos(self):
        """Test getting direct todos."""
        task = Task(name="Task")
        todo1 = Todo(name="Todo 1")
        todo2 = Todo(name="Todo 2")

        task.add_todo(todo1)
        task.add_todo(todo2)

        todos = task.get_todos()

        assert len(todos) == 2
        assert todo1 in todos

    def test_get_all_subtasks_recursive(self):
        """Test getting all subtasks recursively."""
        task = Task(name="Root")
        subtask1 = Task(name="Subtask 1")
        subtask2 = Task(name="Subtask 2")
        nested_subtask = Task(name="Nested")

        subtask1.add_subtask(nested_subtask)
        task.add_subtask(subtask1)
        task.add_subtask(subtask2)

        all_subtasks = task.get_all_subtasks()

        assert len(all_subtasks) == 3  # subtask1, subtask2, nested
        assert nested_subtask in all_subtasks

    def test_get_subtask_by_id(self):
        """Test finding subtask by ID."""
        task = Task(name="Task")
        subtask = Task(name="Subtask")
        task.add_subtask(subtask)

        found = task.get_subtask_by_id(subtask.entity_id)

        assert found is subtask

    def test_get_subtask_by_id_nested(self):
        """Test finding nested subtask by ID."""
        task = Task(name="Root")
        subtask = Task(name="Subtask")
        nested = Task(name="Nested")

        subtask.add_subtask(nested)
        task.add_subtask(subtask)

        found = task.get_subtask_by_id(nested.entity_id)

        assert found is nested

    def test_get_subtask_by_id_not_found(self):
        """Test finding nonexistent subtask returns None."""
        task = Task(name="Task")

        found = task.get_subtask_by_id("nonexistent")

        assert found is None

    def test_is_leaf_true(self):
        """Test is_leaf() for task with no subtasks."""
        task = Task(name="Leaf task")

        assert task.is_leaf() is True

    def test_is_leaf_false(self):
        """Test is_leaf() for task with subtasks."""
        task = Task(name="Task")
        task.add_subtask(Task(name="Subtask"))

        assert task.is_leaf() is False

    def test_is_composite_true(self):
        """Test is_composite() for task with subtasks."""
        task = Task(name="Task")
        task.add_subtask(Task(name="Subtask"))

        assert task.is_composite() is True

    def test_is_composite_false(self):
        """Test is_composite() for task without subtasks."""
        task = Task(name="Leaf")

        assert task.is_composite() is False

    def test_get_depth_leaf(self):
        """Test get_depth() for leaf task."""
        task = Task(name="Leaf")

        assert task.get_depth() == 0

    def test_get_depth_one_level(self):
        """Test get_depth() for one level."""
        task = Task(name="Root")
        task.add_subtask(Task(name="Child"))

        assert task.get_depth() == 1

    def test_get_depth_nested(self):
        """Test get_depth() for nested hierarchy."""
        root = Task(name="Root")
        level1 = Task(name="Level 1")
        level2 = Task(name="Level 2")

        level1.add_subtask(level2)
        root.add_subtask(level1)

        assert root.get_depth() == 2

    def test_has_dependencies_true(self):
        """Test has_dependencies() with dependencies."""
        task = Task(name="Task", dependencies=["task1", "task2"])

        assert task.has_dependencies() is True

    def test_has_dependencies_false(self):
        """Test has_dependencies() without dependencies."""
        task = Task(name="Task")

        assert task.has_dependencies() is False


class TestTodoEntity:
    """Test Todo entity."""

    def test_create_todo(self):
        """Test creating todo with attributes."""
        todo = Todo(
            name="Fix bug",
            action="Update authentication logic",
            assignee="alice"
        )

        assert todo.name == "Fix bug"
        assert todo.action == "Update authentication logic"
        assert todo.assignee == "alice"

    def test_complete_todo(self):
        """Test completing todo."""
        todo = Todo(name="Todo")

        todo.complete()

        assert todo.status == TaskStatus.COMPLETED
        assert todo.completed_at is not None

    def test_is_completed_true(self):
        """Test is_completed() for completed todo."""
        todo = Todo(name="Todo", status=TaskStatus.COMPLETED)

        assert todo.is_completed() is True

    def test_is_completed_false(self):
        """Test is_completed() for pending todo."""
        todo = Todo(name="Todo", status=TaskStatus.PENDING)

        assert todo.is_completed() is False


class TestHierarchyTraversal:
    """Test hierarchy traversal functions."""

    def test_traverse_single_project(self):
        """Test traversing project with no tasks."""
        project = Project(name="Project")

        result = traverse_hierarchy(project)

        assert len(result) == 1
        assert result[0] is project

    def test_traverse_project_with_tasks(self):
        """Test traversing project with tasks."""
        project = Project(name="Project")
        task1 = Task(name="Task 1")
        task2 = Task(name="Task 2")

        project.add_task(task1)
        project.add_task(task2)

        result = traverse_hierarchy(project)

        assert len(result) == 3  # project + 2 tasks
        assert project in result
        assert task1 in result
        assert task2 in result

    def test_traverse_with_subtasks(self):
        """Test traversing with nested subtasks."""
        project = Project(name="Project")
        task = Task(name="Task")
        subtask = Task(name="Subtask")
        task.add_subtask(subtask)
        project.add_task(task)

        result = traverse_hierarchy(project)

        assert len(result) == 3  # project + task + subtask
        assert subtask in result

    def test_traverse_with_todos(self):
        """Test traversing with todos."""
        task = Task(name="Task")
        todo1 = Todo(name="Todo 1")
        todo2 = Todo(name="Todo 2")

        task.add_todo(todo1)
        task.add_todo(todo2)

        result = traverse_hierarchy(task)

        assert len(result) == 3  # task + 2 todos
        assert todo1 in result
        assert todo2 in result

    def test_traverse_with_visit_function(self):
        """Test traversal with visit callback."""
        project = Project(name="Project")
        task = Task(name="Task")
        project.add_task(task)

        visited = []

        def visit(entity):
            visited.append(entity.name)

        traverse_hierarchy(project, visit_fn=visit)

        assert "Project" in visited
        assert "Task" in visited

    def test_find_entity_by_id_project(self):
        """Test finding project by ID."""
        project = Project(name="Project")

        found = find_entity_by_id(project, project.entity_id)

        assert found is project

    def test_find_entity_by_id_task(self):
        """Test finding task by ID in hierarchy."""
        project = Project(name="Project")
        task = Task(name="Task")
        project.add_task(task)

        found = find_entity_by_id(project, task.entity_id)

        assert found is task

    def test_find_entity_by_id_nested(self):
        """Test finding nested entity by ID."""
        project = Project(name="Project")
        task = Task(name="Task")
        subtask = Task(name="Subtask")
        task.add_subtask(subtask)
        project.add_task(task)

        found = find_entity_by_id(project, subtask.entity_id)

        assert found is subtask

    def test_find_entity_by_id_todo(self):
        """Test finding todo by ID."""
        task = Task(name="Task")
        todo = Todo(name="Todo")
        task.add_todo(todo)

        found = find_entity_by_id(task, todo.entity_id)

        assert found is todo

    def test_find_entity_by_id_not_found(self):
        """Test finding nonexistent entity returns None."""
        project = Project(name="Project")

        found = find_entity_by_id(project, "nonexistent")

        assert found is None


class TestRepresentation:
    """Test string representations."""

    def test_project_repr(self):
        """Test Project __repr__()."""
        project = Project(name="My Project", status=TaskStatus.IN_PROGRESS)

        repr_str = repr(project)

        assert "Project" in repr_str
        assert "My Project" in repr_str
        assert "IN_PROGRESS" in repr_str

    def test_task_repr(self):
        """Test Task __repr__()."""
        task = Task(name="My Task")

        repr_str = repr(task)

        assert "Task" in repr_str
        assert "My Task" in repr_str

    def test_todo_repr(self):
        """Test Todo __repr__()."""
        todo = Todo(name="My Todo")

        repr_str = repr(todo)

        assert "Todo" in repr_str
        assert "My Todo" in repr_str
