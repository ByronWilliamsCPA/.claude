#!/usr/bin/env python3
"""Walk every catalog repo and backfill any per-repo retrospectives.

Backfills retrospectives that are missing from the central master log.

Idempotent: dedupes by (session_date, repo). Read-only on per-repo
Markdown files. Appends backfilled entries with reconciled=true.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

if __name__ == "__main__" and __package__ is None:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.compliance_log_common import (
    SCHEMA_VERSION,
    load_entries,
    make_dedupe_key,
    repo_root_from,
)

_REPO_ROOT = repo_root_from(Path(__file__))
DEFAULT_CATALOG = _REPO_ROOT / "docs" / "reference" / "github-repos.json"
DEFAULT_JSONL = _REPO_ROOT / "docs" / "compliance-reports" / "master-log.jsonl"
DEFAULT_RECONCILE_LOG = (
    _REPO_ROOT / "docs" / "compliance-reports" / "state" / "reconcile-log.txt"
)
DEFAULT_REPOS_ROOT = Path.home() / "dev"
RENDERER_SCRIPT = Path(__file__).resolve().parent / "compliance_log_render.py"

DATE_FILENAME_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})(?:-[\w.-]+)?\.md$")


class InvalidRetrospectiveError(ValueError):
    """Raised when a per-repo retrospective file cannot be parsed."""


@dataclass
class ReconcileResult:
    """Aggregate counters returned by :func:`reconcile`."""

    walked: int = 0
    with_clone: int = 0
    skipped_no_clone: int = 0
    appended: int = 0
    duplicates_skipped: int = 0
    parse_failures: list[str] = field(default_factory=list)


def resolve_local_clone(repo_name: str, repos_root: Path) -> Path | None:
    """Find local clone of a repo, allowing - <-> _ slug normalization."""
    direct = repos_root / repo_name
    if direct.is_dir():
        return direct
    alt = repos_root / repo_name.replace("-", "_")
    if alt.is_dir():
        return alt
    alt2 = repos_root / repo_name.replace("_", "-")
    if alt2.is_dir():
        return alt2
    return None


def _parse_session_summary_table(text: str) -> dict[str, int]:
    """Extract totals from the Session Summary table."""
    totals: dict[str, int] = {
        "critical": 0,
        "important": 0,
        "suggested": 0,
        "unclassified_candidates": 0,
        "overrides_applied": 0,
    }
    summary_match = re.search(
        r"##\s+Session Summary\s*\n(.*?)(?=\n##\s+|\Z)",
        text,
        re.DOTALL,
    )
    if not summary_match:
        return totals

    block = summary_match.group(1)
    row_re = re.compile(r"^\|\s*([^|]+?)\s*\|\s*(\d+)\s*\|", re.MULTILINE)
    label_to_field = {
        "critical": "critical",
        "important": "important",
        "suggested": "suggested",
        "unclassified candidates": "unclassified_candidates",
        "overrides applied": "overrides_applied",
    }
    for label, value in row_re.findall(block):
        key = label.strip().lower()
        if key in label_to_field:
            totals[label_to_field[key]] = int(value)
    return totals


def _parse_findings_by_check(text: str) -> list[dict[str, str]]:
    """Extract check IDs from the High-Frequency Existing Checks section."""
    match = re.search(
        r"##\s+High-Frequency Existing Checks\s*\n(.*?)(?=\n##\s+|\Z)",
        text,
        re.DOTALL,
    )
    if not match:
        return []

    findings: list[dict[str, str]] = []
    for line in match.group(1).splitlines():
        m = re.match(r"^-\s+([A-Z][A-Z0-9]*-\d{3})", line.strip())
        if m:
            findings.append(
                {
                    "id": m.group(1),
                    "severity": "unknown",
                    "remediation_status": "open",
                }
            )
    return findings


def _parse_unclassified_candidates(text: str) -> list[dict[str, str]]:
    """Extract candidate IDs from Proposed Manifest Additions YAML blocks."""
    section_match = re.search(
        r"##\s+Proposed Manifest Additions\s*\n(.*?)(?=\n##\s+|\Z)",
        text,
        re.DOTALL,
    )
    if not section_match:
        return []

    candidates: list[dict[str, str]] = []
    for yaml_match in re.finditer(
        r"```yaml\n(.*?)```",
        section_match.group(1),
        re.DOTALL,
    ):
        block = yaml_match.group(1)
        id_match = re.search(r"^\s*-?\s*id:\s*(\S+)", block, re.MULTILINE)
        desc_match = re.search(
            r"^\s*description:\s*\"?([^\"\n]+)\"?",
            block,
            re.MULTILINE,
        )
        if id_match:
            candidates.append(
                {
                    "candidate_id": f"reconciled-{uuid.uuid4().hex[:8]}",
                    "pattern": (desc_match.group(1).strip() if desc_match else ""),
                    "proposed_manifest_id": id_match.group(1).strip(),
                    "proposed_yaml_path": "",
                }
            )
    return candidates


def parse_lessons_learned(path: Path) -> dict[str, Any]:
    """Parse a per-repo lessons-learned Markdown file into a partial entry.

    Raises:
        InvalidRetrospectiveError: if the filename does not match the
            expected YYYY-MM-DD[-tag].md pattern.
    """
    fname_match = DATE_FILENAME_RE.match(path.name)
    if not fname_match:
        raise InvalidRetrospectiveError(
            f"filename {path.name} does not match YYYY-MM-DD[-tag].md"
        )
    session_date = fname_match.group(1)
    text = path.read_text(encoding="utf-8")

    return {
        "session_date": session_date,
        "totals": _parse_session_summary_table(text),
        "findings_by_check": _parse_findings_by_check(text),
        "unclassified_candidates": _parse_unclassified_candidates(text),
        "fleet_action_proposals": [],
        "scope_expansion_flags": [],
        "links": {"lessons_learned": str(path)},
    }


def _make_session_id(date: str) -> str:
    """Build a synthetic session_id for a reconciled entry."""
    nonce = uuid.uuid4().hex[:4]
    return f"{date}T00:00:00Z-{nonce}"


def _build_entry(
    repo_full: str,
    repo_path: Path,
    parsed: dict[str, Any],
) -> dict[str, Any]:
    """Assemble a full master-log entry from a parsed per-repo file."""
    return {
        "schema_version": SCHEMA_VERSION,
        "session_date": parsed["session_date"],
        "session_id": _make_session_id(parsed["session_date"]),
        "repo": repo_full,
        "repo_path": str(repo_path),
        "audit_mode": "unknown",
        "repo_type": "unknown",
        "visibility": "unknown",
        "reconciled": True,
        "totals": parsed["totals"],
        "findings_by_check": parsed["findings_by_check"],
        "unclassified_candidates": parsed["unclassified_candidates"],
        "fleet_action_proposals": parsed["fleet_action_proposals"],
        "scope_expansion_flags": parsed["scope_expansion_flags"],
        "links": parsed["links"],
        "superseded_by": None,
    }


def _append_entry(jsonl_path: Path, entry: dict[str, Any]) -> None:
    """Append an entry to the JSONL master log, creating header if needed."""
    jsonl_path.parent.mkdir(parents=True, exist_ok=True)
    if not jsonl_path.exists():
        header = {
            "type": "header",
            "schema_version": SCHEMA_VERSION,
            "created": datetime.now(tz=timezone.utc).strftime("%Y-%m-%d"),
        }
        jsonl_path.write_text(json.dumps(header) + "\n", encoding="utf-8")
    with jsonl_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry) + "\n")


def reconcile(
    catalog_path: Path | None = None,
    jsonl_path: Path | None = None,
    repos_root: Path | None = None,
    since: str | None = None,
    *,
    dry_run: bool = False,
) -> ReconcileResult:
    """Walk all catalog repos and backfill missing per-repo retrospectives."""
    catalog_path = catalog_path or DEFAULT_CATALOG
    jsonl_path = jsonl_path or DEFAULT_JSONL
    repos_root = repos_root or DEFAULT_REPOS_ROOT

    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    known_keys = {make_dedupe_key(e) for e in load_entries(jsonl_path)}
    result = ReconcileResult()

    for repo in catalog.get("repos", []):
        if repo.get("isArchived"):
            continue
        result.walked += 1
        clone = resolve_local_clone(repo["name"], repos_root)
        if clone is None:
            result.skipped_no_clone += 1
            continue
        result.with_clone += 1

        lessons_dir = clone / "docs" / "compliance-reports" / "lessons-learned"
        if not lessons_dir.is_dir():
            continue

        for md in sorted(lessons_dir.glob("*.md")):
            try:
                parsed = parse_lessons_learned(md)
            except InvalidRetrospectiveError as exc:
                result.parse_failures.append(f"{md}: {exc}")
                continue

            if since and parsed["session_date"] < since:
                continue

            repo_full = f"{repo['org']}/{repo['name']}"
            key = (parsed["session_date"], repo_full)
            if key in known_keys:
                result.duplicates_skipped += 1
                continue

            entry = _build_entry(repo_full, clone, parsed)
            if not dry_run:
                _append_entry(jsonl_path, entry)
                known_keys.add(key)
            result.appended += 1

    return result


def _invoke_renderer() -> None:
    """Run the renderer script as a subprocess.

    Uses a static argument list (no shell=True, no user input) so it is
    safe for any caller. Surfaces renderer failures to stderr and to
    the reconcile log so a stale Markdown view does not silently
    diverge from the JSONL source of truth.
    """
    completed = subprocess.run(  # noqa: S603
        [sys.executable, str(RENDERER_SCRIPT)],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        msg = (
            f"renderer exited with code {completed.returncode}; "
            f"master-log.md may be stale. stderr: {completed.stderr.strip()}"
        )
        print(f"WARNING: {msg}", file=sys.stderr)
        DEFAULT_RECONCILE_LOG.parent.mkdir(parents=True, exist_ok=True)
        with DEFAULT_RECONCILE_LOG.open("a", encoding="utf-8") as fh:
            ts = datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            fh.write(f"[{ts}] {msg}\n")


def main() -> int:
    """CLI entrypoint for the reconciler."""
    parser = argparse.ArgumentParser(description="Reconcile compliance retrospectives.")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--since", help="ISO date YYYY-MM-DD")
    parser.add_argument("--catalog", type=Path, default=None)
    parser.add_argument("--jsonl", type=Path, default=None)
    parser.add_argument("--repos-root", type=Path, default=None)
    args = parser.parse_args()

    result = reconcile(
        catalog_path=args.catalog,
        jsonl_path=args.jsonl,
        repos_root=args.repos_root,
        since=args.since,
        dry_run=args.dry_run,
    )

    log_path = DEFAULT_RECONCILE_LOG
    log_path.parent.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    summary = (
        f"[{ts}] dry_run={args.dry_run} since={args.since or 'all'} "
        f"walked={result.walked} with_clone={result.with_clone} "
        f"skipped_no_clone={result.skipped_no_clone} "
        f"appended={result.appended} duplicates={result.duplicates_skipped} "
        f"parse_failures={len(result.parse_failures)}\n"
    )
    with log_path.open("a", encoding="utf-8") as fh:
        fh.write(summary)
        for failure in result.parse_failures:
            fh.write(f"  ! {failure}\n")

    print(summary, end="")
    for failure in result.parse_failures:
        print(f"  ! {failure}")

    if not args.dry_run and result.appended > 0:
        _invoke_renderer()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
