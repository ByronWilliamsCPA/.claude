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


def test_all_public_names_have_a_lazy_export():
    # Guard against drift: every non-dunder name promised by __all__ must
    # have a backing entry in _LAZY_EXPORTS, or `from claude_config import *`
    # would raise AttributeError at runtime for the missing name.
    public_lazy = {name for name in claude_config.__all__ if not name.startswith("_")}
    assert public_lazy == set(claude_config._LAZY_EXPORTS)


def test_lazy_names_appear_in_dir():
    listed = set(dir(claude_config))
    assert {"Settings", "get_logger", "log_performance", "setup_logging"} <= listed
