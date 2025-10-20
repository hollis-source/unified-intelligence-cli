"""Executor entities for task execution abstraction.

This module provides executor interfaces for decoupling task planning
from execution, supporting multiple execution backends.
"""

from .executor import Executor, ExecutorStatus, ExecutionResult, LocalExecutor, ExecutorPool

__all__ = ["Executor", "ExecutorStatus", "ExecutionResult", "LocalExecutor", "ExecutorPool"]
