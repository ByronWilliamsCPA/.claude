"""Claude Code Configuration package.

Provides settings management and structured logging utilities
for Claude Code projects.
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
