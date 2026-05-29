"""Tests for lazy (PEP 562) public exports on the claude_config package."""

import pytest

import claude_config


def test_settings_is_lazily_exported():
    from claude_config.core.config import Settings

    assert claude_config.Settings is Settings


def test_logging_helpers_are_lazily_exported():
    assert callable(claude_config.setup_logging)
    assert callable(claude_config.get_logger)
    assert callable(claude_config.log_performance)


def test_unknown_attribute_raises_attribute_error():
    with pytest.raises(AttributeError, match="has no attribute 'does_not_exist'"):
        _ = claude_config.does_not_exist
