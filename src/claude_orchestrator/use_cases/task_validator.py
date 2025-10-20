"""TaskValidator - Validation and filtering for generated tasks.

Filters out invalid, duplicate, or dangerous tasks.
Ensures all tasks have clear success criteria.

Clean Architecture: Use Case layer
SOLID: SRP - Single responsibility for task validation
"""
from __future__ import annotations

import logging
import re
from typing import List, Set, Optional
from dataclasses import dataclass

from src.claude_orchestrator.entities.generated_task import GeneratedTask

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of task validation."""
    is_valid: bool
    reasons: List[str]  # Reasons for rejection if invalid


class TaskValidator:
    """
    Validates and filters generated tasks.
    
    Validation rules:
    1. Must have non-empty instruction
    2. Must have clear success criteria (steps or acceptance criteria)
    3. No dangerous operations (rm -rf, DROP TABLE, etc.)
    4. No duplicates (similar instructions)
    5. Reasonable estimated time (5-240 minutes)
    
    Usage:
        validator = TaskValidator()
        valid_tasks = validator.filter_valid(tasks)
    """
    
    # Dangerous patterns to reject
    DANGEROUS_PATTERNS = [
        r'\brm\s+-rf\b',
        r'\bDROP\s+TABLE\b',
        r'\bDROP\s+DATABASE\b',
        r'\bDELETE\s+FROM\b.*\bWHERE\s+1\s*=\s*1\b',
        r'\bsudo\s+rm\b',
        r'\b--force\b.*\bdelete\b',
        r'\bgit\s+push\s+--force\b',
        r'\bformat\s+c:\b',
    ]
    
    def __init__(
        self,
        min_instruction_length: int = 20,
        max_instruction_length: int = 5000,
        min_estimated_minutes: int = 5,
        max_estimated_minutes: int = 240,
    ):
        """
        Initialize task validator.
        
        Args:
            min_instruction_length: Minimum instruction length
            max_instruction_length: Maximum instruction length
            min_estimated_minutes: Minimum estimated time
            max_estimated_minutes: Maximum estimated time
        """
        self.min_instruction_length = min_instruction_length
        self.max_instruction_length = max_instruction_length
        self.min_estimated_minutes = min_estimated_minutes
        self.max_estimated_minutes = max_estimated_minutes
    
    def validate(self, task: GeneratedTask) -> ValidationResult:
        """
        Validate a single task.
        
        Args:
            task: GeneratedTask to validate
            
        Returns:
            ValidationResult with is_valid and reasons
        """
        reasons = []
        
        # Check instruction length
        if not task.instruction or len(task.instruction.strip()) < self.min_instruction_length:
            reasons.append(f"Instruction too short (min {self.min_instruction_length} chars)")
        
        if task.instruction and len(task.instruction) > self.max_instruction_length:
            reasons.append(f"Instruction too long (max {self.max_instruction_length} chars)")
        
        # Check for success criteria (steps or acceptance criteria)
        if task.instruction:
            has_steps = bool(re.search(r'(steps?|procedure|how to):', task.instruction, re.IGNORECASE))
            has_numbered = bool(re.search(r'\n\s*\d+\.', task.instruction))
            has_criteria = bool(re.search(r'(success|acceptance|verify|test):', task.instruction, re.IGNORECASE))
            
            if not (has_steps or has_numbered or has_criteria):
                reasons.append("Missing clear success criteria or steps")
        
        # Check for dangerous patterns
        if task.instruction:
            for pattern in self.DANGEROUS_PATTERNS:
                if re.search(pattern, task.instruction, re.IGNORECASE):
                    reasons.append(f"Contains dangerous pattern: {pattern}")
                    break
        
        # Check estimated time
        if task.estimated_minutes < self.min_estimated_minutes:
            reasons.append(f"Estimated time too short (min {self.min_estimated_minutes} min)")
        
        if task.estimated_minutes > self.max_estimated_minutes:
            reasons.append(f"Estimated time too long (max {self.max_estimated_minutes} min)")
        
        # Check for empty rationale
        if not task.rationale or len(task.rationale.strip()) < 10:
            reasons.append("Missing or insufficient rationale")
        
        is_valid = len(reasons) == 0
        return ValidationResult(is_valid=is_valid, reasons=reasons)
    
    def filter_valid(self, tasks: List[GeneratedTask]) -> List[GeneratedTask]:
        """
        Filter list to only valid tasks.
        
        Args:
            tasks: List of GeneratedTask objects
            
        Returns:
            List of valid tasks
        """
        valid = []
        for task in tasks:
            result = self.validate(task)
            if result.is_valid:
                valid.append(task)
            else:
                logger.warning(f"Task {task.id} rejected: {', '.join(result.reasons)}")
        
        return valid
    
    def deduplicate(
        self,
        tasks: List[GeneratedTask],
        similarity_threshold: float = 0.8,
    ) -> List[GeneratedTask]:
        """
        Remove duplicate tasks based on instruction similarity.
        
        Args:
            tasks: List of GeneratedTask objects
            similarity_threshold: Similarity threshold (0-1)
            
        Returns:
            Deduplicated list of tasks
        """
        if not tasks:
            return []
        
        # Simple deduplication: exact match on normalized instruction
        seen: Set[str] = set()
        unique = []
        
        for task in tasks:
            # Normalize instruction
            normalized = self._normalize_instruction(task.instruction)
            
            if normalized not in seen:
                seen.add(normalized)
                unique.append(task)
            else:
                logger.info(f"Task {task.id} is duplicate, skipping")
        
        return unique
    
    def _normalize_instruction(self, instruction: str) -> str:
        """Normalize instruction for deduplication."""
        # Lowercase, remove extra whitespace, remove punctuation
        normalized = instruction.lower()
        normalized = re.sub(r'\s+', ' ', normalized)
        normalized = re.sub(r'[^\w\s]', '', normalized)
        return normalized.strip()
    
    def filter_and_deduplicate(
        self,
        tasks: List[GeneratedTask],
        similarity_threshold: float = 0.8,
    ) -> List[GeneratedTask]:
        """
        Apply both validation and deduplication.
        
        Args:
            tasks: List of GeneratedTask objects
            similarity_threshold: Similarity threshold for deduplication
            
        Returns:
            Filtered and deduplicated list of tasks
        """
        # First validate
        valid = self.filter_valid(tasks)
        
        # Then deduplicate
        unique = self.deduplicate(valid, similarity_threshold)
        
        logger.info(f"Task filtering: {len(tasks)} → {len(valid)} valid → {len(unique)} unique")
        
        return unique

