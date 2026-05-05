#!/usr/bin/env python3
"""Periodic compliance sweep across all managed repos.

Checks the most drift-prone standards from docs/standards-manifest.yaml:
  CI-020: renovate.json present at repo root
  CI-021: dependabot.yml absent when renovate.json is present
  BP-4:   Required commit signatures enabled
  BP-5:   enforce_admins enabled

Run this weekly (or after any org-wide change) to catch repos that fall out of
alignment before they accumulate. Prints a compact table and exits non-zero if
any repo fails a non-waived check.

Usage:
  python3 scripts/check-repo-compliance.py
  python3 scripts/check-repo-compliance.py --org ByronWilliamsCPA
  python3 scripts/check-repo-compliance.py --repo ByronWilliamsCPA/.claude
"""

import argparse
import json
import shutil
import subprocess
import sys
from dataclasses import dataclass, field

_GH = shutil.which("gh") or "gh"

ORGS = ["ByronWilliamsCPA", "williaby"]

# Repos where Renovate is intentionally ignored; dependabot.yml coexistence is expected
RENOVATE_IGNORED = {"williaby/dart-frog-paludarium", "williaby/homelab-agent-configs"}

# Repos where main branch is not the default
BRANCH_OVERRIDES = {
    "ByronWilliamsCPA/xero-crypto": "master",
    "williaby/FISProject": "master",
    "williaby/backpacking": "master",
    "williaby/family_office": "master",
    "williaby/dart-frog-paludarium": "master",
    "williaby/homelab-agent-configs": "agent/hermes",
}


@dataclass
class RepoResult:
    slug: str
    branch: str
    ci_020: str = "?"  # renovate.json present
    ci_021: str = "?"  # dependabot.yml absent
    bp_4: str = "?"  # required signatures
    bp_5: str = "?"  # enforce admins
    notes: list[str] = field(default_factory=list)


def gh(path: str) -> tuple[dict | list | None, str | None]:
    # path is always constructed from hardcoded f-strings, never from user-supplied input
    r = subprocess.run(  # noqa: S603
        [_GH, "api", path],
        capture_output=True,
        text=True,
        check=False,
    )
    if r.returncode != 0:
        return None, r.stderr.strip()
    return json.loads(r.stdout) if r.stdout.strip() else {}, None


def file_exists(org: str, repo: str, path: str, branch: str) -> bool:
    data, err = gh(f"repos/{org}/{repo}/contents/{path}?ref={branch}")
    return data is not None and "sha" in data


def check_repo(org: str, repo: str) -> RepoResult:
    slug = f"{org}/{repo}"
    branch = BRANCH_OVERRIDES.get(slug, "main")
    result = RepoResult(slug=slug, branch=branch)

    # CI-020: renovate.json present
    has_renovate = file_exists(org, repo, "renovate.json", branch)
    result.ci_020 = "PASS" if has_renovate else "FAIL"

    # CI-021: dependabot.yml absent when Renovate active
    if slug in RENOVATE_IGNORED:
        result.ci_021 = "N/A"
        result.notes.append("Renovate ignored; dependabot.yml coexistence expected")
    elif has_renovate:
        has_dependabot = file_exists(org, repo, ".github/dependabot.yml", branch)
        result.ci_021 = "FAIL" if has_dependabot else "PASS"
    else:
        result.ci_021 = "N/A"  # no Renovate, so CI-020 gap is the issue

    # BP-4: required signatures
    sig_data, err = gh(
        f"repos/{org}/{repo}/branches/{branch}/protection/required_signatures"
    )
    if err:
        result.bp_4 = "NONE"
    else:
        result.bp_4 = "PASS" if sig_data and sig_data.get("enabled") else "FAIL"

    # BP-5: enforce admins
    prot_data, err = gh(f"repos/{org}/{repo}/branches/{branch}/protection")
    if err or not prot_data:
        result.bp_5 = "NONE"
    else:
        admins = prot_data.get("enforce_admins", {}).get("enabled", False)
        result.bp_5 = "PASS" if admins else "FAIL"

    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Repo compliance sweep")
    parser.add_argument("--org", help="Limit to one org")
    parser.add_argument("--repo", help="Check a single repo (owner/repo)")
    args = parser.parse_args()

    if args.repo:
        org, repo = args.repo.split("/", 1)
        repos_to_check = [(org, repo)]
    else:
        repos_to_check = []
        for org in [args.org] if args.org else ORGS:
            data, err = gh(f"orgs/{org}/repos?per_page=100&type=all")
            if err or not data:
                print(f"ERROR fetching repos for {org}: {err}", file=sys.stderr)
                continue
            for r in data:
                repos_to_check.append((org, r["name"]))

    results: list[RepoResult] = []
    total = len(repos_to_check)
    for i, (org, repo) in enumerate(repos_to_check, 1):
        print(f"  [{i:3}/{total}] {org}/{repo} ...", end="\r", flush=True)
        results.append(check_repo(org, repo))

    print(" " * 60, end="\r")  # clear progress line

    # Print table
    w = max(len(r.slug) for r in results) + 2
    header = f"{'Repo':<{w}} {'CI-020':>7} {'CI-021':>7} {'BP-4':>6} {'BP-5':>6}"
    print(header)
    print("-" * len(header))

    failures = 0
    for r in results:
        row = f"{r.slug:<{w}} {r.ci_020:>7} {r.ci_021:>7} {r.bp_4:>6} {r.bp_5:>6}"
        if r.notes:
            row += f"   # {'; '.join(r.notes)}"
        print(row)
        if any(v == "FAIL" for v in [r.ci_020, r.ci_021, r.bp_4, r.bp_5]):
            failures += 1

    print("-" * len(header))

    # Summary
    pass_count = sum(
        1
        for r in results
        if all(v in ("PASS", "N/A") for v in [r.ci_020, r.ci_021, r.bp_4, r.bp_5])
    )
    print(
        f"\n{pass_count}/{len(results)} repos fully compliant  |  {failures} with failures\n"
    )
    print(
        "Checks: CI-020=renovate.json present, CI-021=no dependabot.yml conflict, "
        "BP-4=signed commits, BP-5=enforce admins"
    )

    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
