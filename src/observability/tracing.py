import os
import logging
from contextlib import contextmanager

try:
    from opentelemetry import trace
    from opentelemetry.trace import Status, StatusCode
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    OTEL_AVAILABLE = True
except Exception:  # opentelemetry not installed; degrade gracefully
    OTEL_AVAILABLE = False
    trace = None  # type: ignore

_logger = logging.getLogger(__name__)
_initialized = False


def _build_exporter():
    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    exporter_setting = os.getenv("OTEL_TRACES_EXPORTER", "auto").lower()
    if OTEL_AVAILABLE and (exporter_setting == "console" or (exporter_setting == "auto" and not endpoint)):
        return ConsoleSpanExporter()
    if OTEL_AVAILABLE and endpoint:
        headers = {}
        raw = os.getenv("OTEL_EXPORTER_OTLP_HEADERS", "")
        if raw:
            for kv in raw.split(","):
                if "=" in kv:
                    k, v = kv.split("=", 1)
                    headers[k.strip()] = v.strip()
        return OTLPSpanExporter(endpoint=endpoint, headers=headers or None)
    return None


def init_tracing(service_name: str = "unified-intelligence-cli") -> None:
    global _initialized
    if _initialized:
        return
    if not OTEL_AVAILABLE:
        _logger.debug("OpenTelemetry not installed; tracing disabled")
        _initialized = True
        return
    exporter = _build_exporter()
    resource = Resource.create({"service.name": os.getenv("OTEL_SERVICE_NAME", service_name)})
    provider = TracerProvider(resource=resource)
    if exporter:
        provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    _initialized = True
    _logger.debug("OpenTelemetry tracing initialized (exporter=%s)", exporter.__class__.__name__ if exporter else "none")


def get_tracer(name: str = __name__):
    if not OTEL_AVAILABLE:
        return None
    return trace.get_tracer(name)


@contextmanager
def start_span(name: str, attributes: dict | None = None):
    """Lightweight span helper that degrades to no-op when OTEL is unavailable."""
    if not OTEL_AVAILABLE:
        yield None
        return
    tracer = get_tracer(__name__)
    if tracer is None:
        yield None
        return
    with tracer.start_as_current_span(name) as span:
        try:
            span.set_attribute("operation", name)
        except Exception:
            pass
        if attributes:
            for k, v in attributes.items():
                try:
                    span.set_attribute(k, v)
                except Exception:
                    pass
        try:
            yield span
        except Exception as e:
            span.record_exception(e)
            span.set_status(Status(StatusCode.ERROR, str(e)))
            raise
