# tests/unit/entity/test_htnnode_comprehensive.py
"""Comprehensive tests for HTNNode entity."""

import pytest
from src.entity.htn.htn_node import HTNNode


def test_htnnode_creation():
    """Test HTNNode initialization with all attributes."""
    node = HTNNode(
        task_id="task1",
        description="Test task",
        preconditions={"state": "ready"},
        effects={"state": "done"},
        metadata={"priority": "high"}
    )
    assert node.task_id == "task1"
    assert node.description == "Test task"
    assert node.preconditions == {"state": "ready"}
    assert node.effects == {"state": "done"}
    assert node.metadata == {"priority": "high"}
    assert node.subtasks == []


def test_is_primitive_no_subtasks():
    """Test is_primitive returns True when no subtasks."""
    node = HTNNode("task1", "Test")
    assert node.is_primitive() is True


def test_is_compound_with_subtasks():
    """Test is_compound returns True when subtasks exist."""
    child = HTNNode("child1", "Child task")
    node = HTNNode("task1", "Parent")
    node.add_subtask(child)
    assert node.is_compound() is True


def test_add_subtask():
    """Test adding a subtask updates subtasks list."""
    parent = HTNNode("parent", "Parent task")
    child = HTNNode("child", "Child task")
    parent.add_subtask(child)
    assert len(parent.subtasks) == 1
    assert parent.subtasks[0] == child


@pytest.mark.parametrize("state, expected", [
    ({"state": "ready"}, True),
    ({"state": "not_ready"}, False),
    ({"other_state": "ready"}, False),
    ({}, False)
])
def test_check_preconditions(state, expected):
    """Test check_preconditions with various state scenarios."""
    node = HTNNode("task1", "Test", preconditions={"state": "ready"})
    assert node.check_preconditions(state) == expected


@pytest.mark.parametrize("state, expected", [
    ({"state1": "ready", "state2": "active"}, True),
    ({"state1": "ready", "state2": "inactive"}, False),
    ({"state1": "ready"}, False),
    ({"state2": "active"}, False)
])
def test_check_preconditions_multiple(state, expected):
    """Test check_preconditions with multiple preconditions."""
    node = HTNNode("task1", "Test", preconditions={"state1": "ready", "state2": "active"})
    assert node.check_preconditions(state) == expected


@pytest.mark.parametrize("state", [
    {},
    {"extra": "value"},
    {"key1": "val1", "key2": "val2"}
])
def test_check_preconditions_empty(state):
    """Test check_preconditions returns True when no preconditions."""
    node = HTNNode("task1", "Test")
    assert node.check_preconditions(state) is True


def test_apply_effects_immutable():
    """Test apply_effects does not mutate original state."""
    node = HTNNode("task1", "Test", effects={"state": "done"})
    original_state = {"state": "ready"}
    new_state = node.apply_effects(original_state)
    assert new_state == {"state": "done"}
    assert original_state == {"state": "ready"}


def test_apply_effects_multiple_effects():
    """Test applying multiple effects."""
    node = HTNNode("task1", "Test", effects={"a": 1, "b": 2})
    state = {"a": 0, "c": 3}
    new_state = node.apply_effects(state)
    assert new_state == {"a": 1, "b": 2, "c": 3}
    assert state == {"a": 0, "c": 3}


@pytest.mark.parametrize("effects, state, expected", [
    ({"a": 1}, {"a": 0, "b": 2}, {"a": 1, "b": 2}),
    ({"x": "y"}, {"a": 1}, {"a": 1, "x": "y"}),
    ({}, {"a": 1}, {"a": 1})
])
def test_apply_effects_parametrized(effects, state, expected):
    """Parametrized test for apply_effects with various inputs."""
    node = HTNNode("task1", "Test", effects=effects)
    new_state = node.apply_effects(state)
    assert new_state == expected


def test_decompose_primitive():
    """Test decompose returns [self] for primitive task."""
    node = HTNNode("task1", "Primitive")
    decomposed = node.decompose({})
    assert decomposed == [node]


def test_decompose_compound_no_custom():
    """Test decompose recursively processes compound tasks with default strategy."""
    child1 = HTNNode("child1", "Child 1", effects={"a": 1})
    child2 = HTNNode("child2", "Child 2", preconditions={"a": 1})
    parent = HTNNode("parent", "Parent", subtasks=[child1, child2])

    state = {}
    decomposed = parent.decompose(state)

    assert len(decomposed) == 2
    assert decomposed[0] == child1
    assert decomposed[1] == child2


def test_decompose_precondition_failure():
    """Test decompose raises ValueError when preconditions not met."""
    node = HTNNode("task1", "Test", preconditions={"state": "ready"})
    with pytest.raises(ValueError) as excinfo:
        node.decompose({"state": "not_ready"})
    assert "Preconditions not satisfied" in str(excinfo.value)


def test_decompose_custom_function():
    """Test decompose uses custom decomposition function."""
    def custom_decomp(node, state):
        return [HTNNode("custom", "Custom task")]

    node = HTNNode("task1", "Test", subtasks=[HTNNode("child", "Child")])
    decomposed = node.decompose({}, decomposition_fn=custom_decomp)
    assert len(decomposed) == 1
    assert decomposed[0].task_id == "custom"


def test_decompose_primitive_custom_function():
    """Test custom decomposition function overrides primitive task handling."""
    def custom_decomp(node, state):
        return [HTNNode("custom", "Custom")]

    node = HTNNode("task1", "Primitive")
    decomposed = node.decompose({}, decomposition_fn=custom_decomp)
    assert len(decomposed) == 1
    assert decomposed[0].task_id == "custom"


def test_decompose_custom_function_preconditions_met():
    """Test custom decomposition function is called when preconditions are met."""
    def custom_decomp(node, state):
        return [HTNNode("custom", "Custom")]

    node = HTNNode("task1", "Test", preconditions={"state": "ready"})
    decomposed = node.decompose({"state": "ready"}, decomposition_fn=custom_decomp)
    assert len(decomposed) == 1
    assert decomposed[0].task_id == "custom"


def test_decompose_custom_function_precondition_failure():
    """Test custom decomposition not called if preconditions not met."""
    def custom_decomp(node, state):
        return [HTNNode("custom", "Custom")]

    node = HTNNode("task1", "Test", preconditions={"state": "ready"})
    with pytest.raises(ValueError):
        node.decompose({"state": "not_ready"}, decomposition_fn=custom_decomp)


def test_decompose_custom_compound_node():
    """Test custom decomposition for compound node."""
    def custom_decomp(node, state):
        return [HTNNode("custom", "Custom")]

    child = HTNNode("child", "Child")
    parent = HTNNode("parent", "Parent", subtasks=[child])
    decomposed = parent.decompose({}, decomposition_fn=custom_decomp)
    assert len(decomposed) == 1
    assert decomposed[0].task_id == "custom"


def test_decompose_subtask_precondition_failure():
    """Test decompose fails when a subtask's preconditions are not met."""
    child = HTNNode("child", "Child", preconditions={"state": "ready"})
    parent = HTNNode("parent", "Parent", subtasks=[child])
    with pytest.raises(ValueError) as excinfo:
        parent.decompose({"state": "not_ready"})
    assert "Preconditions not satisfied for task 'child'" in str(excinfo.value)


def test_decompose_compound_subtasks():
    """Test decompose recursively decomposes compound subtasks."""
    grandchild = HTNNode("grandchild", "GC")
    child = HTNNode("child", "Child", subtasks=[grandchild])
    parent = HTNNode("parent", "Parent", subtasks=[child])
    decomposed = parent.decompose({})
    assert len(decomposed) == 1
    assert decomposed[0] == grandchild


def test_get_depth_primitive():
    """Test get_depth returns 0 for primitive task."""
    node = HTNNode("task1", "Primitive")
    assert node.get_depth() == 0


def test_get_depth_single_level():
    """Test get_depth returns 1 for one level hierarchy."""
    child = HTNNode("child", "Child")
    parent = HTNNode("parent", "Parent", subtasks=[child])
    assert parent.get_depth() == 1


def test_get_depth_multi_level():
    """Test get_depth returns correct depth for multi-level hierarchy."""
    grandchild = HTNNode("grandchild", "Grandchild")
    child = HTNNode("child", "Child", subtasks=[grandchild])
    parent = HTNNode("parent", "Parent", subtasks=[child])
    assert parent.get_depth() == 2


def test_get_depth_max_depth():
    """Test get_depth takes max depth of subtasks."""
    child1 = HTNNode("child1", "Child1")
    child2 = HTNNode("child2", "Child2", subtasks=[HTNNode("grandchild", "GC")])
    parent = HTNNode("parent", "Parent", subtasks=[child1, child2])
    assert parent.get_depth() == 2


def test_get_depth_deep_hierarchy():
    """Test get_depth for deep hierarchy (3 levels)."""
    leaf = HTNNode("leaf", "Leaf")
    child = HTNNode("child", "Child", subtasks=[leaf])
    parent = HTNNode("parent", "Parent", subtasks=[child])
    grandparent = HTNNode("grandparent", "Grandparent", subtasks=[parent])
    assert grandparent.get_depth() == 3


def test_get_depth_multiple_subtasks():
    """Test get_depth takes max depth among subtasks."""
    gc = HTNNode("gc", "GC")
    c2 = HTNNode("c2", "C2", subtasks=[gc])
    c1 = HTNNode("c1", "C1")
    parent = HTNNode("parent", "Parent", subtasks=[c1, c2])
    assert parent.get_depth() == 2


def test_repr_primitive():
    """Test __repr__ for primitive task."""
    node = HTNNode("task1", "Primitive")
    repr_str = repr(node)
    assert "type=primitive" in repr_str
    assert "subtasks=0" in repr_str


def test_repr_compound():
    """Test __repr__ for compound task."""
    child = HTNNode("child", "Child")
    parent = HTNNode("parent", "Parent", subtasks=[child])
    repr_str = repr(parent)
    assert "type=compound" in repr_str
    assert "subtasks=1" in repr_str


def test_decompose_parent_preconditions():
    """Test decompose fails if parent's preconditions not met."""
    parent = HTNNode("parent", "Parent", preconditions={"state": "ready"})
    child = HTNNode("child", "Child")
    parent.add_subtask(child)
    with pytest.raises(ValueError) as excinfo:
        parent.decompose({"state": "not_ready"})
    assert "Preconditions not satisfied for task 'parent'" in str(excinfo.value)
