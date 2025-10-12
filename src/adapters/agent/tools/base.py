"""Agent tool interface (adapter layer).

Clean Architecture: Keep domain-agnostic, framework-free abstractions.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict


class AgentTool(ABC):
    """Base interface for agent tools exposed to the ReAct executor.

    Requirements:
    - name: Unique tool identifier referenced by the LLM (snake_case)
    - description: Short explanation for prompt/context
    - parameters: JSON schema-like dict describing inputs
    - execute(**kwargs) -> str: Perform the action and return a string result
    """

    @property
    def name(self) -> str:
        """Tool name for LLM to reference. Reads subclass class attribute or property."""
        # Prefer subclass attribute defined directly on the class to avoid picking up base property
        raw = self.__class__.__dict__.get("name", None)
        if isinstance(raw, property):
            return raw.__get__(self, self.__class__)
        if isinstance(raw, str):
            return raw
        raise NotImplementedError("Tool must define class attribute or @property 'name'")

    @property
    def description(self) -> str:
        """Human-readable description presented to the LLM. Reads subclass class attr or property."""
        raw = self.__class__.__dict__.get("description", None)
        if isinstance(raw, property):
            return raw.__get__(self, self.__class__)
        if isinstance(raw, str):
            return raw
        raise NotImplementedError("Tool must define class attribute or @property 'description'")

    @property
    @abstractmethod
    def parameters(self) -> Dict[str, Any]:  # pragma: no cover - abstract contract
        """JSON-schema-like parameters description used in prompts."""
        raise NotImplementedError

    @abstractmethod
    def execute(self, **kwargs: Any) -> str:  # pragma: no cover - abstract contract
        """Execute the tool with given keyword arguments and return result as string."""
        raise NotImplementedError

