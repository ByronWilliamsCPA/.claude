"""Sync org workflow pin registry against latest GitHub tags.

Called by .github/workflows/sync-org-pins.yml. Reads
docs/org-workflow-pins.yaml, queries the GitHub API for the latest
semver tag on each source repo, and rewrites the file if any entry is
stale. Exits 0 whether or not changes were made; the workflow detects
changes via git diff.

Usage:
    PYTHONPATH=. python3 scripts/sync_org_pins.py [--registry PATH]

Environment:
    GH_TOKEN  GitHub token for API calls (set by workflow).
"""

import argparse
import json
import subprocess
import sys
from copy import deepcopy
from datetime import date
from pathlib import Path
from typing import Any

import yaml

_DEFAULT_REGISTRY = Path("docs/org-workflow-pins.yaml")


def load_registry(path: Path) -> dict[str, Any]:
    """Load and parse the pin registry YAML file.

    Args:
        path: Path to the registry YAML file.

    Returns:
        Parsed registry data as a dict with a 'sources' mapping.

    Raises:
        FileNotFoundError: When the registry file does not exist.
        yaml.YAMLError: When the file is missing a 'sources' mapping.
    """
    if not path.exists():
        raise FileNotFoundError(path)
    with path.open() as fh:
        data = yaml.safe_load(fh)
    if not isinstance(data.get("sources"), dict):
        raise yaml.YAMLError(f"Expected 'sources' mapping in {path}")
    return data


def _latest_tag(repo: str) -> tuple[str, str]:
    """Return (tag_name, commit_sha) for the most recent tag on repo.

    Args:
        repo: GitHub repo slug in owner/name format.

    Returns:
        Tuple of (tag_name, commit_sha) for the latest tag.

    Raises:
        RuntimeError: When no tags exist on the repo.
        subprocess.CalledProcessError: When the gh API call fails.
    """
    result = subprocess.run(
        [
            "gh",
            "api",
            f"repos/{repo}/tags",
            "--jq",
            ".[0] | {name, sha: .commit.sha}",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    tag_data = json.loads(result.stdout.strip())
    if not tag_data or tag_data.get("name") is None:
        raise RuntimeError(f"No tags found on {repo}")
    return tag_data["name"], tag_data["sha"]


def needs_update(entry: dict, *, tag: str, sha: str) -> bool:
    """Return True when either tag or sha differs from the registry entry.

    Args:
        entry: Registry entry dict with current_tag and current_sha fields.
        tag: Latest tag name from GitHub.
        sha: Latest commit SHA from GitHub.

    Returns:
        True if the entry is stale and needs updating, False otherwise.
    """
    return entry["current_tag"] != tag or entry["current_sha"] != sha


def build_updated_registry(
    registry: dict,
    *,
    repo: str,
    new_tag: str,
    new_sha: str,
    sync_date: date,
) -> dict[str, Any]:
    """Return a deep-copy of registry with one source entry updated.

    Args:
        registry: Current registry dict.
        repo: GitHub repo slug identifying which source entry to update.
        new_tag: New tag name to record.
        new_sha: New commit SHA to record.
        sync_date: Date to record as last_synced.

    Returns:
        Deep copy of registry with the named source entry updated.
    """
    updated = deepcopy(registry)
    updated["sources"][repo]["current_tag"] = new_tag
    updated["sources"][repo]["current_sha"] = new_sha
    updated["sources"][repo]["last_synced"] = str(sync_date)
    return updated


def _write_registry(path: Path, registry: dict) -> None:
    """Write the registry to disk with a standard header comment.

    Args:
        path: Destination path for the registry YAML file.
        registry: Registry data to serialize.
    """
    header = (
        "# Canonical SHA pins for org workflow source repos.\n"
        "# Updated by .github/workflows/sync-org-pins.yml.\n"
        "# Consumers should pin to current_sha.\n"
        "# Compliance: CI-054 verifies registry matches latest tag on GitHub;\n"
        "# CI-055 verifies consumer repos match registry current_sha;\n"
        "# CI-056 verifies Renovate config targets org workflow sources.\n"
        "\n"
    )
    body = yaml.dump(registry, default_flow_style=False, sort_keys=False)
    path.write_text(header + body)


def main(argv: list[str] | None = None) -> int:
    """Sync the registry and return exit code 0 on success.

    Args:
        argv: Argument list to parse; defaults to sys.argv when None.

    Returns:
        Exit code 0 on success.
    """
    parser = argparse.ArgumentParser(
        description="Sync org workflow pin registry against latest GitHub tags."
    )
    parser.add_argument("--registry", type=Path, default=_DEFAULT_REGISTRY)
    args = parser.parse_args(argv)

    registry = load_registry(args.registry)
    today = date.today()
    changed = False

    for repo, entry in registry["sources"].items():
        try:
            tag, sha = _latest_tag(repo)
        except (RuntimeError, subprocess.CalledProcessError) as exc:
            print(
                f"::warning::Could not fetch tags for {repo}: {exc}",
                file=sys.stderr,
            )
            continue

        if needs_update(entry, tag=tag, sha=sha):
            print(f"Updating {repo}: {entry['current_tag']} -> {tag}")
            registry = build_updated_registry(
                registry,
                repo=repo,
                new_tag=tag,
                new_sha=sha,
                sync_date=today,
            )
            changed = True
        else:
            print(f"No change for {repo}: already at {tag}")

    if changed:
        _write_registry(args.registry, registry)
        print(f"Registry updated: {args.registry}")
    else:
        print("Registry is current; no changes written.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
