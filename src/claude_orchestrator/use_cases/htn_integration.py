"""HTN Integration - Feed generated tasks into HTN decomposer.

Integrates autonomous task generation with hierarchical task network planning.

Clean Architecture: Use Case layer
SOLID: SRP - Single responsibility for HTN integration
"""
from __future__ import annotations

import logging
from typing import List, Optional, Any

from src.claude_orchestrator.entities.generated_task import GeneratedTask

logger = logging.getLogger(__name__)


class HTNIntegration:
    """
    Integrates generated tasks with HTN decomposer.
    
    Converts GeneratedTask objects into HTN-compatible format
    and feeds them to the decomposer for hierarchical planning.
    
    Usage:
        htn = HTNIntegration(decomposer=htn_decomposer)
        plan = htn.decompose_tasks(tasks)
    """
    
    def __init__(self, decomposer: Optional[Any] = None):
        """
        Initialize HTN integration.
        
        Args:
            decomposer: HTN decomposer instance (optional)
        """
        self.decomposer = decomposer
    
    def decompose_tasks(
        self,
        tasks: List[GeneratedTask],
        max_depth: int = 3,
    ) -> List[Dict[str, Any]]:
        """
        Decompose tasks into hierarchical plan.
        
        Args:
            tasks: List of GeneratedTask objects
            max_depth: Maximum decomposition depth
            
        Returns:
            List of decomposed task dictionaries
        """
        if not self.decomposer:
            logger.warning("No HTN decomposer configured, returning tasks as-is")
            return [self._task_to_dict(t) for t in tasks]
        
        # Convert tasks to HTN format
        htn_tasks = [self._convert_to_htn_format(t) for t in tasks]
        
        # Decompose using HTN decomposer
        try:
            plan = self.decomposer.decompose(htn_tasks, max_depth=max_depth)
            return plan
        except Exception as e:
            logger.error(f"HTN decomposition failed: {e}")
            return [self._task_to_dict(t) for t in tasks]
    
    def _convert_to_htn_format(self, task: GeneratedTask) -> Dict[str, Any]:
        """
        Convert GeneratedTask to HTN-compatible format.
        
        HTN format (example):
        {
            "id": "task-1",
            "name": "Improve coverage",
            "type": "compound",  # or "primitive"
            "preconditions": [],
            "effects": [],
            "subtasks": [],
            "estimated_cost": 60,
        }
        """
        # Determine if task is compound (can be decomposed) or primitive
        is_compound = self._is_compound_task(task)
        
        htn_task = {
            "id": task.id,
            "name": task.instruction[:100],  # Truncate for readability
            "type": "compound" if is_compound else "primitive",
            "preconditions": self._extract_preconditions(task),
            "effects": self._extract_effects(task),
            "subtasks": [],  # Will be filled by decomposer
            "estimated_cost": task.estimated_minutes,
            "priority": task.priority,
            "goal_id": task.goal_id,
        }
        
        return htn_task
    
    def _is_compound_task(self, task: GeneratedTask) -> bool:
        """Determine if task can be decomposed into subtasks."""
        # Heuristic: tasks with "Steps:" or numbered lists are compound
        instruction = task.instruction.lower()
        
        has_steps = "steps:" in instruction or "procedure:" in instruction
        has_numbered = bool([line for line in task.instruction.split('\n') if line.strip().startswith(('1.', '2.', '3.'))])
        
        return has_steps or has_numbered or task.complexity == "high"
    
    def _extract_preconditions(self, task: GeneratedTask) -> List[str]:
        """Extract preconditions from task instruction."""
        # Simple heuristic: look for "requires", "needs", "must have"
        preconditions = []
        
        for line in task.instruction.split('\n'):
            line_lower = line.lower()
            if any(kw in line_lower for kw in ['require', 'need', 'must have', 'prerequisite']):
                preconditions.append(line.strip())
        
        return preconditions
    
    def _extract_effects(self, task: GeneratedTask) -> List[str]:
        """Extract expected effects from task instruction."""
        # Simple heuristic: look for "will", "should", "expected"
        effects = []
        
        for line in task.instruction.split('\n'):
            line_lower = line.lower()
            if any(kw in line_lower for kw in ['will', 'should', 'expected', 'result', 'outcome']):
                effects.append(line.strip())
        
        # Add from rationale
        if task.rationale:
            effects.append(task.rationale)
        
        return effects
    
    def _task_to_dict(self, task: GeneratedTask) -> Dict[str, Any]:
        """Convert GeneratedTask to simple dictionary."""
        return {
            "id": task.id,
            "instruction": task.instruction,
            "rationale": task.rationale,
            "goal_id": task.goal_id,
            "estimated_minutes": task.estimated_minutes,
            "priority": task.priority,
            "complexity": task.complexity,
        }

