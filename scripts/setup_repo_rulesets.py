"""Apply a repo-level ruleset JSON body to a single GitHub repo via gh CLI.

Mirrors setup_org_rulesets.py but POSTs to /repos/:owner/:repo/rulesets.
Same solo-dev guard: refuses any body with required_approving_review_count > 0.
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

from scripts.setup_org_rulesets import (
    _GH_TIMEOUT_SECONDS,
    EXIT_GH_FAILURE,
    EXIT_OK,
    EXIT_SOLO_DEV_VIOLATION,
    SoloDevViolationError,
    validate_solo_dev_safe,
)


def find_existing_repo_ruleset(repo_slug: str, name: str) -> int | None:
    """Return the id of the repo-level ruleset named `name`, or None.

    Args:
        repo_slug: GitHub owner/repo slug.
        name: Ruleset name to search for.

    Returns:
        Integer ruleset id if found, else None.
    """
    out = subprocess.check_output(  # noqa: S603
        ["gh", "api", f"repos/{repo_slug}/rulesets", "--jq", ".[] | {id, name}"],  # noqa: S607
        text=True,
        timeout=_GH_TIMEOUT_SECONDS,
    )
    for line in out.strip().split("\n"):
        if not line:
            continue
        rs = json.loads(line)
        if rs.get("name") == name:
            return rs.get("id")
    return None


def apply(
    repo_slug: str,
    body_path: Path,
    enforcement: str | None,
    dry_run: bool,
) -> None:
    """Apply the body to repo as a ruleset (POST if new, PUT if exists).

    Args:
        repo_slug: Target GitHub owner/repo slug.
        body_path: Path to a ruleset JSON body file.
        enforcement: If set, override body['enforcement'] (active|evaluate|disabled).
        dry_run: If True, print the action and payload but make no mutating API call.

    Raises:
        SoloDevViolationError: If the body would lock out solo-dev workflow.
        subprocess.CalledProcessError: If the gh CLI invocation fails.
    """
    body = json.loads(body_path.read_text(encoding="utf-8"))
    validate_solo_dev_safe(body)
    if enforcement:
        body["enforcement"] = enforcement
    name = body["name"]
    existing_id = find_existing_repo_ruleset(repo_slug, name)
    payload = json.dumps(body)
    if dry_run:
        action = "PUT" if existing_id else "POST"
        print(f"DRY RUN: would {action} ruleset '{name}' to repo '{repo_slug}'")
        print(payload)
        return
    if existing_id:
        cmd = [
            "gh",
            "api",
            "-X",
            "PUT",
            f"repos/{repo_slug}/rulesets/{existing_id}",
            "--input",
            "-",
        ]
    else:
        cmd = ["gh", "api", "-X", "POST", f"repos/{repo_slug}/rulesets", "--input", "-"]
    subprocess.run(  # noqa: S603
        cmd,
        input=payload,
        text=True,
        check=True,
        timeout=_GH_TIMEOUT_SECONDS,
    )
    enforcement_value = body.get("enforcement", "<unset>")
    print(
        f"Applied ruleset '{name}' to repo '{repo_slug}' "
        f"(enforcement={enforcement_value})"
    )


def main(argv: list[str]) -> int:
    """CLI entry point.

    Args:
        argv: Command-line argument vector (excluding program name).

    Returns:
        Exit code: EXIT_OK on success, EXIT_GH_FAILURE on gh CLI failure,
        EXIT_SOLO_DEV_VIOLATION on solo-dev violation.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True, help="owner/repo slug")
    parser.add_argument("--body", required=True, type=Path)
    parser.add_argument("--enforcement", choices=("active", "evaluate", "disabled"))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    try:
        apply(args.repo, args.body, args.enforcement, args.dry_run)
    except SoloDevViolationError as e:
        print(f"REFUSED: {e}", file=sys.stderr)
        return EXIT_SOLO_DEV_VIOLATION
    except subprocess.CalledProcessError as e:
        print(f"gh command failed: {e}", file=sys.stderr)
        return EXIT_GH_FAILURE
    except subprocess.TimeoutExpired as e:
        print(
            f"gh command timed out after {_GH_TIMEOUT_SECONDS}s: {e}",
            file=sys.stderr,
        )
        return EXIT_GH_FAILURE
    except FileNotFoundError as e:
        print(f"gh CLI not on PATH: {e}", file=sys.stderr)
        return EXIT_GH_FAILURE
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
