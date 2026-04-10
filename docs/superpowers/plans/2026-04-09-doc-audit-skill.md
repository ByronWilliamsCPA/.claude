---
schema_type: planning
title: "/doc-audit Skill Implementation"
status: draft
owner: core-maintainer
purpose: "Implementation plan for the /doc-audit skill: Python stdlib-only audit script with four check categories, JSON output, and a SKILL.md that prints a terminal summary and writes docs/audit-report.md."
component: Development-Tools
source: "docs/superpowers/specs/2026-04-09-doc-audit-skill-design.md"
tags:
  - testing
  - tooling
  - automation
  - documentation
---

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a `/doc-audit` skill that runs four documentation health checks (frontmatter, links, counts, versions), outputs a terminal summary table, and writes `docs/audit-report.md`.

**Architecture:** Two new files and one `.gitignore` addition. `scripts/doc-audit.py` is a stdlib-only Python script that outputs JSON to stdout. `.claude/skills/doc-audit/SKILL.md` orchestrates the script, prints the summary, and writes the report. Tests live in `tests/unit/test_doc_audit.py` and use `tmp_path` fixtures to isolate file system state.

**Tech Stack:** Python 3.10+ stdlib only (pathlib, re, json, argparse, datetime), pytest with tmp_path fixtures, importlib for script loading in tests

---

## File Map

| Action | Path | Responsibility |
|--------|------|----------------|
| CREATE | `tests/unit/test_doc_audit.py` | 6 test classes, 14 test methods covering 5 spec scenarios |
| CREATE | `scripts/doc-audit.py` | CLI entry point + 4 checker functions + JSON output |
| CREATE | `.claude/skills/doc-audit/SKILL.md` | Skill orchestration, terminal summary, audit-report.md writer |
| MODIFY | `.gitignore` | Add `docs/audit-report.md` (generated artifact) |

---

### Task 1: Write failing test harness for doc-audit.py

**Files:**
- Create: `tests/unit/test_doc_audit.py`

- [ ] **Step 1: Verify the test directory exists**

```bash
ls /home/byron/dev/.claude/tests/unit/
```

Expected: `__init__.py`, `test_settings.py`, and other existing test files.

- [ ] **Step 2: Create tests/unit/test_doc_audit.py**

Create `/home/byron/dev/.claude/tests/unit/test_doc_audit.py` with this exact content:

```python
"""Tests for scripts/doc-audit.py — documentation health audit script.

Five spec scenarios tested:
1. Clean repo — all checks produce zero findings
2. Missing required frontmatter field — produces WARN
3. Broken internal link — produces ERROR
4. Count claim mismatch — produces WARN
5. Stale Python version reference — produces WARN

Sixth scenario: CLI produces valid JSON and exits 0.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Module loading
# ---------------------------------------------------------------------------

_SCRIPT_PATH = Path(__file__).parents[2] / "scripts" / "doc-audit.py"


@pytest.fixture(scope="module")
def doc_audit_module() -> object:
    """Import doc_audit as a module, failing clearly if not yet implemented."""
    spec = importlib.util.spec_from_file_location("doc_audit", _SCRIPT_PATH)
    assert spec is not None, f"Script not found: {_SCRIPT_PATH}"
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


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


@pytest.fixture()
def docs_root(tmp_path: Path) -> Path:
    """Create docs/ and docs/_data/tags.yml in a temp directory."""
    docs = tmp_path / "docs"
    docs.mkdir()
    data_dir = tmp_path / "docs" / "_data"
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "tags.yml").write_text(_TAGS_YML_CONTENT)
    return docs


@pytest.fixture()
def repo_root(tmp_path: Path, docs_root: Path) -> Path:
    """Return tmp_path as repo root (docs/ already created by docs_root)."""
    return tmp_path


# ---------------------------------------------------------------------------
# Scenario 1: Clean repo — all checks pass
# ---------------------------------------------------------------------------


class TestCleanRepo:
    """All docs valid — each checker returns an empty findings list."""

    @pytest.mark.unit
    def test_frontmatter_clean(
        self,
        doc_audit_module: object,
        docs_root: Path,
        repo_root: Path,
    ) -> None:
        """Valid frontmatter produces zero findings."""
        (docs_root / "valid.md").write_text(_VALID_FRONTMATTER)

        findings = doc_audit_module.check_frontmatter(  # type: ignore[attr-defined]
            str(docs_root), repo_root=str(repo_root)
        )

        assert findings == []

    @pytest.mark.unit
    def test_links_clean(
        self,
        doc_audit_module: object,
        docs_root: Path,
    ) -> None:
        """Internal link pointing to an existing file produces zero findings."""
        (docs_root / "a.md").write_text("See [B](b.md).\n")
        (docs_root / "b.md").write_text("# B\n")

        findings = doc_audit_module.check_links(str(docs_root))  # type: ignore[attr-defined]

        assert findings == []

    @pytest.mark.unit
    def test_counts_clean(
        self,
        doc_audit_module: object,
        docs_root: Path,
        repo_root: Path,
    ) -> None:
        """Count claim matching actual file count produces zero WARN findings."""
        agents_dir = repo_root / ".claude" / "agents"
        agents_dir.mkdir(parents=True)
        (agents_dir / "my-agent.md").write_text("# Agent\n")
        (docs_root / "overview.md").write_text("We have 1 agent available.\n")

        findings = doc_audit_module.check_counts(  # type: ignore[attr-defined]
            str(docs_root), repo_root=str(repo_root)
        )

        warn_or_error = [f for f in findings if f["severity"] in ("ERROR", "WARN")]
        assert warn_or_error == []

    @pytest.mark.unit
    def test_versions_clean(
        self,
        doc_audit_module: object,
        docs_root: Path,
        repo_root: Path,
    ) -> None:
        """Python version inside declared range produces zero findings."""
        (docs_root / "setup.md").write_text("Requires Python 3.12.\n")
        (repo_root / "pyproject.toml").write_text(
            '[project]\nrequires-python = ">=3.10,<3.15"\n'
        )

        findings = doc_audit_module.check_versions(  # type: ignore[attr-defined]
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
        doc_audit_module: object,
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

        findings = doc_audit_module.check_frontmatter(  # type: ignore[attr-defined]
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
        doc_audit_module: object,
        docs_root: Path,
        repo_root: Path,
    ) -> None:
        """Doc with no frontmatter block at all produces exactly one ERROR."""
        (docs_root / "bare.md").write_text("# No frontmatter\n\nJust text.\n")

        findings = doc_audit_module.check_frontmatter(  # type: ignore[attr-defined]
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
        doc_audit_module: object,
        docs_root: Path,
    ) -> None:
        """Markdown link to a non-existent relative path produces ERROR."""
        (docs_root / "broken.md").write_text("See [missing](./missing-file.md).\n")

        findings = doc_audit_module.check_links(str(docs_root))  # type: ignore[attr-defined]

        errors = [f for f in findings if f["severity"] == "ERROR"]
        assert len(errors) == 1
        assert "missing-file.md" in errors[0]["message"]
        assert errors[0]["category"] == "links"
        assert errors[0]["file"].endswith("broken.md")

    @pytest.mark.unit
    def test_http_links_are_skipped(
        self,
        doc_audit_module: object,
        docs_root: Path,
    ) -> None:
        """External https link to a non-existent URL produces zero findings."""
        (docs_root / "ext.md").write_text(
            "See [external](https://example.com/nonexistent).\n"
        )

        findings = doc_audit_module.check_links(str(docs_root))  # type: ignore[attr-defined]

        assert findings == []

    @pytest.mark.unit
    def test_anchor_only_links_are_skipped(
        self,
        doc_audit_module: object,
        docs_root: Path,
    ) -> None:
        """Anchor-only link (#section) produces zero findings."""
        (docs_root / "anchor.md").write_text("Jump to [section](#my-section).\n")

        findings = doc_audit_module.check_links(str(docs_root))  # type: ignore[attr-defined]

        assert findings == []


# ---------------------------------------------------------------------------
# Scenario 4: Count claim mismatch
# ---------------------------------------------------------------------------


class TestCountMismatch:
    """Claimed count differing from actual count produces WARN."""

    @pytest.mark.unit
    def test_agent_count_mismatch_is_warn(
        self,
        doc_audit_module: object,
        docs_root: Path,
        repo_root: Path,
    ) -> None:
        """Claiming '5 agents' when 1 agent exists produces one WARN."""
        (docs_root / "overview.md").write_text("We have 5 agents available.\n")
        agents_dir = repo_root / ".claude" / "agents"
        agents_dir.mkdir(parents=True, exist_ok=True)
        (agents_dir / "one-agent.md").write_text("# Agent\n")

        findings = doc_audit_module.check_counts(  # type: ignore[attr-defined]
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
        doc_audit_module: object,
        docs_root: Path,
        repo_root: Path,
    ) -> None:
        """Python 3.8 with requires-python >=3.10 produces at least one WARN."""
        (docs_root / "setup.md").write_text("Requires Python 3.8 or newer.\n")
        (repo_root / "pyproject.toml").write_text(
            '[project]\nrequires-python = ">=3.10,<3.15"\n'
        )

        findings = doc_audit_module.check_versions(  # type: ignore[attr-defined]
            str(docs_root), repo_root=str(repo_root)
        )

        warns = [f for f in findings if f["severity"] == "WARN"]
        assert len(warns) >= 1
        assert any("3.8" in f["message"] for f in warns)
        assert all(f["category"] == "versions" for f in warns)

    @pytest.mark.unit
    def test_unknown_model_name_is_warn(
        self,
        doc_audit_module: object,
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

        findings = doc_audit_module.check_versions(  # type: ignore[attr-defined]
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

        result = subprocess.run(
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
        assert set(data["summary"].keys()) == {"frontmatter", "links", "counts", "versions"}
        for cat in data["summary"].values():
            assert "pass" in cat
            assert "warn" in cat
            assert "error" in cat
```

- [ ] **Step 3: Run tests to verify they fail**

```bash
cd /home/byron/dev/.claude && uv run pytest tests/unit/test_doc_audit.py -v 2>&1 | head -40
```

Expected: tests fail or error with `AssertionError: Script not found` (script doesn't exist yet). All 14 tests should show as ERROR or FAILED, none PASSED.

---

### Task 2: Implement scripts/doc-audit.py

**Files:**
- Create: `scripts/doc-audit.py`

- [ ] **Step 1: Verify scripts/ directory exists**

```bash
ls /home/byron/dev/.claude/scripts/ | head -5
```

Expected: existing scripts like `validate-frontmatter.sh`, `py310-compat-check.sh`.

- [ ] **Step 2: Create scripts/doc-audit.py**

Create `/home/byron/dev/.claude/scripts/doc-audit.py` with this exact content:

```python
#!/usr/bin/env python3
"""Documentation health audit script.

Scans markdown files in a specified scope directory and checks:
1. Frontmatter validation (required fields per schema_type)
2. Broken internal link detection
3. Count claim verification against actual codebase
4. Version reference staleness (Python versions, Claude model names)

Outputs JSON to stdout. Always exits 0.

Usage:
    python3 scripts/doc-audit.py [--scope docs/] [--repo-root .]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import TypedDict


# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------


class Finding(TypedDict):
    """A single audit finding."""

    category: str
    severity: str  # ERROR | WARN | INFO
    file: str
    line: int
    message: str


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SCHEMA_REQUIRED_FIELDS: dict[str, list[str]] = {
    "common": ["schema_type", "title", "status", "owner", "purpose", "tags"],
    "planning": [
        "schema_type",
        "title",
        "status",
        "owner",
        "purpose",
        "component",
        "source",
        "tags",
    ],
    "adr": ["schema_type", "title", "status", "owner", "purpose", "tags"],
}

KNOWN_CURRENT_MODELS: frozenset[str] = frozenset(
    {
        "claude-sonnet-4-6",
        "claude-opus-4-6",
        "claude-haiku-4-5",
        "claude-haiku-4-5-20251001",
    }
)

_COUNT_WORD_MAP: dict[str, str] = {
    "agent": "agents",
    "agents": "agents",
    "skill": "skills",
    "skills": "skills",
    "hook": "hooks",
    "hooks": "hooks",
    "doc": "docs",
    "docs": "docs",
}


# ---------------------------------------------------------------------------
# Frontmatter parsing (stdlib only — no PyYAML)
# ---------------------------------------------------------------------------


def _parse_frontmatter(content: str) -> dict[str, object] | None:
    """Parse YAML frontmatter between the first two '---' delimiters.

    Returns None if no valid frontmatter block is found. Parses scalars,
    simple lists (- item), and block scalars (> prefix) sufficient for
    the fields validated by check_frontmatter.

    Args:
        content: Full file content as a string.

    Returns:
        Parsed frontmatter as a dict, or None if not present.
    """
    if not content.startswith("---"):
        return None
    end = content.find("---", 3)
    if end == -1:
        return None
    yaml_block = content[3:end].strip()
    return _parse_simple_yaml(yaml_block)


def _parse_simple_yaml(yaml_text: str) -> dict[str, object]:
    """Parse a minimal YAML subset: scalars and indented lists.

    Args:
        yaml_text: Raw YAML text between the '---' delimiters.

    Returns:
        Dict of parsed key-value pairs.
    """
    result: dict[str, object] = {}
    current_list_key: str | None = None
    current_list: list[str] = []

    for line in yaml_text.splitlines():
        stripped = line.strip()

        if line.startswith("  - "):
            if current_list_key is not None:
                current_list.append(line[4:].strip())
            continue

        if current_list_key is not None and not line.startswith("  "):
            result[current_list_key] = list(current_list)
            current_list_key = None
            current_list = []

        if ":" in line and not line.startswith(" "):
            key, _, value = line.partition(":")
            key = key.strip()
            value = value.strip()
            if value in ("", ">", "|"):
                current_list_key = key
                current_list = []
            else:
                result[key] = value.strip("\"'")

    if current_list_key is not None and current_list:
        result[current_list_key] = list(current_list)

    return result


def _load_allowed_tags(repo_root: str) -> frozenset[str]:
    """Load the allowed tag set from docs/_data/tags.yml.

    Args:
        repo_root: Repository root directory path.

    Returns:
        Frozenset of allowed tag strings, or empty frozenset if file absent.
    """
    tags_path = Path(repo_root) / "docs" / "_data" / "tags.yml"
    if not tags_path.exists():
        return frozenset()
    tags: list[str] = []
    in_allowed = False
    for line in tags_path.read_text(encoding="utf-8").splitlines():
        if line.strip() == "allowed:":
            in_allowed = True
            continue
        if in_allowed and line.startswith("  - "):
            tags.append(line[4:].strip())
        elif in_allowed and line.strip() and not line.startswith(" "):
            break
    return frozenset(tags)


# ---------------------------------------------------------------------------
# Check 1: Frontmatter validation
# ---------------------------------------------------------------------------


def check_frontmatter(scope: str, repo_root: str = ".") -> list[Finding]:
    """Validate frontmatter in all markdown files within scope.

    For each .md file:
    - ERROR if no frontmatter block present
    - WARN if schema_type is not in [common, planning, adr]
    - WARN per missing required field for the declared schema_type
    - WARN per tag not in docs/_data/tags.yml

    Args:
        scope: Directory to scan recursively for .md files.
        repo_root: Repository root used to locate docs/_data/tags.yml.

    Returns:
        List of Finding dicts for all violations found.
    """
    findings: list[Finding] = []
    allowed_tags = _load_allowed_tags(repo_root)

    for md_file in sorted(Path(scope).rglob("*.md")):
        content = md_file.read_text(encoding="utf-8")

        if not content.startswith("---"):
            findings.append(
                Finding(
                    category="frontmatter",
                    severity="ERROR",
                    file=str(md_file),
                    line=1,
                    message="missing frontmatter block (file must start with '---')",
                )
            )
            continue

        fm = _parse_frontmatter(content)
        if fm is None:
            findings.append(
                Finding(
                    category="frontmatter",
                    severity="ERROR",
                    file=str(md_file),
                    line=1,
                    message="malformed frontmatter: no closing '---' delimiter",
                )
            )
            continue

        schema_type = str(fm.get("schema_type", ""))
        if schema_type not in SCHEMA_REQUIRED_FIELDS:
            findings.append(
                Finding(
                    category="frontmatter",
                    severity="WARN",
                    file=str(md_file),
                    line=1,
                    message=(
                        f"schema_type '{schema_type}' not in "
                        "[common, planning, adr]"
                    ),
                )
            )
            continue

        for field in SCHEMA_REQUIRED_FIELDS[schema_type]:
            if field not in fm or fm[field] == "":
                findings.append(
                    Finding(
                        category="frontmatter",
                        severity="WARN",
                        file=str(md_file),
                        line=1,
                        message=(
                            f"missing required field '{field}' "
                            f"(schema_type: {schema_type})"
                        ),
                    )
                )

        if allowed_tags:
            raw_tags = fm.get("tags", [])
            tags: list[str] = raw_tags if isinstance(raw_tags, list) else []
            for tag in tags:
                if tag not in allowed_tags:
                    findings.append(
                        Finding(
                            category="frontmatter",
                            severity="WARN",
                            file=str(md_file),
                            line=1,
                            message=(
                                f"tag '{tag}' not in docs/_data/tags.yml allowlist"
                            ),
                        )
                    )

    return findings


# ---------------------------------------------------------------------------
# Check 2: Broken link detection
# ---------------------------------------------------------------------------

_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)#][^)]*)\)")


def check_links(scope: str) -> list[Finding]:
    """Detect broken internal markdown links in all files within scope.

    Skips external links (http/https) and anchor-only links (#section).
    Resolves relative paths against the containing file's directory.

    Args:
        scope: Directory to scan recursively for .md files.

    Returns:
        List of Finding dicts with severity ERROR for each broken link.
    """
    findings: list[Finding] = []

    for md_file in sorted(Path(scope).rglob("*.md")):
        content = md_file.read_text(encoding="utf-8")
        for line_no, line in enumerate(content.splitlines(), start=1):
            for match in _LINK_RE.finditer(line):
                target = match.group(2)
                if target.startswith(("http://", "https://")):
                    continue
                if target.startswith("#"):
                    continue
                path_part = target.split("#")[0]
                if not path_part:
                    continue
                resolved = (md_file.parent / path_part).resolve()
                if not resolved.exists():
                    findings.append(
                        Finding(
                            category="links",
                            severity="ERROR",
                            file=str(md_file),
                            line=line_no,
                            message=f"broken link: '{path_part}' does not exist",
                        )
                    )

    return findings


# ---------------------------------------------------------------------------
# Check 3: Count claim verification
# ---------------------------------------------------------------------------

_COUNT_RE = re.compile(r"\b(\d+)\s+(agents?|skills?|hooks?|docs?)\b", re.IGNORECASE)


def _actual_counts(repo_root: str) -> dict[str, int]:
    """Count actual agents, skills, hooks, and docs in the repository.

    Args:
        repo_root: Repository root directory path.

    Returns:
        Dict mapping category name to actual count.
    """
    root = Path(repo_root)

    agents_count = len(list((root / ".claude" / "agents").glob("*.md")))
    skills_count = len(list((root / ".claude" / "skills").glob("*/SKILL.md")))
    docs_count = len(list((root / "docs").rglob("*.md")))

    hooks_count = 0
    settings_path = Path.home() / ".claude" / "settings.json"
    if settings_path.exists():
        try:
            settings = json.loads(settings_path.read_text(encoding="utf-8"))
            hooks = settings.get("hooks", {})
            hooks_count = len(hooks.get("PreToolUse", [])) + len(
                hooks.get("PostToolUse", [])
            )
        except (json.JSONDecodeError, KeyError, TypeError):
            hooks_count = 0

    return {
        "agents": agents_count,
        "skills": skills_count,
        "hooks": hooks_count,
        "docs": docs_count,
    }


def check_counts(scope: str, repo_root: str = ".") -> list[Finding]:
    """Verify count claims in markdown files against actual codebase counts.

    Searches for patterns like '15 agents', '3 skills', '2 hooks', '50 docs'.
    Known categories (agents, skills, hooks, docs) are verified against real
    filesystem counts. Unrecognized categories are skipped.

    Args:
        scope: Directory to scan recursively for .md files.
        repo_root: Repository root used to compute actual counts.

    Returns:
        List of Finding dicts with severity WARN for each mismatch.
    """
    findings: list[Finding] = []
    actual = _actual_counts(repo_root)

    for md_file in sorted(Path(scope).rglob("*.md")):
        content = md_file.read_text(encoding="utf-8")
        for line_no, line in enumerate(content.splitlines(), start=1):
            for match in _COUNT_RE.finditer(line):
                claimed = int(match.group(1))
                category_key = _COUNT_WORD_MAP.get(match.group(2).lower(), "")
                if not category_key:
                    continue
                real = actual.get(category_key, 0)
                if claimed != real:
                    findings.append(
                        Finding(
                            category="counts",
                            severity="WARN",
                            file=str(md_file),
                            line=line_no,
                            message=(
                                f"claims '{claimed} {match.group(2)}' "
                                f"— actual: {real}"
                            ),
                        )
                    )

    return findings


# ---------------------------------------------------------------------------
# Check 4: Version reference staleness
# ---------------------------------------------------------------------------

_PYTHON_VER_RE = re.compile(r"Python\s+3\.(\d+)")
_MODEL_RE = re.compile(r"claude-[a-z]+-\d[\w-]*")


def _parse_python_range(
    requires_python: str,
) -> tuple[tuple[int, int], tuple[int, int]] | None:
    """Parse requires-python string into inclusive-min, exclusive-max minor tuples.

    Args:
        requires_python: String like '>=3.10,<3.15'.

    Returns:
        ((3, min_minor), (3, max_minor)) or None if unparseable.
    """
    ge_match = re.search(r">=3\.(\d+)", requires_python)
    lt_match = re.search(r"<3\.(\d+)", requires_python)
    if not ge_match or not lt_match:
        return None
    return (3, int(ge_match.group(1))), (3, int(lt_match.group(1)))


def _load_python_range(
    repo_root: str,
) -> tuple[tuple[int, int], tuple[int, int]] | None:
    """Read requires-python from pyproject.toml and parse into version bounds.

    Args:
        repo_root: Repository root directory path.

    Returns:
        ((3, min_minor), (3, max_minor)) or None if pyproject.toml absent.
    """
    pyproject = Path(repo_root) / "pyproject.toml"
    if not pyproject.exists():
        return None
    content = pyproject.read_text(encoding="utf-8")
    match = re.search(r'requires-python\s*=\s*"([^"]+)"', content)
    if not match:
        return None
    return _parse_python_range(match.group(1))


def check_versions(scope: str, repo_root: str = ".") -> list[Finding]:
    """Flag stale Python version references and unknown model names.

    Python version check: any 'Python 3.X' reference where X is outside
    the range declared in pyproject.toml requires-python field is WARN.

    Model name check: any claude-*-* pattern not in the known current
    models list is WARN.

    Args:
        scope: Directory to scan recursively for .md files.
        repo_root: Repository root used to locate pyproject.toml.

    Returns:
        List of Finding dicts with severity WARN for each stale reference.
    """
    findings: list[Finding] = []
    python_range = _load_python_range(repo_root)

    for md_file in sorted(Path(scope).rglob("*.md")):
        content = md_file.read_text(encoding="utf-8")
        for line_no, line in enumerate(content.splitlines(), start=1):
            for match in _PYTHON_VER_RE.finditer(line):
                minor = int(match.group(1))
                if python_range is not None:
                    lo, hi = python_range
                    if (3, minor) < lo or (3, minor) >= hi:
                        findings.append(
                            Finding(
                                category="versions",
                                severity="WARN",
                                file=str(md_file),
                                line=line_no,
                                message=(
                                    f"Python 3.{minor} is outside declared range "
                                    f">=3.{lo[1]},<3.{hi[1]} in pyproject.toml"
                                ),
                            )
                        )

            for match in _MODEL_RE.finditer(line):
                model_name = match.group(0)
                if model_name not in KNOWN_CURRENT_MODELS:
                    findings.append(
                        Finding(
                            category="versions",
                            severity="WARN",
                            file=str(md_file),
                            line=line_no,
                            message=f"model '{model_name}' may be outdated",
                        )
                    )

    return findings


# ---------------------------------------------------------------------------
# Summary aggregation
# ---------------------------------------------------------------------------


def _summarize_category(
    all_findings: list[Finding], category: str, total_checked: int
) -> dict[str, int]:
    """Compute pass/warn/error counts for one check category.

    Args:
        all_findings: Full findings list from all checks.
        category: Category name to filter on.
        total_checked: Total items checked (files or claims) for this category.

    Returns:
        Dict with keys 'pass', 'warn', 'error'.
    """
    cat = [f for f in all_findings if f["category"] == category]
    error = sum(1 for f in cat if f["severity"] == "ERROR")
    warn = sum(1 for f in cat if f["severity"] == "WARN")
    pass_ = max(0, total_checked - error - warn)
    return {"pass": pass_, "warn": warn, "error": error}


# ---------------------------------------------------------------------------
# Main audit runner
# ---------------------------------------------------------------------------


def run_audit(scope: str, repo_root: str = ".") -> dict[str, object]:
    """Run all four checks and assemble the output dict.

    Args:
        scope: Directory to audit.
        repo_root: Repository root for count and version checks.

    Returns:
        Dict matching the JSON output schema.
    """
    today = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
    md_files = list(Path(scope).rglob("*.md"))
    total_files = len(md_files)

    fm_findings = check_frontmatter(scope, repo_root=repo_root)
    lk_findings = check_links(scope)
    ct_findings = check_counts(scope, repo_root=repo_root)
    vr_findings = check_versions(scope, repo_root=repo_root)

    all_findings: list[Finding] = fm_findings + lk_findings + ct_findings + vr_findings

    return {
        "scope": scope,
        "generated": today,
        "summary": {
            "frontmatter": _summarize_category(all_findings, "frontmatter", total_files),
            "links": _summarize_category(all_findings, "links", total_files),
            "counts": _summarize_category(all_findings, "counts", total_files),
            "versions": _summarize_category(all_findings, "versions", total_files),
        },
        "findings": all_findings,
    }


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """Parse arguments, run the audit, and print JSON to stdout."""
    parser = argparse.ArgumentParser(description="Documentation health audit")
    parser.add_argument(
        "--scope",
        default="docs/",
        help="Directory to audit (default: docs/)",
    )
    parser.add_argument(
        "--repo-root",
        default=".",
        help="Repository root for count and version checks (default: .)",
    )
    args = parser.parse_args()

    result = run_audit(args.scope, repo_root=args.repo_root)
    print(json.dumps(result, indent=2))
    sys.exit(0)


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Run tests to verify they pass**

```bash
cd /home/byron/dev/.claude && uv run pytest tests/unit/test_doc_audit.py -v 2>&1
```

Expected: all 14 tests PASSED. Zero failures, zero errors.

- [ ] **Step 4: Run ruff format and lint**

```bash
cd /home/byron/dev/.claude && uv run ruff format scripts/doc-audit.py tests/unit/test_doc_audit.py && uv run ruff check scripts/doc-audit.py tests/unit/test_doc_audit.py
```

Expected: no errors. If ruff auto-fixes spacing or imports, re-run tests to confirm they still pass.

- [ ] **Step 5: Run pre-commit on both files**

```bash
cd /home/byron/dev/.claude && pre-commit run --files scripts/doc-audit.py tests/unit/test_doc_audit.py
```

Expected: all hooks pass.

- [ ] **Step 6: Commit tests and implementation together**

```bash
cd /home/byron/dev/.claude && git add scripts/doc-audit.py tests/unit/test_doc_audit.py
git commit -m "feat: add doc-audit.py — four-category documentation health audit script"
```

---

### Task 3: Create .claude/skills/doc-audit/SKILL.md

**Files:**
- Create: `.claude/skills/doc-audit/SKILL.md`

- [ ] **Step 1: Verify the target directory does not already exist**

```bash
ls /home/byron/dev/.claude/.claude/skills/doc-audit/ 2>/dev/null || echo "directory does not exist — safe to create"
```

Expected: "directory does not exist — safe to create"

- [ ] **Step 2: Create the SKILL.md**

Create `/home/byron/dev/.claude/.claude/skills/doc-audit/SKILL.md` with this exact content:

````markdown
---
description: >
  Documentation health audit. Scans markdown docs for frontmatter violations,
  broken internal links, count claim drift, and stale version references.
  Outputs a terminal summary table and writes docs/audit-report.md.
  Triggers on: doc-audit, audit docs, check docs, frontmatter audit,
  broken links, stale docs, documentation health.
tools: ["Read", "Bash", "Glob", "Grep", "Write"]
---

# Doc Audit Skill

Run a four-category documentation health audit and produce a persistent report.

## Invocation

```
/doc-audit [scope]
```

`scope` is optional (default: `docs/`). Examples:
- `/doc-audit` — audit all of `docs/`
- `/doc-audit docs/superpowers/specs` — audit a subdirectory

## Workflow

1. Determine scope from argument or default `docs/`
2. Run the audit script:
   ```bash
   python3 scripts/doc-audit.py --scope <scope>
   ```
3. Parse the JSON output
4. Print the terminal summary table (see format below)
5. Write `docs/audit-report.md` (overwrite if it exists)
6. Print the completion message

## Terminal Summary Table

Print this table after parsing the JSON:

```
Doc Audit Summary
─────────────────────────────────────────────────────
Category       Status      Issues
─────────────────────────────────────────────────────
Frontmatter    ✅ PASS     0 issues
Broken links   ⚠️  WARN    2 broken internal links
Count claims   ✅ PASS     0 issues
Version refs   ⚠️  WARN    4 stale references
─────────────────────────────────────────────────────
6 issues found. Full report: docs/audit-report.md
```

Status per category:
- `✅ PASS` — error=0 and warn=0
- `⚠️  WARN` — warn>0, error=0
- `❌ ERROR` — error>0 (regardless of warn count)

Issue count in the summary line: sum of all findings with severity ERROR or WARN across
all categories.

## Audit Report

Write `docs/audit-report.md` with this structure (substitute actual values):

```markdown
# Doc Audit Report

Generated: YYYY-MM-DD  Scope: docs/

## Summary

| Category     | Pass | Warn | Error |
|-------------|------|------|-------|
| Frontmatter | N    | N    | N     |
| Broken links | N   | N    | N     |
| Count claims | N   | N    | N     |
| Version refs | N   | N    | N     |

## Frontmatter Issues

- `docs/foo.md` line 1: missing required field `owner` (schema_type: common)

## Broken Links

(none)

## Count Drift

- `docs/overview.md` line 14: claims '15 agents' — actual: 18

## Stale Version References

- `docs/setup.md` line 7: Python 3.8 is outside declared range >=3.10,<3.15 in pyproject.toml
```

For sections with no findings, write `(none)` as the body.

## Completion Messages

Print one of these after writing the report:

- Any `ERROR` finding: "Audit complete. X errors require attention before next PR."
- Only `WARN` findings, no errors: "Audit complete. X warnings flagged for review."
- No findings: "Audit complete. No issues found."

X is the total count of findings at that severity level.
````

- [ ] **Step 3: Verify the file was created correctly**

```bash
head -10 /home/byron/dev/.claude/.claude/skills/doc-audit/SKILL.md
```

Expected: frontmatter block starting with `---`, description field present.

- [ ] **Step 4: Run pre-commit on the new file**

```bash
cd /home/byron/dev/.claude && pre-commit run --files .claude/skills/doc-audit/SKILL.md
```

Expected: all hooks pass.

- [ ] **Step 5: Commit**

```bash
cd /home/byron/dev/.claude && git add .claude/skills/doc-audit/SKILL.md
git commit -m "feat: add /doc-audit skill — terminal summary and audit-report.md writer"
```

---

### Task 4: Update .gitignore and run integration smoke test

**Files:**
- Modify: `.gitignore`

- [ ] **Step 1: Verify docs/audit-report.md is not already in .gitignore**

```bash
grep "audit-report" /home/byron/dev/.claude/.gitignore || echo "not present — safe to add"
```

Expected: "not present — safe to add"

- [ ] **Step 2: Add docs/audit-report.md to .gitignore**

Read the current `.gitignore` to find an appropriate insertion point (near other generated artifacts), then add `docs/audit-report.md`.

In `/home/byron/dev/.claude/.gitignore`, find the section that contains generated or temporary file patterns and add:

```
docs/audit-report.md
```

If there is no obvious generated-artifacts section, append it at the end of the file.

- [ ] **Step 3: Verify the addition**

```bash
grep "audit-report" /home/byron/dev/.claude/.gitignore
```

Expected: `docs/audit-report.md`

- [ ] **Step 4: Run integration smoke test against the live docs/ directory**

```bash
cd /home/byron/dev/.claude && python3 scripts/doc-audit.py --scope docs/ | python3 -m json.tool | head -30
```

Expected: valid JSON output with `scope`, `generated`, `summary`, and `findings` keys. No Python traceback.

- [ ] **Step 5: Verify docs/audit-report.md is git-ignored**

```bash
cd /home/byron/dev/.claude && python3 scripts/doc-audit.py --scope docs/ > /tmp/audit-output.json && echo "script ran OK"
git -C /home/byron/dev/.claude status --short | grep "audit-report" || echo "audit-report.md correctly ignored"
```

Expected: "audit-report.md correctly ignored" (file not tracked by git).

- [ ] **Step 6: Run pre-commit on .gitignore**

```bash
cd /home/byron/dev/.claude && pre-commit run --files .gitignore
```

Expected: all hooks pass.

- [ ] **Step 7: Commit**

```bash
cd /home/byron/dev/.claude && git add .gitignore
git commit -m "chore: add docs/audit-report.md to .gitignore (generated artifact)"
```

---

## Self-Review

**Spec coverage:**

| Spec requirement | Covered by |
|-----------------|-----------|
| `--scope` argument, default `docs/` | Task 2: `argparse`, `run_audit(scope)` |
| Frontmatter: parse `---` block, validate schema_type | Task 2: `check_frontmatter`, `_parse_frontmatter` |
| Frontmatter: required fields per schema_type (common/planning/adr) | Task 2: `SCHEMA_REQUIRED_FIELDS` |
| Frontmatter: tags against `docs/_data/tags.yml` | Task 2: `_load_allowed_tags` |
| Links: extract `[text](path)`, skip http and anchor-only | Task 2: `check_links`, `_LINK_RE` |
| Links: `os.path.exists()` check on resolved path | Task 2: `resolved.exists()` |
| Counts: grep `\b(\d+)\s+(agents?|skills?|hooks?|docs?)\b` | Task 2: `_COUNT_RE`, `check_counts` |
| Counts: actual count commands for all four categories | Task 2: `_actual_counts` |
| Counts: hooks from `~/.claude/settings.json` | Task 2: `_actual_counts` reads `settings.json` |
| Versions: `Python 3.\d+` vs pyproject.toml | Task 2: `check_versions`, `_load_python_range` |
| Versions: model names vs known current list | Task 2: `KNOWN_CURRENT_MODELS`, `_MODEL_RE` |
| JSON to stdout: `{scope, generated, summary, findings}` | Task 2: `run_audit`, `main` |
| Severity values: ERROR/WARN/INFO | Task 2: Finding TypedDict, all check functions |
| Always exits 0 | Task 2: `sys.exit(0)` |
| SKILL.md: invocation `/doc-audit [scope]` | Task 3: SKILL.md invocation section |
| SKILL.md: terminal summary table | Task 3: SKILL.md terminal summary section |
| SKILL.md: write `docs/audit-report.md` | Task 3: SKILL.md audit report section |
| SKILL.md: completion message by severity | Task 3: SKILL.md completion messages |
| `.gitignore` addition | Task 4 |
| TDD: 5 spec scenarios tested | Task 1: 6 test classes, 14 test methods |

**Placeholder scan:** None found. All steps have complete code.

**Type consistency:**
- `check_frontmatter(scope: str, repo_root: str = ".")` used consistently in tests and implementation
- `check_links(scope: str)` — no repo_root needed, consistent
- `check_counts(scope: str, repo_root: str = ".")` — consistent
- `check_versions(scope: str, repo_root: str = ".")` — consistent
- All return `list[Finding]` — consistent with test assertions (`findings[0]["severity"]`)
