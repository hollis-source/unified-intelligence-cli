"""State manager use case - World state management.

Migrated from: src/project_builder/state/
Enhanced with: Better persistence, history tracking, validation

Clean Architecture: Use case layer (business logic)
SOLID: SRP (single responsibility), DIP (depends on abstractions)
"""

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime

from src.interface.state_manager import IStateManager
from src.entity.state import WorldState


@dataclass
class StateManagerUseCase(IStateManager):
    """World state manager use case.
    
    Manages world state during task execution with persistence,
    history tracking, and validation.
    
    Attributes:
        current_state: Current world state
        state_history: History of state transitions
        persistence_path: Path for state persistence
        max_history_size: Maximum history entries to keep (default: 100)
        logger: Optional logger for debugging
    
    Example:
        >>> manager = StateManagerUseCase(persistence_path="state.json")
        >>> manager.update_state({"file_created": True})
        >>> manager.save_state()
    """
    
    current_state: WorldState = field(default_factory=WorldState)
    state_history: List[WorldState] = field(default_factory=list)
    persistence_path: Optional[str] = None
    max_history_size: int = 100
    logger: Optional[logging.Logger] = None
    
    def __post_init__(self):
        """Initialize logger if not provided."""
        if self.logger is None:
            self.logger = logging.getLogger(__name__)
        
        # Add initial state to history
        self._add_to_history(self.current_state)
    
    def get_current_state(self) -> WorldState:
        """Get current world state."""
        return self.current_state
    
    def update_state(self, effects: Dict[str, Any]) -> WorldState:
        """Update current state with effects.
        
        Creates new state with effects applied and adds to history.
        """
        self.logger.debug(f"Updating state with effects: {effects}")
        
        # Apply effects to create new state
        new_state = self.current_state.apply_effects(effects)
        
        # Update current state
        self.current_state = new_state
        
        # Add to history
        self._add_to_history(new_state)
        
        self.logger.info(f"State updated: {len(new_state.facts)} facts")
        
        return new_state
    
    def check_preconditions(self, preconditions: Dict[str, Any]) -> bool:
        """Check if current state satisfies preconditions."""
        satisfied = self.current_state.satisfies(preconditions)
        
        if satisfied:
            self.logger.debug(f"Preconditions satisfied: {preconditions}")
        else:
            self.logger.warning(f"Preconditions NOT satisfied: {preconditions}")
            self._log_missing_preconditions(preconditions)
        
        return satisfied
    
    def save_state(self, path: Optional[str] = None) -> None:
        """Save current state to persistent storage.
        
        Saves state as JSON file.
        """
        save_path = path or self.persistence_path
        
        if not save_path:
            self.logger.warning("No persistence path configured, skipping save")
            return
        
        try:
            # Ensure directory exists
            Path(save_path).parent.mkdir(parents=True, exist_ok=True)
            
            # Save state as JSON
            with open(save_path, 'w') as f:
                f.write(self.current_state.to_json())
            
            self.logger.info(f"State saved to {save_path}")
            
        except Exception as e:
            self.logger.error(f"Failed to save state: {e}")
            raise
    
    def load_state(self, path: Optional[str] = None) -> WorldState:
        """Load state from persistent storage.
        
        Loads state from JSON file.
        """
        load_path = path or self.persistence_path
        
        if not load_path:
            raise ValueError("No persistence path configured")
        
        try:
            with open(load_path, 'r') as f:
                json_str = f.read()
            
            state = WorldState.from_json(json_str)
            
            # Update current state
            self.current_state = state
            
            # Add to history
            self._add_to_history(state)
            
            self.logger.info(f"State loaded from {load_path}")
            
            return state
            
        except FileNotFoundError:
            self.logger.warning(f"State file not found: {load_path}")
            return self.current_state
        except Exception as e:
            self.logger.error(f"Failed to load state: {e}")
            raise
    
    def reset_state(self) -> WorldState:
        """Reset state to initial/empty state."""
        self.logger.info("Resetting state")
        
        new_state = WorldState()
        self.current_state = new_state
        
        # Clear history and add new state
        self.state_history.clear()
        self._add_to_history(new_state)
        
        return new_state
    
    def get_state_history(self) -> List[WorldState]:
        """Get history of state transitions."""
        return self.state_history.copy()
    
    # Additional helper methods
    
    def add_resource(self, resource: str) -> None:
        """Add a resource to current state.
        
        Args:
            resource: Resource name
        
        Example:
            >>> manager.add_resource("database")
        """
        self.current_state.add_resource(resource)
        self.logger.debug(f"Added resource: {resource}")
    
    def remove_resource(self, resource: str) -> None:
        """Remove a resource from current state.
        
        Args:
            resource: Resource name
        
        Example:
            >>> manager.remove_resource("database")
        """
        self.current_state.remove_resource(resource)
        self.logger.debug(f"Removed resource: {resource}")
    
    def has_resource(self, resource: str) -> bool:
        """Check if resource is available.
        
        Args:
            resource: Resource name
        
        Returns:
            True if resource available, False otherwise
        
        Example:
            >>> manager.has_resource("database")
            True
        """
        return self.current_state.has_resource(resource)
    
    def get_fact(self, key: str, default: Any = None) -> Any:
        """Get a fact from current state.
        
        Args:
            key: Fact key
            default: Default value if key not found
        
        Returns:
            Fact value or default
        
        Example:
            >>> manager.get_fact("api_deployed", False)
            True
        """
        return self.current_state.get_fact(key, default)
    
    def set_fact(self, key: str, value: Any) -> None:
        """Set a fact in current state.
        
        Args:
            key: Fact key
            value: Fact value
        
        Example:
            >>> manager.set_fact("api_deployed", True)
        """
        self.current_state.set_fact(key, value)
        self.logger.debug(f"Set fact: {key}={value}")
    
    def export_state_summary(self) -> Dict[str, Any]:
        """Export state summary for reporting.
        
        Returns:
            Dictionary with state summary
        
        Example:
            >>> summary = manager.export_state_summary()
            >>> summary['total_facts']
            5
        """
        return {
            "total_facts": len(self.current_state.facts),
            "total_resources": len(self.current_state.resources),
            "history_size": len(self.state_history),
            "timestamp": self.current_state.timestamp.isoformat() if self.current_state.timestamp else None,
            "facts": self.current_state.facts,
            "resources": list(self.current_state.resources)
        }
    
    # Private helper methods
    
    def _add_to_history(self, state: WorldState) -> None:
        """Add state to history with size limit."""
        self.state_history.append(state)
        
        # Trim history if too large
        if len(self.state_history) > self.max_history_size:
            self.state_history = self.state_history[-self.max_history_size:]
            self.logger.debug(f"Trimmed history to {self.max_history_size} entries")
    
    def _log_missing_preconditions(self, preconditions: Dict[str, Any]) -> None:
        """Log details about missing preconditions."""
        for key, required_value in preconditions.items():
            if not self.current_state.has_fact(key):
                self.logger.warning(f"  Missing fact: {key}")
            elif self.current_state.get_fact(key) != required_value:
                actual_value = self.current_state.get_fact(key)
                self.logger.warning(
                    f"  Fact mismatch: {key} (required: {required_value}, actual: {actual_value})"
                )

