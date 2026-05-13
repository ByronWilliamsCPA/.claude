"""Fuzz tests for tools/validate_front_matter.py -- surfaces crashes on arbitrary input.

These module-level @given-decorated functions satisfy the OpenSSF Scorecard
Fuzzing detector, which requires top-level Hypothesis tests in files matching
the fuzz_*.py naming pattern.

The module under test is a standalone CLI script, not an importable package,
so it is loaded via importlib the same way the unit tests do.  The fuzz
functions treat any unhandled exception (other than the expected ValueError,
TypeError, and AttributeError) as a test failure.
"""

from __future__ import annotations

import importlib.abc
import importlib.util
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import types

from hypothesis import given, settings
from hypothesis import strategies as st

# ---------------------------------------------------------------------------
# Module loading (mirrors tests/unit/test_validate_front_matter.py)
# ---------------------------------------------------------------------------

_TOOLS_DIR = Path(__file__).parents[2] / "tools"
_SCRIPT_PATH = _TOOLS_DIR / "validate_front_matter.py"


def _load_vfm() -> types.ModuleType:
    tools_dir = str(_TOOLS_DIR)
    if tools_dir not in sys.path:
        sys.path.insert(0, tools_dir)
    spec = importlib.util.spec_from_file_location("validate_front_matter", _SCRIPT_PATH)
    assert spec is not None, f"Script not found: {_SCRIPT_PATH}"
    module = importlib.util.module_from_spec(spec)
    assert isinstance(spec.loader, importlib.abc.Loader)
    spec.loader.exec_module(module)
    return module


_vfm: Any = _load_vfm()


# ---------------------------------------------------------------------------
# Fuzz: _strip_code_blocks
# ---------------------------------------------------------------------------


@given(st.text())
@settings(max_examples=200)
def test_fuzz_strip_code_blocks_text(s: str) -> None:
    """Fuzz: arbitrary text must not crash _strip_code_blocks."""
    try:
        result = _vfm._strip_code_blocks(s)
        # Output must always be a string and no longer than the input.
        assert isinstance(result, str)
        assert len(result) <= len(s)
    except (ValueError, TypeError, AttributeError):
        pass  # expected for degenerate input


@given(st.binary())
@settings(max_examples=200)
def test_fuzz_strip_code_blocks_bytes(b: bytes) -> None:
    """Fuzz: arbitrary bytes decoded to str must not crash _strip_code_blocks."""
    s = b.decode("utf-8", errors="replace")
    try:
        result = _vfm._strip_code_blocks(s)
        assert isinstance(result, str)
        assert len(result) <= len(s)
    except (ValueError, TypeError, AttributeError):
        pass


# ---------------------------------------------------------------------------
# Fuzz: _fix_tags
# ---------------------------------------------------------------------------


@given(
    st.dictionaries(
        keys=st.text(max_size=32),
        values=st.one_of(
            st.none(),
            st.text(max_size=64),
            st.lists(st.text(max_size=32), max_size=10),
            st.integers(),
        ),
        max_size=8,
    )
)
@settings(max_examples=200)
def test_fuzz_fix_tags_dict(data: dict[str, Any]) -> None:
    """Fuzz: arbitrary dict must not crash _fix_tags."""
    try:
        result = _vfm._fix_tags(data)
        assert isinstance(result, bool)
    except (ValueError, TypeError, AttributeError):
        pass
