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

# Fallback for branch-protection exemption when the catalog is unavailable.
# The authoritative source is the catalog flag `branchProtectionExempt`; this
# set is only consulted when load_catalog() returns {} (file missing or
# malformed). Keep in sync with docs/reference/github-repos.json.
_FALLBACK_BRANCH_PROTECTION_EXEMPT = frozenset({"williaby/homelab-agent-configs"})


def is_branch_protection_exempt(slug: str, catalog: dict) -> bool:
    """Return True if this repo is exempt from branch protection checks.

    Reads the catalog `branchProtectionExempt` field as the source of truth.
    Falls back to a small hardcoded set if the catalog is unavailable so
    offline runs remain safe.

    Args:
        slug: Repo slug in `org/repo` form.
        catalog: Catalog mapping from `load_catalog()`.

    Returns:
        True if the repo should skip BP-4/BP-5 checks, else False.
    """
    if slug in catalog:
        return bool(catalog[slug].get("branchProtectionExempt", False))
    return slug in _FALLBACK_BRANCH_PROTECTION_EXEMPT


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
    """Load github-repos.json. Returns empty dict if file absent or malformed.

    Returns:
        Mapping of "org/repo" slug to repo entry dict. Empty dict on any
        load or parse error so the script can continue with non-API checks.
    """
    if not CATALOG_PATH.exists():
        return {}
    try:
        with CATALOG_PATH.open() as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        print(f"warning: catalog at {CATALOG_PATH} unreadable: {e}", file=sys.stderr)
        return {}
    catalog = {}
    for r in data.get("repos", []):
        org_name = r.get("org")
        repo_name = r.get("name")
        if org_name and repo_name:
            catalog[f"{org_name}/{repo_name}"] = r
    return catalog


def applies_to_api_repos(org: str, repo: str, catalog: dict) -> bool:
    """Return True if the repo serves an API (api.servesApi == true).

    Handles the case where the `api` key is present but null (returns False).
    """
    entry = catalog.get(f"{org}/{repo}", {})
    api = entry.get("api") or {}
    return bool(api.get("servesApi", False))


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
    if not r.stdout.strip():
        return {}, None
    try:
        return json.loads(r.stdout), None
    except json.JSONDecodeError as e:
        return None, f"malformed JSON from gh: {e}"


def gh_paginated_array(path: str) -> tuple[list | None, str | None]:
    """Fetch a list-valued endpoint with full pagination.

    Uses `gh api --paginate --jq '.[]'` which emits one JSON object per
    line so we never have to parse concatenated arrays. Use this for
    listings (e.g. orgs/X/repos) where the result can exceed one page.

    Args:
        path: API path, constructed from hardcoded f-strings.

    Returns:
        (items, None) on success, (None, error_message) on gh failure.
    """
    r = subprocess.run(  # noqa: S603
        [_GH, "api", "--paginate", "--jq", ".[]", path],
        capture_output=True,
        text=True,
        check=False,
    )
    if r.returncode != 0:
        return None, r.stderr.strip()
    items: list = []
    for line in r.stdout.splitlines():
        if not line.strip():
            continue
        try:
            items.append(json.loads(line))
        except json.JSONDecodeError as e:
            return None, f"malformed JSON line from gh: {e}"
    return items, None


def _signatures_enforced(org: str, repo: str, branch: str) -> bool:
    """Return True if commit signatures are required via ruleset or classic protection.

    Checks the ruleset evaluation endpoint first. If any active ruleset
    includes a required_signatures rule targeting this branch, returns True.
    Falls back to the classic branch-protection endpoint when no ruleset result
    is found.

    Args:
        org: GitHub organization name.
        repo: Repository name.
        branch: Branch name to check.

    Returns:
        True if signatures are required by any active source; False otherwise.
    """
    rules_data, err = gh(f"repos/{org}/{repo}/rules/branches/{branch}")
    if err is None and rules_data:
        try:
            rules = (
                json.loads(rules_data) if isinstance(rules_data, str) else rules_data
            )
            if any(r.get("type") == "required_signatures" for r in rules):
                return True
        except (json.JSONDecodeError, TypeError):
            # Unexpected ruleset shape; fall through to the classic check
            # below rather than raising, since the classic source can still
            # confirm signatures.
            pass
    sig_data, err = gh(
        f"repos/{org}/{repo}/branches/{branch}/protection/required_signatures"
    )
    if err is not None:
        return False
    try:
        if isinstance(sig_data, str):
            return bool(json.loads(sig_data).get("enabled"))
        return bool(sig_data.get("enabled"))
    except (json.JSONDecodeError, AttributeError):
        return False


def _admins_enforced(org: str, repo: str, branch: str) -> bool:
    """Return True if admin bypass is not present in any governing ruleset.

    Reads the rules evaluation endpoint to find all rulesets active on this
    branch, then fetches each ruleset to check for a RepositoryRole id=5
    (OrganizationAdmin) bypass actor. Returns False if any such bypass is
    found, because the user intentionally keeps bypass_mode=always for
    emergency unblock. Falls back to the classic enforce_admins field when no
    rulesets are active.

    Args:
        org: GitHub organization name.
        repo: Repository name.
        branch: Branch name to check.

    Returns:
        True if admins are enforced (no bypass present or classic enabled);
        False if any org-admin bypass actor is configured.
    """
    rules_data, err = gh(f"repos/{org}/{repo}/rules/branches/{branch}")
    ruleset_refs: set[tuple[str, str, int]] = set()
    if err is None and rules_data:
        try:
            rules = (
                json.loads(rules_data) if isinstance(rules_data, str) else rules_data
            )
            for r in rules:
                rs_type = r.get("ruleset_source_type")
                rs_id = r.get("ruleset_id")
                rs_src = r.get("ruleset_source", "")
                if rs_type and rs_id:
                    ruleset_refs.add((rs_type, rs_src, rs_id))
        except (json.JSONDecodeError, TypeError):
            # Unexpected ruleset-evaluation shape; treat as no rulesets
            # active and let the classic enforce_admins check below decide.
            pass
    fetch_failures = 0
    for rs_type, rs_src, rs_id in ruleset_refs:
        path = (
            f"orgs/{rs_src}/rulesets/{rs_id}"
            if rs_type == "Organization"
            else f"repos/{org}/{repo}/rulesets/{rs_id}"
        )
        body, err = gh(path)
        if err is not None:
            # Transient outage path: a successful rules-evaluation pointed to
            # this ruleset but its body cannot be fetched. Log so operators
            # can correlate; preserve safe-fail (do not auto-FAIL the audit
            # on every transient hiccup) per documented policy.
            fetch_failures += 1
            print(
                f"warning: BP-5 ruleset body fetch failed for "
                f"{org}/{repo}@{branch} (rs_type={rs_type}, rs_id={rs_id}): {err}",
                file=sys.stderr,
            )
            continue
        try:
            ruleset = json.loads(body) if isinstance(body, str) else body
        except json.JSONDecodeError:
            continue
        for actor in ruleset.get("bypass_actors", []) or []:
            if (
                actor.get("actor_type") == "RepositoryRole"
                and actor.get("actor_id") == 5
            ):
                return False
    if ruleset_refs and fetch_failures == len(ruleset_refs):
        # All ruleset bodies failed to fetch. We cannot confidently say
        # admins are enforced; fall through to the classic-protection check
        # rather than fail-open by returning True.
        print(
            f"warning: BP-5 all ruleset body fetches failed for "
            f"{org}/{repo}@{branch}; falling back to classic enforce_admins.",
            file=sys.stderr,
        )
    elif ruleset_refs:
        return True
    prot_data, err = gh(f"repos/{org}/{repo}/branches/{branch}/protection")
    if err is not None:
        return False
    try:
        prot = json.loads(prot_data) if isinstance(prot_data, str) else prot_data
        return bool(prot.get("enforce_admins", {}).get("enabled"))
    except (json.JSONDecodeError, AttributeError):
        return False


def file_exists(org: str, repo: str, path: str, branch: str) -> bool:
    data, _err = gh(f"repos/{org}/{repo}/contents/{path}?ref={branch}")
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

    # BP-4 / BP-5: ruleset-aware; exempt repos short-circuit to N/A
    if is_branch_protection_exempt(slug, catalog):
        result.bp_4 = "N/A"
        result.bp_5 = "N/A"
        result.notes.append("Branch protection exempt by catalog flag")
    else:
        result.bp_4 = "PASS" if _signatures_enforced(org, repo, branch) else "FAIL"
        if _admins_enforced(org, repo, branch):
            result.bp_5 = "PASS"
        else:
            result.bp_5 = "FAIL"
            result.notes.append("BP-5 expected FAIL: solo-dev admin bypass intentional")

    # API-001..005: only run for repos with api.servesApi=true
    if applies_to_api_repos(org, repo, catalog):
        catalog_entry = catalog.get(slug, {})
        api_info = catalog_entry.get("api") or {}

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
        # FAIL covers both "not yet audited" (None) and "failing"; matches API-004
        # behavior. New servesApi=true repos surface as FAIL until the openapi-
        # compliance-agent has run on them, which is intentional: the audit drives
        # completion of pending pipeline work.
        test_status = api_info.get("testStatus")
        if test_status is None:
            result.api_005_test_status = "FAIL"
        else:
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
        org_listing_failures: list[str] = []
        for org in [args.org] if args.org else ORGS:
            data, err = gh_paginated_array(f"orgs/{org}/repos?per_page=100&type=all")
            if err or data is None:
                print(f"ERROR fetching repos for {org}: {err}", file=sys.stderr)
                org_listing_failures.append(org)
                continue
            for r in data:
                name = r.get("name") if isinstance(r, dict) else None
                if name:
                    repos_to_check.append((org, name))
        if org_listing_failures:
            print(
                f"WARNING: skipped {len(org_listing_failures)} org(s) due to API "
                f"errors: {', '.join(org_listing_failures)}; results below are "
                "incomplete.",
                file=sys.stderr,
            )

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
