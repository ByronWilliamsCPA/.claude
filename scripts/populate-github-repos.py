#!/usr/bin/env python3
"""Refresh docs/reference/github-repos.json from live `gh repo list` output.

Merges the canonical machine-readable repo catalog with live GitHub state for
ByronWilliamsCPA and williaby orgs. Live fields (`name`, `url`, `defaultBranch`,
`isPrivate`, `isArchived`) are refreshed on every run; every manual annotation
(repositoryType, branchProtectionExempt, migrationPhase, usesDocker, servesApi,
review.*, api.*, idealEntry overrides) is preserved byte-for-byte. `description`
is treated as a fill-on-first-add annotation: set when a repo is added, never
overwritten on subsequent refreshes.

Default behaviour is conservative:

  * New GitHub repos missing from the catalog are added with
    repositoryType=unclassified so the next audit catches them.
  * Catalog repos absent from GitHub are LEFT IN PLACE. Pass --prune to remove
    them after manually confirming the repo is archived-and-deleted.
  * --prune refuses to run when any org returns an empty live response unless
    --allow-empty is also passed, so a transient token-scope loss cannot
    silently erase a whole org's entries.

Designed to run from CI (.github/workflows/catalog-refresh.yml) and locally.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

ORGS: tuple[str, ...] = ("ByronWilliamsCPA", "williaby")
CATALOG_PATH = Path("docs/reference/github-repos.json")

# Fields refreshed from `gh repo list` on every run. Everything else on a repo
# entry is preserved as a manual annotation.
#
# NOTE: `description` is intentionally NOT in LIVE_FIELDS. Some catalog entries
# carry hand-curated descriptions that are richer than (or different from) what
# GitHub stores. Description is treated as a fill-on-first-add annotation: it
# is set when a new repo is added (so the catalog has something to display),
# but never overwritten on subsequent refreshes.
LIVE_FIELDS: frozenset[str] = frozenset(
    {"name", "url", "defaultBranch", "isPrivate", "isArchived"}
)

# Skeleton applied to repos that exist on GitHub but not in the catalog.
SKELETON_ANNOTATIONS: dict[str, Any] = {
    "repositoryType": "unclassified",
}


def fetch_org_repos(org: str) -> list[dict[str, Any]]:
    """Return live repo metadata for `org` via the `gh` CLI.

    Shelling out to `gh` (rather than calling the GitHub API directly) keeps
    auth tokens out of this script: developers and the workflow runner already
    have `gh` configured. Tests override this function via monkeypatch.

    Args:
        org: GitHub organisation slug.

    Returns:
        Parsed JSON list as produced by `gh repo list <org> --json ...`.

    Raises:
        SystemExit: When `gh` is missing, returns non-zero, times out, returns
            non-JSON output, or the parsed JSON is not a list. Each failure
            path emits an actionable message to stderr before exiting.
    """
    gh_bin = os.environ.get("GH_BINARY", "gh")
    cmd: list[str] = [
        gh_bin,
        "repo",
        "list",
        org,
        "--limit",
        "200",
        "--json",
        "name,url,defaultBranchRef,description,isPrivate,isArchived",
    ]
    try:
        result = subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True,
            timeout=60,
        )
    except FileNotFoundError:
        sys.exit(
            f"error: `{gh_bin}` not found on PATH. Install GitHub CLI "
            f"(https://cli.github.com/) or set GH_BINARY to the absolute path."
        )
    except subprocess.TimeoutExpired:
        sys.exit(
            f"error: `gh repo list {org}` timed out after 60 seconds. "
            f"Check network connectivity and `gh auth status`."
        )
    except subprocess.CalledProcessError as exc:
        stderr = (exc.stderr or "").strip() or "(no stderr)"
        sys.exit(
            f"error: `gh repo list {org}` failed with exit code {exc.returncode}. "
            f"stderr: {stderr}. Verify `gh auth status` and that the token has "
            f"read:org scope for {org}."
        )

    try:
        raw_payload: Any = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        preview = result.stdout[:200] if result.stdout else "(empty)"
        sys.exit(
            f"error: `gh repo list {org}` returned non-JSON output ({exc}). "
            f"First 200 chars: {preview!r}"
        )
    if not isinstance(raw_payload, list):
        sys.exit(
            f"error: `gh repo list {org}` returned JSON of type "
            f"{type(raw_payload).__name__}, expected list."
        )
    return raw_payload


def _normalise_live_entry(org: str, raw: dict[str, Any]) -> dict[str, Any]:
    """Flatten `defaultBranchRef.name` to `defaultBranch`, attach `org`."""
    default_branch_ref = raw.get("defaultBranchRef") or {}
    return {
        "org": org,
        "name": raw["name"],
        "url": raw.get("url") or f"https://github.com/{org}/{raw['name']}",
        "defaultBranch": default_branch_ref.get("name", "main"),
        "description": raw.get("description") or "",
        "isPrivate": bool(raw.get("isPrivate", False)),
        "isArchived": bool(raw.get("isArchived", False)),
    }


def _merge_entry(
    existing: dict[str, Any] | None, live: dict[str, Any]
) -> dict[str, Any]:
    """Return an entry that refreshes live fields while preserving annotations.

    Args:
        existing: The catalog entry as currently stored, or None for a new repo.
        live: The normalised live entry from `_normalise_live_entry`.

    Returns:
        A new dict combining live values for LIVE_FIELDS with every other key
        from `existing`. For new repos, SKELETON_ANNOTATIONS is layered in.
    """
    merged: dict[str, Any] = dict(existing) if existing else dict(SKELETON_ANNOTATIONS)
    merged["org"] = live["org"]
    # sorted() makes new-entry key order deterministic across Python processes.
    # frozenset iteration order depends on PYTHONHASHSEED, so two CI runs on
    # different workers would otherwise produce different JSON layouts for the
    # same new entry and break the no-change detection below.
    for field in sorted(LIVE_FIELDS):
        merged[field] = live[field]
    if "description" not in merged:
        # Fill on first add or when missing; never overwrite an existing value.
        # Key-presence check (not falsy-check) so a deliberately empty
        # "description": "" annotation is preserved rather than silently
        # refilled from the GitHub description on every refresh.
        merged["description"] = live["description"]
    return merged


def _sort_key(entry: dict[str, Any]) -> tuple[str, str]:
    """Sort by (org, name.lower()) to match the catalog's case-insensitive order."""
    return (entry["org"], entry["name"].lower())


def refresh_catalog(
    catalog_path: Path, *, prune: bool, allow_empty: bool = False
) -> bool:
    """Refresh `catalog_path` in place. Returns True if the file changed.

    Args:
        catalog_path: Path to docs/reference/github-repos.json.
        prune: When True, remove catalog entries whose repo no longer exists
            on GitHub. When False (default), leave them intact.
        allow_empty: When True, permit `--prune` even if an org returns an
            empty live response. Defaults to False so a transient token-scope
            loss cannot silently erase a whole org's catalog entries.

    Returns:
        True if the on-disk file content was modified, False otherwise.

    Raises:
        SystemExit: When the catalog file is missing, not readable, not valid
            JSON, has no `repos` list, or when `prune` is set and any org
            returns an empty live response without `allow_empty`.
    """
    try:
        original_text = catalog_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        sys.exit(
            f"error: catalog file not found at {catalog_path}. "
            f"Run from the repo root or pass --catalog with an existing path."
        )
    except OSError as exc:
        sys.exit(f"error: cannot read catalog at {catalog_path}: {exc}.")

    try:
        raw_catalog: Any = json.loads(original_text)
    except json.JSONDecodeError as exc:
        sys.exit(
            f"error: catalog at {catalog_path} is not valid JSON "
            f"(line {exc.lineno}, col {exc.colno}): {exc.msg}. "
            f"Check for merge-conflict markers or a partial prior-run write."
        )
    if not isinstance(raw_catalog, dict) or not isinstance(
        raw_catalog.get("repos"), list
    ):
        sys.exit(
            f"error: catalog at {catalog_path} must be a JSON object with a "
            f"top-level `repos` list."
        )
    catalog: dict[str, Any] = raw_catalog

    existing_by_slug: dict[tuple[str, str], dict[str, Any]] = {
        (r["org"], r["name"]): r for r in catalog["repos"]
    }

    live_slugs: set[tuple[str, str]] = set()
    merged_repos: list[dict[str, Any]] = []
    empty_orgs: list[str] = []

    for org in ORGS:
        raw_entries = fetch_org_repos(org)
        if not raw_entries:
            empty_orgs.append(org)
        for raw in raw_entries:
            live = _normalise_live_entry(org, raw)
            slug = (org, live["name"])
            live_slugs.add(slug)
            merged_repos.append(_merge_entry(existing_by_slug.get(slug), live))

    if prune and empty_orgs and not allow_empty:
        sys.exit(
            f"error: --prune refused because {', '.join(empty_orgs)} returned "
            f"zero repos. A transient token-scope loss or org rename would "
            f"silently erase every catalog entry for those orgs. Re-run with "
            f"--allow-empty if the empty response is intentional."
        )

    if not prune:
        # Re-emit any catalog entries whose live counterpart is missing.
        # Conservative default: a transient gh outage or a scope-limited token
        # must not silently delete catalog entries. Use --prune to opt in.
        for slug, entry in existing_by_slug.items():
            if slug not in live_slugs:
                merged_repos.append(entry)

    merged_repos.sort(key=_sort_key)
    catalog["repos"] = merged_repos

    new_text = json.dumps(catalog, indent=2, ensure_ascii=False) + "\n"
    if new_text == original_text:
        return False
    _atomic_write_text(catalog_path, new_text)
    return True


def _atomic_write_text(path: Path, content: str) -> None:
    """Write `content` to `path` atomically via temp file + os.replace.

    A direct write_text on a long-running CI job is vulnerable to truncation
    if the process is killed mid-write (timeout, OOM, disk-full). os.replace
    is atomic on POSIX, so the file is either the old content or the full new
    content, never partial.

    Args:
        path: Destination file path.
        content: Full UTF-8 text content to write.

    Raises:
        SystemExit: When the underlying filesystem write fails.
    """
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    try:
        tmp_path.write_text(content, encoding="utf-8")
        os.replace(tmp_path, path)
    except OSError as exc:
        # Clean up the temp file if it survives the failure.
        try:
            tmp_path.unlink(missing_ok=True)
        except OSError:
            pass
        sys.exit(f"error: failed to write {path}: {exc}.")


def main(argv: list[str] | None = None) -> int:
    """CLI entry point.

    Args:
        argv: Optional argv vector. Defaults to sys.argv[1:].

    Returns:
        Exit code 0 in both success paths (catalog unchanged or refreshed).
        The workflow inspects the file diff to decide whether to open a
        follow-up PR; non-zero exits are reserved for fetch/IO failures
        raised by `refresh_catalog`. Argparse exits 2 on argument errors
        before this function returns.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--catalog",
        type=Path,
        default=CATALOG_PATH,
        help="Path to github-repos.json (default: docs/reference/github-repos.json)",
    )
    parser.add_argument(
        "--prune",
        action="store_true",
        help="Remove catalog entries that no longer exist on GitHub",
    )
    parser.add_argument(
        "--allow-empty",
        action="store_true",
        help=(
            "Permit --prune even if an org returns zero repos. Without this, "
            "an empty live response halts pruning to avoid silently erasing "
            "a whole org on a transient token-scope loss."
        ),
    )
    args = parser.parse_args(argv)

    changed = refresh_catalog(
        args.catalog, prune=args.prune, allow_empty=args.allow_empty
    )
    if changed:
        print(f"Updated {args.catalog}")
    else:
        print(f"{args.catalog} is up to date")
    return 0


if __name__ == "__main__":
    sys.exit(main())
