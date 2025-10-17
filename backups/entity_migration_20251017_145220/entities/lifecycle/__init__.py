"""Lifecycle entities for meta-operational workflow.

This module provides lifecycle state machine for coordinating
Plan → Verify → Decompose → Execute phases in the unified architecture.
"""

from .lifecycle import Lifecycle, LifecycleState

__all__ = ["Lifecycle", "LifecycleState"]
