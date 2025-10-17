"""State manager interface - DIP: Core depends on abstraction.

This interface defines the contract for managing world state during
task execution, including persistence and state transitions.

Clean Architecture: Interface layer (abstraction for use cases)
SOLID: ISP (narrow interface), DIP (depend on abstraction)
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from src.entity.state import WorldState


class IStateManager(ABC):
    """Interface for world state management.
    
    Implementations manage state persistence, transitions, and validation
    during task execution.
    
    Example:
        >>> manager = StateManagerUseCase()
        >>> state = manager.get_current_state()
        >>> manager.update_state({"file_created": True})
        >>> manager.save_state()
    """
    
    @abstractmethod
    def get_current_state(self) -> WorldState:
        """Get current world state.
        
        Returns:
            Current WorldState
        
        Example:
            >>> state = manager.get_current_state()
            >>> state.get_fact("api_deployed")
            True
        """
        pass
    
    @abstractmethod
    def update_state(self, effects: Dict[str, Any]) -> WorldState:
        """Update current state with effects.
        
        Args:
            effects: Dictionary of state changes
        
        Returns:
            Updated WorldState
        
        Example:
            >>> new_state = manager.update_state({"file_created": True})
            >>> new_state.get_fact("file_created")
            True
        """
        pass
    
    @abstractmethod
    def check_preconditions(self, preconditions: Dict[str, Any]) -> bool:
        """Check if current state satisfies preconditions.
        
        Args:
            preconditions: Dictionary of required facts
        
        Returns:
            True if all preconditions satisfied, False otherwise
        
        Example:
            >>> manager.check_preconditions({"file_exists": True})
            True
        """
        pass
    
    @abstractmethod
    def save_state(self, path: Optional[str] = None) -> None:
        """Save current state to persistent storage.
        
        Args:
            path: Optional path to save state (default: configured path)
        
        Example:
            >>> manager.save_state("state.json")
        """
        pass
    
    @abstractmethod
    def load_state(self, path: Optional[str] = None) -> WorldState:
        """Load state from persistent storage.
        
        Args:
            path: Optional path to load state from (default: configured path)
        
        Returns:
            Loaded WorldState
        
        Example:
            >>> state = manager.load_state("state.json")
        """
        pass
    
    @abstractmethod
    def reset_state(self) -> WorldState:
        """Reset state to initial/empty state.
        
        Returns:
            New empty WorldState
        
        Example:
            >>> state = manager.reset_state()
            >>> len(state.facts)
            0
        """
        pass
    
    @abstractmethod
    def get_state_history(self) -> list:
        """Get history of state transitions.
        
        Returns:
            List of historical states
        
        Example:
            >>> history = manager.get_state_history()
            >>> len(history)
            5
        """
        pass

