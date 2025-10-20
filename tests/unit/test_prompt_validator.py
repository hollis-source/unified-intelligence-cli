"""
Unit tests for IPromptValidator interface and related types.

Tests the validation interface contracts and DTOs.
Clean Architecture: Interface layer tests.
"""

import pytest
from src.interface.prompt_validator import (
    IPromptValidator,
    IPromptEnhancer,
    ValidationResult,
    ValidationChecks
)
from src.entity.prompt_strategy import PromptStrategy


class TestValidationChecks:
    """Test suite for ValidationChecks dataclass."""
    
    def test_create_validation_checks(self):
        """Test creating validation checks."""
        checks = ValidationChecks(
            four_sentence_present=True,
            role_present=False,
            specificity=75.5,
            clarity=82.0,
            completeness=True
        )
        
        assert checks.four_sentence_present is True
        assert checks.role_present is False
        assert checks.specificity == 75.5
        assert checks.clarity == 82.0
        assert checks.completeness is True
    
    def test_to_dict(self):
        """Test converting checks to dictionary."""
        checks = ValidationChecks(
            four_sentence_present=True,
            role_present=True,
            specificity=80.0,
            clarity=90.0,
            completeness=True
        )
        
        data = checks.to_dict()
        
        assert data["four_sentence_present"] is True
        assert data["role_present"] is True
        assert data["specificity"] == 80.0
        assert data["clarity"] == 90.0
        assert data["completeness"] is True


class TestValidationResult:
    """Test suite for ValidationResult dataclass."""
    
    def test_create_validation_result(self):
        """Test creating validation result."""
        result = ValidationResult(
            score=85.5,
            passed=True,
            specificity=80.0,
            clarity=90.0,
            completeness=True,
            suggestions=["Good work", "Add more examples"]
        )
        
        assert result.score == 85.5
        assert result.passed is True
        assert result.specificity == 80.0
        assert result.clarity == 90.0
        assert result.completeness is True
        assert len(result.suggestions) == 2
        assert "Good work" in result.suggestions
    
    def test_validation_result_with_checks(self):
        """Test validation result with detailed checks."""
        checks = ValidationChecks(
            four_sentence_present=True,
            role_present=False,
            specificity=75.0,
            clarity=85.0,
            completeness=True
        )
        
        result = ValidationResult(
            score=80.0,
            passed=True,
            specificity=75.0,
            clarity=85.0,
            completeness=True,
            checks=checks
        )
        
        assert result.checks is not None
        assert result.checks.four_sentence_present is True
        assert result.checks.role_present is False
    
    def test_to_dict(self):
        """Test converting result to dictionary."""
        checks = ValidationChecks(
            four_sentence_present=True,
            role_present=True,
            specificity=80.0,
            clarity=90.0,
            completeness=True
        )
        
        result = ValidationResult(
            score=85.0,
            passed=True,
            specificity=80.0,
            clarity=90.0,
            completeness=True,
            suggestions=["Excellent"],
            checks=checks,
            metadata={"validator": "test"}
        )
        
        data = result.to_dict()
        
        assert data["score"] == 85.0
        assert data["passed"] is True
        assert data["specificity"] == 80.0
        assert data["clarity"] == 90.0
        assert data["completeness"] is True
        assert "Excellent" in data["suggestions"]
        assert data["checks"] is not None
        assert data["checks"]["four_sentence_present"] is True
        assert data["metadata"]["validator"] == "test"
    
    def test_from_dict(self):
        """Test creating result from dictionary."""
        data = {
            "score": 78.5,
            "passed": True,
            "specificity": 70.0,
            "clarity": 85.0,
            "completeness": True,
            "suggestions": ["Add examples"],
            "checks": {
                "four_sentence_present": True,
                "role_present": False,
                "specificity": 70.0,
                "clarity": 85.0,
                "completeness": True
            },
            "metadata": {"version": "1.0"}
        }
        
        result = ValidationResult.from_dict(data)
        
        assert result.score == 78.5
        assert result.passed is True
        assert result.specificity == 70.0
        assert result.clarity == 85.0
        assert result.completeness is True
        assert "Add examples" in result.suggestions
        assert result.checks is not None
        assert result.checks.four_sentence_present is True
        assert result.metadata["version"] == "1.0"
    
    def test_round_trip_serialization(self):
        """Test that to_dict/from_dict round-trip works."""
        checks = ValidationChecks(
            four_sentence_present=True,
            role_present=True,
            specificity=82.0,
            clarity=88.0,
            completeness=True
        )
        
        original = ValidationResult(
            score=85.0,
            passed=True,
            specificity=82.0,
            clarity=88.0,
            completeness=True,
            suggestions=["Great job"],
            checks=checks,
            metadata={"test": "value"}
        )
        
        data = original.to_dict()
        restored = ValidationResult.from_dict(data)
        
        assert restored.score == original.score
        assert restored.passed == original.passed
        assert restored.specificity == original.specificity
        assert restored.clarity == original.clarity
        assert restored.completeness == original.completeness
        assert restored.suggestions == original.suggestions
        assert restored.checks.four_sentence_present == original.checks.four_sentence_present
        assert restored.metadata == original.metadata


class MockPromptValidator(IPromptValidator):
    """Mock implementation of IPromptValidator for testing."""
    
    def __init__(self, min_score: float = 60.0):
        self._min_score = min_score
    
    def validate(self, prompt_text: str) -> ValidationResult:
        """Mock validation - always passes."""
        return ValidationResult(
            score=80.0,
            passed=True,
            specificity=75.0,
            clarity=85.0,
            completeness=True,
            suggestions=[]
        )
    
    def validate_strategy(self, strategy: PromptStrategy) -> ValidationResult:
        """Mock strategy validation."""
        return self.validate(strategy.to_markdown())
    
    def get_min_score(self) -> float:
        """Get minimum score."""
        return self._min_score
    
    def set_min_score(self, score: float) -> None:
        """Set minimum score."""
        self._min_score = score


class TestIPromptValidator:
    """Test suite for IPromptValidator interface."""
    
    def test_mock_validator_implements_interface(self):
        """Test that mock validator implements interface."""
        validator = MockPromptValidator()
        
        assert isinstance(validator, IPromptValidator)
    
    def test_validate_method(self):
        """Test validate method."""
        validator = MockPromptValidator()
        result = validator.validate("Test prompt")
        
        assert isinstance(result, ValidationResult)
        assert result.score > 0
        assert isinstance(result.passed, bool)
    
    def test_validate_strategy_method(self):
        """Test validate_strategy method."""
        validator = MockPromptValidator()
        strategy = PromptStrategy(
            persona="Developer",
            goal="Test goal",
            task="Test task",
            context="Test context"
        )
        
        result = validator.validate_strategy(strategy)
        
        assert isinstance(result, ValidationResult)
        assert result.score > 0
    
    def test_get_set_min_score(self):
        """Test get/set min score methods."""
        validator = MockPromptValidator(min_score=70.0)
        
        assert validator.get_min_score() == 70.0
        
        validator.set_min_score(80.0)
        assert validator.get_min_score() == 80.0


class MockPromptEnhancer(IPromptEnhancer):
    """Mock implementation of IPromptEnhancer for testing."""
    
    def enhance(self, prompt_text: str, target_score: float = 80.0) -> str:
        """Mock enhancement - adds a line."""
        return prompt_text + "\n\nEnhanced for better quality."
    
    def suggest_improvements(self, validation_result: ValidationResult) -> list:
        """Mock suggestions."""
        return ["Add more details", "Use specific examples"]


class TestIPromptEnhancer:
    """Test suite for IPromptEnhancer interface."""
    
    def test_mock_enhancer_implements_interface(self):
        """Test that mock enhancer implements interface."""
        enhancer = MockPromptEnhancer()
        
        assert isinstance(enhancer, IPromptEnhancer)
    
    def test_enhance_method(self):
        """Test enhance method."""
        enhancer = MockPromptEnhancer()
        original = "Original prompt"
        enhanced = enhancer.enhance(original, target_score=85.0)
        
        assert isinstance(enhanced, str)
        assert len(enhanced) > len(original)
    
    def test_suggest_improvements_method(self):
        """Test suggest_improvements method."""
        enhancer = MockPromptEnhancer()
        result = ValidationResult(
            score=65.0,
            passed=False,
            specificity=50.0,
            clarity=70.0,
            completeness=True
        )
        
        suggestions = enhancer.suggest_improvements(result)
        
        assert isinstance(suggestions, list)
        assert len(suggestions) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

