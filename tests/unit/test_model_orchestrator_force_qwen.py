import os
import pytest
from typing import List, Dict, Any, Optional

from src.adapters.llm.model_orchestrator import ModelOrchestrator
from src.interfaces.llm_provider import ITextGenerator, LLMConfig
from src.interfaces.factory_interfaces import IProviderFactory


class _FakeQwenProvider(ITextGenerator):
    def __init__(self):
        self.called = False

    def generate(self, messages: List[Dict[str, Any]], config: Optional[LLMConfig] = None) -> str:
        self.called = True
        return "QWEN_OK"


class _FailingProvider(ITextGenerator):
    def generate(self, messages: List[Dict[str, Any]], config: Optional[LLMConfig] = None) -> str:
        raise AssertionError("This provider should not be used when forcing qwen3_hf_inference")


class _FakeProviderFactory(IProviderFactory):
    def __init__(self, qwen_provider: _FakeQwenProvider):
        self.qwen = qwen_provider
        self.requested: List[str] = []

    def create_provider(self, provider_type: str, config: Optional[Dict[str, Any]] = None) -> ITextGenerator:
        self.requested.append(provider_type)
        if provider_type == "qwen3_hf_inference":
            return self.qwen
        # Any other provider creation should not be attempted when forcing Qwen
        return _FailingProvider()

    def register_provider(self, name: str, provider_class: Any) -> None:
        pass


@pytest.mark.parametrize(
    "user_prompt",
    [
        "hello world",
        "Please ULTRATHINK about this complex task",  # ensure ultrathink route is ignored
    ],
)
def test_model_orchestrator_forces_qwen3_hf_inference(user_prompt: str, monkeypatch) -> None:
    # Set FORCE_MODEL to bypass all routing logic
    monkeypatch.setenv("FORCE_MODEL", "qwen3_hf_inference")

    qwen = _FakeQwenProvider()
    factory = _FakeProviderFactory(qwen)
    orch = ModelOrchestrator(provider_factory=factory)

    result = orch.generate([
        {"role": "user", "content": user_prompt}
    ])

    assert result == "QWEN_OK"
    assert qwen.called is True
    assert factory.requested == ["qwen3_hf_inference"]


def test_no_fallback_to_other_models_when_forced(monkeypatch) -> None:
    # Set FORCE_MODEL to bypass fallback logic
    monkeypatch.setenv("FORCE_MODEL", "qwen3_hf_inference")

    qwen = _FakeQwenProvider()
    factory = _FakeProviderFactory(qwen)
    orch = ModelOrchestrator(provider_factory=factory, enable_fallback=True, max_fallback_attempts=3)

    # Even if we signal an error-like prompt, the orchestrator must stick to qwen only
    result = orch.generate([
        {"role": "user", "content": "trigger some edge case"}
    ])

    assert result == "QWEN_OK"
    assert qwen.called is True
    assert factory.requested == ["qwen3_hf_inference"]

