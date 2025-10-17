"""Unit tests for HTN Node entity.

Tests cover instantiation, attribute access, precondition checking,
effect application, and recursive decomposition.
"""

import pytest
from src.entity.htn import HTNNode


class TestHTNNodeInstantiation:
    """Test HTN node creation and attributes."""

    def test_create_primitive_node(self):
        """Test creating a primitive (leaf) node."""
        node = HTNNode(
            task_id="task_1",
            description="Execute unit tests"
        )

        assert node.task_id == "task_1"
        assert node.description == "Execute unit tests"
        assert node.subtasks == []
        assert node.preconditions == {}
        assert node.effects == {}
        assert node.metadata == {}

    def test_create_node_with_preconditions_and_effects(self):
        """Test creating node with preconditions and effects."""
        preconditions = {"env": "test", "dependencies": "installed"}
        effects = {"tests_run": True, "coverage": 85}

        node = HTNNode(
            task_id="task_2",
            description="Run integration tests",
            preconditions=preconditions,
            effects=effects
        )

        assert node.preconditions == preconditions
        assert node.effects == effects

    def test_create_compound_node_with_subtasks(self):
        """Test creating compound node with subtasks."""
        subtask1 = HTNNode(task_id="subtask_1", description="Setup")
        subtask2 = HTNNode(task_id="subtask_2", description="Execute")

        parent = HTNNode(
            task_id="parent",
            description="Run workflow",
            subtasks=[subtask1, subtask2]
        )

        assert len(parent.subtasks) == 2
        assert parent.subtasks[0].task_id == "subtask_1"
        assert parent.subtasks[1].task_id == "subtask_2"


class TestHTNNodeTypeChecking:
    """Test primitive vs compound node detection."""

    def test_is_primitive_returns_true_for_leaf(self):
        """Test is_primitive() on leaf node."""
        node = HTNNode(task_id="leaf", description="Atomic task")
        assert node.is_primitive() is True
        assert node.is_compound() is False

    def test_is_compound_returns_true_for_parent(self):
        """Test is_compound() on node with subtasks."""
        child = HTNNode(task_id="child", description="Child task")
        parent = HTNNode(
            task_id="parent",
            description="Parent task",
            subtasks=[child]
        )

        assert parent.is_compound() is True
        assert parent.is_primitive() is False


class TestHTNNodeSubtaskManagement:
    """Test adding and managing subtasks."""

    def test_add_subtask(self):
        """Test add_subtask() method."""
        parent = HTNNode(task_id="parent", description="Parent")
        child = HTNNode(task_id="child", description="Child")

        parent.add_subtask(child)

        assert len(parent.subtasks) == 1
        assert parent.subtasks[0].task_id == "child"

    def test_add_multiple_subtasks(self):
        """Test adding multiple subtasks sequentially."""
        parent = HTNNode(task_id="parent", description="Parent")

        for i in range(3):
            child = HTNNode(task_id=f"child_{i}", description=f"Child {i}")
            parent.add_subtask(child)

        assert len(parent.subtasks) == 3
        assert parent.subtasks[0].task_id == "child_0"
        assert parent.subtasks[2].task_id == "child_2"


class TestHTNNodePreconditions:
    """Test precondition checking."""

    def test_check_preconditions_success(self):
        """Test precondition check passes with valid state."""
        node = HTNNode(
            task_id="task",
            description="Deploy",
            preconditions={"env": "production", "tests": "passed"}
        )

        state = {"env": "production", "tests": "passed", "extra": "data"}

        assert node.check_preconditions(state) is True

    def test_check_preconditions_fails_missing_key(self):
        """Test precondition check fails when key missing."""
        node = HTNNode(
            task_id="task",
            description="Deploy",
            preconditions={"env": "production", "tests": "passed"}
        )

        state = {"env": "production"}  # Missing 'tests' key

        assert node.check_preconditions(state) is False

    def test_check_preconditions_fails_wrong_value(self):
        """Test precondition check fails when value doesn't match."""
        node = HTNNode(
            task_id="task",
            description="Deploy",
            preconditions={"env": "production"}
        )

        state = {"env": "development"}  # Wrong value

        assert node.check_preconditions(state) is False

    def test_check_preconditions_empty_always_passes(self):
        """Test node with no preconditions always passes."""
        node = HTNNode(task_id="task", description="No requirements")

        assert node.check_preconditions({}) is True
        assert node.check_preconditions({"any": "state"}) is True


class TestHTNNodeEffects:
    """Test effect application."""

    def test_apply_effects_updates_state(self):
        """Test apply_effects() updates state correctly."""
        node = HTNNode(
            task_id="task",
            description="Build project",
            effects={"built": True, "artifacts": "generated"}
        )

        initial_state = {"built": False}
        new_state = node.apply_effects(initial_state)

        assert new_state["built"] is True
        assert new_state["artifacts"] == "generated"

    def test_apply_effects_immutable(self):
        """Test apply_effects() doesn't mutate original state."""
        node = HTNNode(
            task_id="task",
            description="Update state",
            effects={"counter": 1}
        )

        initial_state = {"counter": 0}
        new_state = node.apply_effects(initial_state)

        # Original should be unchanged
        assert initial_state["counter"] == 0
        # New state should be updated
        assert new_state["counter"] == 1

    def test_apply_effects_preserves_existing_keys(self):
        """Test apply_effects() preserves non-affected state."""
        node = HTNNode(
            task_id="task",
            description="Update",
            effects={"new_key": "new_value"}
        )

        initial_state = {"existing_key": "existing_value"}
        new_state = node.apply_effects(initial_state)

        assert new_state["existing_key"] == "existing_value"
        assert new_state["new_key"] == "new_value"


class TestHTNNodeDecomposition:
    """Test recursive task decomposition."""

    def test_decompose_primitive_returns_self(self):
        """Test decompose() on primitive node returns itself."""
        node = HTNNode(task_id="primitive", description="Leaf task")

        state = {}
        result = node.decompose(state)

        assert len(result) == 1
        assert result[0] is node

    def test_decompose_compound_returns_subtasks(self):
        """Test decompose() on compound node returns subtasks."""
        child1 = HTNNode(task_id="child1", description="First")
        child2 = HTNNode(task_id="child2", description="Second")
        parent = HTNNode(
            task_id="parent",
            description="Parent",
            subtasks=[child1, child2]
        )

        state = {}
        result = parent.decompose(state)

        assert len(result) == 2
        assert result[0].task_id == "child1"
        assert result[1].task_id == "child2"

    def test_decompose_fails_when_preconditions_not_met(self):
        """Test decompose() raises error when preconditions fail."""
        node = HTNNode(
            task_id="task",
            description="Requires env",
            preconditions={"env": "test"}
        )

        state = {"env": "production"}  # Wrong environment

        with pytest.raises(ValueError) as exc_info:
            node.decompose(state)

        assert "Preconditions not satisfied" in str(exc_info.value)

    def test_decompose_recursive_with_nested_subtasks(self):
        """Test decompose() recursively flattens nested hierarchy."""
        # Create hierarchy: parent -> child -> grandchild
        grandchild = HTNNode(task_id="grandchild", description="Leaf")
        child = HTNNode(
            task_id="child",
            description="Middle",
            subtasks=[grandchild]
        )
        parent = HTNNode(
            task_id="parent",
            description="Root",
            subtasks=[child]
        )

        state = {}
        result = parent.decompose(state)

        # Should flatten to just the grandchild (leaf node)
        assert len(result) == 1
        assert result[0].task_id == "grandchild"

    def test_decompose_applies_effects_sequentially(self):
        """Test decompose() applies effects from subtasks to state."""
        # First subtask adds "step1" to state
        subtask1 = HTNNode(
            task_id="step1",
            description="First step",
            effects={"step1": "done"}
        )

        # Second subtask requires "step1" to be done
        subtask2 = HTNNode(
            task_id="step2",
            description="Second step",
            preconditions={"step1": "done"},
            effects={"step2": "done"}
        )

        parent = HTNNode(
            task_id="workflow",
            description="Sequential workflow",
            subtasks=[subtask1, subtask2]
        )

        state = {}
        result = parent.decompose(state)

        # Should successfully decompose both subtasks
        assert len(result) == 2
        assert result[0].task_id == "step1"
        assert result[1].task_id == "step2"

    def test_decompose_with_custom_function(self):
        """Test decompose() with custom decomposition strategy."""
        def custom_decomposer(node: HTNNode, state: dict) -> list:
            """Custom decomposition that reverses subtask order."""
            if node.is_primitive():
                return [node]
            # Return subtasks in reverse order
            return list(reversed(node.subtasks))

        child1 = HTNNode(task_id="first", description="First")
        child2 = HTNNode(task_id="second", description="Second")
        parent = HTNNode(
            task_id="parent",
            description="Parent",
            subtasks=[child1, child2]
        )

        state = {}
        result = parent.decompose(state, decomposition_fn=custom_decomposer)

        # Custom function should reverse order
        assert len(result) == 2
        assert result[0].task_id == "second"
        assert result[1].task_id == "first"


class TestHTNNodeDepthCalculation:
    """Test hierarchy depth calculation."""

    def test_depth_primitive_is_zero(self):
        """Test depth of primitive node is 0."""
        node = HTNNode(task_id="leaf", description="Leaf")
        assert node.get_depth() == 0

    def test_depth_single_level(self):
        """Test depth of one-level hierarchy."""
        child = HTNNode(task_id="child", description="Child")
        parent = HTNNode(
            task_id="parent",
            description="Parent",
            subtasks=[child]
        )

        assert parent.get_depth() == 1

    def test_depth_nested_hierarchy(self):
        """Test depth of nested hierarchy."""
        grandchild = HTNNode(task_id="grandchild", description="Leaf")
        child = HTNNode(
            task_id="child",
            description="Middle",
            subtasks=[grandchild]
        )
        parent = HTNNode(
            task_id="parent",
            description="Root",
            subtasks=[child]
        )

        assert parent.get_depth() == 2

    def test_depth_multiple_branches(self):
        """Test depth with multiple branches (takes max)."""
        # Shallow branch
        shallow = HTNNode(task_id="shallow", description="Shallow")

        # Deep branch
        deep_leaf = HTNNode(task_id="deep_leaf", description="Deep leaf")
        deep_middle = HTNNode(
            task_id="deep_middle",
            description="Deep middle",
            subtasks=[deep_leaf]
        )

        parent = HTNNode(
            task_id="parent",
            description="Root",
            subtasks=[shallow, deep_middle]
        )

        # Should be 2 (depth of deepest branch)
        assert parent.get_depth() == 2


class TestHTNNodeRepresentation:
    """Test string representation."""

    def test_repr_primitive(self):
        """Test __repr__() for primitive node."""
        node = HTNNode(task_id="test", description="Test task")
        repr_str = repr(node)

        assert "test" in repr_str
        assert "primitive" in repr_str
        assert "subtasks=0" in repr_str

    def test_repr_compound(self):
        """Test __repr__() for compound node."""
        child1 = HTNNode(task_id="child1", description="Child 1")
        child2 = HTNNode(task_id="child2", description="Child 2")
        parent = HTNNode(
            task_id="parent",
            description="Parent",
            subtasks=[child1, child2]
        )

        repr_str = repr(parent)

        assert "parent" in repr_str
        assert "compound" in repr_str
        assert "subtasks=2" in repr_str
