"""HTN Node entity for hierarchical task representation.

Implements recursive task decomposition with preconditions and effects,
following the graph-theoretic HTN model from the unified architecture.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable


@dataclass
class HTNNode:
    """Represents a node in a Hierarchical Task Network.

    An HTN node models a task that can be recursively decomposed into subtasks.
    It maintains preconditions (required state), effects (state changes), and
    supports graph-theoretic operations for task planning.

    Attributes:
        task_id: Unique identifier for this task
        description: Human-readable task description
        subtasks: Child nodes in the task hierarchy
        preconditions: State requirements that must be satisfied
        effects: State changes produced by task execution
        metadata: Additional task-specific data
    """

    task_id: str
    description: str
    subtasks: List["HTNNode"] = field(default_factory=list)
    preconditions: Dict[str, Any] = field(default_factory=dict)
    effects: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_primitive(self) -> bool:
        """Check if this is a primitive (leaf) task.

        Returns:
            True if task has no subtasks (leaf node)
        """
        return self.subtasks is None or len(self.subtasks) == 0

    def is_compound(self) -> bool:
        """Check if this is a compound (non-leaf) task.

        Returns:
            True if task has subtasks (internal node)
        """
        return self.subtasks is not None and len(self.subtasks) > 0

    def add_subtask(self, subtask: "HTNNode") -> None:
        """Add a child task to this node.

        Args:
            subtask: HTN node to add as child
        """
        if self.subtasks is None:
            self.subtasks = []
        self.subtasks.append(subtask)

    def check_preconditions(self, state: Dict[str, Any]) -> bool:
        """Verify preconditions against current state.

        Args:
            state: Current world state to check against

        Returns:
            True if all preconditions are satisfied
        """
        for key, expected_value in self.preconditions.items():
            if key not in state:
                return False
            if state[key] != expected_value:
                return False
        return True

    def apply_effects(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Apply task effects to state.

        Creates new state dict with effects applied, following
        immutable state pattern.

        Args:
            state: Current world state

        Returns:
            New state with effects applied
        """
        new_state = state.copy()
        new_state.update(self.effects)
        return new_state

    def decompose(
        self,
        state: Dict[str, Any],
        decomposition_fn: Optional[Callable[["HTNNode", Dict[str, Any]], List["HTNNode"]]] = None
    ) -> List["HTNNode"]:
        """Recursively decompose this task into executable subtasks.

        If task is primitive (no subtasks), returns self in list.
        If task is compound, returns decomposed subtasks.
        Optional decomposition_fn allows custom decomposition strategies.

        Args:
            state: Current world state for precondition checking
            decomposition_fn: Optional custom decomposition strategy

        Returns:
            List of decomposed subtasks ready for execution

        Raises:
            ValueError: If preconditions not satisfied
        """
        if not self.check_preconditions(state):
            raise ValueError(
                f"Preconditions not satisfied for task '{self.task_id}'. "
                f"Required: {self.preconditions}, Got: {state}"
            )

        # Use custom decomposition if provided
        if decomposition_fn is not None:
            return decomposition_fn(self, state)

        # Default decomposition: return subtasks if compound, self if primitive
        if self.is_primitive():
            return [self]

        # Recursively decompose all subtasks
        decomposed = []
        current_state = state.copy()

        for subtask in self.subtasks:
            # Decompose subtask with current state
            subtask_decomposed = subtask.decompose(current_state, decomposition_fn)
            decomposed.extend(subtask_decomposed)

            # Update state with subtask effects for next subtask
            current_state = subtask.apply_effects(current_state)

        return decomposed

    def get_depth(self) -> int:
        """Calculate maximum depth of task hierarchy.

        Returns:
            Maximum depth from this node to deepest leaf
        """
        if self.is_primitive():
            return 0
        if self.subtasks is None or len(self.subtasks) == 0:
            return 0
        return 1 + max(subtask.get_depth() for subtask in self.subtasks)

    def __repr__(self) -> str:
        """String representation for debugging."""
        subtask_count = len(self.subtasks)
        task_type = "primitive" if self.is_primitive() else "compound"
        return (
            f"HTNNode(id='{self.task_id}', "
            f"type={task_type}, "
            f"subtasks={subtask_count})"
        )
