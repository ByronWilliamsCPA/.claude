"""Unit tests for package initialization and metadata."""

import pytest


class TestPackageInitialization:
    """Test package initialization and version info."""

    @pytest.mark.unit
    def test_package_version_exists(self) -> None:
        """Verify package has __version__ attribute.

        This test verifies that the package exports a version string
        that follows semantic versioning.
        """
        from claude_config import __version__

        assert __version__ is not None
        assert isinstance(__version__, str)
        assert len(__version__) > 0

    @pytest.mark.unit
    def test_package_author_exists(self) -> None:
        """Verify package has __author__ attribute.

        This test verifies that the package exports author information.
        """
        from claude_config import __author__, __email__

        assert __author__ is not None
        assert isinstance(__author__, str)
        assert __email__ is not None
        assert isinstance(__email__, str)

    @pytest.mark.unit
    def test_public_api_exports(self) -> None:
        """Verify package exports expected public API.

        This test ensures the main package exports the expected
        classes and functions for user convenience.
        """
        from claude_config import Settings, get_logger, log_performance, setup_logging

        assert Settings is not None
        assert callable(get_logger)
        assert callable(log_performance)
        assert callable(setup_logging)
