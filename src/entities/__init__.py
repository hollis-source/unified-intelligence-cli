"""Core business entities - Pure domain models with no external dependencies."""

from .agent import Agent, Task

__all__ = ["Agent", "Task"]