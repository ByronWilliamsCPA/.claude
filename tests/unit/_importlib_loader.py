"""Shared importlib.util loader for scripts with hyphenated filenames.

Scripts whose filenames contain hyphens cannot be imported via the normal
import machinery because hyphens are not valid in Python identifiers.
This module centralises the spec-from-file-location boilerplate so each
_load_*.py helper is a one-liner.
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


@functools.cache
def load_script(script_name: str, module_name: str) -> ModuleType:
    """Load a hyphenated script file as a Python module.

    Args:
        script_name: Filename under scripts/, e.g. "check-repo-compliance.py".
        module_name: Identifier to register in sys.modules, e.g.
            "check_repo_compliance". Must be a valid Python identifier.

    Returns:
        The loaded module object, cached after first load.
    """
    script_path = _PROJECT_ROOT / "scripts" / script_name
    spec = importlib.util.spec_from_file_location(module_name, script_path)
    assert spec is not None, f"Script not found: {script_path}"
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    assert isinstance(spec.loader, importlib.abc.Loader)
    spec.loader.exec_module(module)
    return module
