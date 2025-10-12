"""Test JSON logging configuration.

Verifies JSON logging works correctly for production deployments.
"""

import os
import json
import logging
import io
from src.observability.json_logger import JsonFormatter, configure_logging


def test_json_formatter():
    """Test JsonFormatter produces valid JSON output."""
    # Create formatter
    formatter = JsonFormatter()

    # Create logger with string stream
    logger = logging.getLogger("test_json")
    logger.setLevel(logging.INFO)
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    # Log a message
    logger.info("Test message")

    # Get output
    output = stream.getvalue().strip()

    # Verify it's valid JSON
    data = json.loads(output)

    # Verify required fields
    assert "timestamp" in data
    assert "level" in data
    assert data["level"] == "INFO"
    assert "message" in data
    assert data["message"] == "Test message"
    assert "logger" in data
    assert data["logger"] == "test_json"


def test_configure_logging_text_format():
    """Test configure_logging with text format (default)."""
    # Configure with text format
    configure_logging(level="INFO", format_type="text")

    # Get root logger
    logger = logging.getLogger()

    # Verify level is INFO
    assert logger.level == logging.INFO

    # Verify has handler
    assert len(logger.handlers) > 0


def test_configure_logging_json_format():
    """Test configure_logging with JSON format."""
    # Set environment variable
    os.environ["PB_LOG_FORMAT"] = "json"
    os.environ["PB_LOG_LEVEL"] = "DEBUG"

    # Configure
    configure_logging()

    # Get root logger
    logger = logging.getLogger()

    # Verify level is DEBUG
    assert logger.level == logging.DEBUG

    # Verify has JsonFormatter
    assert len(logger.handlers) > 0
    handler = logger.handlers[0]
    assert isinstance(handler.formatter, JsonFormatter)

    # Clean up env vars
    del os.environ["PB_LOG_FORMAT"]
    del os.environ["PB_LOG_LEVEL"]


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
