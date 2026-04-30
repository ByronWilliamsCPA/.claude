#!/usr/bin/env python3
"""Refresh releaseHealth fields in the catalog by querying GitHub releases API."""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import TypedDict, cast

import requests as req_lib

CATALOG = Path(__file__).parent.parent / "docs" / "reference" / "github-repos.json"
GITHUB_API = "https://api.github.com"


class ReleaseHealth(TypedDict, total=False):
    """The releaseHealth sub-object within a repo entry's review block."""

    hasRelease: bool
    daysSinceRelease: int | None


class ReviewFields(TypedDict, total=False):
    """Subset of review fields used by this script."""

    releaseHealth: ReleaseHealth


class RepoEntry(TypedDict, total=False):
    """A single repository entry from the catalog repos array."""

    org: str
    name: str
    review: ReviewFields


class Catalog(TypedDict):
    """Subset of docs/reference/github-repos.json used by this script."""

    repos: list[RepoEntry]


def get_token() -> str:
    """Read GitHub token from environment."""
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        sys.exit("GITHUB_TOKEN environment variable not set")
    return token


def fetch_release_health(
    org: str, repo: str, token: str, dry_run: bool
) -> tuple[bool, int | None]:
    """Query GitHub for the latest release and compute days since release.

    Returns (has_release, days_since_release).
    """
    if dry_run:
        print(f"[DRY RUN] Would query releases for {org}/{repo}")
        return True, 0

    url = f"{GITHUB_API}/repos/{org}/{repo}/releases/latest"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    try:
        resp = req_lib.get(url, headers=headers, timeout=30)
        if resp.status_code == 404:
            return False, None
        resp.raise_for_status()
        data = resp.json()
        published = datetime.fromisoformat(data["published_at"].replace("Z", "+00:00"))
        days = (datetime.now(timezone.utc) - published).days
        return True, days
    except req_lib.HTTPError as exc:
        print(
            f"[WARN] {org}/{repo}: {exc.response.status_code} {exc.response.text[:120]}",
            file=sys.stderr,
        )
        return False, None
    except req_lib.RequestException as exc:
        print(f"[WARN] {org}/{repo}: {exc}", file=sys.stderr)
        return False, None


def main(dry_run: bool = False) -> int:
    """Refresh releaseHealth for all repos in the catalog."""
    catalog = cast("Catalog", json.loads(CATALOG.read_text()))
    token = get_token()

    updated = 0
    no_release = 0
    skipped = 0

    for entry in catalog["repos"]:
        org = entry.get("org", "")
        name = entry.get("name", "")
        if not org or not name:
            skipped += 1
            continue

        has_release, days = fetch_release_health(org, name, token, dry_run)

        review = cast("dict[str, object]", entry.get("review", {}))
        rh = cast("dict[str, object]", review.get("releaseHealth", {}))

        if has_release:
            rh["hasRelease"] = True
            rh["daysSinceRelease"] = days
            print(f"[OK] {org}/{name}: {days} days since latest release")
            updated += 1
        else:
            rh["hasRelease"] = False
            rh["daysSinceRelease"] = None
            print(f"[NO RELEASE] {org}/{name}")
            no_release += 1

        review["releaseHealth"] = rh
        entry["review"] = cast("ReviewFields", review)

    if not dry_run:
        CATALOG.write_text(json.dumps(catalog, indent=2) + "\n")

    print(
        f"\nComplete: {updated} with releases, {no_release} without releases,"
        f" {skipped} skipped"
    )
    return 0


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    dry_run: bool = cast("bool", args.dry_run)
    sys.exit(main(dry_run=dry_run))
