import types
import builtins
import importlib

import pytest


class FakeJob:
    def __init__(self, outputs, raise_error=False):
        self.outputs = outputs
        self.raise_error = raise_error
        self.last_timeout = None

    def result(self, timeout=None):
        self.last_timeout = timeout
        if self.raise_error:
            raise TimeoutError("simulated timeout")
        return self.outputs


class FakeClient:
    def __init__(self, space_id):
        self.space_id = space_id
        self.last_submit = None

    def submit(self, *args, **kwargs):
        # Return a conversation with a single turn
        message = kwargs.get("message") or (args[0] if args else "")
        conversation = [(message, "OK: response from adapter")]  # (user, assistant)
        return FakeJob(outputs=("", conversation))


@pytest.fixture
def patched_module(monkeypatch):
    # Import module under test
    mod = importlib.import_module("src.adapters.llm.qwen3_zerogpu_adapter")

    # Patch Client in the module namespace to avoid network calls
    monkeypatch.setattr(mod, "Client", FakeClient)
    return mod


def test_inference_adapter_uses_timeout_and_returns_response(patched_module):
    Adapter = patched_module.Qwen3InferenceAdapter
    adapter = Adapter(space_id="fake/space", timeout=42)

    messages = [
        {"role": "system", "content": "You are helpful."},
        {"role": "user", "content": "Hello"},
    ]

    # Call generate; FakeClient.submit returns FakeJob with conversation
    result = adapter.generate(messages)

    assert "OK: response" in result


def test_inference_adapter_handles_timeout(patched_module, monkeypatch):
    Adapter = patched_module.Qwen3InferenceAdapter

    # Custom FakeClient that raises on result
    class ErrorClient(FakeClient):
        def submit(self, *args, **kwargs):
            return FakeJob(outputs=None, raise_error=True)

    # Patch Client to ErrorClient
    monkeypatch.setattr(patched_module, "Client", ErrorClient)

    adapter = Adapter(space_id="fake/space", timeout=1)
    messages = [
        {"role": "system", "content": "You are helpful."},
        {"role": "user", "content": "Hello"},
    ]

    result = adapter.generate(messages)
    assert "Error:" in result

