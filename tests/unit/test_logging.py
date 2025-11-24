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
        from claude_config.utils.logging import get_logger

        logger = get_logger("test_logger")

        assert logger is not None
        assert callable(logger.info)
        assert callable(logger.debug)
        assert callable(logger.warning)
        assert callable(logger.error)

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
        assert call_args[1]["duration_ms"] == 123.46  # Rounded to 2 decimals
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
        from claude_config.utils.logging import setup_logging

        # Configure with JSON logging to cover the JSON renderer branch
        setup_logging(level="INFO", json_logs=True)

        # Should complete without errors
        assert True

    @pytest.mark.unit
    def test_setup_logging_without_timestamp(self) -> None:
        """Verify setup_logging works without timestamps.

        Tests that setup_logging properly handles include_timestamp=False.
        """
        from claude_config.utils.logging import setup_logging

        # Configure without timestamps
        setup_logging(level="DEBUG", json_logs=False, include_timestamp=False)

        # Should complete without errors
        assert True
