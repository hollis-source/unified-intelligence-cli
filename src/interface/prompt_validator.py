"""
Prompt Validator Interface - Contract for prompt quality validation.

Defines the interface for validating prompt strategies against quality standards.
Follows Dependency Inversion Principle (DIP) - high-level modules depend on abstraction.

Clean Architecture: Interface layer (contracts).
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


@dataclass
class ValidationChecks:
    """
    Detailed validation check results.
    
    Attributes:
        four_sentence_present: Has all 4-Sentence Framework sections
        role_present: Has all ROLE Model sections
        specificity: Specificity score (0-100)
        clarity: Clarity score (0-100)
        completeness: Has complete structure (≥50 words, headers, framework)
    """
    four_sentence_present: bool
    role_present: bool
    specificity: float
    clarity: float
    completeness: bool
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "four_sentence_present": self.four_sentence_present,
            "role_present": self.role_present,
            "specificity": self.specificity,
            "clarity": self.clarity,
            "completeness": self.completeness
        }


@dataclass
class ValidationResult:
    """
    Result of prompt validation.
    
    Attributes:
        score: Overall quality score (0-100)
        passed: Whether validation passed minimum thresholds
        specificity: Specificity score (0-100)
        clarity: Clarity score (0-100)
        completeness: Whether structure is complete
        suggestions: List of improvement suggestions
        checks: Detailed check results
        metadata: Additional validation metadata
    """
    score: float
    passed: bool
    specificity: float
    clarity: float
    completeness: bool
    suggestions: List[str] = field(default_factory=list)
    checks: Optional[ValidationChecks] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "score": self.score,
            "passed": self.passed,
            "specificity": self.specificity,
            "clarity": self.clarity,
            "completeness": self.completeness,
            "suggestions": self.suggestions,
            "checks": self.checks.to_dict() if self.checks else None,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ValidationResult':
        """Create from dictionary."""
        checks_data = data.get("checks")
        checks = None
        if checks_data:
            checks = ValidationChecks(**checks_data)
        
        return cls(
            score=data["score"],
            passed=data["passed"],
            specificity=data["specificity"],
            clarity=data["clarity"],
            completeness=data["completeness"],
            suggestions=data.get("suggestions", []),
            checks=checks,
            metadata=data.get("metadata", {})
        )


class IPromptValidator(ABC):
    """
    Interface for prompt validation.
    
    Implementations validate prompts against quality standards:
    - Framework compliance (4-Sentence or ROLE)
    - Specificity (file paths, code examples, numeric constraints)
    - Clarity (avoid ambiguous language)
    - Completeness (structure, word count)
    
    DIP: High-level modules (LLMAgentExecutor) depend on this abstraction,
    not concrete implementations (PromptStrategyValidator).
    """
    
    @abstractmethod
    def validate(self, prompt_text: str) -> ValidationResult:
        """
        Validate raw prompt text.
        
        Args:
            prompt_text: Markdown-formatted prompt text
            
        Returns:
            ValidationResult with score and suggestions
        """
        pass
    
    @abstractmethod
    def validate_strategy(self, strategy: 'PromptStrategy') -> ValidationResult:
        """
        Validate a PromptStrategy entity.
        
        Args:
            strategy: PromptStrategy entity to validate
            
        Returns:
            ValidationResult with score and suggestions
        """
        pass
    
    @abstractmethod
    def get_min_score(self) -> float:
        """
        Get minimum acceptable quality score.
        
        Returns:
            Minimum score threshold (0-100)
        """
        pass
    
    @abstractmethod
    def set_min_score(self, score: float) -> None:
        """
        Set minimum acceptable quality score.
        
        Args:
            score: Minimum score threshold (0-100)
        """
        pass


class IPromptEnhancer(ABC):
    """
    Interface for prompt enhancement/improvement.
    
    Optional interface for implementations that can suggest
    or automatically apply improvements to prompts.
    """
    
    @abstractmethod
    def enhance(
        self,
        prompt_text: str,
        target_score: float = 80.0
    ) -> str:
        """
        Enhance prompt to reach target quality score.
        
        Args:
            prompt_text: Original prompt text
            target_score: Target quality score (0-100)
            
        Returns:
            Enhanced prompt text
        """
        pass
    
    @abstractmethod
    def suggest_improvements(
        self,
        validation_result: ValidationResult
    ) -> List[str]:
        """
        Generate specific improvement suggestions.
        
        Args:
            validation_result: Validation result to analyze
            
        Returns:
            List of actionable improvement suggestions
        """
        pass

