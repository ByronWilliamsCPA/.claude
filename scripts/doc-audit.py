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

_CLAUDE_SUBDIR = ".claude"

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
# Frontmatter parsing (stdlib only: no PyYAML)
# ---------------------------------------------------------------------------


def _parse_frontmatter(content: str) -> dict[str, object] | None:
    """Parse YAML frontmatter between the first two '---' delimiters.

    Returns None if no valid frontmatter block is found.

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


def _parse_yaml_scalar_line(
    line: str,
    result: dict[str, object],
) -> tuple[str | None, list[str]]:
    """Parse a top-level YAML key: value line and update result in place.

    Args:
        line: A single YAML line (not a list item).
        result: Dict being built; updated in place for scalar values.

    Returns:
        (list_key, []) when the line starts a new list value; (None, []) otherwise.
    """
    if ":" not in line or line.startswith(" "):
        return None, []
    key, _, value = line.partition(":")
    key = key.strip()
    value = value.strip()
    if value in ("", ">", "|"):
        return key, []
    result[key] = value.strip("\"'")
    return None, []


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
        if line.startswith("  - "):
            if current_list_key is not None:
                current_list.append(line[4:].strip())
            continue

        if current_list_key is not None and not line.startswith("  "):
            result[current_list_key] = list(current_list)
            current_list_key = None
            current_list = []

        new_key, new_list = _parse_yaml_scalar_line(line, result)
        if new_key is not None:
            current_list_key = new_key
            current_list = new_list

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
    try:
        tags_text = tags_path.read_text(encoding="utf-8")
    except OSError:
        return frozenset()
    tags: list[str] = []
    in_allowed = False
    for line in tags_text.splitlines():
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


def check_frontmatter(scope: str, *, repo_root: str = ".") -> list[Finding]:
    """Validate frontmatter in all markdown files within scope.

    For each .md file:
    - ERROR if no frontmatter block present
    - WARN if schema_type not in [common, planning, adr]
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
        try:
            content = md_file.read_text(encoding="utf-8")
        except OSError as e:
            findings.append(
                Finding(
                    category="frontmatter",
                    severity="ERROR",
                    file=str(md_file),
                    line=1,
                    message=f"cannot read file: {e}",
                )
            )
            continue

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
                        f"schema_type '{schema_type}' not in [common, planning, adr]"
                    ),
                )
            )
            continue

        findings.extend(
            Finding(
                category="frontmatter",
                severity="WARN",
                file=str(md_file),
                line=1,
                message=(
                    f"missing required field '{field}' (schema_type: {schema_type})"
                ),
            )
            for field in SCHEMA_REQUIRED_FIELDS[schema_type]
            if field not in fm or fm[field] == ""
        )

        if allowed_tags:
            raw_tags = fm.get("tags", [])
            tags: list[str] = raw_tags if isinstance(raw_tags, list) else []
            findings.extend(
                Finding(
                    category="frontmatter",
                    severity="WARN",
                    file=str(md_file),
                    line=1,
                    message=f"tag '{tag}' not in docs/_data/tags.yml allowlist",
                )
                for tag in tags
                if tag not in allowed_tags
            )

    return findings


# ---------------------------------------------------------------------------
# Check 2: Broken link detection
# ---------------------------------------------------------------------------

_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")


def _extract_local_path(target: str) -> str | None:
    """Return the local file path portion of a link target, or None to skip.

    Skips external links (http/https), anchor-only links (#section), and
    empty path parts.

    Args:
        target: Raw link target string from a markdown link.

    Returns:
        Local path string, or None if the link should be skipped.
    """
    if target.startswith(("http://", "https://")):
        return None
    if target.startswith("#"):
        return None
    path_part = target.split("#", maxsplit=1)[0]
    return path_part or None


def _check_links_in_file(md_file: Path) -> list[Finding]:
    """Check all internal links in a single markdown file.

    Args:
        md_file: Path to the markdown file to check.

    Returns:
        List of Finding dicts with severity ERROR for each broken link.
    """
    findings: list[Finding] = []
    try:
        content = md_file.read_text(encoding="utf-8")
    except OSError as e:
        return [
            Finding(
                category="links",
                severity="ERROR",
                file=str(md_file),
                line=1,
                message=f"cannot read file: {e}",
            )
        ]
    for line_no, line in enumerate(content.splitlines(), start=1):
        for match in _LINK_RE.finditer(line):
            path_part = _extract_local_path(match.group(2))
            if path_part is None:
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
        findings.extend(_check_links_in_file(md_file))
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

    agents_dir = root / _CLAUDE_SUBDIR / "agents"
    # CLAUDE.md in agents/ holds authoring conventions, not an agent definition.
    agents_count = (
        len([p for p in agents_dir.glob("*.md") if p.name != "CLAUDE.md"])
        if agents_dir.exists()
        else 0
    )

    skills_dir = root / _CLAUDE_SUBDIR / "skills"
    skills_count = (
        len(list(skills_dir.glob("*/SKILL.md"))) if skills_dir.exists() else 0
    )

    docs_dir = root / "docs"
    docs_count = len(list(docs_dir.rglob("*.md"))) if docs_dir.exists() else 0

    hooks_count = 0
    settings_path = Path.home() / _CLAUDE_SUBDIR / "settings.json"
    if settings_path.exists():
        try:
            settings = json.loads(settings_path.read_text(encoding="utf-8"))
            hooks = settings.get("hooks", {})
            hooks_count = len(hooks.get("PreToolUse", [])) + len(
                hooks.get("PostToolUse", [])
            )
        except (json.JSONDecodeError, KeyError, OSError, TypeError):
            hooks_count = 0

    return {
        "agents": agents_count,
        "skills": skills_count,
        "hooks": hooks_count,
        "docs": docs_count,
    }


def _check_count_match(
    match: re.Match[str],
    actual: dict[str, int],
    md_file: Path,
    line_no: int,
) -> Finding | None:
    """Evaluate a single count-claim regex match against actual counts.

    Args:
        match: Regex match from _COUNT_RE with groups (number, category_word).
        actual: Mapping from category key to actual filesystem count.
        md_file: Source markdown file (used for the Finding file field).
        line_no: 1-based line number in md_file (used for the Finding line field).

    Returns:
        A Finding if the claim is unrecognised or mismatched, else None.
    """
    claimed = int(match.group(1))
    category_key = _COUNT_WORD_MAP.get(match.group(2).lower(), "")
    if not category_key:
        return Finding(
            category="counts",
            severity="INFO",
            file=str(md_file),
            line=line_no,
            message=(
                f"count claim '{match.group(2)}': "
                "unrecognized category, flagged for manual review"
            ),
        )
    real = actual.get(category_key, 0)
    if claimed != real:
        return Finding(
            category="counts",
            severity="WARN",
            file=str(md_file),
            line=line_no,
            message=(f"claims '{claimed} {match.group(2)}': actual: {real}"),
        )
    return None


def check_counts(scope: str, *, repo_root: str = ".") -> list[Finding]:
    """Verify count claims in markdown files against actual codebase counts.

    Searches for patterns like '15 agents', '3 skills', '2 hooks', '50 docs'.
    Known categories are verified against real filesystem counts.

    Args:
        scope: Directory to scan recursively for .md files.
        repo_root: Repository root used to compute actual counts.

    Returns:
        List of Finding dicts with severity WARN for each mismatch.
    """
    findings: list[Finding] = []
    actual = _actual_counts(repo_root)

    for md_file in sorted(Path(scope).rglob("*.md")):
        try:
            content = md_file.read_text(encoding="utf-8")
        except OSError as e:
            findings.append(
                Finding(
                    category="counts",
                    severity="ERROR",
                    file=str(md_file),
                    line=1,
                    message=f"cannot read file: {e}",
                )
            )
            continue
        for line_no, line in enumerate(content.splitlines(), start=1):
            for match in _COUNT_RE.finditer(line):
                finding = _check_count_match(match, actual, md_file, line_no)
                if finding is not None:
                    findings.append(finding)

    return findings


# ---------------------------------------------------------------------------
# Check 4: Version reference staleness
# ---------------------------------------------------------------------------

_PYTHON_VER_RE = re.compile(r"Python\s+3\.(\d+)")
_MODEL_RE = re.compile(r"claude-[a-z]+-\d[\w-]*")
_SCHEMA_VER_RE = re.compile(r"schema_version\s+\d+")


def _parse_python_range(
    requires_python: str,
) -> tuple[tuple[int, int], tuple[int, int]] | None:
    """Parse requires-python string into version bound tuples.

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
    try:
        content = pyproject.read_text(encoding="utf-8")
    except OSError:
        return None
    match = re.search(r'requires-python\s*=\s*"([^"]+)"', content)
    if not match:
        return None
    return _parse_python_range(match.group(1))


def _check_python_version(
    line: str,
    file_path: str,
    line_no: int,
    python_range: tuple[tuple[int, int], tuple[int, int]] | None,
) -> list[Finding]:
    """Check a single line for out-of-range Python version references.

    Args:
        line: Source line text.
        file_path: Path string of the file being scanned.
        line_no: 1-based line number.
        python_range: Parsed (min, max) version tuples from pyproject.toml.

    Returns:
        List of WARN findings for each out-of-range reference.
    """
    if python_range is None:
        return []
    lo, hi = python_range
    return [
        Finding(
            category="versions",
            severity="WARN",
            file=file_path,
            line=line_no,
            message=(
                f"Python 3.{int(m.group(1))} is outside declared range "
                f">=3.{lo[1]},<3.{hi[1]} in pyproject.toml"
            ),
        )
        for m in _PYTHON_VER_RE.finditer(line)
        if (3, int(m.group(1))) < lo or (3, int(m.group(1))) >= hi
    ]


def _check_model_names(line: str, file_path: str, line_no: int) -> list[Finding]:
    """Check a single line for unknown Claude model name references.

    Args:
        line: Source line text.
        file_path: Path string of the file being scanned.
        line_no: 1-based line number.

    Returns:
        List of WARN findings for each unrecognized model name.
    """
    return [
        Finding(
            category="versions",
            severity="WARN",
            file=file_path,
            line=line_no,
            message=f"model '{m.group(0)}' may be outdated",
        )
        for m in _MODEL_RE.finditer(line)
        if m.group(0) not in KNOWN_CURRENT_MODELS
    ]


def _check_schema_version_refs(
    line: str, file_path: str, line_no: int
) -> list[Finding]:
    """Check a single line for schema_version references flagged for manual review.

    Args:
        line: Source line text.
        file_path: Path string of the file being scanned.
        line_no: 1-based line number.

    Returns:
        List of INFO findings for each schema_version reference.
    """
    return [
        Finding(
            category="versions",
            severity="INFO",
            file=file_path,
            line=line_no,
            message=(
                f"schema_version reference '{m.group(0)}': flagged for manual review"
            ),
        )
        for m in _SCHEMA_VER_RE.finditer(line)
    ]


def check_versions(scope: str, *, repo_root: str = ".") -> list[Finding]:
    """Flag stale Python version references and unknown model names.

    Python version: any 'Python 3.X' outside pyproject.toml range is WARN.
    Model names: any claude-*-* not in KNOWN_CURRENT_MODELS is WARN.
    Schema version references: flagged as INFO for manual review.

    Args:
        scope: Directory to scan recursively for .md files.
        repo_root: Repository root used to locate pyproject.toml.

    Returns:
        List of Finding dicts for each stale or flagged reference.
    """
    findings: list[Finding] = []
    python_range = _load_python_range(repo_root)

    for md_file in sorted(Path(scope).rglob("*.md")):
        file_path = str(md_file)
        try:
            file_lines = md_file.read_text(encoding="utf-8").splitlines()
        except OSError as e:
            findings.append(
                Finding(
                    category="versions",
                    severity="ERROR",
                    file=file_path,
                    line=1,
                    message=f"cannot read file: {e}",
                )
            )
            continue
        for line_no, line in enumerate(file_lines, start=1):
            findings.extend(
                _check_python_version(line, file_path, line_no, python_range)
            )
            findings.extend(_check_model_names(line, file_path, line_no))
            findings.extend(_check_schema_version_refs(line, file_path, line_no))

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
        total_checked: Total items checked for this category.

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


def run_audit(scope: str, *, repo_root: str = ".") -> dict[str, object]:
    """Run all four checks and assemble the output dict.

    Args:
        scope: Directory to audit.
        repo_root: Repository root for count and version checks.

    Returns:
        Dict matching the JSON output schema.
    """
    today = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
    total_files = len(list(Path(scope).rglob("*.md")))

    fm_findings = check_frontmatter(scope, repo_root=repo_root)
    lk_findings = check_links(scope)
    ct_findings = check_counts(scope, repo_root=repo_root)
    vr_findings = check_versions(scope, repo_root=repo_root)

    all_findings: list[Finding] = fm_findings + lk_findings + ct_findings + vr_findings

    return {
        "scope": scope,
        "generated": today,
        "summary": {
            "frontmatter": _summarize_category(
                all_findings, "frontmatter", total_files
            ),
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
