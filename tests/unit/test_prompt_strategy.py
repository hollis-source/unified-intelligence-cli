"""
Unit tests for PromptStrategy entity.

Tests the core domain model for structured prompts.
Clean Architecture: Entity layer tests.
"""

import pytest
from datetime import datetime
from src.entity.prompt_strategy import PromptStrategy


class TestPromptStrategy:
    """Test suite for PromptStrategy entity."""
    
    def test_create_basic_strategy(self):
        """Test creating a basic prompt strategy."""
        strategy = PromptStrategy(
            persona="Senior Python Developer",
            goal="Refactor code to improve maintainability",
            task="Extract duplicate logic into reusable functions",
            context="Legacy codebase with 30% code duplication"
        )
        
        assert strategy.persona == "Senior Python Developer"
        assert strategy.goal == "Refactor code to improve maintainability"
        assert strategy.task == "Extract duplicate logic into reusable functions"
        assert strategy.context == "Legacy codebase with 30% code duplication"
        assert strategy.iteration == 1
        assert strategy.validation_passed is False
        assert strategy.created_at is not None
    
    def test_create_with_metadata(self):
        """Test creating strategy with full metadata."""
        strategy = PromptStrategy(
            persona="Database Architect",
            goal="Optimize query performance",
            task="Add composite indexes to improve JOIN performance",
            context="PostgreSQL 14, 10M rows, current query time 5s",
            agent_type="database-specialist",
            domain="database",
            iteration=2,
            quality_score=85.5
        )
        
        assert strategy.agent_type == "database-specialist"
        assert strategy.domain == "database"
        assert strategy.iteration == 2
        assert strategy.quality_score == 85.5
    
    def test_to_system_prompt_basic(self):
        """Test converting to system prompt without ULTRATHINK."""
        strategy = PromptStrategy(
            persona="Frontend Developer",
            goal="Improve UI responsiveness",
            task="Implement lazy loading for images",
            context="React 18 application with 100+ images per page"
        )
        
        prompt = strategy.to_system_prompt(include_ultrathink=False)
        
        assert "Frontend Developer" in prompt
        assert "Improve UI responsiveness" in prompt
        assert "Implement lazy loading" in prompt
        assert "React 18" in prompt
        assert "ULTRATHINK" not in prompt
    
    def test_to_system_prompt_with_ultrathink(self):
        """Test converting to system prompt with ULTRATHINK."""
        strategy = PromptStrategy(
            persona="Backend Developer",
            goal="Reduce API latency",
            task="Implement caching layer",
            context="REST API with 1000 req/s"
        )
        
        prompt = strategy.to_system_prompt(include_ultrathink=True)
        
        assert "Backend Developer" in prompt
        assert "ULTRATHINK MODE" in prompt
        assert "<think></think>" in prompt
        assert "step-by-step" in prompt
    
    def test_to_user_prompt(self):
        """Test converting to user prompt."""
        strategy = PromptStrategy(
            persona="QA Engineer",
            goal="Increase test coverage to 90%",
            task="Write unit tests for authentication module",
            context="Current coverage: 65%, using pytest"
        )
        
        prompt = strategy.to_user_prompt()
        
        assert "Write unit tests" in prompt
        assert "Increase test coverage to 90%" in prompt
        assert "pytest" in prompt
    
    def test_to_markdown(self):
        """Test converting to markdown format."""
        strategy = PromptStrategy(
            persona="DevOps Engineer",
            goal="Automate deployment pipeline",
            task="Create GitHub Actions workflow",
            context="Deploy to AWS ECS, run tests first",
            agent_type="devops-specialist",
            domain="devops",
            iteration=1,
            quality_score=75.0
        )
        
        md = strategy.to_markdown()
        
        assert "# Prompt Strategy" in md
        assert "## Persona" in md
        assert "## Goal" in md
        assert "## Task" in md
        assert "## Context" in md
        assert "DevOps Engineer" in md
        assert "devops" in md
        assert "75.0" in md
    
    def test_update_validation(self):
        """Test updating validation results."""
        strategy = PromptStrategy(
            persona="Architect",
            goal="Design microservices architecture",
            task="Create service boundaries",
            context="Monolithic app with 500K LOC"
        )
        
        assert strategy.quality_score is None
        assert strategy.validation_passed is False
        assert len(strategy.validation_suggestions) == 0
        
        strategy.update_validation(
            score=82.5,
            passed=True,
            suggestions=["Add more specific metrics", "Include code examples"]
        )
        
        assert strategy.quality_score == 82.5
        assert strategy.validation_passed is True
        assert len(strategy.validation_suggestions) == 2
        assert "Add more specific metrics" in strategy.validation_suggestions
    
    def test_to_dict(self):
        """Test converting to dictionary."""
        strategy = PromptStrategy(
            persona="Research Engineer",
            goal="Evaluate ML model performance",
            task="Run A/B test with 10K samples",
            context="Classification task, current accuracy 85%",
            agent_type="research-specialist",
            domain="research",
            quality_score=90.0,
            validation_passed=True,
            validation_suggestions=["Good specificity"]
        )
        
        data = strategy.to_dict()
        
        assert data["persona"] == "Research Engineer"
        assert data["goal"] == "Evaluate ML model performance"
        assert data["agent_type"] == "research-specialist"
        assert data["domain"] == "research"
        assert data["quality_score"] == 90.0
        assert data["validation_passed"] is True
        assert "Good specificity" in data["validation_suggestions"]
        assert "created_at" in data
    
    def test_from_dict(self):
        """Test creating from dictionary."""
        data = {
            "persona": "Testing Specialist",
            "goal": "Improve test reliability",
            "task": "Fix flaky tests",
            "context": "10% of tests fail intermittently",
            "agent_type": "test-specialist",
            "domain": "testing",
            "iteration": 3,
            "quality_score": 78.0,
            "validation_passed": True,
            "validation_suggestions": ["Add retry logic"],
            "metadata": {"priority": "high"},
            "created_at": "2025-10-19T12:00:00"
        }
        
        strategy = PromptStrategy.from_dict(data)
        
        assert strategy.persona == "Testing Specialist"
        assert strategy.goal == "Improve test reliability"
        assert strategy.agent_type == "test-specialist"
        assert strategy.domain == "testing"
        assert strategy.iteration == 3
        assert strategy.quality_score == 78.0
        assert strategy.validation_passed is True
        assert strategy.metadata["priority"] == "high"
        assert strategy.created_at == "2025-10-19T12:00:00"
    
    def test_round_trip_serialization(self):
        """Test that to_dict/from_dict round-trip works."""
        original = PromptStrategy(
            persona="Full Stack Developer",
            goal="Build REST API",
            task="Implement CRUD endpoints",
            context="FastAPI, PostgreSQL, JWT auth",
            agent_type="backend-developer",
            domain="backend",
            iteration=2,
            quality_score=88.5,
            validation_passed=True,
            validation_suggestions=["Excellent clarity"],
            metadata={"framework": "FastAPI"}
        )
        
        # Round trip
        data = original.to_dict()
        restored = PromptStrategy.from_dict(data)
        
        assert restored.persona == original.persona
        assert restored.goal == original.goal
        assert restored.task == original.task
        assert restored.context == original.context
        assert restored.agent_type == original.agent_type
        assert restored.domain == original.domain
        assert restored.iteration == original.iteration
        assert restored.quality_score == original.quality_score
        assert restored.validation_passed == original.validation_passed
        assert restored.validation_suggestions == original.validation_suggestions
        assert restored.metadata == original.metadata
    
    def test_created_at_auto_generated(self):
        """Test that created_at is auto-generated if not provided."""
        strategy = PromptStrategy(
            persona="Developer",
            goal="Test goal",
            task="Test task",
            context="Test context"
        )
        
        assert strategy.created_at is not None
        # Should be ISO format
        datetime.fromisoformat(strategy.created_at)  # Should not raise
    
    def test_validation_suggestions_default_empty(self):
        """Test that validation_suggestions defaults to empty list."""
        strategy = PromptStrategy(
            persona="Developer",
            goal="Test goal",
            task="Test task",
            context="Test context"
        )
        
        assert isinstance(strategy.validation_suggestions, list)
        assert len(strategy.validation_suggestions) == 0
    
    def test_metadata_default_empty(self):
        """Test that metadata defaults to empty dict."""
        strategy = PromptStrategy(
            persona="Developer",
            goal="Test goal",
            task="Test task",
            context="Test context"
        )
        
        assert isinstance(strategy.metadata, dict)
        assert len(strategy.metadata) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

