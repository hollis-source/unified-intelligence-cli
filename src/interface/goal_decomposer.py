"""Goal decomposer interface - DIP: Core depends on abstraction.

This interface defines the contract for decomposing natural language goals
into structured Hierarchical Task Networks (HTN).

Clean Architecture: Interface layer (abstraction for use cases)
SOLID: ISP (narrow interface), DIP (depend on abstraction)
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from src.entity.htn import HTNNode


class IGoalDecomposer(ABC):
    """Interface for goal → HTN decomposition.
    
    Implementations use LLMs to convert natural language goals into
    structured task hierarchies with preconditions and effects.
    
    Example:
        >>> decomposer = GoalDecomposerUseCase(llm_provider=provider)
        >>> goal = "Build a REST API with authentication"
        >>> htn = await decomposer.decompose_goal(goal)
        >>> print(f"Decomposed into {len(htn.subtasks)} tasks")
    """
    
    @abstractmethod
    async def decompose_goal(
        self,
        goal: str,
        context: Optional[Dict[str, Any]] = None
    ) -> HTNNode:
        """Decompose natural language goal into HTN structure.
        
        Args:
            goal: Natural language goal description
                  Example: "Build a REST API with user authentication"
            context: Optional context for decomposition
                    - project_info: Project metadata
                    - constraints: Technical constraints
                    - preferences: User preferences
                    - existing_code: Existing codebase info
        
        Returns:
            HTNNode: Root of decomposed task hierarchy with:
                    - task_id: Unique identifier
                    - description: Task description
                    - subtasks: Child tasks (recursive)
                    - preconditions: Required state
                    - effects: State changes
        
        Raises:
            ValueError: If decomposition fails after retries
            LLMError: If LLM provider fails
        
        Example:
            >>> context = {
            ...     "project_info": {"language": "Python", "framework": "FastAPI"},
            ...     "constraints": {"max_complexity": "medium"}
            ... }
            >>> htn = await decomposer.decompose_goal(
            ...     "Build REST API",
            ...     context=context
            ... )
        """
        pass
    
    @abstractmethod
    def validate_htn(self, htn: HTNNode) -> bool:
        """Validate HTN structure.
        
        Args:
            htn: HTN node to validate
        
        Returns:
            bool: True if valid, False otherwise
        
        Raises:
            ValueError: If validation fails with details
        """
        pass

