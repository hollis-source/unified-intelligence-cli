"""Lifecycle entity for meta-operational workflow coordination.

Implements state machine for Plan → Verify → Decompose → Execute lifecycle
phases, ensuring systematic task processing and validation.
"""

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime


class LifecycleState(Enum):
    """Lifecycle phase states."""

    PLAN = auto()
    VERIFY = auto()
    DECOMPOSE = auto()
    EXECUTE = auto()
    COMPLETED = auto()
    FAILED = auto()


@dataclass
class LifecycleTransition:
    """Record of a state transition.

    Attributes:
        from_state: Previous state
        to_state: New state
        timestamp: When transition occurred
        metadata: Additional transition information
    """

    from_state: LifecycleState
    to_state: LifecycleState
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)


class Lifecycle:
    """Meta-operational lifecycle state machine.

    Coordinates task processing through four phases:
    1. PLAN: Generate initial plan based on goals
    2. VERIFY: Validate plan against constraints
    3. DECOMPOSE: Break plan into executable units
    4. EXECUTE: Run units and monitor results

    Supports linear progression and failure handling.
    """

    # Valid state transitions
    VALID_TRANSITIONS = {
        LifecycleState.PLAN: [LifecycleState.VERIFY, LifecycleState.FAILED],
        LifecycleState.VERIFY: [LifecycleState.DECOMPOSE, LifecycleState.PLAN, LifecycleState.FAILED],
        LifecycleState.DECOMPOSE: [LifecycleState.EXECUTE, LifecycleState.FAILED],
        LifecycleState.EXECUTE: [LifecycleState.COMPLETED, LifecycleState.PLAN, LifecycleState.FAILED],
        LifecycleState.COMPLETED: [],  # Terminal state
        LifecycleState.FAILED: [LifecycleState.PLAN],  # Can retry from planning
    }

    def __init__(self, initial_state: LifecycleState = LifecycleState.PLAN):
        """Initialize lifecycle in given state.

        Args:
            initial_state: Starting state (default: PLAN)
        """
        self.current_state = initial_state
        self.history: List[LifecycleTransition] = []
        self.state_data: Dict[LifecycleState, Any] = {}
        self.phase_callbacks: Dict[LifecycleState, List[Callable]] = {
            state: [] for state in LifecycleState
        }

    def get_state(self) -> LifecycleState:
        """Get current lifecycle state.

        Returns:
            Current state
        """
        return self.current_state

    def is_terminal(self) -> bool:
        """Check if in terminal state (COMPLETED or FAILED).

        Returns:
            True if lifecycle is complete or failed
        """
        return self.current_state in [LifecycleState.COMPLETED, LifecycleState.FAILED]

    def can_transition_to(self, target_state: LifecycleState) -> bool:
        """Check if transition to target state is valid.

        Args:
            target_state: State to transition to

        Returns:
            True if transition is allowed
        """
        valid_targets = self.VALID_TRANSITIONS.get(self.current_state, [])
        return target_state in valid_targets

    def transition(
        self,
        target_state: LifecycleState,
        **metadata
    ) -> None:
        """Transition to new state.

        Args:
            target_state: State to transition to
            **metadata: Additional transition information

        Raises:
            ValueError: If transition is invalid
        """
        if not self.can_transition_to(target_state):
            raise ValueError(
                f"Invalid transition from {self.current_state.name} "
                f"to {target_state.name}"
            )

        # Record transition
        transition = LifecycleTransition(
            from_state=self.current_state,
            to_state=target_state,
            metadata=metadata
        )
        self.history.append(transition)

        # Update state
        old_state = self.current_state
        self.current_state = target_state

        # Trigger callbacks for new state
        self._trigger_callbacks(target_state)

    def plan(self, plan_data: Any = None) -> None:
        """Transition to PLAN state.

        Args:
            plan_data: Planning information to store

        Raises:
            ValueError: If not in valid state for planning
        """
        if self.current_state == LifecycleState.PLAN:
            # Already planning, just update data
            self.state_data[LifecycleState.PLAN] = plan_data
        else:
            self.transition(LifecycleState.PLAN, action="start_planning")
            self.state_data[LifecycleState.PLAN] = plan_data

    def verify(self, verification_result: bool = True, **metadata) -> None:
        """Transition to VERIFY state and validate plan.

        Args:
            verification_result: Whether verification passed
            **metadata: Additional verification information

        Raises:
            ValueError: If not in PLAN or VERIFY state
        """
        if verification_result:
            self.transition(LifecycleState.VERIFY, **metadata)
            self.state_data[LifecycleState.VERIFY] = metadata
        else:
            # Verification failed, go back to planning (if not already there)
            if self.current_state != LifecycleState.PLAN:
                self.transition(LifecycleState.PLAN, reason="verification_failed", **metadata)

    def decompose(self, decomposed_units: Any = None) -> None:
        """Transition to DECOMPOSE state.

        Args:
            decomposed_units: Decomposed task units

        Raises:
            ValueError: If not in VERIFY state
        """
        self.transition(LifecycleState.DECOMPOSE, action="decomposing")
        self.state_data[LifecycleState.DECOMPOSE] = decomposed_units

    def execute(self, execution_data: Any = None) -> None:
        """Transition to EXECUTE state.

        Args:
            execution_data: Execution information

        Raises:
            ValueError: If not in DECOMPOSE state
        """
        self.transition(LifecycleState.EXECUTE, action="executing")
        self.state_data[LifecycleState.EXECUTE] = execution_data

    def complete(self, **metadata) -> None:
        """Mark lifecycle as COMPLETED.

        Args:
            **metadata: Completion information

        Raises:
            ValueError: If not in EXECUTE state
        """
        self.transition(LifecycleState.COMPLETED, **metadata)

    def fail(self, error: Optional[str] = None, **metadata) -> None:
        """Mark lifecycle as FAILED.

        Args:
            error: Error description
            **metadata: Additional failure information
        """
        self.transition(LifecycleState.FAILED, error=error, **metadata)

    def retry(self) -> None:
        """Retry from planning after failure.

        Raises:
            ValueError: If not in FAILED state
        """
        if self.current_state != LifecycleState.FAILED:
            raise ValueError("Can only retry from FAILED state")

        self.transition(LifecycleState.PLAN, action="retrying")

    def get_state_data(self, state: LifecycleState) -> Any:
        """Get data stored for a specific state.

        Args:
            state: State to retrieve data for

        Returns:
            Data for that state, or None if not set
        """
        return self.state_data.get(state)

    def get_transition_history(self) -> List[LifecycleTransition]:
        """Get full transition history.

        Returns:
            List of all transitions
        """
        return self.history.copy()

    def get_current_phase_duration(self) -> Optional[float]:
        """Get duration of current phase in seconds.

        Returns:
            Duration in seconds, or None if no transitions yet
        """
        if not self.history:
            return None

        last_transition = self.history[-1]
        duration = (datetime.utcnow() - last_transition.timestamp).total_seconds()
        return duration

    def register_callback(
        self,
        state: LifecycleState,
        callback: Callable[["Lifecycle"], None]
    ) -> None:
        """Register callback to execute when entering state.

        Args:
            state: State to trigger callback
            callback: Function to call (receives lifecycle instance)
        """
        self.phase_callbacks[state].append(callback)

    def _trigger_callbacks(self, state: LifecycleState) -> None:
        """Trigger all callbacks for a state.

        Args:
            state: State that was entered
        """
        for callback in self.phase_callbacks[state]:
            callback(self)

    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"Lifecycle(state={self.current_state.name}, "
            f"transitions={len(self.history)})"
        )


def run_full_lifecycle(
    plan_fn: Callable[[], Any],
    verify_fn: Callable[[Any], bool],
    decompose_fn: Callable[[Any], Any],
    execute_fn: Callable[[Any], Any]
) -> Lifecycle:
    """Helper to run complete lifecycle with provided functions.

    Args:
        plan_fn: Function to generate plan
        verify_fn: Function to verify plan (returns bool)
        decompose_fn: Function to decompose plan
        execute_fn: Function to execute decomposed units

    Returns:
        Completed lifecycle instance

    Raises:
        Exception: If any phase fails
    """
    lifecycle = Lifecycle()

    # Plan phase
    plan_data = plan_fn()
    lifecycle.plan(plan_data)

    # Verify phase
    is_valid = verify_fn(plan_data)
    if not is_valid:
        lifecycle.fail(error="Plan verification failed")
        return lifecycle

    lifecycle.verify(verification_result=True)

    # Decompose phase
    decomposed = decompose_fn(plan_data)
    lifecycle.decompose(decomposed)

    # Execute phase
    try:
        result = execute_fn(decomposed)
        lifecycle.execute(result)
        lifecycle.complete()
    except Exception as e:
        lifecycle.fail(error=str(e))

    return lifecycle
