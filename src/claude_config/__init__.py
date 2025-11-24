"""Claude Code Configuration.

Global Claude Code development standards, commands, and configuration for all projects.

Example:
    >>> from claude_config import Settings, get_logger, setup_logging
    >>> settings = Settings()
    >>> setup_logging(level=settings.log_level)
    >>> logger = get_logger(__name__)
"""

from claude_config.core.config import Settings
from claude_config.utils.logging import get_logger, log_performance, setup_logging

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
