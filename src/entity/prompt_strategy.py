"""
Prompt Strategy Entity - Core domain model for structured prompts.

This entity represents a validated prompt strategy following either:
- 4-Sentence Framework (Persona, Goal, Task, Context)
- ROLE Model (Role, Objective, Logistics, Expectations)

Integration with agentic-prompt-strategy-framework for quality validation.
Clean Architecture: Entity layer (domain model).
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone


@dataclass
class PromptStrategy:
    """
    Core prompt strategy entity following structured frameworks.
    
    Attributes:
        persona: Agent role and expertise level (WHO)
        goal: Measurable outcome to achieve (WHAT)
        task: Concrete action to perform (HOW)
        context: Background, constraints, dependencies (WHY/WHEN/WHERE)
        
        agent_type: Agent role identifier (e.g., 'software-architect')
        domain: Domain classification (e.g., 'frontend', 'backend', 'testing')
        iteration: Version/iteration number for continuous improvement
        quality_score: Validation score (0-100)
        
        validation_passed: Whether validation checks passed
        validation_suggestions: List of improvement suggestions
        metadata: Additional metadata for tracking
    """
    
    # Core 4-Sentence Framework fields
    persona: str
    goal: str
    task: str
    context: str
    
    # Metadata
    agent_type: Optional[str] = None
    domain: Optional[str] = None
    iteration: int = 1
    quality_score: Optional[float] = None
    
    # Validation results
    validation_passed: bool = False
    validation_suggestions: List[str] = field(default_factory=list)
    
    # Additional metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: Optional[str] = None
    
    def __post_init__(self):
        """Initialize created_at timestamp if not provided."""
        if self.created_at is None:
            self.created_at = datetime.now(timezone.utc).isoformat()
    
    def to_system_prompt(self, include_ultrathink: bool = False) -> str:
        """
        Convert to LLM system prompt format.
        
        Args:
            include_ultrathink: Whether to include ULTRATHINK instructions
            
        Returns:
            Formatted system prompt string
        """
        base_prompt = f"""You are a {self.persona}.

Goal: {self.goal}

Task: {self.task}

Context: {self.context}"""
        
        if include_ultrathink:
            ultrathink_section = """

ULTRATHINK MODE: You MUST think step-by-step through problems before answering.
- Use <think></think> tags to show your reasoning process
- Break down complex problems into smaller steps
- Analyze multiple approaches before selecting the best one
- Verify your logic and check for errors
- Be thorough and rigorous in your analysis"""
            base_prompt += ultrathink_section
        
        return base_prompt
    
    def to_user_prompt(self) -> str:
        """
        Convert to LLM user prompt format.
        
        Returns:
            Formatted user prompt string
        """
        return f"""Task: {self.task}

Context: {self.context}

Please complete this task according to the goal: {self.goal}"""
    
    def to_markdown(self) -> str:
        """
        Convert to markdown format for validation/storage.
        
        Returns:
            Markdown-formatted prompt strategy
        """
        md = f"""# Prompt Strategy: {self.agent_type or 'Unknown'}

**Date:** {self.created_at or 'N/A'}
**Domain:** {self.domain or 'general'}
**Iteration:** {self.iteration}
**Quality Score:** {self.quality_score or 'Not validated'}

---

## Persona
{self.persona}

---

## Goal
{self.goal}

---

## Task
{self.task}

---

## Context
{self.context}

---
"""
        
        if self.validation_suggestions:
            md += "\n## Validation Suggestions\n\n"
            for suggestion in self.validation_suggestions:
                md += f"- {suggestion}\n"
        
        return md
    
    def update_validation(
        self,
        score: float,
        passed: bool,
        suggestions: List[str]
    ) -> None:
        """
        Update validation results.
        
        Args:
            score: Quality score (0-100)
            passed: Whether validation passed
            suggestions: List of improvement suggestions
        """
        self.quality_score = score
        self.validation_passed = passed
        self.validation_suggestions = suggestions
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary for serialization.
        
        Returns:
            Dictionary representation
        """
        return {
            "persona": self.persona,
            "goal": self.goal,
            "task": self.task,
            "context": self.context,
            "agent_type": self.agent_type,
            "domain": self.domain,
            "iteration": self.iteration,
            "quality_score": self.quality_score,
            "validation_passed": self.validation_passed,
            "validation_suggestions": self.validation_suggestions,
            "metadata": self.metadata,
            "created_at": self.created_at
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PromptStrategy':
        """
        Create from dictionary.
        
        Args:
            data: Dictionary with prompt strategy data
            
        Returns:
            PromptStrategy instance
        """
        return cls(
            persona=data["persona"],
            goal=data["goal"],
            task=data["task"],
            context=data["context"],
            agent_type=data.get("agent_type"),
            domain=data.get("domain"),
            iteration=data.get("iteration", 1),
            quality_score=data.get("quality_score"),
            validation_passed=data.get("validation_passed", False),
            validation_suggestions=data.get("validation_suggestions", []),
            metadata=data.get("metadata", {}),
            created_at=data.get("created_at")
        )

