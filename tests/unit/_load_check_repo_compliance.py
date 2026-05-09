"""Helper for tests that need to load scripts/check-repo-compliance.py.

The script's filename has a hyphen (which is not a valid Python module
name), so tests load it via importlib.util. This helper centralizes
that boilerplate including the sys.modules registration required for
@dataclass to resolve __module__ at class-creation time.
"""

from __future__ import annotations

import importlib.abc
import importlib.util
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_SCRIPT_PATH = _PROJECT_ROOT / "scripts" / "check-repo-compliance.py"

_MODULE_CACHE = None


def load_module():
    """Load the check-repo-compliance script as a Python module.

    Returns:
        The loaded module object, cached after first load.
    """
    global _MODULE_CACHE  # noqa: PLW0603 -- module-level cache singleton
    if _MODULE_CACHE is not None:
        return _MODULE_CACHE
    spec = importlib.util.spec_from_file_location(
        "check_repo_compliance",
        _SCRIPT_PATH,
    )
    assert spec is not None, f"Script not found: {_SCRIPT_PATH}"
    module = importlib.util.module_from_spec(spec)
    sys.modules["check_repo_compliance"] = module
    assert isinstance(spec.loader, importlib.abc.Loader)
    spec.loader.exec_module(module)
    _MODULE_CACHE = module
    return module
