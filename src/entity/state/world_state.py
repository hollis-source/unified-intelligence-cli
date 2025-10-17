"""World state entity - Core domain model for state management.

Represents the current state of the world during task execution,
including all facts, resources, and conditions.

Clean Architecture: Entity layer (core domain)
SOLID: SRP (single responsibility - state representation)
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, Set
from datetime import datetime
import json


@dataclass
class WorldState:
    """Represents the current state of the world.
    
    Tracks all facts, resources, and conditions that tasks depend on
    and modify during execution.
    
    Attributes:
        facts: Dictionary of state facts (key-value pairs)
        resources: Set of available resources
        timestamp: When this state was created
        metadata: Additional metadata
    
    Example:
        >>> state = WorldState()
        >>> state.set_fact("file_exists", True)
        >>> state.add_resource("database")
        >>> state.has_fact("file_exists")
        True
    """
    
    facts: Dict[str, Any] = field(default_factory=dict)
    resources: Set[str] = field(default_factory=set)
    timestamp: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Initialize timestamp if not provided."""
        if self.timestamp is None:
            self.timestamp = datetime.now()
    
    def set_fact(self, key: str, value: Any) -> None:
        """Set a state fact.
        
        Args:
            key: Fact key
            value: Fact value
        
        Example:
            >>> state.set_fact("api_deployed", True)
            >>> state.set_fact("version", "1.0.0")
        """
        self.facts[key] = value
    
    def get_fact(self, key: str, default: Any = None) -> Any:
        """Get a state fact.
        
        Args:
            key: Fact key
            default: Default value if key not found
        
        Returns:
            Fact value or default
        
        Example:
            >>> state.get_fact("api_deployed", False)
            True
        """
        return self.facts.get(key, default)
    
    def has_fact(self, key: str) -> bool:
        """Check if a fact exists.
        
        Args:
            key: Fact key
        
        Returns:
            True if fact exists, False otherwise
        
        Example:
            >>> state.has_fact("api_deployed")
            True
        """
        return key in self.facts
    
    def remove_fact(self, key: str) -> None:
        """Remove a state fact.
        
        Args:
            key: Fact key
        
        Example:
            >>> state.remove_fact("temporary_flag")
        """
        self.facts.pop(key, None)
    
    def add_resource(self, resource: str) -> None:
        """Add an available resource.
        
        Args:
            resource: Resource name
        
        Example:
            >>> state.add_resource("database")
            >>> state.add_resource("cache")
        """
        self.resources.add(resource)
    
    def remove_resource(self, resource: str) -> None:
        """Remove an available resource.
        
        Args:
            resource: Resource name
        
        Example:
            >>> state.remove_resource("database")
        """
        self.resources.discard(resource)
    
    def has_resource(self, resource: str) -> bool:
        """Check if a resource is available.
        
        Args:
            resource: Resource name
        
        Returns:
            True if resource available, False otherwise
        
        Example:
            >>> state.has_resource("database")
            True
        """
        return resource in self.resources
    
    def satisfies(self, preconditions: Dict[str, Any]) -> bool:
        """Check if state satisfies preconditions.
        
        Args:
            preconditions: Dictionary of required facts
        
        Returns:
            True if all preconditions satisfied, False otherwise
        
        Example:
            >>> state.set_fact("file_exists", True)
            >>> state.satisfies({"file_exists": True})
            True
            >>> state.satisfies({"file_exists": False})
            False
        """
        for key, required_value in preconditions.items():
            if not self.has_fact(key):
                return False
            if self.get_fact(key) != required_value:
                return False
        return True
    
    def apply_effects(self, effects: Dict[str, Any]) -> "WorldState":
        """Apply effects to create new state.
        
        Args:
            effects: Dictionary of state changes
        
        Returns:
            New WorldState with effects applied
        
        Example:
            >>> state = WorldState()
            >>> new_state = state.apply_effects({"file_created": True})
            >>> new_state.get_fact("file_created")
            True
        """
        # Create new state (immutable pattern)
        new_state = WorldState(
            facts=self.facts.copy(),
            resources=self.resources.copy(),
            metadata=self.metadata.copy()
        )
        
        # Apply effects
        for key, value in effects.items():
            new_state.set_fact(key, value)
        
        return new_state
    
    def merge(self, other: "WorldState") -> "WorldState":
        """Merge with another state.
        
        Args:
            other: Other WorldState to merge
        
        Returns:
            New WorldState with merged facts and resources
        
        Example:
            >>> state1 = WorldState(facts={"a": 1})
            >>> state2 = WorldState(facts={"b": 2})
            >>> merged = state1.merge(state2)
            >>> merged.get_fact("a")
            1
            >>> merged.get_fact("b")
            2
        """
        merged_facts = {**self.facts, **other.facts}
        merged_resources = self.resources | other.resources
        merged_metadata = {**self.metadata, **other.metadata}
        
        return WorldState(
            facts=merged_facts,
            resources=merged_resources,
            metadata=merged_metadata
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization.
        
        Returns:
            Dictionary representation
        
        Example:
            >>> state = WorldState(facts={"a": 1})
            >>> state.to_dict()
            {'facts': {'a': 1}, 'resources': [], 'timestamp': '...', 'metadata': {}}
        """
        return {
            "facts": self.facts,
            "resources": list(self.resources),
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WorldState":
        """Create from dictionary.
        
        Args:
            data: Dictionary representation
        
        Returns:
            WorldState instance
        
        Example:
            >>> data = {'facts': {'a': 1}, 'resources': ['db']}
            >>> state = WorldState.from_dict(data)
            >>> state.get_fact('a')
            1
        """
        timestamp = None
        if data.get("timestamp"):
            timestamp = datetime.fromisoformat(data["timestamp"])
        
        return cls(
            facts=data.get("facts", {}),
            resources=set(data.get("resources", [])),
            timestamp=timestamp,
            metadata=data.get("metadata", {})
        )
    
    def to_json(self) -> str:
        """Convert to JSON string.
        
        Returns:
            JSON string representation
        
        Example:
            >>> state = WorldState(facts={"a": 1})
            >>> json_str = state.to_json()
            >>> "facts" in json_str
            True
        """
        return json.dumps(self.to_dict(), indent=2)
    
    @classmethod
    def from_json(cls, json_str: str) -> "WorldState":
        """Create from JSON string.
        
        Args:
            json_str: JSON string representation
        
        Returns:
            WorldState instance
        
        Example:
            >>> json_str = '{"facts": {"a": 1}}'
            >>> state = WorldState.from_json(json_str)
            >>> state.get_fact('a')
            1
        """
        data = json.loads(json_str)
        return cls.from_dict(data)
    
    def __repr__(self) -> str:
        """String representation."""
        return f"WorldState(facts={len(self.facts)}, resources={len(self.resources)})"

