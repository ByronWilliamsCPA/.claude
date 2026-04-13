"""Unit tests for logging configuration and utilities."""

from unittest.mock import MagicMock

import pytest


class TestLogging:
    """Test logging configuration and utilities.

    Tests for structured logging setup covering:
    - Logger creation
    - Logging at different levels
    - Performance logging
    """

    @pytest.mark.unit
    def test_get_logger_returns_logger(self) -> None:
        """Verify get_logger returns a functional logger instance.

        This test verifies that get_logger creates a valid structlog
        logger with expected methods.
        """
        import structlog

        from claude_config.utils.logging import get_logger

        logger = get_logger("test_logger")

        assert logger is not None
        # structlog loggers expose bind(); generic objects do not
        assert hasattr(logger, "bind"), "logger should be a structlog bound logger"
        assert callable(logger.info)
        assert callable(logger.debug)
        assert callable(logger.warning)
        assert callable(logger.error)
        # calling a method should not raise
        logger.info("test_message", test_key="value")
        # structlog config should be active
        config = structlog.get_config()
        assert config["wrapper_class"] is structlog.stdlib.BoundLogger

    @pytest.mark.unit
    def test_log_performance(self) -> None:
        """Verify performance logging works correctly.

        This test verifies that log_performance can be called without error
        and properly formats the metrics.
        """
        from claude_config.utils.logging import log_performance

        mock_logger = MagicMock()

        log_performance(
            mock_logger,
            operation="test_operation",
            duration_ms=123.456,
            success=True,
            extra_metric=42,
        )

        assert mock_logger.info.called
        call_args = mock_logger.info.call_args
        assert call_args[0][0] == "performance"
        assert call_args[1]["operation"] == "test_operation"
        assert call_args[1]["duration_ms"] == pytest.approx(
            123.46, rel=1e-6
        )  # float comparison for rounded value
        assert call_args[1]["success"] is True
        assert call_args[1]["extra_metric"] == 42

    @pytest.mark.unit
    def test_log_performance_failure(self) -> None:
        """Verify performance logging handles failure status.

        This test verifies that log_performance correctly logs
        failed operations.
        """
        from claude_config.utils.logging import log_performance

        mock_logger = MagicMock()

        log_performance(
            mock_logger,
            operation="failed_operation",
            duration_ms=500.0,
            success=False,
            error="timeout",
        )

        assert mock_logger.info.called
        call_args = mock_logger.info.call_args
        assert call_args[1]["success"] is False
        assert call_args[1]["error"] == "timeout"


class TestLoggingJSON:
    """Test JSON logging configuration.

    Tests for JSON renderer when json_logs=True.
    """

    @pytest.mark.unit
    def test_json_logging_renderer(self) -> None:
        """Verify JSON renderer is used when json_logs=True.

        Tests that setup_logging properly configures JSON output.
        """
        import structlog

        from claude_config.utils.logging import setup_logging

        setup_logging(level="INFO", json_logs=True)

        processors = structlog.get_config()["processors"]
        assert any(
            isinstance(p, structlog.processors.JSONRenderer) for p in processors
        ), "JSONRenderer should be present when json_logs=True"
        assert not any(
            isinstance(p, structlog.dev.ConsoleRenderer) for p in processors
        ), "ConsoleRenderer should not be present when json_logs=True"

    @pytest.mark.unit
    def test_setup_logging_without_timestamp(self) -> None:
        """Verify setup_logging excludes TimeStamper when include_timestamp=False.

        Tests that setup_logging properly handles include_timestamp=False.
        """
        import structlog

        from claude_config.utils.logging import setup_logging

        setup_logging(level="DEBUG", json_logs=False, include_timestamp=False)

        processors = structlog.get_config()["processors"]
        assert not any(
            isinstance(p, structlog.processors.TimeStamper) for p in processors
        ), "TimeStamper should not be present when include_timestamp=False"
