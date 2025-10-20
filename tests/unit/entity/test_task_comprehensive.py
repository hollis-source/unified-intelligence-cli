# tests/unit/entity/test_task_comprehensive.py
"""Comprehensive tests for Task entity."""

import pytest
from src.entity.agent import Task


def test_task_creation_minimal():
    """Test Task creation with only required parameter (description)."""
    task = Task("Implement login feature")
    assert task.description == "Implement login feature"
    assert task.priority == 1  # Default
    assert task.task_id is None  # Default
    assert task.dependencies == []  # Default


def test_task_creation_full():
    """Test Task creation with all parameters."""
    task = Task(
        description="Full task",
        priority=5,
        task_id="task_123",
        dependencies=["dep1", "dep2"]
    )
    assert task.description == "Full task"
    assert task.priority == 5
    assert task.task_id == "task_123"
    assert task.dependencies == ["dep1", "dep2"]


def test_default_priority():
    """Test that default priority is 1."""
    task = Task("Test task")
    assert task.priority == 1


def test_default_task_id():
    """Test that default task_id is None."""
    task = Task("Test task")
    assert task.task_id is None


def test_default_dependencies():
    """Test that default dependencies is empty list."""
    task = Task("Test task")
    assert task.dependencies == []
    assert isinstance(task.dependencies, list)


def test_task_with_multiple_dependencies():
    """Test Task with multiple dependencies."""
    task = Task("Task", dependencies=["dep1", "dep2", "dep3"])
    assert len(task.dependencies) == 3
    assert task.dependencies == ["dep1", "dep2", "dep3"]


def test_dependencies_not_shared():
    """Test that each Task instance has its own dependencies list."""
    task1 = Task("Task 1")
    task2 = Task("Task 2")

    task1.dependencies.append("dep1")

    assert task1.dependencies == ["dep1"]
    assert task2.dependencies == []


@pytest.mark.parametrize("description", [
    "",                      # Empty string
    "Normal task",           # Normal description
    "A" * 1000,             # Very long description
    "Task\nwith\nnewlines", # Multiline
    "Task with special chars: !@#$%",
])
def test_description_edge_cases(description):
    """Test various description edge cases."""
    task = Task(description)
    assert task.description == description


@pytest.mark.parametrize("priority", [
    0,      # Zero priority
    1,      # Default
    5,      # Medium
    10,     # High
    100,    # Very high
    -1,     # Negative (edge case)
])
def test_priority_values(priority):
    """Test various priority values."""
    task = Task("Task", priority=priority)
    assert task.priority == priority


@pytest.mark.parametrize("task_id", [
    None,           # Default
    "",             # Empty string
    "task_123",     # Normal ID
    "very-long-task-id-" + "x" * 100,  # Long ID
])
def test_task_id_values(task_id):
    """Test various task_id values."""
    task = Task("Task", task_id=task_id)
    assert task.task_id == task_id


@pytest.mark.parametrize("dependencies", [
    [],                          # Empty list
    ["dep1"],                    # Single dependency
    ["dep1", "dep2"],           # Multiple dependencies
    ["dep1", "dep2", "dep3", "dep4", "dep5"],  # Many dependencies
])
def test_dependencies_values(dependencies):
    """Test various dependency configurations."""
    task = Task("Task", dependencies=dependencies)
    assert task.dependencies == dependencies
    assert len(task.dependencies) == len(dependencies)
