"""Structured logging utilities using structlog."""

import logging
from typing import Any

import structlog


def setup_logging(
    level: str = "INFO",
    json_logs: bool = False,
    include_timestamp: bool = True,
) -> None:
    """Configure structlog for the application.

    Args:
        level: Logging level string (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        json_logs: If True, use JSON renderer; otherwise use console renderer.
        include_timestamp: If True, include ISO timestamp in log records.
    """
    logging.basicConfig(level=getattr(logging, level, logging.INFO))

    processors: list[Any] = [
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    if include_timestamp:
        processors.insert(0, structlog.processors.TimeStamper(fmt="iso"))

    if json_logs:
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> Any:
    """Return a structlog logger bound to the given name.

    Args:
        name: Logger name, typically the module name.

    Returns:
        A structlog BoundLogger instance.
    """
    return structlog.get_logger(name)


def log_performance(
    logger: Any,
    operation: str,
    duration_ms: float,
    success: bool,
    **kwargs: Any,
) -> None:
    """Log a performance metric.

    Args:
        logger: Logger instance to write to.
        operation: Name of the operation being measured.
        duration_ms: Duration in milliseconds (rounded to 2 decimal places).
        success: Whether the operation succeeded.
        **kwargs: Additional key-value pairs to include in the log entry.
    """
    logger.info(
        "performance",
        operation=operation,
        duration_ms=round(duration_ms, 2),
        success=success,
        **kwargs,
    )
