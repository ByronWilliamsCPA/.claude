"""Tests for scripts/doc-audit.py: documentation health audit script.

Five spec scenarios tested:
1. Clean repo: all checks produce zero findings
2. Missing required frontmatter field: produces WARN
3. Broken internal link: produces ERROR
4. Count claim mismatch: produces WARN
5. Stale Python version reference: produces WARN

Sixth scenario: CLI produces valid JSON and exits 0.
"""

from __future__ import annotations

import importlib.abc
import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from typing import Protocol, TypedDict, cast

import pytest


class Finding(TypedDict):
    """Shape of a single finding returned by doc-audit checkers."""

    category: str
    severity: str
    file: str
    line: int
    message: str


class DocAuditModule(Protocol):
    """Structural interface for the dynamically-loaded doc_audit module."""

    def check_frontmatter(
        self, scope: str, *, repo_root: str = "."
    ) -> list[Finding]: ...

    def check_links(self, scope: str) -> list[Finding]: ...

    def check_counts(self, scope: str, *, repo_root: str = ".") -> list[Finding]: ...

    def check_versions(self, scope: str, *, repo_root: str = ".") -> list[Finding]: ...


# ---------------------------------------------------------------------------
# Module loading
# ---------------------------------------------------------------------------

_SCRIPT_PATH = Path(__file__).parents[2] / "scripts" / "doc-audit.py"


@pytest.fixture(scope="module")
def doc_audit_module() -> DocAuditModule:
    """Import doc_audit as a module, failing clearly if not yet implemented."""
    spec = importlib.util.spec_from_file_location("doc_audit", _SCRIPT_PATH)
    assert spec is not None, f"Script not found: {_SCRIPT_PATH}"
    module = importlib.util.module_from_spec(spec)
    assert isinstance(spec.loader, importlib.abc.Loader)
    spec.loader.exec_module(module)
    return cast("DocAuditModule", module)


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

_VALID_FRONTMATTER = """\
---
schema_type: common
title: Test Doc
status: active
owner: core-maintainer
purpose: Testing fixture
tags:
  - testing
---

Body content here.
"""

_TAGS_YML_CONTENT = """\
allowed:
  - testing
  - automation
  - tooling
  - documentation
"""


@pytest.fixture
def docs_root(tmp_path: Path) -> Path:
    """Create docs/ and docs/_data/tags.yml in a temp directory."""
    docs = tmp_path / "docs"
    docs.mkdir()
    data_dir = tmp_path / "docs" / "_data"
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "tags.yml").write_text(_TAGS_YML_CONTENT)
    return docs


@pytest.fixture
def repo_root(tmp_path: Path, docs_root: Path) -> Path:
    """Return tmp_path as repo root (docs/ already created by docs_root fixture)."""
    _ = docs_root  # pytest fixture dependency: ensures docs/ exists before tests run
    return tmp_path


# ---------------------------------------------------------------------------
# Scenario 1: Clean repo: all checks pass
# ---------------------------------------------------------------------------


class TestCleanRepo:
    """All docs valid: each checker returns an empty findings list."""

    @pytest.mark.unit
    def test_frontmatter_clean(
        self,
        doc_audit_module: DocAuditModule,
        docs_root: Path,
        repo_root: Path,
    ) -> None:
        """Valid frontmatter produces zero findings."""
        (docs_root / "valid.md").write_text(_VALID_FRONTMATTER)

        findings = doc_audit_module.check_frontmatter(
            str(docs_root), repo_root=str(repo_root)
        )

        assert findings == []

    @pytest.mark.unit
    def test_links_clean(
        self,
        doc_audit_module: DocAuditModule,
        docs_root: Path,
    ) -> None:
        """Internal link pointing to an existing file produces zero findings."""
        (docs_root / "a.md").write_text("See [B](b.md).\n")
        (docs_root / "b.md").write_text("# B\n")

        findings = doc_audit_module.check_links(str(docs_root))

        assert findings == []

    @pytest.mark.unit
    def test_counts_clean(
        self,
        doc_audit_module: DocAuditModule,
        docs_root: Path,
        repo_root: Path,
    ) -> None:
        """Count claim matching actual file count produces zero WARN findings."""
        agents_dir = repo_root / ".claude" / "agents"
        agents_dir.mkdir(parents=True)
        (agents_dir / "my-agent.md").write_text("# Agent\n")
        (docs_root / "overview.md").write_text("We have 1 agent available.\n")

        findings = doc_audit_module.check_counts(
            str(docs_root), repo_root=str(repo_root)
        )

        error_or_warn = [f for f in findings if f["severity"] in ("ERROR", "WARN")]
        assert error_or_warn == []

    @pytest.mark.unit
    def test_versions_clean(
        self,
        doc_audit_module: DocAuditModule,
        docs_root: Path,
        repo_root: Path,
    ) -> None:
        """Python version inside declared range produces zero findings."""
        (docs_root / "setup.md").write_text("Requires Python 3.12.\n")
        (repo_root / "pyproject.toml").write_text(
            '[project]\nrequires-python = ">=3.10,<3.15"\n'
        )

        findings = doc_audit_module.check_versions(
            str(docs_root), repo_root=str(repo_root)
        )

        assert findings == []


# ---------------------------------------------------------------------------
# Scenario 2: Missing required frontmatter field
# ---------------------------------------------------------------------------


class TestMissingFrontmatterField:
    """Frontmatter missing 'owner' produces WARN; missing block produces ERROR."""

    @pytest.mark.unit
    def test_missing_owner_is_warn(
        self,
        doc_audit_module: DocAuditModule,
        docs_root: Path,
        repo_root: Path,
    ) -> None:
        """Doc missing required field 'owner' produces exactly one WARN."""
        content = """\
---
schema_type: common
title: No Owner
status: active
purpose: Testing
tags:
  - testing
---
Body.
"""
        (docs_root / "no-owner.md").write_text(content)

        findings = doc_audit_module.check_frontmatter(
            str(docs_root), repo_root=str(repo_root)
        )

        warns = [f for f in findings if f["severity"] == "WARN"]
        assert len(warns) == 1
        assert "owner" in warns[0]["message"]
        assert warns[0]["file"].endswith("no-owner.md")
        assert warns[0]["category"] == "frontmatter"

    @pytest.mark.unit
    def test_missing_frontmatter_block_is_error(
        self,
        doc_audit_module: DocAuditModule,
        docs_root: Path,
        repo_root: Path,
    ) -> None:
        """Doc with no frontmatter block at all produces exactly one ERROR."""
        (docs_root / "bare.md").write_text("# No frontmatter\n\nJust text.\n")

        findings = doc_audit_module.check_frontmatter(
            str(docs_root), repo_root=str(repo_root)
        )

        errors = [f for f in findings if f["severity"] == "ERROR"]
        assert len(errors) == 1
        assert errors[0]["file"].endswith("bare.md")
        assert errors[0]["category"] == "frontmatter"


# ---------------------------------------------------------------------------
# Scenario 3: Broken internal link
# ---------------------------------------------------------------------------


class TestBrokenLink:
    """Link to a non-existent file produces ERROR; http and anchor links are skipped."""

    @pytest.mark.unit
    def test_broken_link_is_error(
        self,
        doc_audit_module: DocAuditModule,
        docs_root: Path,
    ) -> None:
        """Markdown link to a non-existent relative path produces ERROR."""
        (docs_root / "broken.md").write_text("See [missing](./missing-file.md).\n")

        findings = doc_audit_module.check_links(str(docs_root))

        errors = [f for f in findings if f["severity"] == "ERROR"]
        assert len(errors) == 1
        assert "missing-file.md" in errors[0]["message"]
        assert errors[0]["category"] == "links"
        assert errors[0]["file"].endswith("broken.md")

    @pytest.mark.unit
    def test_http_links_are_skipped(
        self,
        doc_audit_module: DocAuditModule,
        docs_root: Path,
    ) -> None:
        """External https link to a non-existent URL produces zero findings."""
        (docs_root / "ext.md").write_text(
            "See [external](https://example.com/nonexistent).\n"
        )

        findings = doc_audit_module.check_links(str(docs_root))

        assert findings == []

    @pytest.mark.unit
    def test_anchor_only_links_are_skipped(
        self,
        doc_audit_module: DocAuditModule,
        docs_root: Path,
    ) -> None:
        """Anchor-only link (#section) produces zero findings."""
        (docs_root / "anchor.md").write_text("Jump to [section](#my-section).\n")

        findings = doc_audit_module.check_links(str(docs_root))

        assert findings == []


# ---------------------------------------------------------------------------
# Scenario 4: Count claim mismatch
# ---------------------------------------------------------------------------


class TestCountMismatch:
    """Claimed count differing from actual count produces WARN."""

    @pytest.mark.unit
    def test_agent_count_mismatch_is_warn(
        self,
        doc_audit_module: DocAuditModule,
        docs_root: Path,
        repo_root: Path,
    ) -> None:
        """Claiming '5 agents' when 1 agent exists produces one WARN."""
        (docs_root / "overview.md").write_text("We have 5 agents available.\n")
        agents_dir = repo_root / ".claude" / "agents"
        agents_dir.mkdir(parents=True, exist_ok=True)
        (agents_dir / "one-agent.md").write_text("# Agent\n")

        findings = doc_audit_module.check_counts(
            str(docs_root), repo_root=str(repo_root)
        )

        warns = [f for f in findings if f["severity"] == "WARN"]
        assert len(warns) == 1
        assert "5" in warns[0]["message"]
        assert "1" in warns[0]["message"]
        assert warns[0]["category"] == "counts"


# ---------------------------------------------------------------------------
# Scenario 5: Stale version reference
# ---------------------------------------------------------------------------


class TestStaleVersionReference:
    """Python version outside declared range or unknown model name produces WARN."""

    @pytest.mark.unit
    def test_out_of_range_python_version_is_warn(
        self,
        doc_audit_module: DocAuditModule,
        docs_root: Path,
        repo_root: Path,
    ) -> None:
        """Python 3.8 with requires-python >=3.10 produces at least one WARN."""
        (docs_root / "setup.md").write_text("Requires Python 3.8 or newer.\n")
        (repo_root / "pyproject.toml").write_text(
            '[project]\nrequires-python = ">=3.10,<3.15"\n'
        )

        findings = doc_audit_module.check_versions(
            str(docs_root), repo_root=str(repo_root)
        )

        warns = [f for f in findings if f["severity"] == "WARN"]
        assert len(warns) >= 1
        assert any("3.8" in f["message"] for f in warns)
        assert all(f["category"] == "versions" for f in warns)

    @pytest.mark.unit
    def test_unknown_model_name_is_warn(
        self,
        doc_audit_module: DocAuditModule,
        docs_root: Path,
        repo_root: Path,
    ) -> None:
        """Reference to a non-current model name produces WARN."""
        (docs_root / "models.md").write_text(
            "Use claude-instant-1 for fast responses.\n"
        )
        (repo_root / "pyproject.toml").write_text(
            '[project]\nrequires-python = ">=3.10,<3.15"\n'
        )

        findings = doc_audit_module.check_versions(
            str(docs_root), repo_root=str(repo_root)
        )

        warns = [f for f in findings if f["severity"] == "WARN"]
        assert len(warns) >= 1
        assert any("claude-instant-1" in f["message"] for f in warns)


# ---------------------------------------------------------------------------
# Scenario 6: CLI output is valid JSON
# ---------------------------------------------------------------------------


class TestCLIOutput:
    """Script emits valid JSON to stdout and exits 0."""

    @pytest.mark.unit
    def test_cli_outputs_valid_json(self, tmp_path: Path) -> None:
        """Running script with --scope on empty dir produces parseable JSON."""
        docs = tmp_path / "docs"
        docs.mkdir()

        result = subprocess.run(  # noqa: S603  # trusted: sys.executable + repo-local script + tmp_path args
            [sys.executable, str(_SCRIPT_PATH), "--scope", str(docs)],
            capture_output=True,
            text=True,
            check=False,
        )

        assert result.returncode == 0, f"Script exited non-zero: {result.stderr}"
        data = json.loads(result.stdout)
        assert "scope" in data
        assert "generated" in data
        assert "summary" in data
        assert "findings" in data
        assert set(data["summary"].keys()) == {
            "frontmatter",
            "links",
            "counts",
            "versions",
        }
        for cat in data["summary"].values():
            assert "pass" in cat
            assert "warn" in cat
            assert "error" in cat
