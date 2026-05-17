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

import yaml

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
    """Extract candidate proposals from Proposed Manifest Additions blocks.

    The source ``id:`` field is preserved as ``proposed_manifest_id`` so a
    reviewer can trace the entry back to its origin. The returned
    ``candidate_id`` is synthesised (``reconciled-<hex>``) rather than
    copied from the source, because per-repo files do not carry stable
    candidate IDs across rollups.

    YAML block scalars (``description: >-``, ``|``, multi-line) are
    parsed with ``yaml.safe_load`` so the captured description is the
    real text, not the literal scalar marker.
    """
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
        try:
            parsed_yaml = yaml.safe_load(block)
        except yaml.YAMLError:
            continue
        if isinstance(parsed_yaml, list):
            items = [i for i in parsed_yaml if isinstance(i, dict)]
        elif isinstance(parsed_yaml, dict):
            items = [parsed_yaml]
        else:
            continue
        for item in items:
            item_id = item.get("id")
            if not item_id:
                continue
            description = item.get("description", "")
            candidates.append(
                {
                    "candidate_id": f"reconciled-{uuid.uuid4().hex[:8]}",
                    "pattern": str(description).strip(),
                    "proposed_manifest_id": str(item_id).strip(),
                    "proposed_yaml_path": "",
                }
            )
    return candidates


def parse_lessons_learned(path: Path, clone: Path) -> dict[str, Any]:
    """Parse a per-repo lessons-learned Markdown file into a partial entry.

    Args:
        path: Absolute path to the lessons-learned Markdown file.
        clone: Absolute path to the repo root containing the file. Used
            to compute a repo-relative ``links.lessons_learned`` so the
            committed master log does not leak local filesystem paths.

    Returns:
        Partial entry dict with parsed totals, findings, candidates,
        and a repo-relative ``links.lessons_learned`` pointer.

    Raises:
        InvalidRetrospectiveError: If the filename does not match the
            expected ``YYYY-MM-DD[-tag].md`` pattern, or if ``path`` is
            not under ``clone``.
    """
    fname_match = DATE_FILENAME_RE.match(path.name)
    if not fname_match:
        raise InvalidRetrospectiveError(
            f"filename {path.name} does not match YYYY-MM-DD[-tag].md"
        )
    session_date = fname_match.group(1)
    text = path.read_text(encoding="utf-8")

    try:
        rel_link = str(path.relative_to(clone))
    except ValueError as exc:
        raise InvalidRetrospectiveError(
            f"{path} is not inside clone root {clone}"
        ) from exc

    return {
        "session_date": session_date,
        "totals": _parse_session_summary_table(text),
        "findings_by_check": _parse_findings_by_check(text),
        "unclassified_candidates": _parse_unclassified_candidates(text),
        "fleet_action_proposals": [],
        "scope_expansion_flags": [],
        "links": {"lessons_learned": rel_link},
    }


def _make_session_id(date: str) -> str:
    """Build a synthetic session_id for a reconciled entry."""
    nonce = uuid.uuid4().hex[:4]
    return f"{date}T00:00:00Z-{nonce}"


def _build_entry(
    repo_full: str,
    parsed: dict[str, Any],
) -> dict[str, Any]:
    """Assemble a full master-log entry from a parsed per-repo file.

    The ``repo_path`` field is left empty for reconciled entries because
    the operator's local clone path is machine-specific and must not be
    committed. The ``repo`` slug (``org/name``) is the portable
    identifier; ``links.lessons_learned`` provides the repo-relative
    pointer set by :func:`parse_lessons_learned`.
    """
    return {
        "schema_version": SCHEMA_VERSION,
        "session_date": parsed["session_date"],
        "session_id": _make_session_id(parsed["session_date"]),
        "repo": repo_full,
        "repo_path": "",
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
    """Walk all catalog repos and backfill missing per-repo retrospectives.

    Args:
        catalog_path: Optional path to the repo catalog JSON. Defaults
            to ``docs/reference/github-repos.json`` discovered via the
            script's repo root.
        jsonl_path: Optional path to the master-log JSONL to append to.
            Defaults to the production master log.
        repos_root: Optional directory containing local clones of every
            catalog repo. Defaults to ``$HOME/dev``.
        since: Optional inclusive lower bound on ``session_date`` in
            ISO ``YYYY-MM-DD`` form. Entries dated earlier are skipped.
        dry_run: When True, parses and dedupes as usual but performs no
            writes. The ``appended`` counter still increments to reflect
            what a real run would have written.

    Returns:
        A :class:`ReconcileResult` carrying counters and any
        ``parse_failures`` collected during the walk.

    Raises:
        FileNotFoundError: If the catalog file does not exist; the
            caller's :func:`main` translates this into a non-zero exit.
        ValueError: If the catalog file is unreadable or contains
            invalid JSON; surfaced with the path and JSON column.
    """
    catalog_path = catalog_path or DEFAULT_CATALOG
    jsonl_path = jsonl_path or DEFAULT_JSONL
    repos_root = repos_root or DEFAULT_REPOS_ROOT

    try:
        catalog_text = catalog_path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise FileNotFoundError(
            f"Catalog not found at {catalog_path}. "
            f"Regenerate with: gh repo list <org> --json ... > {catalog_path}"
        ) from exc
    except OSError as exc:
        msg = f"Catalog unreadable at {catalog_path}: {exc}"
        raise ValueError(msg) from exc

    try:
        catalog = json.loads(catalog_text)
    except json.JSONDecodeError as exc:
        msg = f"Catalog JSON malformed at {catalog_path}: {exc}"
        raise ValueError(msg) from exc

    known_keys = {make_dedupe_key(e) for e in load_entries(jsonl_path)}
    result = ReconcileResult()

    for repo in catalog.get("repos", []):
        if repo.get("isArchived"):
            continue
        repo_name = repo.get("name")
        repo_org = repo.get("org")
        if not repo_name or not repo_org:
            result.parse_failures.append(f"catalog entry missing name/org: {repo!r}")
            continue
        result.walked += 1
        clone = resolve_local_clone(repo_name, repos_root)
        if clone is None:
            result.skipped_no_clone += 1
            continue
        result.with_clone += 1

        lessons_dir = clone / "docs" / "compliance-reports" / "lessons-learned"
        if not lessons_dir.is_dir():
            continue

        for md in sorted(lessons_dir.glob("*.md")):
            try:
                parsed = parse_lessons_learned(md, clone)
            except InvalidRetrospectiveError as exc:
                result.parse_failures.append(f"{md}: {exc}")
                continue
            except (OSError, UnicodeDecodeError) as exc:
                result.parse_failures.append(
                    f"{md}: read failed: {type(exc).__name__}: {exc}"
                )
                continue

            if since and parsed["session_date"] < since:
                continue

            repo_full = f"{repo_org}/{repo_name}"
            key = (parsed["session_date"], repo_full)
            if key in known_keys:
                result.duplicates_skipped += 1
                continue

            entry = _build_entry(repo_full, parsed)
            if not dry_run:
                _append_entry(jsonl_path, entry)
            known_keys.add(key)
            result.appended += 1

    return result


def _invoke_renderer(
    jsonl_path: Path | None = None,
    md_path: Path | None = None,
) -> int:
    """Run the renderer script as a subprocess.

    Args:
        jsonl_path: Optional override of the source JSONL path. When
            provided, propagated to the renderer as ``--jsonl`` so the
            rendered Markdown matches the JSONL the caller actually
            updated.
        md_path: Optional override of the output Markdown path. When
            provided, propagated to the renderer as ``--md``.

    Returns:
        The renderer subprocess return code. 0 on success; non-zero is
        surfaced to stderr and to the reconcile log so a stale Markdown
        view does not silently diverge from the JSONL source of truth.
        Callers should propagate non-zero return codes as their own
        exit code rather than reporting success.
    """
    args = [sys.executable, str(RENDERER_SCRIPT)]
    if jsonl_path is not None:
        args.extend(["--jsonl", str(jsonl_path)])
    if md_path is not None:
        args.extend(["--md", str(md_path)])
    completed = subprocess.run(  # noqa: S603 -- args list is static-prefixed and trusted
        args,
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
    return completed.returncode


def _iso_date(value: str) -> str:
    """Argparse type for ``--since``: validate ISO ``YYYY-MM-DD`` form."""
    try:
        datetime.strptime(value, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except ValueError as exc:
        msg = f"--since must be ISO YYYY-MM-DD, got {value!r}"
        raise argparse.ArgumentTypeError(msg) from exc
    return value


def main() -> int:
    """CLI entrypoint for the reconciler.

    Returns:
        Exit code:
        - ``0`` on full success.
        - ``2`` when reconcile succeeded but the renderer failed; the
          JSONL is correct but ``master-log.md`` may be stale.
        - ``3`` when the catalog is missing or unreadable.
    """
    parser = argparse.ArgumentParser(description="Reconcile compliance retrospectives.")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--since", type=_iso_date, help="ISO date YYYY-MM-DD")
    parser.add_argument("--catalog", type=Path, default=None)
    parser.add_argument("--jsonl", type=Path, default=None)
    parser.add_argument("--repos-root", type=Path, default=None)
    args = parser.parse_args()

    try:
        result = reconcile(
            catalog_path=args.catalog,
            jsonl_path=args.jsonl,
            repos_root=args.repos_root,
            since=args.since,
            dry_run=args.dry_run,
        )
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 3
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 3

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
        render_rc = _invoke_renderer(jsonl_path=args.jsonl)
        if render_rc != 0:
            return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
