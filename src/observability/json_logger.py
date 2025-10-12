"""JSON Logging Configuration for Production.

Sprint 1: Production Deployment - P1.1
Provides structured JSON logging for container environments.

Clean Architecture: Infrastructure adapter for observability.
SOLID: SRP - Single responsibility for logging configuration.
"""

import logging
import json
import os
import sys
from datetime import datetime
from typing import Any, Dict, Optional


class JsonFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging.

    Outputs logs in JSON format for easy parsing by log aggregation tools
    (ELK, Loki, CloudWatch, etc.).
    """

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON.

        Args:
            record: Log record to format

        Returns:
            JSON-formatted log string
        """
        log_data: Dict[str, Any] = {
            "timestamp": datetime.utcfromtimestamp(record.created).isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add extra fields if present
        if hasattr(record, "extra_fields"):
            log_data.update(record.extra_fields)

        # Add context fields (project_id, task_id, etc.)
        for field in ["project_id", "task_id", "agent_name", "request_id"]:
            if hasattr(record, field):
                log_data[field] = getattr(record, field)

        return json.dumps(log_data)


def configure_logging(
    level: str = "INFO",
    format_type: str = "text",
    logger_name: Optional[str] = None
) -> None:
    """Configure logging for the application.

    Reads configuration from environment variables:
    - PB_LOG_LEVEL: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    - PB_LOG_FORMAT: Format type (json, text)

    Args:
        level: Default logging level if PB_LOG_LEVEL not set
        format_type: Default format type if PB_LOG_FORMAT not set
        logger_name: Specific logger to configure (None = root logger)
    """
    # Read from environment with fallbacks
    log_level = os.environ.get("PB_LOG_LEVEL", level).upper()
    log_format = os.environ.get("PB_LOG_FORMAT", format_type).lower()

    # Map string level to logging constant
    level_map = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL,
    }
    numeric_level = level_map.get(log_level, logging.INFO)

    # Select formatter
    if log_format == "json":
        formatter = JsonFormatter()
    else:
        # Text format for development
        formatter = logging.Formatter(
            fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

    # Configure handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    # Get logger (root or specific)
    logger = logging.getLogger(logger_name)
    logger.setLevel(numeric_level)

    # Remove existing handlers to avoid duplicates
    logger.handlers.clear()

    # Add new handler
    logger.addHandler(handler)

    # Prevent propagation to root logger if configuring specific logger
    if logger_name:
        logger.propagate = False


def get_logger(name: str) -> logging.Logger:
    """Get a logger with the given name.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)
