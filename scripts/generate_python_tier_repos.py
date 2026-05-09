"""Emit Python-tier repo include list for the org-ruleset Python-tier body.

Reads the repo catalog and prints the names of every non-exempt repo whose
repositoryType is one of {python-package, python-app, python-script} for a
given organization.
"""

import json
import sys
from pathlib import Path

PYTHON_TYPES = frozenset({"python-package", "python-app", "python-script"})


def python_repos_for_org(org: str, catalog_path: Path) -> list[str]:
    """Return sorted list of Python-repo names in `org`, excluding exempt repos.

    Args:
        org: GitHub organization slug to filter on.
        catalog_path: Path to docs/reference/github-repos.json.

    Returns:
        Sorted list of repo names whose repositoryType is one of
        PYTHON_TYPES and whose branchProtectionExempt is not true.
    """
    data = json.loads(catalog_path.read_text(encoding="utf-8"))
    return sorted(
        repo["name"]
        for repo in data["repos"]
        if repo["org"] == org
        and repo.get("repositoryType") in PYTHON_TYPES
        and not repo.get("branchProtectionExempt")
    )


def main(argv: list[str]) -> int:
    """CLI entry point.

    Args:
        argv: Command-line argument vector (sys.argv).

    Returns:
        Exit code: 0 on success, 2 on argument error.
    """
    if len(argv) != 3:
        print(
            "usage: generate_python_tier_repos.py <org> <catalog-path>",
            file=sys.stderr,
        )
        return 2
    org, catalog = argv[1], Path(argv[2])
    for name in python_repos_for_org(org, catalog):
        print(name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
