"""Integration tests demonstrating end-to-end workflows.

These tests verify that multiple components work together
to accomplish realistic tasks.
"""

import pytest


class TestSettingsLoggingIntegration:
    """Integration tests for Settings and logging working together."""

    @pytest.mark.integration
    def test_settings_and_logging_integration(self) -> None:
        """Verify Settings and logging work together.

        This test demonstrates that configuration and logging
        can be integrated properly.
        """
        from claude_config.core.config import Settings
        from claude_config.utils.logging import get_logger

        settings = Settings(log_level="INFO")
        logger = get_logger(__name__)

        assert settings.log_level == "INFO"
        assert logger is not None

    @pytest.mark.integration
    def test_full_logging_setup_with_settings(self) -> None:
        """Verify full logging setup using Settings.

        This test ensures that settings can drive logging configuration.
        """
        from claude_config.core.config import Settings
        from claude_config.utils.logging import get_logger, setup_logging

        settings = Settings(log_level="DEBUG", json_logs=False)
        setup_logging(
            level=settings.log_level,
            json_logs=settings.json_logs,
            include_timestamp=settings.include_timestamp,
        )
        import structlog

        logger = get_logger(__name__)

        # Should be able to log without errors
        logger.debug("Test debug message", test_key="test_value")
        # Verify structlog configuration is active after settings-driven setup
        assert hasattr(logger, "bind"), "logger should be a structlog bound logger"
        config = structlog.get_config()
        assert config["wrapper_class"] is structlog.stdlib.BoundLogger


class TestPackageImports:
    """Integration tests for package imports."""

    @pytest.mark.integration
    def test_package_imports(self) -> None:
        """Verify all public API imports work correctly.

        This test ensures that users can import the public API
        from the package root without errors.
        """
        # Test importing main package
        import claude_config

        assert hasattr(claude_config, "__version__")
        assert hasattr(claude_config, "Settings")
        assert hasattr(claude_config, "get_logger")
        assert hasattr(claude_config, "setup_logging")

        # Test importing from submodules
        from claude_config.utils import get_logger

        assert callable(get_logger)

        from claude_config.core import Settings

        assert Settings is not None

    @pytest.mark.integration
    def test_direct_imports_from_package(self) -> None:
        """Verify direct imports from package root work.

        This test ensures the enhanced __init__.py exports work.
        """
        from claude_config import Settings, get_logger, log_performance, setup_logging

        # All imports should be the correct types
        assert Settings is not None
        assert callable(get_logger)
        assert callable(log_performance)
        assert callable(setup_logging)

        # Should be able to use them
        settings = Settings()
        assert settings.log_level == "INFO"

        logger = get_logger("test")
        assert logger is not None
