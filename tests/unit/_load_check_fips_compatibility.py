"""Helper for tests that need to load scripts/check_fips_compatibility.py.

The script lives under scripts/ which has no __init__.py, so tests load it
via importlib.util. This helper centralises that boilerplate including the
sys.modules registration required for @dataclass to resolve __module__ at
class-creation time.
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
_SCRIPT_PATH = _PROJECT_ROOT / "scripts" / "check_fips_compatibility.py"


@functools.cache
def load_module() -> ModuleType:
    """Load the check_fips_compatibility script as a Python module.

    Returns:
        The loaded module object, cached after first load via functools.cache.
    """
    spec = importlib.util.spec_from_file_location(
        "check_fips_compatibility",
        _SCRIPT_PATH,
    )
    assert spec is not None, f"Script not found: {_SCRIPT_PATH}"
    module = importlib.util.module_from_spec(spec)
    sys.modules["check_fips_compatibility"] = module
    assert isinstance(spec.loader, importlib.abc.Loader)
    spec.loader.exec_module(module)
    return module
