"""Tracer interface for distributed tracing.

Defines the contract for tracer implementations following
Dependency Inversion Principle. Use cases depend on this
interface, not concrete implementations.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional

from ..entities import Trace, Span, TraceStatus


class ITracer(ABC):
    """Interface for distributed tracing.

    Abstracts OpenTelemetry or other tracing backend implementation details.
    Implementations must maintain immutability of Trace and Span entities.

    Contract:
    - start_trace() creates new trace with generated ID
    - finish_trace() returns completed trace (immutable update)
    - add_span() returns trace with new span (immutable update)
    - export_traces() sends traces to backend (Jaeger, Zipkin, etc.)
    - get_trace() retrieves trace by ID for inspection
    """

    @abstractmethod
    def start_trace(self, operation_name: str, tags: Optional[Dict[str, str]] = None) -> Trace:
        """Start a new distributed trace.

        Args:
            operation_name: Name of the root operation (e.g., "project_builder.create_project")
            tags: Optional metadata tags (e.g., {"project_id": "123", "user": "alice"})

        Returns:
            New Trace with generated trace_id and start_time set

        Raises:
            ValueError: If operation_name is empty or invalid
        """
        pass

    @abstractmethod
    def finish_trace(
        self, trace: Trace, status: TraceStatus, error_message: Optional[str] = None
    ) -> Trace:
        """Finish an existing trace.

        Args:
            trace: Trace to finish
            status: Final status (SUCCESS, ERROR, TIMEOUT, CANCELLED)
            error_message: Optional error message if status is ERROR

        Returns:
            New Trace instance with end_time and status set

        Raises:
            ValueError: If trace already finished
        """
        pass

    @abstractmethod
    def add_span(
        self,
        trace: Trace,
        span_name: str,
        parent_span_id: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None,
    ) -> tuple[Trace, Span]:
        """Add a child span to trace.

        Args:
            trace: Parent trace
            span_name: Name of the span (e.g., "llm.generate", "db.query")
            parent_span_id: Optional parent span ID (None for root span)
            tags: Optional metadata tags

        Returns:
            Tuple of (updated_trace, new_span)

        Raises:
            ValueError: If parent_span_id not found in trace
        """
        pass

    @abstractmethod
    def finish_span(self, trace: Trace, span: Span, status: TraceStatus) -> tuple[Trace, Span]:
        """Finish a span.

        Args:
            trace: Trace containing the span
            span: Span to finish
            status: Final span status

        Returns:
            Tuple of (updated_trace, finished_span)

        Raises:
            ValueError: If span not found in trace or already finished
        """
        pass

    @abstractmethod
    def export_traces(self, traces: List[Trace]) -> None:
        """Export traces to backend (Jaeger, Zipkin, etc.).

        Args:
            traces: List of completed traces to export

        Raises:
            RuntimeError: If export fails (network error, backend unavailable)

        Note:
            Should be non-blocking or async in production.
            Failed exports should not crash the application.
        """
        pass

    @abstractmethod
    def get_trace(self, trace_id: str) -> Optional[Trace]:
        """Retrieve trace by ID.

        Args:
            trace_id: Trace identifier

        Returns:
            Trace if found, None otherwise

        Note:
            Useful for testing and debugging.
            Production implementations may not need to implement this
            if traces are immediately exported.
        """
        pass

    @abstractmethod
    def get_active_traces(self) -> List[Trace]:
        """Get all active (not finished) traces.

        Returns:
            List of active traces

        Note:
            Useful for monitoring and debugging.
            May return empty list if implementation doesn't track active traces.
        """
        pass
