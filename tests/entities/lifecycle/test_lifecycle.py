"""Unit tests for Lifecycle entity.

Tests cover state machine transitions, phase methods, callbacks,
and complete lifecycle execution.
"""

import pytest
from src.entity.lifecycle import Lifecycle, LifecycleState
from src.entity.lifecycle.lifecycle import run_full_lifecycle


class TestLifecycleCreation:
    """Test lifecycle initialization."""

    def test_create_default_lifecycle(self):
        """Test creating lifecycle with default state."""
        lifecycle = Lifecycle()

        assert lifecycle.get_state() == LifecycleState.PLAN
        assert len(lifecycle.history) == 0
        assert lifecycle.is_terminal() is False

    def test_create_lifecycle_with_state(self):
        """Test creating lifecycle with specific initial state."""
        lifecycle = Lifecycle(initial_state=LifecycleState.EXECUTE)

        assert lifecycle.get_state() == LifecycleState.EXECUTE

    def test_lifecycle_starts_with_empty_history(self):
        """Test lifecycle starts with no transitions."""
        lifecycle = Lifecycle()

        history = lifecycle.get_transition_history()

        assert len(history) == 0


class TestLifecycleStateQueries:
    """Test state query methods."""

    def test_get_state(self):
        """Test getting current state."""
        lifecycle = Lifecycle(initial_state=LifecycleState.VERIFY)

        assert lifecycle.get_state() == LifecycleState.VERIFY

    def test_is_terminal_completed(self):
        """Test is_terminal() returns True for COMPLETED."""
        lifecycle = Lifecycle(initial_state=LifecycleState.COMPLETED)

        assert lifecycle.is_terminal() is True

    def test_is_terminal_failed(self):
        """Test is_terminal() returns True for FAILED."""
        lifecycle = Lifecycle(initial_state=LifecycleState.FAILED)

        assert lifecycle.is_terminal() is True

    def test_is_terminal_non_terminal(self):
        """Test is_terminal() returns False for non-terminal states."""
        for state in [LifecycleState.PLAN, LifecycleState.VERIFY,
                      LifecycleState.DECOMPOSE, LifecycleState.EXECUTE]:
            lifecycle = Lifecycle(initial_state=state)
            assert lifecycle.is_terminal() is False


class TestLifecycleTransitionValidation:
    """Test transition validation."""

    def test_can_transition_valid(self):
        """Test can_transition_to() for valid transition."""
        lifecycle = Lifecycle(initial_state=LifecycleState.PLAN)

        assert lifecycle.can_transition_to(LifecycleState.VERIFY) is True

    def test_can_transition_invalid(self):
        """Test can_transition_to() for invalid transition."""
        lifecycle = Lifecycle(initial_state=LifecycleState.PLAN)

        # Cannot go directly from PLAN to EXECUTE
        assert lifecycle.can_transition_to(LifecycleState.EXECUTE) is False

    def test_plan_valid_transitions(self):
        """Test valid transitions from PLAN state."""
        lifecycle = Lifecycle(initial_state=LifecycleState.PLAN)

        assert lifecycle.can_transition_to(LifecycleState.VERIFY) is True
        assert lifecycle.can_transition_to(LifecycleState.FAILED) is True
        assert lifecycle.can_transition_to(LifecycleState.DECOMPOSE) is False

    def test_verify_valid_transitions(self):
        """Test valid transitions from VERIFY state."""
        lifecycle = Lifecycle(initial_state=LifecycleState.VERIFY)

        assert lifecycle.can_transition_to(LifecycleState.DECOMPOSE) is True
        assert lifecycle.can_transition_to(LifecycleState.PLAN) is True  # Back to planning
        assert lifecycle.can_transition_to(LifecycleState.FAILED) is True

    def test_execute_valid_transitions(self):
        """Test valid transitions from EXECUTE state."""
        lifecycle = Lifecycle(initial_state=LifecycleState.EXECUTE)

        assert lifecycle.can_transition_to(LifecycleState.COMPLETED) is True
        assert lifecycle.can_transition_to(LifecycleState.PLAN) is True  # Retry
        assert lifecycle.can_transition_to(LifecycleState.FAILED) is True

    def test_completed_no_transitions(self):
        """Test COMPLETED is terminal (no valid transitions)."""
        lifecycle = Lifecycle(initial_state=LifecycleState.COMPLETED)

        for state in LifecycleState:
            assert lifecycle.can_transition_to(state) is False

    def test_failed_can_retry(self):
        """Test FAILED can transition back to PLAN."""
        lifecycle = Lifecycle(initial_state=LifecycleState.FAILED)

        assert lifecycle.can_transition_to(LifecycleState.PLAN) is True


class TestLifecycleTransitions:
    """Test state transitions."""

    def test_basic_transition(self):
        """Test basic state transition."""
        lifecycle = Lifecycle(initial_state=LifecycleState.PLAN)

        lifecycle.transition(LifecycleState.VERIFY)

        assert lifecycle.get_state() == LifecycleState.VERIFY

    def test_transition_records_history(self):
        """Test transitions are recorded in history."""
        lifecycle = Lifecycle(initial_state=LifecycleState.PLAN)

        lifecycle.transition(LifecycleState.VERIFY)

        history = lifecycle.get_transition_history()
        assert len(history) == 1
        assert history[0].from_state == LifecycleState.PLAN
        assert history[0].to_state == LifecycleState.VERIFY

    def test_transition_with_metadata(self):
        """Test transitions can include metadata."""
        lifecycle = Lifecycle(initial_state=LifecycleState.PLAN)

        lifecycle.transition(LifecycleState.VERIFY, reason="plan_approved")

        history = lifecycle.get_transition_history()
        assert history[0].metadata["reason"] == "plan_approved"

    def test_invalid_transition_raises_error(self):
        """Test invalid transition raises ValueError."""
        lifecycle = Lifecycle(initial_state=LifecycleState.PLAN)

        with pytest.raises(ValueError) as exc_info:
            lifecycle.transition(LifecycleState.EXECUTE)

        assert "Invalid transition" in str(exc_info.value)

    def test_multiple_transitions(self):
        """Test sequence of transitions."""
        lifecycle = Lifecycle(initial_state=LifecycleState.PLAN)

        lifecycle.transition(LifecycleState.VERIFY)
        lifecycle.transition(LifecycleState.DECOMPOSE)
        lifecycle.transition(LifecycleState.EXECUTE)

        assert lifecycle.get_state() == LifecycleState.EXECUTE
        assert len(lifecycle.history) == 3


class TestLifecyclePhaseMethods:
    """Test phase-specific methods."""

    def test_plan_method(self):
        """Test plan() method transitions to PLAN."""
        lifecycle = Lifecycle(initial_state=LifecycleState.FAILED)

        lifecycle.plan(plan_data={"task": "build"})

        assert lifecycle.get_state() == LifecycleState.PLAN
        assert lifecycle.get_state_data(LifecycleState.PLAN) == {"task": "build"}

    def test_plan_updates_data_when_already_planning(self):
        """Test plan() updates data if already in PLAN state."""
        lifecycle = Lifecycle(initial_state=LifecycleState.PLAN)

        lifecycle.plan(plan_data={"task": "updated"})

        # Should stay in PLAN but update data
        assert lifecycle.get_state() == LifecycleState.PLAN
        assert lifecycle.get_state_data(LifecycleState.PLAN) == {"task": "updated"}

    def test_verify_successful(self):
        """Test verify() with successful verification."""
        lifecycle = Lifecycle(initial_state=LifecycleState.PLAN)

        lifecycle.verify(verification_result=True, checks_passed=["all"])

        assert lifecycle.get_state() == LifecycleState.VERIFY
        data = lifecycle.get_state_data(LifecycleState.VERIFY)
        assert data["checks_passed"] == ["all"]

    def test_verify_failed_returns_to_plan(self):
        """Test verify() with failed verification returns to PLAN."""
        lifecycle = Lifecycle(initial_state=LifecycleState.PLAN)
        lifecycle.transition(LifecycleState.VERIFY)

        lifecycle.verify(verification_result=False, error="invalid_plan")

        assert lifecycle.get_state() == LifecycleState.PLAN

    def test_decompose_method(self):
        """Test decompose() method."""
        lifecycle = Lifecycle(initial_state=LifecycleState.VERIFY)

        units = ["unit1", "unit2", "unit3"]
        lifecycle.decompose(decomposed_units=units)

        assert lifecycle.get_state() == LifecycleState.DECOMPOSE
        assert lifecycle.get_state_data(LifecycleState.DECOMPOSE) == units

    def test_execute_method(self):
        """Test execute() method."""
        lifecycle = Lifecycle(initial_state=LifecycleState.DECOMPOSE)

        lifecycle.execute(execution_data={"status": "running"})

        assert lifecycle.get_state() == LifecycleState.EXECUTE

    def test_complete_method(self):
        """Test complete() method."""
        lifecycle = Lifecycle(initial_state=LifecycleState.EXECUTE)

        lifecycle.complete(result="success")

        assert lifecycle.get_state() == LifecycleState.COMPLETED
        assert lifecycle.is_terminal() is True

    def test_fail_method(self):
        """Test fail() method."""
        lifecycle = Lifecycle(initial_state=LifecycleState.EXECUTE)

        lifecycle.fail(error="execution_error", details="network_timeout")

        assert lifecycle.get_state() == LifecycleState.FAILED
        assert lifecycle.is_terminal() is True

    def test_retry_after_failure(self):
        """Test retry() method after failure."""
        lifecycle = Lifecycle(initial_state=LifecycleState.FAILED)

        lifecycle.retry()

        assert lifecycle.get_state() == LifecycleState.PLAN

    def test_retry_from_non_failed_fails(self):
        """Test retry() from non-FAILED state raises error."""
        lifecycle = Lifecycle(initial_state=LifecycleState.EXECUTE)

        with pytest.raises(ValueError) as exc_info:
            lifecycle.retry()

        assert "FAILED state" in str(exc_info.value)


class TestLifecycleCompleteFlow:
    """Test complete lifecycle flows."""

    def test_successful_linear_flow(self):
        """Test complete successful lifecycle flow."""
        lifecycle = Lifecycle()

        # Plan → Verify → Decompose → Execute → Complete
        lifecycle.plan({"goal": "deploy"})
        assert lifecycle.get_state() == LifecycleState.PLAN

        lifecycle.verify(verification_result=True)
        assert lifecycle.get_state() == LifecycleState.VERIFY

        lifecycle.decompose(["step1", "step2"])
        assert lifecycle.get_state() == LifecycleState.DECOMPOSE

        lifecycle.execute({"status": "success"})
        assert lifecycle.get_state() == LifecycleState.EXECUTE

        lifecycle.complete()
        assert lifecycle.get_state() == LifecycleState.COMPLETED

        # Should have 5 transitions (plan is a transition from initial)
        assert len(lifecycle.history) == 4

    def test_flow_with_verification_failure(self):
        """Test lifecycle with verification failure."""
        lifecycle = Lifecycle()

        lifecycle.plan({"goal": "deploy"})
        lifecycle.verify(verification_result=False, error="invalid")

        # Should return to PLAN
        assert lifecycle.get_state() == LifecycleState.PLAN

    def test_flow_with_execution_failure_and_retry(self):
        """Test lifecycle with execution failure and retry."""
        lifecycle = Lifecycle()

        # First attempt
        lifecycle.plan({"attempt": 1})
        lifecycle.verify(verification_result=True)
        lifecycle.decompose(["step1"])
        lifecycle.execute({"attempt": 1})
        lifecycle.fail(error="timeout")

        assert lifecycle.get_state() == LifecycleState.FAILED

        # Retry
        lifecycle.retry()
        assert lifecycle.get_state() == LifecycleState.PLAN

        # Second attempt
        lifecycle.plan({"attempt": 2})
        lifecycle.verify(verification_result=True)
        lifecycle.decompose(["step1"])
        lifecycle.execute({"attempt": 2})
        lifecycle.complete()

        assert lifecycle.get_state() == LifecycleState.COMPLETED


class TestLifecycleCallbacks:
    """Test callback registration and triggering."""

    def test_register_callback(self):
        """Test registering callback for state."""
        lifecycle = Lifecycle(initial_state=LifecycleState.PLAN)
        called = []

        def callback(lc):
            called.append(lc.get_state())

        lifecycle.register_callback(LifecycleState.VERIFY, callback)
        lifecycle.transition(LifecycleState.VERIFY)

        assert LifecycleState.VERIFY in called

    def test_multiple_callbacks(self):
        """Test multiple callbacks for same state."""
        lifecycle = Lifecycle(initial_state=LifecycleState.PLAN)
        call_count = []

        def callback1(lc):
            call_count.append(1)

        def callback2(lc):
            call_count.append(2)

        lifecycle.register_callback(LifecycleState.VERIFY, callback1)
        lifecycle.register_callback(LifecycleState.VERIFY, callback2)
        lifecycle.transition(LifecycleState.VERIFY)

        assert len(call_count) == 2
        assert 1 in call_count
        assert 2 in call_count

    def test_callback_receives_lifecycle(self):
        """Test callback receives lifecycle instance."""
        lifecycle = Lifecycle(initial_state=LifecycleState.PLAN)
        received_lifecycle = []

        def callback(lc):
            received_lifecycle.append(lc)

        lifecycle.register_callback(LifecycleState.VERIFY, callback)
        lifecycle.transition(LifecycleState.VERIFY)

        assert received_lifecycle[0] is lifecycle


class TestLifecycleDataManagement:
    """Test state data storage and retrieval."""

    def test_get_state_data_empty(self):
        """Test get_state_data() returns None for unset state."""
        lifecycle = Lifecycle()

        data = lifecycle.get_state_data(LifecycleState.EXECUTE)

        assert data is None

    def test_get_state_data_after_setting(self):
        """Test get_state_data() retrieves stored data."""
        lifecycle = Lifecycle()

        lifecycle.plan({"task": "test"})
        data = lifecycle.get_state_data(LifecycleState.PLAN)

        assert data == {"task": "test"}

    def test_state_data_persists_across_transitions(self):
        """Test state data persists after transitioning away."""
        lifecycle = Lifecycle()

        lifecycle.plan({"task": "test"})
        lifecycle.verify(verification_result=True)

        # Should still have PLAN data
        plan_data = lifecycle.get_state_data(LifecycleState.PLAN)
        assert plan_data == {"task": "test"}


class TestLifecycleHistory:
    """Test transition history tracking."""

    def test_get_transition_history_empty(self):
        """Test history is empty initially."""
        lifecycle = Lifecycle()

        history = lifecycle.get_transition_history()

        assert len(history) == 0

    def test_get_transition_history_returns_copy(self):
        """Test history returns copy (not original)."""
        lifecycle = Lifecycle()
        lifecycle.plan()

        history1 = lifecycle.get_transition_history()
        history2 = lifecycle.get_transition_history()

        assert history1 is not history2

    def test_history_records_timestamps(self):
        """Test transitions include timestamps."""
        lifecycle = Lifecycle()

        lifecycle.plan()
        lifecycle.verify(verification_result=True)

        history = lifecycle.get_transition_history()
        assert all(hasattr(t, "timestamp") for t in history)

    def test_get_current_phase_duration(self):
        """Test getting duration of current phase."""
        lifecycle = Lifecycle()

        # Transition to VERIFY to create a history entry
        lifecycle.transition(LifecycleState.VERIFY)
        duration = lifecycle.get_current_phase_duration()

        assert duration is not None
        assert duration >= 0

    def test_get_current_phase_duration_no_history(self):
        """Test duration returns None with no transitions."""
        lifecycle = Lifecycle()

        duration = lifecycle.get_current_phase_duration()

        assert duration is None


class TestRunFullLifecycle:
    """Test run_full_lifecycle helper function."""

    def test_successful_full_lifecycle(self):
        """Test run_full_lifecycle with successful execution."""
        def plan():
            return {"task": "build"}

        def verify(plan):
            return True

        def decompose(plan):
            return ["step1", "step2"]

        def execute(units):
            return {"result": "success"}

        lifecycle = run_full_lifecycle(plan, verify, decompose, execute)

        assert lifecycle.get_state() == LifecycleState.COMPLETED

    def test_full_lifecycle_with_failed_verification(self):
        """Test run_full_lifecycle with failed verification."""
        def plan():
            return {"task": "invalid"}

        def verify(plan):
            return False

        def decompose(plan):
            return []

        def execute(units):
            return {}

        lifecycle = run_full_lifecycle(plan, verify, decompose, execute)

        assert lifecycle.get_state() == LifecycleState.FAILED

    def test_full_lifecycle_with_execution_error(self):
        """Test run_full_lifecycle with execution error."""
        def plan():
            return {"task": "build"}

        def verify(plan):
            return True

        def decompose(plan):
            return ["step1"]

        def execute(units):
            raise RuntimeError("Execution failed")

        lifecycle = run_full_lifecycle(plan, verify, decompose, execute)

        assert lifecycle.get_state() == LifecycleState.FAILED


class TestLifecycleRepresentation:
    """Test string representation."""

    def test_repr(self):
        """Test __repr__() includes state and transition count."""
        lifecycle = Lifecycle()
        lifecycle.plan()
        lifecycle.verify(verification_result=True)

        repr_str = repr(lifecycle)

        assert "VERIFY" in repr_str
        assert "transitions=" in repr_str
