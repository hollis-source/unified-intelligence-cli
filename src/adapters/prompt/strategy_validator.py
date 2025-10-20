"""
Prompt Strategy Validator Adapter - Integration with agentic-prompt-strategy-framework.

Wraps the validation logic from agentic-prompt-strategy-framework
to provide prompt quality validation for ATADO.

Clean Architecture: Adapter layer (external framework integration).
DIP: Implements IPromptValidator interface.
"""

import sys
import logging
from pathlib import Path
from typing import Dict, Any, List

# Configure framework path for venv integration
# The framework is a sibling directory to unified-intelligence-cli
framework_path = Path(__file__).parent.parent.parent.parent.parent / "agentic-prompt-strategy-framework"

# Add to Python path if not already present
if str(framework_path) not in sys.path:
    sys.path.insert(0, str(framework_path))

try:
    # Import validation functions from framework
    from scripts.validate_prompt import (
        extract_sections,
        has_all_sections,
        detect_specificity,
        detect_clarity,
        detect_completeness,
        compute_score,
        FOUR_SENTENCE_SECTIONS,
        ROLE_SECTIONS,
        Checks as FrameworkChecks
    )
    FRAMEWORK_AVAILABLE = True
except ImportError as e:
    logging.warning(
        f"agentic-prompt-strategy-framework not available: {e}. "
        "Prompt validation will use fallback mode."
    )
    FRAMEWORK_AVAILABLE = False

from src.interface.prompt_validator import (
    IPromptValidator,
    ValidationResult,
    ValidationChecks
)
from src.entity.prompt_strategy import PromptStrategy


class PromptStrategyValidator(IPromptValidator):
    """
    Adapter for agentic-prompt-strategy-framework validation.
    
    Validates prompts against quality standards:
    - Framework compliance (4-Sentence or ROLE)
    - Specificity ≥50% (file paths, code examples, numeric constraints)
    - Clarity ≥70% (avoid ambiguous language)
    - Completeness (≥50 words, structured, all sections present)
    
    Attributes:
        min_score: Minimum acceptable quality score (default: 60.0)
        fallback_mode: Whether using fallback validation (framework unavailable)
    """
    
    def __init__(self, min_score: float = 60.0):
        """
        Initialize validator.
        
        Args:
            min_score: Minimum acceptable quality score (0-100)
        """
        self.min_score = min_score
        self.fallback_mode = not FRAMEWORK_AVAILABLE
        
        if self.fallback_mode:
            logging.warning(
                "PromptStrategyValidator running in fallback mode. "
                "Install agentic-prompt-strategy-framework for full validation."
            )
    
    def validate(self, prompt_text: str) -> ValidationResult:
        """
        Validate raw prompt text.
        
        Args:
            prompt_text: Markdown-formatted prompt text
            
        Returns:
            ValidationResult with score and suggestions
        """
        if self.fallback_mode:
            return self._fallback_validate(prompt_text)
        
        # Use framework validation
        sections = extract_sections(prompt_text)
        
        four_ok = has_all_sections(sections, FOUR_SENTENCE_SECTIONS)
        role_ok = has_all_sections(sections, ROLE_SECTIONS)
        
        _, _, _, spec_pct = detect_specificity(prompt_text)
        clarity_pct = detect_clarity(prompt_text)
        complete_ok = detect_completeness(prompt_text, sections)
        
        checks = FrameworkChecks(
            four_sentence_present=four_ok,
            role_present=role_ok,
            specificity=round(spec_pct, 1),
            clarity=round(clarity_pct, 1),
            completeness=complete_ok
        )
        
        score = compute_score(checks)
        
        # Generate suggestions
        suggestions = self._generate_suggestions(
            four_ok, role_ok, spec_pct, clarity_pct, complete_ok
        )
        
        # Determine if passed
        passed = (
            (four_ok or role_ok) and
            complete_ok and
            score >= self.min_score and
            clarity_pct >= 70.0 and
            spec_pct >= 50.0
        )
        
        return ValidationResult(
            score=score,
            passed=passed,
            specificity=spec_pct,
            clarity=clarity_pct,
            completeness=complete_ok,
            suggestions=suggestions,
            checks=ValidationChecks(
                four_sentence_present=four_ok,
                role_present=role_ok,
                specificity=spec_pct,
                clarity=clarity_pct,
                completeness=complete_ok
            ),
            metadata={
                "validator": "PromptStrategyValidator",
                "framework_version": "1.0",
                "min_score": self.min_score
            }
        )
    
    def validate_strategy(self, strategy: PromptStrategy) -> ValidationResult:
        """
        Validate a PromptStrategy entity.
        
        Args:
            strategy: PromptStrategy entity to validate
            
        Returns:
            ValidationResult with score and suggestions
        """
        # Convert to markdown format for validation
        prompt_text = strategy.to_markdown()
        
        # Validate
        result = self.validate(prompt_text)
        
        # Update strategy with validation results
        strategy.update_validation(
            score=result.score,
            passed=result.passed,
            suggestions=result.suggestions
        )
        
        return result
    
    def get_min_score(self) -> float:
        """Get minimum acceptable quality score."""
        return self.min_score
    
    def set_min_score(self, score: float) -> None:
        """Set minimum acceptable quality score."""
        if not 0 <= score <= 100:
            raise ValueError(f"Score must be between 0 and 100, got {score}")
        self.min_score = score
    
    def _generate_suggestions(
        self,
        four_ok: bool,
        role_ok: bool,
        spec_pct: float,
        clarity_pct: float,
        complete_ok: bool
    ) -> List[str]:
        """
        Generate improvement suggestions based on validation results.
        
        Args:
            four_ok: Has 4-Sentence Framework sections
            role_ok: Has ROLE Model sections
            spec_pct: Specificity percentage
            clarity_pct: Clarity percentage
            complete_ok: Has complete structure
            
        Returns:
            List of actionable suggestions
        """
        suggestions = []
        
        if not four_ok and not role_ok:
            suggestions.append(
                "Add framework sections: either 4-Sentence (Persona, Goal, Task, Context) "
                "or ROLE (Role, Objective, Logistics, Expectations)"
            )
        elif not four_ok:
            suggestions.append(
                "Consider adding 4-Sentence Framework sections for better structure"
            )
        elif not role_ok:
            suggestions.append(
                "Consider adding ROLE Model sections for comprehensive coverage"
            )
        
        if spec_pct < 50.0:
            suggestions.append(
                "Increase specificity: add file paths (e.g., src/main.py:42), "
                "code examples with ``` blocks, and numeric constraints (e.g., <100ms, ≥95%)"
            )
        elif spec_pct < 70.0:
            suggestions.append(
                "Good specificity, but could add more concrete examples or constraints"
            )
        
        if clarity_pct < 70.0:
            suggestions.append(
                "Improve clarity: remove ambiguous words (maybe, perhaps, etc.) "
                "and use direct, imperative phrasing"
            )
        elif clarity_pct < 85.0:
            suggestions.append(
                "Good clarity, but review for any remaining vague language"
            )
        
        if not complete_ok:
            suggestions.append(
                "Ensure completeness: ≥50 words, clear headers (##), "
                "and all framework sections present"
            )
        
        return suggestions
    
    def _fallback_validate(self, prompt_text: str) -> ValidationResult:
        """
        Fallback validation when framework is unavailable.
        
        Uses simple heuristics to provide basic validation.
        
        Args:
            prompt_text: Prompt text to validate
            
        Returns:
            ValidationResult with basic checks
        """
        # Simple word count
        words = prompt_text.split()
        word_count = len(words)
        
        # Check for headers
        has_headers = "##" in prompt_text
        
        # Simple specificity check (look for common patterns)
        has_code = "```" in prompt_text
        has_numbers = any(char.isdigit() for char in prompt_text)
        specificity = 50.0 if (has_code or has_numbers) else 30.0
        
        # Simple clarity check (word count based)
        clarity = min(100.0, (word_count / 100.0) * 70.0)
        
        # Completeness
        completeness = word_count >= 50 and has_headers
        
        # Score
        score = (specificity * 0.4) + (clarity * 0.4) + (20.0 if completeness else 0.0)
        
        return ValidationResult(
            score=round(score, 1),
            passed=score >= self.min_score,
            specificity=specificity,
            clarity=clarity,
            completeness=completeness,
            suggestions=[
                "Framework validation unavailable. Install agentic-prompt-strategy-framework "
                "for detailed quality analysis."
            ],
            metadata={
                "validator": "PromptStrategyValidator",
                "mode": "fallback",
                "min_score": self.min_score
            }
        )

