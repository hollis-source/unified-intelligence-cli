"""
Unit tests for PromptStrategyValidator adapter.

Tests the adapter that wraps agentic-prompt-strategy-framework validation.
Clean Architecture: Adapter layer tests.
"""

import pytest
from src.adapters.prompt.strategy_validator import PromptStrategyValidator, FRAMEWORK_AVAILABLE
from src.interface.prompt_validator import ValidationResult, ValidationChecks
from src.entity.prompt_strategy import PromptStrategy


class TestPromptStrategyValidator:
    """Test suite for PromptStrategyValidator adapter."""
    
    def test_create_validator_default_score(self):
        """Test creating validator with default minimum score."""
        validator = PromptStrategyValidator()
        
        assert validator.get_min_score() == 60.0
    
    def test_create_validator_custom_score(self):
        """Test creating validator with custom minimum score."""
        validator = PromptStrategyValidator(min_score=75.0)
        
        assert validator.get_min_score() == 75.0
    
    def test_set_min_score(self):
        """Test setting minimum score."""
        validator = PromptStrategyValidator(min_score=60.0)
        
        validator.set_min_score(80.0)
        assert validator.get_min_score() == 80.0
    
    def test_set_min_score_invalid_range(self):
        """Test that invalid score raises ValueError."""
        validator = PromptStrategyValidator()
        
        with pytest.raises(ValueError):
            validator.set_min_score(150.0)
        
        with pytest.raises(ValueError):
            validator.set_min_score(-10.0)
    
    def test_validate_good_prompt(self):
        """Test validating a well-structured prompt."""
        validator = PromptStrategyValidator(min_score=60.0)
        
        # Well-structured prompt with all sections
        prompt_text = """## Persona
Senior Python Developer with 10+ years experience in backend development.

## Goal
Reduce API response time from 500ms to under 100ms while maintaining accuracy.

## Task
Implement Redis caching layer for frequently accessed database queries in src/api/handlers.py:42-85.

## Context
Current State:
- PostgreSQL database with 10M rows
- 1000 requests/second peak load
- No caching layer

Constraints:
- Must maintain data consistency
- Cache TTL: 5 minutes
- Redis 7.0 available

Requirements:
- Add cache invalidation on updates
- Monitor cache hit rate (target: >80%)
- Implement in src/cache/redis_client.py

Deliverables:
- Caching implementation with tests
- Performance benchmarks showing <100ms response time
- Documentation in docs/caching.md
"""
        
        result = validator.validate(prompt_text)
        
        assert isinstance(result, ValidationResult)
        assert result.score > 0
        assert isinstance(result.passed, bool)
        assert isinstance(result.specificity, float)
        assert isinstance(result.clarity, float)
        assert isinstance(result.completeness, bool)
        assert isinstance(result.suggestions, list)
        
        # Should have good scores due to specificity (file paths, numbers, etc.)
        if FRAMEWORK_AVAILABLE:
            assert result.specificity >= 50.0  # Has file paths and numbers
            assert result.clarity >= 70.0  # Clear language
    
    def test_validate_poor_prompt(self):
        """Test validating a poorly structured prompt."""
        validator = PromptStrategyValidator(min_score=60.0)
        
        # Poor prompt - vague, no structure
        prompt_text = """
Maybe we should try to improve the system somehow.
It would be nice if things were faster.
Perhaps we could add some caching or something.
"""
        
        result = validator.validate(prompt_text)
        
        assert isinstance(result, ValidationResult)
        assert result.score >= 0
        
        # Should have low scores
        if FRAMEWORK_AVAILABLE:
            assert result.specificity < 50.0  # No specific details
            assert result.clarity < 70.0  # Ambiguous language
            assert result.passed is False  # Should fail
            assert len(result.suggestions) > 0  # Should have suggestions
    
    def test_validate_strategy(self):
        """Test validating a PromptStrategy entity."""
        validator = PromptStrategyValidator(min_score=60.0)
        
        strategy = PromptStrategy(
            persona="Database Architect with expertise in PostgreSQL optimization",
            goal="Reduce query execution time from 5 seconds to under 100ms",
            task="Add composite indexes on (user_id, created_at) in users table at schema/tables.sql:42",
            context="""Current State:
- PostgreSQL 14 with 10M rows in users table
- Query: SELECT * FROM users WHERE user_id = ? AND created_at > ?
- Current execution time: 5.2 seconds

Constraints:
- Cannot modify application code
- Must maintain data integrity
- Index size limit: 1GB

Requirements:
- Add BTREE composite index
- Analyze query plan with EXPLAIN
- Benchmark with 1000 sample queries

Deliverables:
- Migration script in migrations/add_user_indexes.sql
- Performance report showing <100ms execution time
- Updated documentation in docs/database.md""",
            agent_type="database-specialist",
            domain="database"
        )
        
        result = validator.validate_strategy(strategy)
        
        assert isinstance(result, ValidationResult)
        assert result.score > 0
        
        # Strategy should be updated with validation results
        assert strategy.quality_score == result.score
        assert strategy.validation_passed == result.passed
        assert strategy.validation_suggestions == result.suggestions
        
        # Should have good scores due to specificity
        if FRAMEWORK_AVAILABLE:
            assert result.specificity >= 50.0  # Has file paths, numbers, etc.
    
    def test_fallback_mode_when_framework_unavailable(self):
        """Test that fallback mode works when framework is unavailable."""
        validator = PromptStrategyValidator()
        
        # Even in fallback mode, should return valid result
        result = validator.validate("Test prompt with some content here.")
        
        assert isinstance(result, ValidationResult)
        assert result.score >= 0
        assert isinstance(result.passed, bool)
        
        if validator.fallback_mode:
            assert "Framework validation unavailable" in result.suggestions[0]
            assert result.metadata["mode"] == "fallback"
    
    def test_validation_checks_included(self):
        """Test that validation result includes detailed checks."""
        validator = PromptStrategyValidator()
        
        prompt_text = """## Persona
Senior Developer

## Goal
Improve performance

## Task
Optimize code

## Context
Current system is slow
"""
        
        result = validator.validate(prompt_text)
        
        if FRAMEWORK_AVAILABLE:
            assert result.checks is not None
            assert isinstance(result.checks, ValidationChecks)
            assert isinstance(result.checks.four_sentence_present, bool)
            assert isinstance(result.checks.role_present, bool)
            assert isinstance(result.checks.specificity, float)
            assert isinstance(result.checks.clarity, float)
            assert isinstance(result.checks.completeness, bool)
    
    def test_suggestions_generated(self):
        """Test that suggestions are generated for low-quality prompts."""
        validator = PromptStrategyValidator(min_score=60.0)
        
        # Minimal prompt - should generate suggestions
        prompt_text = """## Persona
Developer

## Goal
Do something

## Task
Fix it

## Context
It's broken
"""
        
        result = validator.validate(prompt_text)
        
        # Should have suggestions for improvement
        assert len(result.suggestions) > 0
        
        if FRAMEWORK_AVAILABLE:
            # Check for common suggestion patterns
            suggestions_text = " ".join(result.suggestions).lower()
            # Should suggest adding specificity or clarity
            assert any(word in suggestions_text for word in ["specificity", "clarity", "details", "examples"])
    
    def test_metadata_included(self):
        """Test that validation result includes metadata."""
        validator = PromptStrategyValidator(min_score=70.0)
        
        result = validator.validate("Test prompt")
        
        assert "metadata" in result.to_dict()
        assert result.metadata["validator"] == "PromptStrategyValidator"
        assert result.metadata["min_score"] == 70.0
    
    def test_high_quality_prompt_passes(self):
        """Test that a high-quality prompt passes validation."""
        validator = PromptStrategyValidator(min_score=60.0)
        
        # High-quality prompt with all elements
        prompt_text = """## Persona
Senior Backend Engineer with 8+ years experience in Python and FastAPI, specializing in API design and database optimization.

## Goal
Reduce API endpoint latency from 450ms to under 100ms while maintaining 99.9% uptime and data consistency.

## Task
Implement Redis caching layer for GET /api/v1/users/{id} endpoint in src/api/users.py:125-180, with automatic cache invalidation on user updates.

## Context
Current State:
- FastAPI 0.104.1 application
- PostgreSQL 14 database with 5M user records
- Average response time: 450ms (p95: 850ms)
- 500 requests/second during peak hours
- No caching infrastructure

Constraints:
- Must maintain ACID properties for user updates
- Cache TTL: 300 seconds (5 minutes)
- Redis 7.0 cluster available at redis://cache:6379
- Maximum memory: 4GB for cache

Requirements:
- Implement cache-aside pattern
- Add cache invalidation on POST/PUT/DELETE operations
- Monitor cache hit rate (target: ≥85%)
- Add circuit breaker for Redis failures
- Implement in src/cache/redis_manager.py

Deliverables:
- Caching implementation with unit tests (≥90% coverage)
- Integration tests for cache invalidation
- Performance benchmarks showing <100ms p95 latency
- Monitoring dashboard in Grafana
- Documentation in docs/caching-strategy.md
"""
        
        result = validator.validate(prompt_text)
        
        if FRAMEWORK_AVAILABLE:
            # Should have high scores
            assert result.specificity >= 60.0  # Lots of specific details
            assert result.clarity >= 80.0  # Clear, direct language
            assert result.completeness is True  # Complete structure
            assert result.score >= 70.0  # High overall score
            assert result.passed is True  # Should pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

