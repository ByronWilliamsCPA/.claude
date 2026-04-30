#!/usr/bin/env python3
"""Enable GitHub native secret scanning and push protection across all catalog repos."""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import TypedDict, cast

CATALOG = Path(__file__).parent.parent / "docs" / "reference" / "github-repos.json"
GITHUB_API = "https://api.github.com"


class RepoEntry(TypedDict, total=False):
    """A single repository entry from the catalog repos array."""

    org: str
    name: str


class Catalog(TypedDict):
    """Top-level structure of docs/reference/github-repos.json."""

    repos: list[RepoEntry]


def get_token() -> str:
    """Read GitHub token from environment."""
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        sys.exit("GITHUB_TOKEN environment variable not set")
    return token


def enable_secret_scanning(org: str, repo: str, token: str, dry_run: bool) -> bool:
    """Enable secret scanning and push protection for a single repo.

    Returns True on success or already-enabled, False on error.
    """
    if dry_run:
        print(f"[DRY RUN] Would enable secret scanning on {org}/{repo}")
        return True

    url = f"{GITHUB_API}/repos/{org}/{repo}"
    payload = json.dumps(
        {
            "security_and_analysis": {
                "secret_scanning": {"status": "enabled"},
                "secret_scanning_push_protection": {"status": "enabled"},
            }
        }
    ).encode()
    req = urllib.request.Request(  # noqa: S310 - URL scheme is always https (GITHUB_API constant)
        url,
        data=payload,
        method="PATCH",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30):  # noqa: S310 - URL scheme is always https (GITHUB_API constant)
            print(f"[OK] Enabled secret scanning on {org}/{repo}")
            return True
    except urllib.error.HTTPError as exc:
        body = exc.read(120).decode(errors="replace")
        print(f"[FAIL] {org}/{repo}: {exc.code} {body}", file=sys.stderr)
        return False


def main(dry_run: bool = False) -> int:
    """Enable secret scanning on all repos in the catalog."""
    catalog = cast("Catalog", json.loads(CATALOG.read_text()))
    token = get_token()
    results: list[bool] = []
    for entry in catalog["repos"]:
        org = entry.get("org", "")
        name = entry.get("name", "")
        if not org or not name:
            continue
        ok = enable_secret_scanning(org, name, token, dry_run)
        results.append(ok)
    failed = results.count(False)
    print(f"\nComplete: {results.count(True)} OK, {failed} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    dry_run: bool = cast("bool", args.dry_run)
    sys.exit(main(dry_run=dry_run))
