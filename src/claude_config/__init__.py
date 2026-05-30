"""Claude Code Configuration package.

Provides settings management and structured logging utilities for Claude Code
projects. The public names (``Settings`` and the logging helpers) are exposed
lazily via :pep:`562` ``__getattr__`` so importing a lightweight CLI submodule
(for example ``claude_config.compliance.log_render``) does not pull pydantic or
structlog. This keeps the path-invoked shims under ``scripts/`` free of heavy
runtime dependencies they never use.
"""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from claude_config.core.config import Settings
    from claude_config.utils.logging import (
        get_logger,
        log_performance,
        setup_logging,
    )

__version__ = "1.0.0"
__author__ = "Byron Williams"
__email__ = "byronawilliams@gmail.com"

__all__ = [
    "Settings",
    "__author__",
    "__email__",
    "__version__",
    "get_logger",
    "log_performance",
    "setup_logging",
]

# Public name -> module that defines it. Imported on first attribute access.
_LOGGING_MODULE = "claude_config.utils.logging"
_LAZY_EXPORTS: dict[str, str] = {
    "Settings": "claude_config.core.config",
    "get_logger": _LOGGING_MODULE,
    "log_performance": _LOGGING_MODULE,
    "setup_logging": _LOGGING_MODULE,
}


def __getattr__(name: str) -> Any:
    """Resolve a public export lazily on first access.

    Args:
        name: Attribute requested from the ``claude_config`` package.

    Returns:
        The named object imported from its defining module.

    Raises:
        AttributeError: If ``name`` is not a known public export.
    """
    module_path = _LAZY_EXPORTS.get(name)
    if module_path is None:
        msg = f"module 'claude_config' has no attribute '{name}'"
        raise AttributeError(msg)
    return getattr(importlib.import_module(module_path), name)


def __dir__() -> list[str]:
    """Return public attribute names so lazy exports stay discoverable.

    Returns:
        Sorted module globals combined with the lazily exported public
        names, so :pep:`562` exports appear in ``dir()`` and REPL
        tab-completion despite not being eagerly bound.
    """
    return sorted({*globals(), *__all__})
