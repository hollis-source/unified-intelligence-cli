import pytest
from src.dsl.entities.monad import Monad  # This will fail initially in red phase


class TestMonad:
    """Pytest tests for Monad entity.

    These tests follow TDD red phase: they should fail initially because the Monad class
    and its methods are not yet implemented. Once implemented, they will pass.

    Assumes Monad implements bind (>>), unit, and follows monad laws.
    """

    def test_monadic_bind(self):
        """Test monadic bind (>>) operation."""
        # Assume Monad has a unit method and bind
        m = Monad.unit(5)  # Wrap value in monad
        f = lambda x: Monad.unit(x * 2)  # Function returning a monad

        result = m >> f  # Bind operation
        assert result == Monad.unit(10)  # Expected result after bind

    def test_sequencing_with_effects(self):
        """Test sequencing with effects (e.g., side effects in bind chain)."""
        effects = []

        def log_and_double(x):
            effects.append(f"processing {x}")
            return Monad.unit(x * 2)

        m = Monad.unit(3)
        result = m >> log_and_double >> log_and_double

        assert result == Monad.unit(12)
        assert effects == ["processing 3", "processing 6"]  # Effects should be sequenced

    def test_error_propagation(self):
        """Test error propagation through bind."""
        def failing_func(x):
            raise ValueError("error")

        m = Monad.unit(5)
        with pytest.raises(ValueError, match="error"):
            m >> failing_func  # Should propagate the error

    def test_left_identity_law(self):
        """Test left identity monad law: unit(a) >> f == f(a)."""
        a = 5
        f = lambda x: Monad.unit(x + 1)

        left_side = Monad.unit(a) >> f
        right_side = f(a)

        assert left_side == right_side

    def test_right_identity_law(self):
        """Test right identity monad law: m >> unit == m."""
        m = Monad.unit(10)

        result = m >> Monad.unit
        assert result == m

    def test_associativity_law(self):
        """Test associativity monad law: (m >> f) >> g == m >> (lambda x: f(x) >> g)."""
        m = Monad.unit(2)
        f = lambda x: Monad.unit(x * 3)
        g = lambda x: Monad.unit(x + 4)

        left_side = (m >> f) >> g
        right_side = m >> (lambda x: f(x) >> g)

        assert left_side == right_side

    def test_bind_with_none(self):
        """Test bind with None or empty monad."""
        # Assume Monad can handle None
        m = Monad.unit(None)
        f = lambda x: Monad.unit("handled")

        result = m >> f
        assert result == Monad.unit("handled")

    def test_multiple_binds(self):
        """Test chaining multiple binds."""
        m = Monad.unit(1)
        result = m >> (lambda x: Monad.unit(x + 1)) >> (lambda x: Monad.unit(x * 2))
        assert result == Monad.unit(4)
