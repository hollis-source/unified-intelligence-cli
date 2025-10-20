"""Tests for WorldState entity.

Tests state representation, preconditions, effects, and serialization.
"""

import pytest
import json
from src.entity.state import WorldState


def test_world_state_creation():
    """Test WorldState creation."""
    state = WorldState()
    
    assert len(state.facts) == 0
    assert len(state.resources) == 0
    assert state.timestamp is not None


def test_set_and_get_fact():
    """Test setting and getting facts."""
    state = WorldState()
    
    state.set_fact("api_deployed", True)
    state.set_fact("version", "1.0.0")
    
    assert state.get_fact("api_deployed") is True
    assert state.get_fact("version") == "1.0.0"
    assert state.get_fact("nonexistent", "default") == "default"


def test_has_fact():
    """Test checking fact existence."""
    state = WorldState()
    
    state.set_fact("api_deployed", True)
    
    assert state.has_fact("api_deployed") is True
    assert state.has_fact("nonexistent") is False


def test_remove_fact():
    """Test removing facts."""
    state = WorldState()
    
    state.set_fact("temporary", True)
    assert state.has_fact("temporary") is True
    
    state.remove_fact("temporary")
    assert state.has_fact("temporary") is False


def test_add_and_check_resource():
    """Test adding and checking resources."""
    state = WorldState()
    
    state.add_resource("database")
    state.add_resource("cache")
    
    assert state.has_resource("database") is True
    assert state.has_resource("cache") is True
    assert state.has_resource("nonexistent") is False


def test_remove_resource():
    """Test removing resources."""
    state = WorldState()
    
    state.add_resource("database")
    assert state.has_resource("database") is True
    
    state.remove_resource("database")
    assert state.has_resource("database") is False


def test_satisfies_preconditions_success():
    """Test precondition satisfaction (success case)."""
    state = WorldState()
    state.set_fact("file_exists", True)
    state.set_fact("version", "1.0.0")
    
    preconditions = {
        "file_exists": True,
        "version": "1.0.0"
    }
    
    assert state.satisfies(preconditions) is True


def test_satisfies_preconditions_missing_fact():
    """Test precondition satisfaction (missing fact)."""
    state = WorldState()
    state.set_fact("file_exists", True)
    
    preconditions = {
        "file_exists": True,
        "database_ready": True  # Missing
    }
    
    assert state.satisfies(preconditions) is False


def test_satisfies_preconditions_wrong_value():
    """Test precondition satisfaction (wrong value)."""
    state = WorldState()
    state.set_fact("file_exists", False)
    
    preconditions = {
        "file_exists": True  # Required True, actual False
    }
    
    assert state.satisfies(preconditions) is False


def test_apply_effects():
    """Test applying effects to create new state."""
    state = WorldState()
    state.set_fact("initial", True)
    
    effects = {
        "file_created": True,
        "version": "1.0.0"
    }
    
    new_state = state.apply_effects(effects)
    
    # New state has effects
    assert new_state.get_fact("file_created") is True
    assert new_state.get_fact("version") == "1.0.0"
    
    # New state preserves original facts
    assert new_state.get_fact("initial") is True
    
    # Original state unchanged (immutable pattern)
    assert state.has_fact("file_created") is False


def test_merge_states():
    """Test merging two states."""
    state1 = WorldState()
    state1.set_fact("a", 1)
    state1.add_resource("db1")
    
    state2 = WorldState()
    state2.set_fact("b", 2)
    state2.add_resource("db2")
    
    merged = state1.merge(state2)
    
    assert merged.get_fact("a") == 1
    assert merged.get_fact("b") == 2
    assert merged.has_resource("db1") is True
    assert merged.has_resource("db2") is True


def test_merge_states_override():
    """Test merging states with overlapping facts."""
    state1 = WorldState()
    state1.set_fact("version", "1.0.0")
    
    state2 = WorldState()
    state2.set_fact("version", "2.0.0")
    
    merged = state1.merge(state2)
    
    # state2 values override state1
    assert merged.get_fact("version") == "2.0.0"


def test_to_dict():
    """Test converting state to dictionary."""
    state = WorldState()
    state.set_fact("api_deployed", True)
    state.add_resource("database")
    
    data = state.to_dict()
    
    assert data["facts"]["api_deployed"] is True
    assert "database" in data["resources"]
    assert "timestamp" in data
    assert "metadata" in data


def test_from_dict():
    """Test creating state from dictionary."""
    data = {
        "facts": {"api_deployed": True, "version": "1.0.0"},
        "resources": ["database", "cache"],
        "metadata": {"env": "production"}
    }
    
    state = WorldState.from_dict(data)
    
    assert state.get_fact("api_deployed") is True
    assert state.get_fact("version") == "1.0.0"
    assert state.has_resource("database") is True
    assert state.has_resource("cache") is True
    assert state.metadata["env"] == "production"


def test_to_json():
    """Test converting state to JSON."""
    state = WorldState()
    state.set_fact("api_deployed", True)
    state.add_resource("database")
    
    json_str = state.to_json()
    
    # Verify it's valid JSON
    data = json.loads(json_str)
    assert data["facts"]["api_deployed"] is True
    assert "database" in data["resources"]


def test_from_json():
    """Test creating state from JSON."""
    json_str = '''
    {
        "facts": {"api_deployed": true, "version": "1.0.0"},
        "resources": ["database"],
        "metadata": {}
    }
    '''
    
    state = WorldState.from_json(json_str)
    
    assert state.get_fact("api_deployed") is True
    assert state.get_fact("version") == "1.0.0"
    assert state.has_resource("database") is True


def test_round_trip_serialization():
    """Test round-trip serialization (to_json → from_json)."""
    original = WorldState()
    original.set_fact("api_deployed", True)
    original.set_fact("version", "1.0.0")
    original.add_resource("database")
    original.add_resource("cache")
    
    # Serialize
    json_str = original.to_json()
    
    # Deserialize
    restored = WorldState.from_json(json_str)
    
    # Verify all data preserved
    assert restored.get_fact("api_deployed") is True
    assert restored.get_fact("version") == "1.0.0"
    assert restored.has_resource("database") is True
    assert restored.has_resource("cache") is True


def test_repr():
    """Test string representation."""
    state = WorldState()
    state.set_fact("a", 1)
    state.set_fact("b", 2)
    state.add_resource("db")
    
    repr_str = repr(state)
    
    assert "WorldState" in repr_str
    assert "facts=2" in repr_str
    assert "resources=1" in repr_str

