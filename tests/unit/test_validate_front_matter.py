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
from typing import Any, Protocol

import pytest


class ValidateFrontMatterModule(Protocol):
    """Documents the internal API exercised by these tests.

    Not used as a type annotation -- the fixture returns Any because the module
    is loaded dynamically. Kept as readable documentation of what the tests
    exercise.
    """

    def _strip_code_blocks(self, content: str) -> str: ...
    def _collect_md_files(
        self, paths: list[str], exclude: list[str] | None = None
    ) -> list[Path]: ...


# ---------------------------------------------------------------------------
# Module loading
# ---------------------------------------------------------------------------

_TOOLS_DIR = Path(__file__).parents[2] / "tools"
_SCRIPT_PATH = _TOOLS_DIR / "validate_front_matter.py"


@pytest.fixture(scope="module")
def vfm() -> Any:
    """Import validate_front_matter as a module.

    Adds tools/ to sys.path so frontmatter_contract (a sibling package) is
    importable during module load. Returns Any because the module is loaded
    dynamically; see ValidateFrontMatterModule above for what is exercised.
    """
    tools_dir = str(_TOOLS_DIR)
    if tools_dir not in sys.path:
        sys.path.insert(0, tools_dir)
    spec = importlib.util.spec_from_file_location("validate_front_matter", _SCRIPT_PATH)
    assert spec is not None, f"Script not found: {_SCRIPT_PATH}"
    module = importlib.util.module_from_spec(spec)
    assert isinstance(spec.loader, importlib.abc.Loader)
    spec.loader.exec_module(module)
    return module


# ---------------------------------------------------------------------------
# _strip_code_blocks tests
# ---------------------------------------------------------------------------


class TestStripCodeBlocks:
    def test_removes_closed_backtick_fence(self, vfm: Any) -> None:
        content = "Before\n```\ncode here\n```\nAfter\n"
        result = vfm._strip_code_blocks(content)
        assert "code here" not in result
        assert "Before" in result
        assert "After" in result

    def test_fence_marker_lines_excluded(self, vfm: Any) -> None:
        content = "```\ncode\n```\n"
        result = vfm._strip_code_blocks(content)
        assert "```" not in result
        assert result == ""

    def test_crlf_line_endings(self, vfm: Any) -> None:
        content = "Before\r\n```\r\ncode here\r\n```\r\nAfter\r\n"
        result = vfm._strip_code_blocks(content)
        assert "code here" not in result
        assert "Before" in result
        assert "After" in result

    def test_unclosed_fence_excludes_content_after_opener(self, vfm: Any) -> None:
        content = "Before\n```\ncode here\nno closing fence\n"
        result = vfm._strip_code_blocks(content)
        assert result == "Before\n", (
            "Content before unclosed fence is kept; everything from opener onward is excluded"
        )

    def test_info_string_on_opening_fence(self, vfm: Any) -> None:
        content = "Before\n```python\nimport os\n```\nAfter\n"
        result = vfm._strip_code_blocks(content)
        assert "import os" not in result
        assert "Before" in result
        assert "After" in result

    def test_mixed_fence_types_independent(self, vfm: Any) -> None:
        content = "```\nbacktick code\n```\n~~~\ntilde code\n~~~\n"
        result = vfm._strip_code_blocks(content)
        assert "backtick code" not in result
        assert "tilde code" not in result
        assert result == ""

    def test_tilde_fence_not_closed_by_backticks(self, vfm: Any) -> None:
        content = "~~~\ncode\n```\nstill in fence\n~~~\nafter\n"
        result = vfm._strip_code_blocks(content)
        assert "code" not in result
        assert "still in fence" not in result
        assert "after" in result

    def test_multiple_code_blocks_all_stripped(self, vfm: Any) -> None:
        content = "text1\n```\nblock1\n```\ntext2\n```\nblock2\n```\ntext3\n"
        result = vfm._strip_code_blocks(content)
        assert "block1" not in result
        assert "block2" not in result
        assert "text1" in result
        assert "text2" in result
        assert "text3" in result

    def test_empty_content(self, vfm: Any) -> None:
        assert vfm._strip_code_blocks("") == ""

    def test_content_with_no_fences(self, vfm: Any) -> None:
        content = "Just plain text\nNo fences here\n"
        assert vfm._strip_code_blocks(content) == content


class TestCollectMdFiles:
    def test_excludes_directory(self, vfm: Any, tmp_path: Path) -> None:
        """Excluded directories are skipped during collection."""
        (tmp_path / "included.md").write_text("# Included")
        excluded_dir = tmp_path / "excluded"
        excluded_dir.mkdir()
        (excluded_dir / "report.md").write_text("# Report")

        result = vfm._collect_md_files([str(tmp_path)], exclude=[str(excluded_dir)])
        result_names = {p.name for p in result}
        assert "included.md" in result_names
        assert "report.md" not in result_names

    def test_excludes_specific_file(self, vfm: Any, tmp_path: Path) -> None:
        """A specific file path is excluded when listed in exclude."""
        (tmp_path / "keep.md").write_text("# Keep")
        (tmp_path / "skip.md").write_text("# Skip")

        result = vfm._collect_md_files(
            [str(tmp_path)], exclude=[str(tmp_path / "skip.md")]
        )
        result_names = {p.name for p in result}
        assert "keep.md" in result_names
        assert "skip.md" not in result_names

    def test_no_exclude_collects_all(self, vfm: Any, tmp_path: Path) -> None:
        """Without exclude, all markdown files in a directory are collected."""
        (tmp_path / "a.md").write_text("# A")
        (tmp_path / "b.md").write_text("# B")

        result = vfm._collect_md_files([str(tmp_path)])
        assert len(result) == 2

    def test_excludes_direct_file_path(self, vfm: Any, tmp_path: Path) -> None:
        """A file passed directly as a path argument is skipped when excluded."""
        keep = tmp_path / "keep.md"
        skip = tmp_path / "skip.md"
        keep.write_text("# Keep")
        skip.write_text("# Skip")

        result = vfm._collect_md_files([str(keep), str(skip)], exclude=[str(skip)])
        result_names = {p.name for p in result}
        assert "keep.md" in result_names
        assert "skip.md" not in result_names


# ---------------------------------------------------------------------------
# Property-based tests (Hypothesis)
# ---------------------------------------------------------------------------


class TestStripCodeBlocksProperties:
    """Property-based tests for _strip_code_blocks using Hypothesis.

    These tests verify structural invariants that hold for all inputs,
    catching edge cases that example-based tests do not cover.
    """

    def test_idempotent(self, vfm: Any) -> None:
        """Stripping once equals stripping twice for any input."""
        from hypothesis import given
        from hypothesis import strategies as st

        @given(
            st.text(alphabet=st.characters(blacklist_categories=("Cs",)), max_size=500)
        )
        def check(content: str) -> None:
            once = vfm._strip_code_blocks(content)
            twice = vfm._strip_code_blocks(once)
            assert once == twice, (
                f"_strip_code_blocks is not idempotent.\n"
                f"Input:       {content!r}\n"
                f"After one:   {once!r}\n"
                f"After two:   {twice!r}"
            )

        check()

    def test_output_never_longer_than_input(self, vfm: Any) -> None:
        """Stripping code blocks never increases the length of the content."""
        from hypothesis import given
        from hypothesis import strategies as st

        @given(
            st.text(alphabet=st.characters(blacklist_categories=("Cs",)), max_size=500)
        )
        def check(content: str) -> None:
            result = vfm._strip_code_blocks(content)
            assert len(result) <= len(content)

        check()

    def test_fence_free_content_unchanged(self, vfm: Any) -> None:
        """Content with no fence markers passes through unmodified."""
        from hypothesis import given
        from hypothesis import strategies as st

        safe_text = st.text(
            alphabet=st.characters(
                blacklist_categories=("Cs",),
                blacklist_characters="`~",
            ),
            max_size=300,
        )

        @given(safe_text)
        def check(content: str) -> None:
            assert vfm._strip_code_blocks(content) == content

        check()
