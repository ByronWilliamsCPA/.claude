"""Helper for tests that need to load scripts/sync_org_pins.py.

The script lives outside the normal package tree, so tests load it via
importlib.util. This helper centralizes that boilerplate including the
sys.modules registration required for module-level state to resolve
correctly at import time.
"""

from __future__ import annotations

import importlib.abc
import importlib.util
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_SCRIPT_PATH = _PROJECT_ROOT / "scripts" / "sync_org_pins.py"

_MODULE_CACHE = None


def load_module():
    global _MODULE_CACHE  # noqa: PLW0603 -- module-level cache singleton
    if _MODULE_CACHE is not None:
        return _MODULE_CACHE
    spec = importlib.util.spec_from_file_location(
        "sync_org_pins",
        _SCRIPT_PATH,
    )
    assert spec is not None, f"Script not found: {_SCRIPT_PATH}"
    module = importlib.util.module_from_spec(spec)
    sys.modules["sync_org_pins"] = module
    assert isinstance(spec.loader, importlib.abc.Loader)
    spec.loader.exec_module(module)
    _MODULE_CACHE = module
    return module
