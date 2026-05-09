"""Apply an org ruleset JSON body to a GitHub org via gh CLI.

Solo-dev safety: refuses to apply any body that would require human PR
approval (required_approving_review_count > 0). The user merges their own
PRs; restoring approval requirements would lock the repo.
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

from scripts.generate_python_tier_repos import python_repos_for_org

CATALOG_DEFAULT = Path("docs/reference/github-repos.json")
EXIT_OK = 0
EXIT_GH_FAILURE = 4
EXIT_SOLO_DEV_VIOLATION = 3


class SoloDevViolationError(RuntimeError):
    """Raised when a ruleset body would lock out the solo-dev workflow."""


# Backward-compatible alias; use SoloDevViolationError in new code.
SoloDevViolation = SoloDevViolationError


def validate_solo_dev_safe(body: dict) -> None:
    """Raise SoloDevViolation if body would require human PR approval.

    Args:
        body: Parsed ruleset body.

    Raises:
        SoloDevViolation: If any pull_request rule has
            required_approving_review_count > 0.
    """
    for rule in body.get("rules", []):
        if rule.get("type") != "pull_request":
            continue
        params = rule.get("parameters", {}) or {}
        count = params.get("required_approving_review_count", 0)
        if count and count > 0:
            raise SoloDevViolation(
                f"Body requires {count} approving reviews "
                f"(required_approving_review_count={count}); solo-dev policy "
                "forbids any value > 0. The user merges their own PRs."
            )


def render_body(body: dict, org: str, catalog: Path) -> dict:
    """Substitute __GENERATED__ tokens with catalog-derived values.

    Args:
        body: Parsed ruleset body (will be deep-copied).
        org: Organization slug for which to generate Python-tier repo list.
        catalog: Path to docs/reference/github-repos.json.

    Returns:
        Deep-copied body with any ["__GENERATED__"] include lists replaced
        by the Python-tier repo names for `org`.
    """
    out = json.loads(json.dumps(body))  # deep copy
    repo_cond = out.get("conditions", {}).get("repository_name", {})
    if repo_cond.get("include") == ["__GENERATED__"]:
        repo_cond["include"] = python_repos_for_org(org, catalog)
    return out


def find_existing_ruleset(org: str, name: str) -> int | None:
    """Return the id of the org-level ruleset named `name`, or None.

    Args:
        org: GitHub org slug.
        name: Ruleset name to search for.

    Returns:
        Integer ruleset id if found, else None.
    """
    out = subprocess.check_output(  # noqa: S603
        ["gh", "api", f"orgs/{org}/rulesets", "--jq", ".[] | {id, name}"],  # noqa: S607
        text=True,
    )
    for line in out.strip().split("\n"):
        if not line:
            continue
        rs = json.loads(line)
        if rs.get("name") == name:
            return rs.get("id")
    return None


def apply(
    org: str,
    body_path: Path,
    enforcement: str | None,
    catalog: Path,
    dry_run: bool,
) -> None:
    """Apply the body to org as a ruleset (POST if new, PUT if exists).

    Args:
        org: Target GitHub org slug.
        body_path: Path to a ruleset JSON body file.
        enforcement: If set, override body['enforcement'] (active|evaluate|disabled).
        catalog: Path to the repo catalog (for __GENERATED__ substitution).
        dry_run: If True, print the action and payload but make no API call.

    Raises:
        SoloDevViolation: If the body would lock out solo-dev workflow.
        subprocess.CalledProcessError: If the gh CLI invocation fails
            (auth error, 4xx response, network failure).
    """
    body = json.loads(body_path.read_text())
    validate_solo_dev_safe(body)
    body = render_body(body, org, catalog)
    if enforcement:
        body["enforcement"] = enforcement
    name = body["name"]
    existing_id = find_existing_ruleset(org, name)
    payload = json.dumps(body)
    if dry_run:
        action = "PUT" if existing_id else "POST"
        print(f"DRY RUN: would {action} ruleset '{name}' to org '{org}'")
        print(payload)
        return
    if existing_id:
        cmd = [
            "gh",
            "api",
            "-X",
            "PUT",
            f"orgs/{org}/rulesets/{existing_id}",
            "--input",
            "-",
        ]
    else:
        cmd = ["gh", "api", "-X", "POST", f"orgs/{org}/rulesets", "--input", "-"]
    subprocess.run(cmd, input=payload, text=True, check=True)  # noqa: S603
    print(
        f"Applied ruleset '{name}' to org '{org}' (enforcement={body['enforcement']})"
    )


def main(argv: list[str]) -> int:
    """CLI entry point.

    Args:
        argv: Command-line argument vector (excluding program name).

    Returns:
        Exit code: EXIT_OK on success, EXIT_GH_FAILURE on gh CLI failure,
        EXIT_SOLO_DEV_VIOLATION on solo-dev violation. Argparse errors exit
        directly with code 2.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("--org", required=True)
    parser.add_argument("--body", required=True, type=Path)
    parser.add_argument("--enforcement", choices=("active", "evaluate", "disabled"))
    parser.add_argument("--catalog", type=Path, default=CATALOG_DEFAULT)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    try:
        apply(args.org, args.body, args.enforcement, args.catalog, args.dry_run)
    except SoloDevViolationError as e:
        print(f"REFUSED: {e}", file=sys.stderr)
        return EXIT_SOLO_DEV_VIOLATION
    except subprocess.CalledProcessError as e:
        print(f"gh command failed: {e}", file=sys.stderr)
        return EXIT_GH_FAILURE
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
