# OpenTelemetry Tracing

This project includes minimal OpenTelemetry tracing for key operations.

Quick start:
- Development: set OTEL_TRACES_EXPORTER=console to log spans to stdout
- Production: set OTEL_EXPORTER_OTLP_ENDPOINT (e.g., http://collector:4318) to export via OTLP/HTTP

Env vars:
- OTEL_SERVICE_NAME (default: unified-intelligence-cli)
- OTEL_TRACES_EXPORTER=console|otlp|auto (default: auto)
- OTEL_EXPORTER_OTLP_ENDPOINT (e.g., http://localhost:4318)
- OTEL_EXPORTER_OTLP_HEADERS (optional, comma-separated key=value)

Instrumented areas:
- CLI coordinate and workflow execution
- Hybrid orchestrator routing and execution paths

Overhead is kept minimal using BatchSpanProcessor.
