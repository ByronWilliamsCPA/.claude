"""Tests for validate-planning-docs.py skill script."""

from __future__ import annotations

import importlib.abc
import importlib.util
import sys
from pathlib import Path

_SCRIPT = (
    Path(__file__).resolve().parents[2]
    / ".claude"
    / "skills"
    / "project-planning"
    / "scripts"
    / "validate-planning-docs.py"
)


def _load() -> object:
    spec = importlib.util.spec_from_file_location("validate_planning_docs", _SCRIPT)
    assert spec is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules["validate_planning_docs"] = mod
    assert isinstance(spec.loader, importlib.abc.Loader)
    spec.loader.exec_module(mod)
    return mod


def test_validate_doc_helper_exists() -> None:
    mod = _load()
    assert hasattr(mod, "_validate_doc"), "_validate_doc helper not found"


def test_validate_doc_word_count_issue() -> None:
    mod = _load()
    content = " ".join(["word"] * 2001)
    issues = mod._validate_doc(
        content,
        Path("fake.md"),
        max_words=2000,
        required_sections=["Architecture"],
    )
    assert any("Too long" in i for i in issues)


def test_validate_doc_no_issues_for_compliant_content() -> None:
    mod = _load()
    content = "## Architecture\n\n## TL;DR\n\n" + " ".join(["word"] * 100)
    issues = mod._validate_doc(
        content,
        Path("fake.md"),
        max_words=2000,
        required_sections=["Architecture"],
    )
    assert issues == []
