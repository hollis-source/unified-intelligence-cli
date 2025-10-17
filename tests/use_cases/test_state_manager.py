"""Tests for state manager use case.

Tests state management, persistence, and history tracking.
"""

import pytest
import tempfile
import os
from pathlib import Path
from src.use_cases.state_manager import StateManagerUseCase
from src.entity.state import WorldState


def test_state_manager_creation():
    """Test StateManager creation."""
    manager = StateManagerUseCase()
    
    state = manager.get_current_state()
    assert isinstance(state, WorldState)
    assert len(state.facts) == 0


def test_update_state():
    """Test updating state with effects."""
    manager = StateManagerUseCase()
    
    effects = {"file_created": True, "version": "1.0.0"}
    new_state = manager.update_state(effects)
    
    assert new_state.get_fact("file_created") is True
    assert new_state.get_fact("version") == "1.0.0"
    
    # Current state updated
    current = manager.get_current_state()
    assert current.get_fact("file_created") is True


def test_check_preconditions_satisfied():
    """Test checking preconditions (satisfied)."""
    manager = StateManagerUseCase()
    manager.update_state({"file_exists": True, "version": "1.0.0"})
    
    preconditions = {"file_exists": True, "version": "1.0.0"}
    
    assert manager.check_preconditions(preconditions) is True


def test_check_preconditions_not_satisfied():
    """Test checking preconditions (not satisfied)."""
    manager = StateManagerUseCase()
    manager.update_state({"file_exists": False})
    
    preconditions = {"file_exists": True}
    
    assert manager.check_preconditions(preconditions) is False


def test_save_and_load_state():
    """Test saving and loading state."""
    with tempfile.TemporaryDirectory() as tmpdir:
        state_path = os.path.join(tmpdir, "state.json")
        
        # Create manager and update state
        manager = StateManagerUseCase(persistence_path=state_path)
        manager.update_state({"api_deployed": True, "version": "1.0.0"})
        
        # Save state
        manager.save_state()
        
        # Verify file exists
        assert Path(state_path).exists()
        
        # Create new manager and load state
        manager2 = StateManagerUseCase(persistence_path=state_path)
        loaded_state = manager2.load_state()
        
        # Verify state loaded correctly
        assert loaded_state.get_fact("api_deployed") is True
        assert loaded_state.get_fact("version") == "1.0.0"


def test_save_state_no_path():
    """Test saving state without persistence path (should skip)."""
    manager = StateManagerUseCase()  # No persistence_path
    
    # Should not raise error, just log warning
    manager.save_state()


def test_load_state_no_path():
    """Test loading state without persistence path (should raise)."""
    manager = StateManagerUseCase()  # No persistence_path
    
    with pytest.raises(ValueError, match="No persistence path configured"):
        manager.load_state()


def test_load_state_file_not_found():
    """Test loading state from non-existent file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        state_path = os.path.join(tmpdir, "nonexistent.json")
        
        manager = StateManagerUseCase(persistence_path=state_path)
        
        # Should return current state (not raise error)
        loaded_state = manager.load_state()
        assert isinstance(loaded_state, WorldState)


def test_reset_state():
    """Test resetting state."""
    manager = StateManagerUseCase()
    manager.update_state({"api_deployed": True})
    
    # Verify state has facts
    assert len(manager.get_current_state().facts) > 0
    
    # Reset state
    new_state = manager.reset_state()
    
    # Verify state is empty
    assert len(new_state.facts) == 0
    assert len(manager.get_current_state().facts) == 0


def test_state_history():
    """Test state history tracking."""
    manager = StateManagerUseCase()
    
    # Initial state in history
    assert len(manager.get_state_history()) == 1
    
    # Update state multiple times
    manager.update_state({"step1": True})
    manager.update_state({"step2": True})
    manager.update_state({"step3": True})
    
    # History should have all states
    history = manager.get_state_history()
    assert len(history) == 4  # Initial + 3 updates


def test_state_history_size_limit():
    """Test state history size limit."""
    manager = StateManagerUseCase(max_history_size=5)
    
    # Add more states than limit
    for i in range(10):
        manager.update_state({f"step{i}": True})
    
    # History should be trimmed to max size
    history = manager.get_state_history()
    assert len(history) <= 5


def test_add_resource():
    """Test adding resource."""
    manager = StateManagerUseCase()
    
    manager.add_resource("database")
    manager.add_resource("cache")
    
    assert manager.has_resource("database") is True
    assert manager.has_resource("cache") is True


def test_remove_resource():
    """Test removing resource."""
    manager = StateManagerUseCase()
    
    manager.add_resource("database")
    assert manager.has_resource("database") is True
    
    manager.remove_resource("database")
    assert manager.has_resource("database") is False


def test_get_and_set_fact():
    """Test getting and setting facts."""
    manager = StateManagerUseCase()
    
    manager.set_fact("api_deployed", True)
    manager.set_fact("version", "1.0.0")
    
    assert manager.get_fact("api_deployed") is True
    assert manager.get_fact("version") == "1.0.0"
    assert manager.get_fact("nonexistent", "default") == "default"


def test_export_state_summary():
    """Test exporting state summary."""
    manager = StateManagerUseCase()
    manager.update_state({"api_deployed": True, "version": "1.0.0"})
    manager.add_resource("database")
    
    summary = manager.export_state_summary()
    
    assert summary["total_facts"] == 2
    assert summary["total_resources"] == 1
    assert summary["history_size"] == 2  # Initial + 1 update
    assert "timestamp" in summary
    assert summary["facts"]["api_deployed"] is True
    assert "database" in summary["resources"]


def test_state_persistence_with_custom_path():
    """Test saving state with custom path."""
    with tempfile.TemporaryDirectory() as tmpdir:
        default_path = os.path.join(tmpdir, "default.json")
        custom_path = os.path.join(tmpdir, "custom.json")
        
        manager = StateManagerUseCase(persistence_path=default_path)
        manager.update_state({"api_deployed": True})
        
        # Save to custom path
        manager.save_state(custom_path)
        
        # Verify custom file exists
        assert Path(custom_path).exists()
        
        # Load from custom path
        manager2 = StateManagerUseCase()
        loaded_state = manager2.load_state(custom_path)
        
        assert loaded_state.get_fact("api_deployed") is True


def test_state_manager_with_initial_state():
    """Test creating state manager with initial state."""
    initial_state = WorldState()
    initial_state.set_fact("initial", True)
    
    manager = StateManagerUseCase(current_state=initial_state)
    
    assert manager.get_fact("initial") is True

