"""
Unit tests for LLMAgentExecutor with PromptStrategy integration.

Tests Phase 2 enhancements: prompt strategy building and validation.
Clean Architecture: Adapter layer tests.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from src.adapters.agent.llm_executor import LLMAgentExecutor
from src.entity import Agent, Task, ExecutionContext
from src.entity.prompt_strategy import PromptStrategy
from src.interface import LLMConfig, GenerationResult
from src.interface.prompt_validator import IPromptValidator, ValidationResult
from src.adapters.prompt import PromptStrategyValidator


class MockTextGenerator:
    """Mock text generator for testing."""
    
    def generate(self, messages, config=None):
        """Mock generation."""
        return GenerationResult(
            content="Mock response",
            usage={"prompt_tokens": 10, "completion_tokens": 20}
        )


class MockPromptValidator(IPromptValidator):
    """Mock prompt validator for testing."""
    
    def __init__(self, score=80.0, passed=True):
        self.score = score
        self.passed = passed
        self.validate_calls = []
    
    def validate(self, prompt_text: str) -> ValidationResult:
        """Mock validation."""
        self.validate_calls.append(("validate", prompt_text))
        return ValidationResult(
            score=self.score,
            passed=self.passed,
            specificity=75.0,
            clarity=85.0,
            completeness=True,
            suggestions=[] if self.passed else ["Improve specificity"]
        )
    
    def validate_strategy(self, strategy: PromptStrategy) -> ValidationResult:
        """Mock strategy validation."""
        self.validate_calls.append(("validate_strategy", strategy))
        return self.validate(strategy.to_markdown())
    
    def get_min_score(self) -> float:
        return 60.0
    
    def set_min_score(self, score: float) -> None:
        pass


class TestLLMAgentExecutorPromptStrategy:
    """Test suite for LLMAgentExecutor with PromptStrategy."""
    
    def test_create_executor_with_validator(self):
        """Test creating executor with prompt validator."""
        llm = MockTextGenerator()
        validator = MockPromptValidator()
        
        executor = LLMAgentExecutor(
            llm_provider=llm,
            prompt_validator=validator,
            validate_prompts=True,
            use_prompt_strategy=True
        )
        
        assert executor.prompt_validator is validator
        assert executor.validate_prompts is True
        assert executor.use_prompt_strategy is True
    
    def test_create_executor_without_validator(self):
        """Test creating executor without validator (backward compatibility)."""
        llm = MockTextGenerator()
        
        executor = LLMAgentExecutor(llm_provider=llm)
        
        assert executor.prompt_validator is None
        assert executor.validate_prompts is False
        assert executor.use_prompt_strategy is False
    
    def test_build_prompt_strategy(self):
        """Test building PromptStrategy from agent and task."""
        llm = MockTextGenerator()
        executor = LLMAgentExecutor(llm_provider=llm, use_prompt_strategy=True)
        
        agent = Agent(
            role="backend-developer",
            capabilities=["python", "fastapi", "postgresql"],
            tier=1
        )
        
        task = Task(description="Implement caching layer for API endpoints")
        
        strategy = executor._build_prompt_strategy(agent, task, None)
        
        assert isinstance(strategy, PromptStrategy)
        # Persona can come from template or dynamic builder; verify key signals
        assert "python" in strategy.persona
        assert "tier" in strategy.persona.lower()
        assert "backend" in strategy.persona.lower() or "engineer" in strategy.persona.lower()
        assert "Implement caching layer" in strategy.task
        assert strategy.agent_type == "backend-developer"
        assert strategy.domain == "backend"
    
    def test_extract_goal_with_keywords(self):
        """Test extracting goal from task with goal keywords."""
        llm = MockTextGenerator()
        executor = LLMAgentExecutor(llm_provider=llm)
        
        task = Task(description="Reduce API latency from 500ms to 100ms")
        goal = executor._extract_goal(task)
        
        assert goal == "Reduce API latency from 500ms to 100ms"
    
    def test_extract_goal_without_keywords(self):
        """Test extracting goal from task without goal keywords."""
        llm = MockTextGenerator()
        executor = LLMAgentExecutor(llm_provider=llm)
        
        task = Task(description="Add logging to authentication module")
        goal = executor._extract_goal(task)
        
        assert "Successfully complete" in goal
        assert "Add logging" in goal
    
    def test_infer_domain_backend(self):
        """Test inferring backend domain."""
        llm = MockTextGenerator()
        executor = LLMAgentExecutor(llm_provider=llm)
        
        assert executor._infer_domain("backend-developer") == "backend"
        assert executor._infer_domain("Backend Engineer") == "backend"
    
    def test_infer_domain_frontend(self):
        """Test inferring frontend domain."""
        llm = MockTextGenerator()
        executor = LLMAgentExecutor(llm_provider=llm)
        
        assert executor._infer_domain("frontend-developer") == "frontend"
        assert executor._infer_domain("React Frontend") == "frontend"
    
    def test_infer_domain_testing(self):
        """Test inferring testing domain."""
        llm = MockTextGenerator()
        executor = LLMAgentExecutor(llm_provider=llm)
        
        assert executor._infer_domain("test-engineer") == "testing"
        assert executor._infer_domain("QA Specialist") == "qa"
    
    def test_infer_domain_unknown(self):
        """Test inferring unknown domain defaults to general."""
        llm = MockTextGenerator()
        executor = LLMAgentExecutor(llm_provider=llm)
        
        assert executor._infer_domain("unknown-role") == "general"
    
    def test_build_context_text_with_tier(self):
        """Test building context text with agent tier."""
        llm = MockTextGenerator()
        executor = LLMAgentExecutor(llm_provider=llm, enable_ultrathink=True)
        
        agent = Agent(role="developer", capabilities=["python"], tier=2)
        task = Task(description="Test task")
        
        context_text = executor._build_context_text(agent, task, None)
        
        assert "Agent Tier: 2" in context_text
        assert "ULTRATHINK" in context_text
    
    def test_build_context_text_with_history(self):
        """Test building context text with execution history."""
        llm = MockTextGenerator()
        executor = LLMAgentExecutor(llm_provider=llm)

        agent = Agent(role="developer", capabilities=["python"])
        task = Task(description="Test task")
        context = ExecutionContext(
            session_id="test-session",
            history=[{"role": "user", "content": "Previous"}]
        )

        context_text = executor._build_context_text(agent, task, context)

        assert "Previous interactions: 1" in context_text
    
    def test_strategy_to_messages(self):
        """Test converting PromptStrategy to messages."""
        llm = MockTextGenerator()
        executor = LLMAgentExecutor(llm_provider=llm, enable_ultrathink=True)
        
        strategy = PromptStrategy(
            persona="Senior Developer",
            goal="Improve code quality",
            task="Refactor module",
            context="Legacy codebase"
        )
        
        messages = executor._strategy_to_messages(strategy, None)
        
        assert len(messages) == 2  # system + user
        assert messages[0]["role"] == "system"
        assert "Senior Developer" in messages[0]["content"]
        assert "ULTRATHINK" in messages[0]["content"]
        assert messages[1]["role"] == "user"
        assert "Refactor module" in messages[1]["content"]
    
    def test_strategy_to_messages_with_context_history(self):
        """Test converting strategy to messages with context history."""
        llm = MockTextGenerator()
        executor = LLMAgentExecutor(llm_provider=llm)

        strategy = PromptStrategy(
            persona="Developer",
            goal="Test goal",
            task="Test task",
            context="Test context"
        )

        context = ExecutionContext(
            session_id="test-session",
            history=[
                {"role": "user", "content": "Message 1"},
                {"role": "assistant", "content": "Response 1"}
            ]
        )

        messages = executor._strategy_to_messages(strategy, context)

        # Should have system + history + user
        assert len(messages) == 4
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"
        assert messages[1]["content"] == "Message 1"
        assert messages[2]["role"] == "assistant"
        assert messages[3]["role"] == "user"
    
    def test_build_messages_with_prompt_strategy(self):
        """Test building messages using PromptStrategy."""
        llm = MockTextGenerator()
        executor = LLMAgentExecutor(
            llm_provider=llm,
            use_prompt_strategy=True
        )
        
        agent = Agent(role="developer", capabilities=["python"])
        task = Task(description="Implement feature")
        
        messages = executor._build_messages(agent, task, None)
        
        assert len(messages) >= 2
        assert messages[0]["role"] == "system"
        assert messages[-1]["role"] == "user"
    
    def test_build_messages_with_validation_passing(self):
        """Test building messages with validation that passes."""
        llm = MockTextGenerator()
        validator = MockPromptValidator(score=85.0, passed=True)

        executor = LLMAgentExecutor(
            llm_provider=llm,
            prompt_validator=validator,
            validate_prompts=True,
            use_prompt_strategy=True
        )

        agent = Agent(role="developer", capabilities=["python"])
        task = Task(description="Implement feature")

        messages = executor._build_messages(agent, task, None)

        # Should have validated (validate_strategy calls validate internally)
        assert len(validator.validate_calls) >= 1
        assert validator.validate_calls[0][0] == "validate_strategy"

        # Should still build messages
        assert len(messages) >= 2
    
    def test_build_messages_with_validation_failing(self):
        """Test building messages with validation that fails."""
        llm = MockTextGenerator()
        validator = MockPromptValidator(score=45.0, passed=False)
        
        executor = LLMAgentExecutor(
            llm_provider=llm,
            prompt_validator=validator,
            validate_prompts=True,
            use_prompt_strategy=True
        )
        
        agent = Agent(role="developer", capabilities=["python"])
        task = Task(description="Implement feature")
        
        with patch('logging.warning') as mock_warning:
            messages = executor._build_messages(agent, task, None)
            
            # Should log warning
            assert mock_warning.called
            warning_msg = mock_warning.call_args[0][0]
            assert "validation failed" in warning_msg.lower()
            assert "45.0" in warning_msg
        
        # Should still build messages (validation doesn't block)
        assert len(messages) >= 2
    
    def test_build_messages_legacy_path(self):
        """Test building messages using legacy path (backward compatibility)."""
        llm = MockTextGenerator()
        executor = LLMAgentExecutor(
            llm_provider=llm,
            use_prompt_strategy=False  # Legacy mode
        )
        
        agent = Agent(role="developer", capabilities=["python"])
        task = Task(description="Implement feature")
        
        messages = executor._build_messages(agent, task, None)
        
        # Should use legacy message building
        assert len(messages) >= 2
        assert messages[0]["role"] == "system"
        assert "developer" in messages[0]["content"].lower()
    
    def test_validation_disabled_by_default(self):
        """Test that validation is disabled by default."""
        llm = MockTextGenerator()
        validator = MockPromptValidator()
        
        executor = LLMAgentExecutor(
            llm_provider=llm,
            prompt_validator=validator,
            validate_prompts=False  # Explicitly disabled
        )
        
        agent = Agent(role="developer", capabilities=["python"])
        task = Task(description="Implement feature")
        
        executor._build_messages(agent, task, None)
        
        # Should not validate
        assert len(validator.validate_calls) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

