"""Helper for tests that need to load scripts/check-required-checks.py.

The script's filename has a hyphen (which isn't a valid Python module
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
_SCRIPT_PATH = _PROJECT_ROOT / "scripts" / "check-required-checks.py"


def load_module():
    spec = importlib.util.spec_from_file_location(
        "check_required_checks",
        _SCRIPT_PATH,
    )
    assert spec is not None, f"Script not found: {_SCRIPT_PATH}"
    module = importlib.util.module_from_spec(spec)
    sys.modules["check_required_checks"] = module
    assert isinstance(spec.loader, importlib.abc.Loader)
    spec.loader.exec_module(module)
    return module
