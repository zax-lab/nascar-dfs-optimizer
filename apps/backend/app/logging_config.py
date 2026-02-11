"""
Structured logging configuration for Axiomatic NASCAR DFS backend.

This module provides JSON structured logging with correlation ID support
for distributed tracing and observability platform integration.

Key features:
- JSON log format for easy parsing by observability tools
- RotatingFileHandler with 10MB max size and 5 backup files
- Async-safe context variable support for correlation IDs
- Stack trace capture for error logging
- ISO 8601 timestamps

Usage:
    from app.logging_config import configure_logging, get_logger

    # Configure logging at application startup
    configure_logging(log_level="INFO")

    # Get logger for module
    logger = get_logger(__name__)
    logger.info("Message", extra_field="value")
"""

import logging
import structlog
from logging.handlers import RotatingFileHandler
from pathlib import Path


def configure_logging(log_level: str = "INFO") -> None:
    """
    Configure structured logging with JSON output and file rotation.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)

    This configures both structlog and stdlib logging to work together:
    - structlog handles JSON formatting and context binding
    - stdlib handles log levels and handlers
    """
    # Create logs directory
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    # File handler with rotation (10MB max, 5 backups)
    file_handler = RotatingFileHandler(
        log_dir / "app.log",
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
    )
    file_handler.setLevel(log_level)

    # Stream handler for console output (useful for local development)
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(log_level)

    # Configure structlog processors
    # Processors run in order to transform log entries
    structlog.configure(
        processors=[
            # Merge context variables (correlation ID, request ID, etc.)
            structlog.contextvars.merge_contextvars,
            # Add log level (INFO, ERROR, etc.)
            structlog.stdlib.add_log_level,
            # Add ISO 8601 timestamp
            structlog.processors.TimeStamper(fmt="iso"),
            # Add stack info (file, line number) for debugging
            structlog.processors.StackInfoRenderer(),
            # Format exception info with stack trace
            structlog.processors.format_exc_info,
            # Render final output as JSON
            structlog.processors.JSONRenderer(),
        ],
        # Use stdlib BoundLogger (works with standard logging handlers)
        wrapper_class=structlog.stdlib.BoundLogger,
        # Use dict for context storage
        context_class=dict,
        # Use stdlib LoggerFactory
        logger_factory=structlog.stdlib.LoggerFactory(),
        # Cache logger on first use for performance
        cache_logger_on_first_use=True,
    )

    # Configure stdlib logging (integrates with structlog)
    logging.basicConfig(
        level=log_level,
        handlers=[stream_handler, file_handler],
        format="%(message)s",  # Let structlog handle all formatting
    )


def get_logger(name: str = None) -> structlog.stdlib.BoundLogger:
    """
    Get a structured logger for a module.

    Args:
        name: Logger name (usually __name__)

    Returns:
        Structured logger with JSON output

    Example:
        from app.logging_config import get_logger

        logger = get_logger(__name__)
        logger.info("Processing request", user_id=123, action="submit")
    """
    return structlog.get_logger(name)
