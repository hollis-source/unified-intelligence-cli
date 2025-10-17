"""Goal decomposer use case - LLM-driven goal → HTN conversion.

Migrated from: src/project_builder/goal_decomposer/decomposer.py
Enhanced with: Better error handling, validation, context support

Clean Architecture: Use case layer (business logic)
SOLID: SRP (single responsibility), DIP (depends on ITextGenerator)
"""

import json
import re
import logging
from dataclasses import dataclass
from typing import Optional, Dict, Any

from src.interface.goal_decomposer import IGoalDecomposer
from src.interface.llm_provider import ITextGenerator, LLMConfig
from src.entity.htn import HTNNode


@dataclass
class GoalDecomposerUseCase(IGoalDecomposer):
    """LLM-driven goal decomposition use case.
    
    Uses LLM to convert natural language goals into structured HTN
    with automatic retry logic and validation.
    
    Attributes:
        llm_provider: LLM provider for text generation
        max_retries: Maximum retry attempts (default: 3)
        logger: Optional logger for debugging
    
    Example:
        >>> from src.factories.provider_factory import ProviderFactory
        >>> provider = ProviderFactory.create_provider("auto")
        >>> decomposer = GoalDecomposerUseCase(llm_provider=provider)
        >>> htn = await decomposer.decompose_goal("Build REST API")
    """
    
    llm_provider: ITextGenerator
    max_retries: int = 3
    logger: Optional[logging.Logger] = None
    
    def __post_init__(self):
        """Initialize logger if not provided."""
        if self.logger is None:
            self.logger = logging.getLogger(__name__)
    
    async def decompose_goal(
        self,
        goal: str,
        context: Optional[Dict[str, Any]] = None
    ) -> HTNNode:
        """Decompose goal using LLM with retry logic.
        
        Implements retry logic with temperature adjustment:
        - Attempt 1: temperature=0.4 (balanced)
        - Attempt 2: temperature=0.3 (more deterministic)
        - Attempt 3: temperature=0.2 (most deterministic)
        """
        temperature = 0.4
        last_error: Optional[Exception] = None
        
        for attempt in range(1, self.max_retries + 1):
            try:
                self.logger.info(f"Goal decomposition attempt {attempt}/{self.max_retries}")
                
                # Build prompt with context
                prompt = self._build_prompt(goal, context, attempt)
                
                # Generate HTN structure via LLM
                config = LLMConfig(
                    temperature=temperature,
                    max_tokens=8192
                )
                
                response = await self.llm_provider.generate(
                    messages=[{"role": "user", "content": prompt}],
                    config=config
                )
                
                # Parse and validate
                htn_data = self._parse_json(response)
                htn_node = self._dict_to_htn(htn_data)
                self.validate_htn(htn_node)
                
                # Safety: Remove root preconditions (root has no dependencies)
                htn_node.preconditions = {}
                
                self.logger.info(f"Goal decomposed successfully: {len(htn_node.subtasks)} top-level tasks")
                return htn_node
                
            except Exception as e:
                last_error = e
                self.logger.warning(f"Attempt {attempt} failed: {e}")
                # Reduce temperature for next attempt (more deterministic)
                temperature = max(0.1, temperature - 0.1)
                continue
        
        raise ValueError(
            f"Failed to decompose goal after {self.max_retries} attempts: {last_error}"
        )
    
    def validate_htn(self, htn: HTNNode) -> bool:
        """Validate HTN structure recursively.
        
        Checks:
        - task_id is not empty
        - description is not empty
        - subtasks are valid (recursive)
        - preconditions/effects are dicts
        
        Raises:
            ValueError: If validation fails with specific error
        """
        if not htn.task_id:
            raise ValueError("HTN node missing task_id")
        
        if not htn.description:
            raise ValueError(f"HTN node '{htn.task_id}' missing description")
        
        if not isinstance(htn.preconditions, dict):
            raise ValueError(f"HTN node '{htn.task_id}' preconditions must be dict")
        
        if not isinstance(htn.effects, dict):
            raise ValueError(f"HTN node '{htn.task_id}' effects must be dict")
        
        # Validate subtasks recursively
        for i, subtask in enumerate(htn.subtasks):
            try:
                self.validate_htn(subtask)
            except ValueError as e:
                raise ValueError(f"Subtask {i} of '{htn.task_id}' invalid: {e}")
        
        return True
    
    def _build_prompt(
        self,
        goal: str,
        context: Optional[Dict[str, Any]],
        attempt: int
    ) -> str:
        """Build decomposition prompt for LLM.
        
        Includes:
        - Goal description
        - JSON structure requirements
        - Context (if provided)
        - Retry instructions (if attempt > 1)
        """
        base_prompt = f"""You are an expert planner. Convert the following goal into a Hierarchical Task Network (HTN) JSON structure.

Goal: {goal}

Required JSON structure:
{{
  "task_id": "unique_id",
  "description": "task description",
  "subtasks": [
    {{
      "task_id": "subtask1",
      "description": "subtask description",
      "preconditions": {{"key": "value"}},
      "effects": {{"key": "value"}},
      "subtasks": []
    }}
  ],
  "preconditions": {{}},
  "effects": {{}}
}}

Guidelines:
- Use descriptive task_id (e.g., "design_api", "implement_auth")
- Break down complex tasks into subtasks
- Define preconditions (what must be true before task)
- Define effects (what changes after task)
- Primitive tasks have empty subtasks array

Return ONLY valid JSON, no markdown, no comments, no explanations."""
        
        # Add retry instructions for subsequent attempts
        if attempt > 1:
            base_prompt += "\n\nCRITICAL: Previous response had errors. Return strict, valid JSON with proper structure."
        
        # Add context if provided
        if context:
            base_prompt += f"\n\nContext:\n{json.dumps(context, indent=2)}"
        
        return base_prompt
    
    def _parse_json(self, response: str) -> Dict[str, Any]:
        """Parse JSON from LLM response.
        
        Handles:
        - Markdown code blocks (```json ... ```)
        - Extra whitespace
        - Common formatting issues
        """
        # Remove markdown code blocks if present
        response = re.sub(r'```json\s*', '', response)
        response = re.sub(r'```\s*', '', response)
        
        # Remove leading/trailing whitespace
        response = response.strip()
        
        try:
            return json.loads(response)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON from LLM: {e}\nResponse: {response[:200]}...")
    
    def _dict_to_htn(self, data: Dict[str, Any]) -> HTNNode:
        """Convert dict to HTNNode recursively.
        
        Handles:
        - Nested subtasks
        - Missing optional fields
        - Type conversion
        """
        # Validate required fields
        if "task_id" not in data:
            raise ValueError("Missing required field: task_id")
        if "description" not in data:
            raise ValueError("Missing required field: description")
        
        # Convert subtasks recursively
        subtasks = [
            self._dict_to_htn(subtask)
            for subtask in data.get("subtasks", [])
        ]
        
        return HTNNode(
            task_id=data["task_id"],
            description=data["description"],
            subtasks=subtasks,
            preconditions=data.get("preconditions", {}),
            effects=data.get("effects", {}),
            metadata=data.get("metadata", {})
        )


# Convenience function for quick usage
async def decompose_goal(
    goal: str,
    llm_provider: ITextGenerator,
    context: Optional[Dict[str, Any]] = None,
    max_retries: int = 3
) -> HTNNode:
    """Convenience function for goal decomposition.
    
    Args:
        goal: Natural language goal
        llm_provider: LLM provider instance
        context: Optional context dict
        max_retries: Maximum retry attempts
    
    Returns:
        HTNNode: Decomposed task hierarchy
    
    Example:
        >>> from src.factories.provider_factory import ProviderFactory
        >>> provider = ProviderFactory.create_provider("auto")
        >>> htn = await decompose_goal("Build REST API", provider)
    """
    decomposer = GoalDecomposerUseCase(
        llm_provider=llm_provider,
        max_retries=max_retries
    )
    return await decomposer.decompose_goal(goal, context)

