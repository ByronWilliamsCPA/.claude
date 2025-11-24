"""Unit tests for configuration settings."""

import pytest


class TestSettings:
    """Test configuration settings.

    Tests for the Settings class covering:
    - Default values
    - Environment variable overrides
    - Keyword argument overrides
    - Type validation
    """

    @pytest.mark.unit
    def test_settings_default_values(self) -> None:
        """Verify Settings initializes with correct defaults.

        This test verifies that when no environment variables or
        keyword arguments are provided, Settings uses sensible defaults.
        """
        from claude_config.core.config import Settings

        settings = Settings()

        assert settings.log_level == "INFO"
        assert settings.json_logs is False
        assert settings.include_timestamp is True

    @pytest.mark.unit
    def test_settings_keyword_arguments(self) -> None:
        """Verify Settings keyword arguments override defaults.

        This test verifies that keyword arguments passed to Settings
        take precedence over defaults.
        """
        from claude_config.core.config import Settings

        settings = Settings(
            log_level="DEBUG",
            json_logs=True,
            include_timestamp=False,
        )

        assert settings.log_level == "DEBUG"
        assert settings.json_logs is True
        assert settings.include_timestamp is False

    @pytest.mark.unit
    def test_settings_valid_log_levels(self) -> None:
        """Verify Settings accepts all valid log levels.

        This test ensures all standard Python log levels are accepted.
        """
        from claude_config.core.config import Settings

        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

        for level in valid_levels:
            settings = Settings(log_level=level)
            assert settings.log_level == level
