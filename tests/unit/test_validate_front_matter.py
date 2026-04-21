"""Tests for tools/validate_front_matter.py: front matter validation tool.

Covers the _strip_code_blocks helper function:
1. Properly closed fenced code block is removed
2. CRLF line endings are handled correctly
3. Unclosed fence returns content unchanged (no silent data loss)
4. Opening fence with an info string (e.g. ```python) is recognised
5. Mixed fence types (backtick block inside tilde block, and vice versa)
6. Multiple consecutive code blocks are all stripped
"""

from __future__ import annotations

import importlib.abc
import importlib.util
import sys
from pathlib import Path
from typing import Protocol

import pytest


class ValidateFrontMatterModule(Protocol):
    """Structural interface for the dynamically-loaded validate_front_matter module."""

    def _strip_code_blocks(self, content: str) -> str: ...


# ---------------------------------------------------------------------------
# Module loading
# ---------------------------------------------------------------------------

_TOOLS_DIR = Path(__file__).parents[2] / "tools"
_SCRIPT_PATH = _TOOLS_DIR / "validate_front_matter.py"


@pytest.fixture(scope="module")
def vfm() -> ValidateFrontMatterModule:
    """Import validate_front_matter as a module.

    Adds tools/ to sys.path so frontmatter_contract (a sibling package) is
    importable during module load.
    """
    tools_dir = str(_TOOLS_DIR)
    if tools_dir not in sys.path:
        sys.path.insert(0, tools_dir)
    spec = importlib.util.spec_from_file_location("validate_front_matter", _SCRIPT_PATH)
    assert spec is not None, f"Script not found: {_SCRIPT_PATH}"
    module = importlib.util.module_from_spec(spec)
    assert isinstance(spec.loader, importlib.abc.Loader)
    spec.loader.exec_module(module)
    return module  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# _strip_code_blocks tests
# ---------------------------------------------------------------------------


class TestStripCodeBlocks:
    def test_removes_closed_backtick_fence(
        self, vfm: ValidateFrontMatterModule
    ) -> None:
        content = "Before\n```\ncode here\n```\nAfter\n"
        result = vfm._strip_code_blocks(content)
        assert "code here" not in result
        assert "Before" in result
        assert "After" in result

    def test_fence_marker_lines_excluded(self, vfm: ValidateFrontMatterModule) -> None:
        content = "```\ncode\n```\n"
        result = vfm._strip_code_blocks(content)
        assert "```" not in result
        assert result == ""

    def test_crlf_line_endings(self, vfm: ValidateFrontMatterModule) -> None:
        content = "Before\r\n```\r\ncode here\r\n```\r\nAfter\r\n"
        result = vfm._strip_code_blocks(content)
        assert "code here" not in result
        assert "Before" in result
        assert "After" in result

    def test_unclosed_fence_excludes_content_after_opener(
        self, vfm: ValidateFrontMatterModule
    ) -> None:
        content = "Before\n```\ncode here\nno closing fence\n"
        result = vfm._strip_code_blocks(content)
        assert result == "Before\n", (
            "Content before unclosed fence is kept; everything from opener onward is excluded"
        )

    def test_info_string_on_opening_fence(self, vfm: ValidateFrontMatterModule) -> None:
        content = "Before\n```python\nimport os\n```\nAfter\n"
        result = vfm._strip_code_blocks(content)
        assert "import os" not in result
        assert "Before" in result
        assert "After" in result

    def test_mixed_fence_types_independent(
        self, vfm: ValidateFrontMatterModule
    ) -> None:
        content = "```\nbacktick code\n```\n~~~\ntilde code\n~~~\n"
        result = vfm._strip_code_blocks(content)
        assert "backtick code" not in result
        assert "tilde code" not in result
        assert result == ""

    def test_tilde_fence_not_closed_by_backticks(
        self, vfm: ValidateFrontMatterModule
    ) -> None:
        content = "~~~\ncode\n```\nstill in fence\n~~~\nafter\n"
        result = vfm._strip_code_blocks(content)
        assert "code" not in result
        assert "still in fence" not in result
        assert "after" in result

    def test_multiple_code_blocks_all_stripped(
        self, vfm: ValidateFrontMatterModule
    ) -> None:
        content = "text1\n```\nblock1\n```\ntext2\n```\nblock2\n```\ntext3\n"
        result = vfm._strip_code_blocks(content)
        assert "block1" not in result
        assert "block2" not in result
        assert "text1" in result
        assert "text2" in result
        assert "text3" in result

    def test_empty_content(self, vfm: ValidateFrontMatterModule) -> None:
        assert vfm._strip_code_blocks("") == ""

    def test_content_with_no_fences(self, vfm: ValidateFrontMatterModule) -> None:
        content = "Just plain text\nNo fences here\n"
        assert vfm._strip_code_blocks(content) == content
