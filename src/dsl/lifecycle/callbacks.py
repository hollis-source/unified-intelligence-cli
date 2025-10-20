"""DSL execution lifecycle callbacks (lightweight, optional).

Adapters like the CLI executor and interpreter can call these hooks to emit
execution events without coupling to a heavy state machine.

No-op defaults keep integration simple and safe.
"""
from __future__ import annotations

from typing import Any


class DSLExecutionCallbacks:
    """Interface for receiving DSL execution events.

    All methods are optional for implementers; default implementations are no-ops.
    """

    def on_start(self, program_text: str) -> None:
        pass

    def on_before_node(self, node: Any) -> None:
        pass

    def on_after_node(self, node: Any, result: Any) -> None:
        pass

    def on_finish(self, result: Any) -> None:
        pass

    def on_error(self, error: Exception) -> None:
        pass


class NullDSLExecutionCallbacks(DSLExecutionCallbacks):
    """Explicit no-op implementation for convenience."""

    # Inherit no-op implementations
    ...

