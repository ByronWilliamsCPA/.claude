#!/usr/bin/env python3
"""
Create CODE_OF_CONDUCT.md and GOVERNANCE.md pointer files across all repos
that are missing them.

Reads docs/reference/github-repos.json to determine which repos need files.
For repos without branch protection: commits directly to the default branch.
For repos with branch protection: creates chore/community-health-pointers branch
and opens a PR.

Skips: ByronWilliamsCPA/.github (source), ByronWilliamsCPA/.claude (managed
locally in this working tree), archived repos, and any repo where both files
already exist according to the catalog.

Usage:
    python3 tools/create_community_health_pointers.py
    python3 tools/create_community_health_pointers.py --dry-run
"""

import argparse
import base64
import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

# #CRITICAL: path is anchored to __file__ so the script works regardless of cwd
# #VERIFY: run tools/refresh_catalog_release_health.py to update before bulk runs
CATALOG = Path(__file__).parent.parent / "docs/reference/github-repos.json"
BRANCH_NAME = "chore/community-health-pointers"

# #ASSUME: org names are stable; update ALLOWED_ORGS if new orgs are added to the catalog
ALLOWED_ORGS = frozenset({"ByronWilliamsCPA", "williaby"})

COC_CONTENT = """\
# Code of Conduct

This project follows the [ByronWilliamsCPA organization Code of Conduct](https://github.com/ByronWilliamsCPA/.github/blob/main/CODE_OF_CONDUCT.md).
"""

GOV_CONTENT = """\
# Governance

This project follows the [ByronWilliamsCPA organization Governance policy](https://github.com/ByronWilliamsCPA/.github/blob/main/GOVERNANCE.md).
"""

SKIP_REPOS = {"ByronWilliamsCPA/.github", "ByronWilliamsCPA/.claude"}


def gh(path, method="GET", data=None):
    cmd = ["gh", "api", path, "-X", method]
    if data:
        cmd += ["--input", "-"]
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            input=json.dumps(data) if data else None,
            check=False,
            timeout=30,
        )
    except subprocess.TimeoutExpired:
        return None, f"gh api {path} timed out after 30s"
    if result.returncode != 0:
        return None, result.stderr.strip()
    if not result.stdout.strip():
        return {}, None
    try:
        return json.loads(result.stdout), None
    except json.JSONDecodeError as exc:
        return None, f"gh api {path} returned non-JSON: {exc}"


def get_default_branch(org, name):
    resp, err = gh(f"repos/{org}/{name}")
    if resp is None:
        return None, err
    return resp.get("default_branch", "main"), None


def get_branch_sha(org, name, branch):
    resp, _ = gh(f"repos/{org}/{name}/git/ref/heads/{branch}")
    return (resp or {}).get("object", {}).get("sha")


def create_branch(org, name, branch, from_sha, dry_run=False):
    if dry_run:
        return True, None
    resp, err = gh(
        f"repos/{org}/{name}/git/refs",
        "POST",
        {"ref": f"refs/heads/{branch}", "sha": from_sha},
    )
    already_exists = resp is None and "already exists" in (err or "")
    return resp is not None or already_exists, err


def create_file(org, name, path, content, branch, message, dry_run):
    if dry_run:
        return True, None
    encoded = base64.b64encode(content.encode()).decode()
    resp, err = gh(
        f"repos/{org}/{name}/contents/{path}",
        "PUT",
        {"message": message, "content": encoded, "branch": branch},
    )
    if (
        resp is None
        and "sha" in (err or "").lower()
        and "wasn't supplied" in (err or "")
    ):
        return True, None  # file already exists on this branch
    return resp is not None, err


def open_pr(org, name, branch, base, files, dry_run):
    if dry_run:
        return f"(dry-run) would open PR in {org}/{name}", None
    body = (
        f"Adds minimal pointer files for {', '.join(files)} referencing "
        f"the ByronWilliamsCPA org-level policy documents.\n\n"
        "These satisfy FOUND-012 (CODE_OF_CONDUCT) and FOUND-013 (GOVERNANCE) "
        "compliance checks without duplicating content that is maintained at "
        "the org level in ByronWilliamsCPA/.github."
    )
    resp, err = gh(
        f"repos/{org}/{name}/pulls",
        "POST",
        {
            "title": "docs: add community health pointer files",
            "body": body,
            "head": branch,
            "base": base,
            "draft": False,
        },
    )
    if resp is None and (
        "422" in (err or "") or "already exists" in (err or "").lower()
    ):
        existing, _ = gh(
            f"repos/{org}/{name}/pulls?head={org}:{branch}&base={base}&state=open"
        )
        if existing:
            return existing[0].get("html_url"), None
    return (resp or {}).get("html_url"), err


def _files_needed(foundations):
    files = []
    if not foundations.get("codeOfConduct", False):
        files.append(
            (
                "CODE_OF_CONDUCT.md",
                COC_CONTENT,
                "docs: add CODE_OF_CONDUCT.md pointer to org-level policy",
            )
        )
    if not foundations.get("governanceMd", False):
        files.append(
            (
                "GOVERNANCE.md",
                GOV_CONTENT,
                "docs: add GOVERNANCE.md pointer to org-level policy",
            )
        )
    return files


def _setup_branch(org, name, default_branch, dry_run):
    main_sha = get_branch_sha(org, name, default_branch)
    if not main_sha:
        return None, "could not get default branch SHA"
    ok, err = create_branch(org, name, BRANCH_NAME, main_sha, dry_run)
    if not ok:
        return None, f"create branch failed: {err}"
    return BRANCH_NAME, None


def _is_ruleset_error(err):
    lower = (err or "").lower()
    return "pull request" in lower or "rule violations" in lower


def _via_pr(org, name, default_branch, files_to_create, dry_run):
    target_branch, err = _setup_branch(org, name, default_branch, dry_run)
    if not target_branch:
        return "error", err
    created = []
    for path, content, message in files_to_create:
        ok, err = create_file(org, name, path, content, target_branch, message, dry_run)
        if not ok:
            return "error", f"{path} create failed: {err}"
        created.append(path)
    pr_url, err = open_pr(org, name, BRANCH_NAME, default_branch, created, dry_run)
    if not pr_url:
        return "error", f"PR open failed: {err}"
    return "pr", pr_url


def process_repo(entry, dry_run):
    org = entry["org"]
    name = entry["name"]
    slug = f"{org}/{name}"

    # #CRITICAL: allowlist prevents writes to unexpected orgs if catalog data is corrupted
    if org not in ALLOWED_ORGS:
        return slug, "error", f"unexpected org {org!r}; not in allowlist"

    # #EDGE: catalog entries may have missing nested keys from older script versions
    review = entry.get("review", {})
    foundations = review.get("foundations", {})
    has_protection = review.get("branchProtection", {}).get("enabled", False)

    files_to_create = _files_needed(foundations)
    if not files_to_create:
        return slug, "skip", "already compliant"

    # #CRITICAL: API failure returns (None, err); silently falling back to "main" would
    # commit to the wrong branch on repos where the default is something else
    # #VERIFY: gh CLI must be authenticated; run `gh auth status` before bulk runs
    default_branch, err = get_default_branch(org, name)
    if default_branch is None:
        return slug, "error", f"could not get default branch: {err}"

    if has_protection:
        status, detail = _via_pr(org, name, default_branch, files_to_create, dry_run)
        return slug, status, detail

    # Attempt direct commits; fall back to PR if repository rulesets block the push
    created = []
    for path, content, message in files_to_create:
        ok, err = create_file(
            org, name, path, content, default_branch, message, dry_run
        )
        if not ok:
            if _is_ruleset_error(err):
                # #EDGE: pass only remaining files so already-committed files are not re-sent
                remaining = files_to_create[len(created) :]
                status, detail = _via_pr(org, name, default_branch, remaining, dry_run)
                if created:
                    detail = (
                        f"{detail} (already committed directly: {', '.join(created)})"
                    )
                return slug, status, detail
            already = f"; already committed: {', '.join(created)}" if created else ""
            return slug, "error", f"{path} create failed: {err}{already}"
        created.append(path)

    return slug, "committed", f"wrote {', '.join(created)} to {default_branch}"


def _safe_process_repo(entry, dry_run):
    """Wrap process_repo so thread-worker exceptions are captured as error results."""
    try:
        return process_repo(entry, dry_run)
    except Exception as exc:
        org = entry.get("org", "?")
        name = entry.get("name", "?")
        return f"{org}/{name}", "error", f"unhandled exception: {exc}"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would happen without making API calls",
    )
    args = parser.parse_args()

    with CATALOG.open() as f:
        data = json.load(f)
    repos = [
        r
        for r in data["repos"]
        if not r["isArchived"]
        and f"{r['org']}/{r['name']}" not in SKIP_REPOS
        and not (
            r.get("review", {}).get("foundations", {}).get("codeOfConduct", False)
            and r.get("review", {}).get("foundations", {}).get("governanceMd", False)
        )
    ]

    mode = "DRY RUN -- " if args.dry_run else ""
    print(f"{mode}Processing {len(repos)} repos...\n")

    results = {"pr": [], "committed": [], "error": [], "skip": []}

    # #ASSUME: 6 workers is safe under GitHub secondary rate limits (~80 mutations/minute)
    # #VERIFY: reduce max_workers to 3 if rate-limit errors appear in output
    with ThreadPoolExecutor(max_workers=6) as pool:
        futures = {pool.submit(_safe_process_repo, r, args.dry_run): r for r in repos}
        for future in as_completed(futures):
            slug, status, detail = future.result()
            results[status].append((slug, detail))
            marker = {"pr": "PR", "committed": "OK", "error": "ERR", "skip": "SKIP"}[
                status
            ]
            print(f"  [{marker}] {slug}: {detail}")

    print("\nSummary:")
    print(f"  PRs opened:     {len(results['pr'])}")
    print(f"  Direct commits: {len(results['committed'])}")
    print(f"  Errors:         {len(results['error'])}")
    print(f"  Skipped:        {len(results['skip'])}")

    if results["error"]:
        print("\nFailed repos:")
        for slug, detail in results["error"]:
            print(f"  {slug}: {detail}")
        sys.exit(1)


if __name__ == "__main__":
    main()
