"""Helper for tests that need scripts/hooks/delegation-ratio-nudge.py.

The script lives under scripts/hooks/ which has no __init__.py and carries a
hyphenated filename, so it cannot be imported via the normal import machinery.
The shared _importlib_loader.load_script helper resolves names against
scripts/ only, so this module carries its own path.
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
_SCRIPT_PATH = _PROJECT_ROOT / "scripts" / "hooks" / "delegation-ratio-nudge.py"


@functools.cache
def load_module() -> ModuleType:
    """Load the delegation-ratio-nudge hook as a Python module.

    Returns:
        The loaded module object, cached after first load via functools.cache.
    """
    assert _SCRIPT_PATH.exists(), f"Script not found: {_SCRIPT_PATH}"
    spec = importlib.util.spec_from_file_location(
        "delegation_ratio_nudge",
        _SCRIPT_PATH,
    )
    assert spec is not None, f"spec_from_file_location returned None: {_SCRIPT_PATH}"
    assert isinstance(spec.loader, importlib.abc.Loader)
    module = importlib.util.module_from_spec(spec)
    sys.modules["delegation_ratio_nudge"] = module
    spec.loader.exec_module(module)
    return module
