"""In-memory tracer adapter for testing and development.

Stores traces in memory without requiring external backend.
Useful for unit tests and local development.
"""

from datetime import datetime
from typing import Dict, List, Optional
import uuid
import logging

from ..interfaces import ITracer
from ..entities import Trace, Span, TraceStatus

logger = logging.getLogger(__name__)


class InMemoryTracer(ITracer):
    """In-memory tracer implementation for testing.

    Stores traces in a dictionary keyed by trace_id.
    Provides simple implementation of ITracer contract without
    requiring external dependencies (Jaeger, Zipkin, etc.).

    Thread-safe for single-threaded test environments.
    For production, use OTelTracer with proper export backend.
    """

    def __init__(self):
        """Initialize empty trace storage."""
        self._traces: Dict[str, Trace] = {}
        self._exported_traces: List[Trace] = []

    def start_trace(self, operation_name: str, tags: Optional[Dict[str, str]] = None) -> Trace:
        """Start a new distributed trace.

        Args:
            operation_name: Name of the root operation
            tags: Optional metadata tags

        Returns:
            New Trace with generated trace_id

        Raises:
            ValueError: If operation_name is empty
        """
        if not operation_name or not operation_name.strip():
            raise ValueError("Operation name cannot be empty")

        trace = Trace.create(operation_name=operation_name, tags=tags)
        self._traces[trace.trace_id] = trace

        logger.debug(f"Started trace {trace.trace_id}: {operation_name}")
        return trace

    def finish_trace(
        self, trace: Trace, status: TraceStatus, error_message: Optional[str] = None
    ) -> Trace:
        """Finish an existing trace.

        Args:
            trace: Trace to finish
            status: Final status
            error_message: Optional error message

        Returns:
            Finished trace with end_time set

        Raises:
            ValueError: If trace already finished
        """
        if trace.is_complete():
            raise ValueError(f"Trace {trace.trace_id} already finished")

        finished_trace = trace.finish(status=status, error_message=error_message)
        self._traces[trace.trace_id] = finished_trace

        logger.debug(
            f"Finished trace {trace.trace_id}: {status.value} "
            f"(duration: {finished_trace.duration_ms():.2f}ms)"
        )

        return finished_trace

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
            span_name: Name of the span
            parent_span_id: Optional parent span ID
            tags: Optional metadata tags

        Returns:
            Tuple of (updated_trace, new_span)

        Raises:
            ValueError: If parent_span_id not found in trace
        """
        if not span_name or not span_name.strip():
            raise ValueError("Span name cannot be empty")

        # Validate parent span exists if specified
        if parent_span_id is not None:
            parent_span = trace.get_span(parent_span_id)
            if parent_span is None:
                raise ValueError(f"Parent span {parent_span_id} not found in trace {trace.trace_id}")

        # Create new span
        span = Span(
            span_id=str(uuid.uuid4()),
            trace_id=trace.trace_id,
            parent_span_id=parent_span_id,
            operation_name=span_name,
            start_time=datetime.now(),
            tags=tags or {},
        )

        # Add span to trace (immutable update)
        updated_trace = trace.add_span(span)
        self._traces[trace.trace_id] = updated_trace

        logger.debug(f"Added span {span.span_id} to trace {trace.trace_id}: {span_name}")
        return updated_trace, span

    def finish_span(self, trace: Trace, span: Span, status: TraceStatus) -> tuple[Trace, Span]:
        """Finish a span.

        Args:
            trace: Trace containing the span
            span: Span to finish
            status: Final span status

        Returns:
            Tuple of (updated_trace, finished_span)

        Raises:
            ValueError: If span not found or already finished
        """
        if span.is_complete():
            raise ValueError(f"Span {span.span_id} already finished")

        # Verify span exists in trace
        existing_span = trace.get_span(span.span_id)
        if existing_span is None:
            raise ValueError(f"Span {span.span_id} not found in trace {trace.trace_id}")

        # Create finished span
        finished_span = Span(
            span_id=span.span_id,
            trace_id=span.trace_id,
            parent_span_id=span.parent_span_id,
            operation_name=span.operation_name,
            start_time=span.start_time,
            end_time=datetime.now(),
            status=status,
            tags=span.tags,
            logs=span.logs,
        )

        # Replace span in trace
        updated_spans = [
            finished_span if s.span_id == span.span_id else s for s in trace.spans
        ]

        updated_trace = Trace(
            trace_id=trace.trace_id,
            operation_name=trace.operation_name,
            start_time=trace.start_time,
            end_time=trace.end_time,
            status=trace.status,
            tags=trace.tags,
            baggage=trace.baggage,
            spans=updated_spans,
            error_message=trace.error_message,
        )

        self._traces[trace.trace_id] = updated_trace

        logger.debug(
            f"Finished span {span.span_id}: {status.value} "
            f"(duration: {finished_span.duration_ms():.2f}ms)"
        )

        return updated_trace, finished_span

    def export_traces(self, traces: List[Trace]) -> None:
        """Export traces to in-memory storage.

        For InMemoryTracer, this just moves traces to exported list
        for inspection in tests.

        Args:
            traces: List of traces to export
        """
        self._exported_traces.extend(traces)
        logger.debug(f"Exported {len(traces)} traces (total exported: {len(self._exported_traces)})")

    def get_trace(self, trace_id: str) -> Optional[Trace]:
        """Retrieve trace by ID.

        Args:
            trace_id: Trace identifier

        Returns:
            Trace if found, None otherwise
        """
        return self._traces.get(trace_id)

    def get_active_traces(self) -> List[Trace]:
        """Get all active (not finished) traces.

        Returns:
            List of active traces
        """
        return [trace for trace in self._traces.values() if not trace.is_complete()]

    def get_all_traces(self) -> List[Trace]:
        """Get all traces (active and finished).

        Returns:
            List of all traces

        Note:
            Not part of ITracer interface. Useful for testing.
        """
        return list(self._traces.values())

    def get_exported_traces(self) -> List[Trace]:
        """Get all exported traces.

        Returns:
            List of exported traces

        Note:
            Not part of ITracer interface. Useful for testing exports.
        """
        return self._exported_traces.copy()

    def clear(self) -> None:
        """Clear all traces.

        Note:
            Not part of ITracer interface. Useful for test cleanup.
        """
        self._traces.clear()
        self._exported_traces.clear()
        logger.debug("Cleared all traces")
