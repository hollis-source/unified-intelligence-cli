"""
Unit tests for LLMAgentExecutor metrics logging (Phase 4).
"""
import pytest
from unittest.mock import Mock

from src.adapters.agent.llm_executor import LLMAgentExecutor
from src.adapters.db.prompt_metrics_store import InMemoryPromptMetricsStore
from src.entity.prompt_strategy import PromptStrategy
from src.entity import Agent, Task
from src.interface.prompt_validator import IPromptValidator, ValidationResult


class DummyValidator(IPromptValidator):
    def __init__(self, score=72.0, passed=True):
        self._score = score
        self._passed = passed

    def validate(self, prompt_text: str) -> ValidationResult:
        return ValidationResult(
            score=self._score,
            passed=self._passed,
            specificity=65.0,
            clarity=90.0,
            completeness=True,
            suggestions=["add code blocks", "add numbers"] if not self._passed else []
        )

    def validate_strategy(self, strategy: PromptStrategy) -> ValidationResult:
        return self.validate(strategy.to_markdown())

    def get_min_score(self) -> float:
        return 60.0

    def set_min_score(self, score: float) -> None:
        pass


def test_executor_logs_metrics_on_validation():
    # Arrange
    store = InMemoryPromptMetricsStore()

    class MockLLM:
        def generate(self, messages, config=None):
            class Res: pass
            r = Res(); r.content = "ok"; r.usage = {"prompt_tokens": 1, "completion_tokens": 1}
            return r

    executor = LLMAgentExecutor(
        llm_provider=MockLLM(),
        prompt_validator=DummyValidator(score=58.0, passed=False),
        validate_prompts=True,
        use_prompt_strategy=True,
        metrics_store=store,
    )

    agent = Agent(role="backend-developer", capabilities=["python"], tier=1)
    task = Task(description="Implement caching layer")

    # Act: Build messages triggers validation and metrics logging
    executor._build_messages(agent, task, None)

    # Assert
    assert store.count() == 1
    m = store.last()
    assert m is not None
    assert m.domain == "backend"
    assert m.agent_type == "backend-developer"
    assert m.validation_score == 58.0
    assert isinstance(m.template_used, bool)

