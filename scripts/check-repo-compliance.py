#!/usr/bin/env python3
"""Periodic compliance sweep across all managed repos.

Checks the most drift-prone standards from docs/standards-manifest.yaml:
  CI-020: renovate.json present at repo root
  CI-021: dependabot.yml absent when renovate.json is present
  BP-4:   Required commit signatures enabled
  BP-5:   enforce_admins enabled
  API-001..005: OpenAPI/Postman compliance (api.servesApi=true repos only)

Run this weekly (or after any org-wide change) to catch repos that fall out of
alignment before they accumulate. Prints a compact table and exits non-zero if
any repo fails a non-waived check.

Usage:
  python3 scripts/check-repo-compliance.py
  python3 scripts/check-repo-compliance.py --org ByronWilliamsCPA
  python3 scripts/check-repo-compliance.py --repo ByronWilliamsCPA/.claude
"""

import argparse
import datetime
import json
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

_GH = shutil.which("gh") or "gh"

ORGS = ["ByronWilliamsCPA", "williaby"]

CATALOG_PATH = Path(__file__).parent.parent / "docs/reference/github-repos.json"

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


def load_catalog() -> dict:
    """Load github-repos.json. Returns empty dict if file absent."""
    if not CATALOG_PATH.exists():
        return {}
    with CATALOG_PATH.open() as f:
        data = json.load(f)
    return {f"{r['org']}/{r['name']}": r for r in data.get("repos", [])}


def applies_to_api_repos(org: str, repo: str, catalog: dict) -> bool:
    """Return True if the repo serves an API (api.servesApi == true)."""
    entry = catalog.get(f"{org}/{repo}", {})
    return bool(entry.get("api", {}).get("servesApi", False))


@dataclass
class RepoResult:
    slug: str
    branch: str
    ci_020: str = "?"  # renovate.json present
    ci_021: str = "?"  # dependabot.yml absent
    bp_4: str = "?"  # required signatures
    bp_5: str = "?"  # enforce admins
    api_001_openapi_spec: str = "N/A"
    api_002_postman_collection: str = "N/A"
    api_003_ci_workflow: str = "N/A"
    api_004_last_audited: str = "N/A"
    api_005_test_status: str = "N/A"
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


def check_repo(org: str, repo: str, catalog: dict) -> RepoResult:
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

    # API-001..005: only run for repos with api.servesApi=true
    if applies_to_api_repos(org, repo, catalog):
        catalog_entry = catalog.get(slug, {})
        api_info = catalog_entry.get("api", {})

        # API-001: openapi.yaml present
        result.api_001_openapi_spec = (
            "PASS"
            if file_exists(org, repo, "docs/api/openapi.yaml", branch)
            else "FAIL"
        )

        # API-002: postman-collection.json present
        result.api_002_postman_collection = (
            "PASS"
            if file_exists(org, repo, "docs/api/postman-collection.json", branch)
            else "FAIL"
        )

        # API-003: CI workflow present
        result.api_003_ci_workflow = (
            "PASS"
            if file_exists(org, repo, ".github/workflows/postman-api-tests.yml", branch)
            else "FAIL"
        )

        # API-004: lastAudited within 90 days
        last_audited = api_info.get("lastAudited")
        if last_audited is None:
            result.api_004_last_audited = "FAIL"
        else:
            try:
                audited_date = datetime.date.fromisoformat(last_audited)
                today = datetime.datetime.now(tz=datetime.timezone.utc).date()
                days_ago = (today - audited_date).days
                result.api_004_last_audited = "PASS" if days_ago <= 90 else "FAIL"
            except ValueError:
                result.api_004_last_audited = "FAIL"

        # API-005: testStatus == "passing"
        test_status = api_info.get("testStatus")
        result.api_005_test_status = "PASS" if test_status == "passing" else "FAIL"

    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Repo compliance sweep")
    parser.add_argument("--org", help="Limit to one org")
    parser.add_argument("--repo", help="Check a single repo (owner/repo)")
    args = parser.parse_args()

    catalog = load_catalog()

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
        results.append(check_repo(org, repo, catalog))

    print(" " * 60, end="\r")  # clear progress line

    # Print table
    w = max(len(r.slug) for r in results) + 2
    header = (
        f"{'Repo':<{w}} {'CI-020':>7} {'CI-021':>7} {'BP-4':>6} {'BP-5':>6}"
        f" {'API-001':>8} {'API-002':>8} {'API-003':>8} {'API-004':>8} {'API-005':>8}"
    )
    print(header)
    print("-" * len(header))

    failures = 0
    for r in results:
        row = (
            f"{r.slug:<{w}} {r.ci_020:>7} {r.ci_021:>7} {r.bp_4:>6} {r.bp_5:>6}"
            f" {r.api_001_openapi_spec:>8} {r.api_002_postman_collection:>8}"
            f" {r.api_003_ci_workflow:>8} {r.api_004_last_audited:>8}"
            f" {r.api_005_test_status:>8}"
        )
        if r.notes:
            row += f"   # {'; '.join(r.notes)}"
        print(row)
        all_checks = [
            r.ci_020,
            r.ci_021,
            r.bp_4,
            r.bp_5,
            r.api_001_openapi_spec,
            r.api_002_postman_collection,
            r.api_003_ci_workflow,
            r.api_004_last_audited,
            r.api_005_test_status,
        ]
        if any(v == "FAIL" for v in all_checks):
            failures += 1

    print("-" * len(header))

    # Summary
    all_check_fields = [
        "ci_020",
        "ci_021",
        "bp_4",
        "bp_5",
        "api_001_openapi_spec",
        "api_002_postman_collection",
        "api_003_ci_workflow",
        "api_004_last_audited",
        "api_005_test_status",
    ]
    pass_count = sum(
        1
        for r in results
        if all(getattr(r, f) in ("PASS", "N/A") for f in all_check_fields)
    )
    print(
        f"\n{pass_count}/{len(results)} repos fully compliant  |  {failures} with failures\n"
    )
    print(
        "Checks: CI-020=renovate.json present, CI-021=no dependabot.yml conflict, "
        "BP-4=signed commits, BP-5=enforce admins, "
        "API-001..005=OpenAPI/Postman compliance (api_repos only)"
    )

    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
