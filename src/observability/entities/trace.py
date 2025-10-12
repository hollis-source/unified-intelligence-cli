"""Tracing domain entities for distributed observability.

Entities represent core domain concepts for distributed tracing:
- TraceStatus: Enumeration of trace outcomes
- Span: Individual operation within a trace
- Trace: Complete distributed trace with timing and metadata

All entities are immutable (frozen dataclasses) following Clean Architecture principles.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional
import uuid


class TraceStatus(str, Enum):
    """Status of a completed trace.

    Represents the outcome of a traced operation.
    """

    SUCCESS = "success"
    ERROR = "error"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"

    def is_failure(self) -> bool:
        """Check if status represents a failure."""
        return self in (TraceStatus.ERROR, TraceStatus.TIMEOUT, TraceStatus.CANCELLED)


@dataclass(frozen=True)
class Span:
    """Individual operation within a distributed trace.

    Immutable entity representing a single span in a trace.
    A span represents a unit of work with timing and metadata.
    """

    span_id: str
    trace_id: str
    parent_span_id: Optional[str]
    operation_name: str
    start_time: datetime
    end_time: Optional[datetime] = None
    status: TraceStatus = TraceStatus.SUCCESS
    tags: Dict[str, str] = field(default_factory=dict)
    logs: List[Dict[str, str]] = field(default_factory=list)

    def __post_init__(self):
        """Validate span data."""
        if not self.span_id or not self.span_id.strip():
            raise ValueError("Span ID cannot be empty")
        if not self.trace_id or not self.trace_id.strip():
            raise ValueError("Trace ID cannot be empty")
        if not self.operation_name or not self.operation_name.strip():
            raise ValueError("Operation name cannot be empty")

    def is_complete(self) -> bool:
        """Check if span has completed."""
        return self.end_time is not None

    def duration_ms(self) -> Optional[float]:
        """Calculate span duration in milliseconds.

        Returns:
            Duration in milliseconds, or None if span not complete
        """
        if not self.is_complete():
            return None

        duration = self.end_time - self.start_time
        return duration.total_seconds() * 1000

    def is_slow(self, threshold_ms: float = 1000.0) -> bool:
        """Check if span exceeds duration threshold.

        Args:
            threshold_ms: Threshold in milliseconds (default 1000ms = 1s)

        Returns:
            True if span duration exceeds threshold
        """
        duration = self.duration_ms()
        if duration is None:
            return False
        return duration > threshold_ms


@dataclass(frozen=True)
class Trace:
    """Complete distributed trace representing a request/workflow.

    Immutable entity tracking a request flow through the system.
    Contains root span and all child spans with timing and metadata.
    """

    trace_id: str
    operation_name: str
    start_time: datetime
    end_time: Optional[datetime] = None
    status: TraceStatus = TraceStatus.SUCCESS
    tags: Dict[str, str] = field(default_factory=dict)
    baggage: Dict[str, str] = field(default_factory=dict)  # Cross-service context
    spans: List[Span] = field(default_factory=list)
    error_message: Optional[str] = None

    def __post_init__(self):
        """Validate trace data."""
        if not self.trace_id or not self.trace_id.strip():
            raise ValueError("Trace ID cannot be empty")
        if not self.operation_name or not self.operation_name.strip():
            raise ValueError("Operation name cannot be empty")

    @staticmethod
    def create(operation_name: str, tags: Optional[Dict[str, str]] = None) -> "Trace":
        """Factory method to create a new trace.

        Args:
            operation_name: Name of the root operation
            tags: Optional metadata tags

        Returns:
            New Trace with generated trace_id
        """
        return Trace(
            trace_id=str(uuid.uuid4()),
            operation_name=operation_name,
            start_time=datetime.now(),
            tags=tags or {},
        )

    def is_complete(self) -> bool:
        """Check if trace has completed."""
        return self.end_time is not None

    def duration_ms(self) -> Optional[float]:
        """Calculate total trace duration in milliseconds.

        Returns:
            Duration in milliseconds, or None if trace not complete
        """
        if not self.is_complete():
            return None

        duration = self.end_time - self.start_time
        return duration.total_seconds() * 1000

    def is_slow(self, threshold_ms: float = 30000.0) -> bool:
        """Check if trace exceeds performance threshold.

        Args:
            threshold_ms: Threshold in milliseconds (default 30000ms = 30s)

        Returns:
            True if trace duration exceeds threshold
        """
        duration = self.duration_ms()
        if duration is None:
            return False
        return duration > threshold_ms

    def has_errors(self) -> bool:
        """Check if trace or any span has errors."""
        if self.status.is_failure():
            return True
        return any(span.status.is_failure() for span in self.spans)

    def span_count(self) -> int:
        """Get total number of spans in trace."""
        return len(self.spans)

    def get_span(self, span_id: str) -> Optional[Span]:
        """Get span by ID.

        Args:
            span_id: Span identifier

        Returns:
            Span if found, None otherwise
        """
        for span in self.spans:
            if span.span_id == span_id:
                return span
        return None

    def get_root_span(self) -> Optional[Span]:
        """Get root span (span with no parent).

        Returns:
            Root span if exists, None otherwise
        """
        for span in self.spans:
            if span.parent_span_id is None:
                return span
        return None

    def get_child_spans(self, parent_span_id: str) -> List[Span]:
        """Get all child spans of a parent span.

        Args:
            parent_span_id: Parent span identifier

        Returns:
            List of child spans
        """
        return [span for span in self.spans if span.parent_span_id == parent_span_id]

    def finish(self, status: TraceStatus, error_message: Optional[str] = None) -> "Trace":
        """Create a new Trace with end_time and status set.

        Since Trace is immutable, this returns a new instance.

        Args:
            status: Final trace status
            error_message: Optional error message if status is ERROR

        Returns:
            New Trace instance with completion data
        """
        return Trace(
            trace_id=self.trace_id,
            operation_name=self.operation_name,
            start_time=self.start_time,
            end_time=datetime.now(),
            status=status,
            tags=self.tags,
            baggage=self.baggage,
            spans=self.spans,
            error_message=error_message,
        )

    def add_span(self, span: Span) -> "Trace":
        """Create a new Trace with additional span.

        Since Trace is immutable, this returns a new instance.

        Args:
            span: Span to add

        Returns:
            New Trace instance with span added
        """
        if span.trace_id != self.trace_id:
            raise ValueError(f"Span trace_id {span.trace_id} does not match trace {self.trace_id}")

        return Trace(
            trace_id=self.trace_id,
            operation_name=self.operation_name,
            start_time=self.start_time,
            end_time=self.end_time,
            status=self.status,
            tags=self.tags,
            baggage=self.baggage,
            spans=self.spans + [span],
            error_message=self.error_message,
        )
