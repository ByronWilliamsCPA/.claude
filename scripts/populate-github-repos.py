#!/usr/bin/env python3
"""Refresh docs/reference/github-repos.json from live `gh repo list` output.

Merges the canonical machine-readable repo catalog with live GitHub state for
ByronWilliamsCPA and williaby orgs. Live fields (description, isArchived,
defaultBranch, isPrivate, url) are refreshed; every manual annotation
(repositoryType, branchProtectionExempt, migrationPhase, usesDocker, servesApi,
review.*, api.*, idealEntry overrides) is preserved byte-for-byte.

Default behaviour is conservative:

  * New GitHub repos missing from the catalog are added with
    repositoryType=unclassified so the next audit catches them.
  * Catalog repos absent from GitHub are LEFT IN PLACE. Pass --prune to remove
    them after manually confirming the repo is archived-and-deleted.

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
    result = subprocess.run(  # noqa: S603 - args are static, gh is a trusted CLI
        cmd,
        check=True,
        capture_output=True,
        text=True,
    )
    parsed: list[dict[str, Any]] = json.loads(result.stdout)
    return parsed


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
    for field in LIVE_FIELDS:
        merged[field] = live[field]
    if not merged.get("description"):
        # Fill on first add or when missing; never overwrite an existing value.
        merged["description"] = live["description"]
    return merged


def _sort_key(entry: dict[str, Any]) -> tuple[str, str]:
    """Sort by (org, name.lower()) to match the catalog's case-insensitive order."""
    return (entry["org"], entry["name"].lower())


def refresh_catalog(catalog_path: Path, *, prune: bool) -> bool:
    """Refresh `catalog_path` in place. Returns True if the file changed.

    Args:
        catalog_path: Path to docs/reference/github-repos.json.
        prune: When True, remove catalog entries whose repo no longer exists
            on GitHub. When False (default), leave them intact.

    Returns:
        True if the on-disk file content was modified, False otherwise.
    """
    original_text = catalog_path.read_text(encoding="utf-8")
    catalog: dict[str, Any] = json.loads(original_text)
    existing_by_slug: dict[tuple[str, str], dict[str, Any]] = {
        (r["org"], r["name"]): r for r in catalog.get("repos", [])
    }

    live_slugs: set[tuple[str, str]] = set()
    merged_repos: list[dict[str, Any]] = []

    for org in ORGS:
        for raw in fetch_org_repos(org):
            live = _normalise_live_entry(org, raw)
            slug = (org, live["name"])
            live_slugs.add(slug)
            merged_repos.append(_merge_entry(existing_by_slug.get(slug), live))

    if not prune:
        # Re-emit any catalog entries whose live counterpart is missing.
        for slug, entry in existing_by_slug.items():
            if slug not in live_slugs:
                merged_repos.append(entry)

    merged_repos.sort(key=_sort_key)
    catalog["repos"] = merged_repos

    new_text = json.dumps(catalog, indent=2, ensure_ascii=False) + "\n"
    if new_text == original_text:
        return False
    catalog_path.write_text(new_text, encoding="utf-8")
    return True


def main(argv: list[str] | None = None) -> int:
    """CLI entry point.

    Args:
        argv: Optional argv vector. Defaults to sys.argv[1:].

    Returns:
        Exit code: 0 if catalog is unchanged, 0 if catalog was refreshed, 2 on
        argument error. The workflow inspects the file diff to decide whether
        to open a follow-up PR; a non-zero exit is reserved for failures.
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
    args = parser.parse_args(argv)

    changed = refresh_catalog(args.catalog, prune=args.prune)
    if changed:
        print(f"Updated {args.catalog}")
    else:
        print(f"{args.catalog} is up to date")
    return 0


if __name__ == "__main__":
    sys.exit(main())
