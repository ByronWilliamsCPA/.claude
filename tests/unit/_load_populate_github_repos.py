"""Helper for tests that need to load scripts/populate-github-repos.py.

The script's filename has a hyphen (which is not a valid Python module
name), so tests load it via importlib.util. Mirrors the pattern used by
_load_check_repo_compliance.py.
"""

from __future__ import annotations

import functools
import importlib.abc
import importlib.util
import sys
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from types import ModuleType

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_SCRIPT_PATH = _PROJECT_ROOT / "scripts" / "populate-github-repos.py"


@functools.cache
def load_module() -> ModuleType:
    """Load the populate-github-repos script as a Python module.

    Returns:
        The loaded module object, cached after first load via functools.cache.
    """
    spec = importlib.util.spec_from_file_location(
        "populate_github_repos",
        _SCRIPT_PATH,
    )
    assert spec is not None, f"Script not found: {_SCRIPT_PATH}"
    module = importlib.util.module_from_spec(spec)
    sys.modules["populate_github_repos"] = module
    assert isinstance(spec.loader, importlib.abc.Loader)
    spec.loader.exec_module(module)
    return module
