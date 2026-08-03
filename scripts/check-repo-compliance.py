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
import enum
import json
import re
import shutil
import subprocess
import sys
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from pathlib import Path

# The sweep's core checks read JSON only. Manifest-derived scope counts are the
# one feature that needs YAML, and they degrade to an unknown count rather than
# taking the whole sweep down. Imported at module level (not inside the
# function) so the optional dependency is declared in one place and no per-call
# lint suppression is needed.
try:
    import yaml

    _YAML_AVAILABLE = True
except ImportError:  # pragma: no cover - pyyaml is optional for the sweep
    _YAML_AVAILABLE = False

_GH = shutil.which("gh") or "gh"

ORGS = ["ByronWilliamsCPA", "williaby"]

CATALOG_PATH = Path(__file__).parent.parent / "docs/reference/github-repos.json"
MANIFEST_PATH = Path(__file__).parent.parent / "docs/standards-manifest.yaml"

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


# --------------------------------------------------------------------------- #
# applies_to scope resolution (tri-state)                                      #
#                                                                              #
# An `applies_to` scope is decided by a catalog flag. Coercing an absent or    #
# null flag to False silently reclassifies "nobody has said" as "does not      #
# apply", which skips the domain and renders an audit indistinguishable from   #
# a passing one. The MkDocs domain shipped in exactly that state: publishesDocs#
# is absent on 44 of 45 catalog entries and false on the 45th, so all 14       #
# MKDOCS-* checks evaluated to a silent skip fleet-wide.                       #
#                                                                              #
# Only an explicit `false` means "does not apply". Absent, null, and           #
# non-boolean values resolve to UNKNOWN, which is a finding: the catalog needs #
# populating.                                                                  #
# --------------------------------------------------------------------------- #


class Applicability(enum.Enum):
    """Tri-state verdict for whether an ``applies_to`` scope covers a repo."""

    APPLIES = "APPLIES"
    SKIP = "SKIP"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class ScopeDefinition:
    """Binds an ``applies_to`` scope to the catalog flag that decides it.

    Attributes:
        scope: The ``applies_to`` value used in the standards manifest.
        flag_path: Key path into a catalog entry, e.g. ``("api", "servesApi")``.
        domain: The manifest ``domain`` whose checks this scope gates.
    """

    scope: str
    flag_path: tuple[str, ...]
    domain: str

    @property
    def flag_name(self) -> str:
        """Dotted catalog flag name, for display in SKIP/UNKNOWN lines."""
        return ".".join(self.flag_path)


SCOPE_DEFINITIONS: dict[str, ScopeDefinition] = {
    "api_repos": ScopeDefinition("api_repos", ("api", "servesApi"), "api"),
    "docs_repos": ScopeDefinition("docs_repos", ("publishesDocs",), "mkdocs"),
    "deployed_repos": ScopeDefinition("deployed_repos", ("isDeployed",), "operations"),
}


@dataclass(frozen=True)
class ScopeVerdict:
    """Outcome of resolving one ``applies_to`` scope against one repo.

    Attributes:
        scope: The scope that was resolved.
        applicability: APPLIES, SKIP, or UNKNOWN.
        raw_value: The catalog flag value as found, for the audit line.
        reason: Human-readable basis, shown on SKIP and UNKNOWN lines.
    """

    scope: str
    applicability: Applicability
    raw_value: object
    reason: str

    @property
    def definition(self) -> ScopeDefinition:
        """The scope definition this verdict was resolved against."""
        return SCOPE_DEFINITIONS[self.scope]


def _read_flag(entry: dict, flag_path: tuple[str, ...]) -> tuple[object, bool]:
    """Walk ``flag_path`` through ``entry``.

    Args:
        entry: A catalog repo entry.
        flag_path: Sequence of keys to descend.

    Returns:
        ``(value, found)``. ``found`` is False when any key along the path is
        absent, which is distinct from a path that resolves to ``None``.
    """
    cursor: object = entry
    for key in flag_path:
        if not isinstance(cursor, dict) or key not in cursor:
            return None, False
        cursor = cursor[key]
    return cursor, True


def resolve_applicability(slug: str, catalog: dict, scope: str) -> ScopeVerdict:
    """Resolve one ``applies_to`` scope for one repo.

    Absent, null, and non-boolean flag values all resolve to UNKNOWN so an
    unpopulated catalog surfaces as a finding instead of a silent skip. Only an
    explicit ``false`` yields SKIP.

    Args:
        slug: Repo slug in ``org/repo`` form.
        catalog: Catalog mapping from :func:`load_catalog`.
        scope: A key of :data:`SCOPE_DEFINITIONS`.

    Returns:
        The :class:`ScopeVerdict` for this repo and scope.

    Raises:
        KeyError: If ``scope`` is not a known ``applies_to`` scope.
    """
    definition = SCOPE_DEFINITIONS[scope]
    entry = catalog.get(slug)
    if entry is None:
        return ScopeVerdict(
            scope,
            Applicability.UNKNOWN,
            None,
            f"{slug} absent from catalog; add an entry and set {definition.flag_name}",
        )
    value, found = _read_flag(entry, definition.flag_path)
    if not found:
        return ScopeVerdict(
            scope,
            Applicability.UNKNOWN,
            None,
            f"{definition.flag_name} absent from catalog entry; populate it",
        )
    if value is None:
        return ScopeVerdict(
            scope,
            Applicability.UNKNOWN,
            None,
            f"{definition.flag_name} is null; populate it with an explicit boolean",
        )
    if value is True:
        return ScopeVerdict(
            scope, Applicability.APPLIES, raw_value=True, reason="in scope"
        )
    if value is False:
        return ScopeVerdict(
            scope,
            Applicability.SKIP,
            raw_value=False,
            reason="explicitly out of scope",
        )
    return ScopeVerdict(
        scope,
        Applicability.UNKNOWN,
        value,
        f"{definition.flag_name} is {value!r}, not a boolean; correct it",
    )


def load_manifest_scope_checks() -> dict[str, list[str]]:
    """Map each ``applies_to`` scope to the manifest check IDs carrying it.

    Read from the manifest rather than hardcoded so the "N checks skipped"
    count in the audit summary cannot drift from the manifest. Degrades to an
    empty mapping when the manifest is missing or unparseable; callers render
    an unknown count rather than failing the sweep.

    Returns:
        Mapping of scope name to the sorted check IDs scoped to it.
    """
    if not _YAML_AVAILABLE:
        print("warning: pyyaml unavailable, scope counts unknown", file=sys.stderr)
        return {}
    try:
        with MANIFEST_PATH.open(encoding="utf-8") as handle:
            data = yaml.safe_load(handle)
    except (OSError, yaml.YAMLError) as exc:
        print(
            f"warning: manifest at {MANIFEST_PATH} unreadable: {exc}", file=sys.stderr
        )
        return {}
    # safe_load returns whatever the document is: a list, a scalar, or None for
    # an empty file. Only a mapping has `.get`, so anything else must exit here
    # or the sweep dies on AttributeError instead of degrading to unknown counts.
    if not isinstance(data, dict):
        print(
            f"warning: manifest at {MANIFEST_PATH} has a non-mapping root "
            f"({type(data).__name__}), scope counts unknown",
            file=sys.stderr,
        )
        return {}
    scoped: dict[str, list[str]] = {}
    for check in data.get("checks", []) or []:
        if not isinstance(check, dict):
            continue
        raw = check.get("applies_to")
        if raw is None:
            continue
        values = raw if isinstance(raw, list) else [raw]
        for value in values:
            scoped.setdefault(str(value), []).append(str(check.get("id", "<no id>")))
    return {scope: sorted(ids) for scope, ids in scoped.items()}


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
    # Every applies_to scope resolved for this repo, keyed by scope name. Carries
    # SKIP and UNKNOWN verdicts so the summary can report them per repo instead
    # of dropping them silently.
    scopes: dict[str, ScopeVerdict] = field(default_factory=dict)


_API_RESULT_FIELDS = (
    "api_001_openapi_spec",
    "api_002_postman_collection",
    "api_003_ci_workflow",
    "api_004_last_audited",
    "api_005_test_status",
)


def render_scope_summary(
    results: list[RepoResult], scope_checks: dict[str, list[str]]
) -> list[str]:
    """Render the per-scope applicability summary block.

    A skipped domain must be visible. For every scope this prints one
    ``SKIP (<flag>: <value>)`` line and one ``UNKNOWN`` line, each carrying the
    number of manifest checks that were not evaluated as a result, so a skip can
    never be mistaken for a passing audit.

    Args:
        results: Per-repo results carrying resolved scope verdicts.
        scope_checks: Scope-to-check-ID mapping from
            :func:`load_manifest_scope_checks`.

    Returns:
        The rendered lines, in scope-name order.
    """
    lines = ["", "APPLICABILITY BY SCOPE", "-" * 60]
    for scope, definition in sorted(SCOPE_DEFINITIONS.items()):
        check_ids = scope_checks.get(scope, [])
        # An unreadable manifest means the per-repo check count is UNKNOWN, not
        # zero. Rendering it as 0 would print a definitive "0 check evaluations
        # skipped" for a quantity nobody measured, which is the same hollow
        # reporting this whole summary exists to prevent.
        count_label = str(len(check_ids)) if check_ids else "?"

        def skipped_label(repos: int, ids: list[str] = check_ids) -> str:
            """Render the skipped-evaluation count, or ``?`` when unmeasurable."""
            return str(repos * len(ids)) if ids else "?"

        buckets: dict[Applicability, list[RepoResult]] = {
            state: [] for state in Applicability
        }
        for result in results:
            verdict = result.scopes.get(scope)
            if verdict is not None:
                buckets[verdict.applicability].append(result)
        applies = len(buckets[Applicability.APPLIES])
        skipped = len(buckets[Applicability.SKIP])
        unknown = len(buckets[Applicability.UNKNOWN])
        lines.append(
            f"{scope} (flag: {definition.flag_name}, domain: {definition.domain}, "
            f"{count_label} checks/repo)"
        )
        lines.append(f"  APPLIES  {applies:>3} repo(s)")
        lines.append(
            f"  SKIP ({definition.flag_name}: false)  {skipped:>3} repo(s), "
            f"{skipped_label(skipped)} check evaluations skipped"
        )
        lines.append(
            f"  UNKNOWN  {unknown:>3} repo(s), "
            f"{skipped_label(unknown)} check evaluations skipped "
            f"-- catalog needs populating"
        )
        for result in buckets[Applicability.UNKNOWN]:
            verdict = result.scopes[scope]
            lines.append(f"      [UNKNOWN] {result.slug}: {verdict.reason}")
        lines.append("")
    return lines


def assert_scopes_reachable(
    results: list[RepoResult], scope_checks: dict[str, list[str]]
) -> list[str]:
    """Flag every ``applies_to`` scope that no repo in the fleet evaluates true.

    A scope with zero in-scope repos means its whole domain is dead: the checks
    exist, the audit runs, and nothing is ever evaluated. That is the failure
    mode the MkDocs domain shipped in. Fleet-wide reach is the only place it is
    detectable, because each individual repo's skip looks locally correct.

    Args:
        results: Per-repo results carrying resolved scope verdicts.
        scope_checks: Scope-to-check-ID mapping from
            :func:`load_manifest_scope_checks`.

    Returns:
        One problem line per unreachable scope; empty when every scope has at
        least one in-scope repo.
    """
    problems: list[str] = []
    for scope, definition in sorted(SCOPE_DEFINITIONS.items()):
        if not results:
            continue
        in_scope = [
            r
            for r in results
            if (v := r.scopes.get(scope)) is not None
            and v.applicability is Applicability.APPLIES
        ]
        if in_scope:
            continue
        check_ids = scope_checks.get(scope, [])
        detail = (
            f"{len(check_ids)} check(s): {', '.join(check_ids)}"
            if check_ids
            else "check list unavailable (manifest unreadable)"
        )
        problems.append(
            f"[UNREACHABLE SCOPE] {scope}: zero of {len(results)} repos have "
            f"{definition.flag_name}: true, so the entire '{definition.domain}' "
            f"domain is never evaluated -- {detail}. Populate the catalog flag or "
            f"retire the scope."
        )
    return problems


def gh(path: str) -> tuple[dict | list | None, str | None]:
    # path is always constructed from hardcoded f-strings, never from user-supplied input
    r = subprocess.run(
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
    r = subprocess.run(
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
        except (json.JSONDecodeError, TypeError) as exc:
            # Unexpected ruleset shape; fall through to the classic check
            # below rather than raising, since the classic source can still
            # confirm signatures. Log so operators can spot schema drift.
            print(
                f"warning: BP-4 ruleset shape unexpected for "
                f"{org}/{repo}@{branch}: {exc}",
                file=sys.stderr,
            )
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
        except (json.JSONDecodeError, TypeError) as exc:
            # Unexpected ruleset-evaluation shape; treat as no rulesets
            # active and let the classic enforce_admins check below decide.
            # Log so operators can spot schema drift.
            print(
                f"warning: BP-5 ruleset-evaluation shape unexpected for "
                f"{org}/{repo}@{branch}: {exc}",
                file=sys.stderr,
            )
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

    # Resolve every applies_to scope up front so SKIP and UNKNOWN verdicts are
    # recorded for the summary even when the scope gates no locally-run check.
    result.scopes = {
        scope: resolve_applicability(slug, catalog, scope)
        for scope in SCOPE_DEFINITIONS
    }

    api_verdict = result.scopes["api_repos"]
    if api_verdict.applicability is Applicability.UNKNOWN:
        # Unresolvable scope is not "not applicable". Mark the columns UNK so the
        # row cannot be mistaken for a clean skip, and carry the reason forward.
        for api_field in _API_RESULT_FIELDS:
            setattr(result, api_field, "UNK")
        result.notes.append(f"api_repos UNKNOWN: {api_verdict.reason}")
    elif api_verdict.applicability is Applicability.APPLIES:
        _apply_api_checks(result, org, repo, catalog)

    return result


def _apply_api_checks(result: RepoResult, org: str, repo: str, catalog: dict) -> None:
    """Evaluate API-001..005 for a repo already confirmed in ``api_repos`` scope.

    Args:
        result: The repo result to populate in place.
        org: GitHub organization name.
        repo: Repository name.
        catalog: Catalog mapping from :func:`load_catalog`.
    """
    branch = result.branch
    api_info = catalog.get(result.slug, {}).get("api") or {}

    # API-001: openapi.yaml present
    result.api_001_openapi_spec = (
        "PASS" if file_exists(org, repo, "docs/api/openapi.yaml", branch) else "FAIL"
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
            result.api_004_last_audited = (
                "PASS" if (today - audited_date).days <= 90 else "FAIL"
            )
        except ValueError:
            result.api_004_last_audited = "FAIL"

    # API-005: testStatus == "passing"
    # FAIL covers both "not yet audited" (None) and "failing"; matches API-004
    # behavior. New servesApi=true repos surface as FAIL until the openapi-
    # compliance-agent has run on them, which is intentional: the audit drives
    # completion of pending pipeline work.
    test_status = api_info.get("testStatus")
    result.api_005_test_status = "PASS" if test_status == "passing" else "FAIL"


# --------------------------------------------------------------------------- #
# Local-path auditor                                                          #
#                                                                             #
# These checks evaluate a single manifest check against a local repo          #
# directory (e.g. a regression fixture) using only file inspection, no        #
# GitHub API calls. Each returns (passed, detail). They mirror the manifest   #
# `verify` fields for the checks the auditor-regression corpus covers.        #
# --------------------------------------------------------------------------- #

REQUIRED_INTEGRATION_ID = 15368
_RENOVATE_PIN_RE = re.compile(r"^renovate/renovate:[\w.-]+@sha256:[a-f0-9]{64}$")


def _iter_required_status_checks(obj: object) -> Iterator[list[object]]:
    """Yield every ``required_status_checks`` list found in a ruleset document.

    Walks the JSON structure recursively so the check is robust to the exact
    nesting GitHub uses (``rules[].parameters.required_status_checks``).

    Args:
        obj: A decoded JSON value (dict, list, or scalar).

    Yields:
        Each ``required_status_checks`` list encountered, in document order.
    """
    if isinstance(obj, dict):
        for key, value in obj.items():
            if key == "required_status_checks" and isinstance(value, list):
                yield value
            else:
                yield from _iter_required_status_checks(value)
    elif isinstance(obj, list):
        for item in obj:
            yield from _iter_required_status_checks(item)


def local_found_001(root: Path) -> tuple[bool, str]:
    """FOUND-001: SECURITY.md present at the repo root."""
    present = (root / "SECURITY.md").is_file()
    return present, "SECURITY.md present" if present else "SECURITY.md missing"


def local_found_002(root: Path) -> tuple[bool, str]:
    """FOUND-002: CONTRIBUTING.md present at the repo root."""
    present = (root / "CONTRIBUTING.md").is_file()
    return present, "CONTRIBUTING.md present" if present else "CONTRIBUTING.md missing"


def local_ci_028(root: Path) -> tuple[bool, str]:
    """CI-028: every required_status_checks entry carries integration_id 15368.

    Scans ``docs/reference/org-rulesets/*.json``. With no ruleset files present
    the check is vacuously satisfied (there is nothing to mis-pin).
    """
    files = sorted((root / "docs" / "reference" / "org-rulesets").glob("*.json"))
    if not files:
        return True, "no org-ruleset files present; check vacuously satisfied"
    bad: list[str] = []
    for ruleset_file in files:
        try:
            data = json.loads(ruleset_file.read_text())
        except (json.JSONDecodeError, OSError) as exc:
            bad.append(f"{ruleset_file.name}: unreadable ({exc})")
            continue
        for entries in _iter_required_status_checks(data):
            for entry in entries:
                if not isinstance(entry, dict):
                    continue
                if entry.get("integration_id") != REQUIRED_INTEGRATION_ID:
                    ctx = entry.get("context", "<unknown>")
                    bad.append(
                        f"{ruleset_file.name}: '{ctx}' missing "
                        f"integration_id:{REQUIRED_INTEGRATION_ID}"
                    )
    if bad:
        return False, "; ".join(bad)
    return True, f"all entries pinned to integration_id:{REQUIRED_INTEGRATION_ID}"


def _workflow_files(root: Path) -> list[Path]:
    """Return all workflow files under ``.github/workflows`` (``.yml``/``.yaml``)."""
    wf_dir = root / ".github" / "workflows"
    return sorted([*wf_dir.glob("*.yml"), *wf_dir.glob("*.yaml")])


def local_ci_043(root: Path) -> tuple[bool, str]:
    """CI-043: no workflow combines a privileged trigger with code checkout.

    A ``pull_request_target`` or ``workflow_run`` trigger that also runs
    ``actions/checkout`` can execute untrusted PR code with elevated
    permissions. Any such workflow fails the check.
    """
    offenders: list[str] = []
    for workflow in _workflow_files(root):
        text = workflow.read_text()
        privileged = "pull_request_target" in text or "workflow_run" in text
        if privileged and "actions/checkout" in text:
            offenders.append(workflow.name)
    if offenders:
        return False, "privileged trigger + checkout in: " + ", ".join(offenders)
    return True, "no privileged-trigger workflow checks out untrusted code"


def local_ci_061(root: Path) -> tuple[bool, str]:
    """CI-061: the Renovate Docker image is digest-pinned, not a floating tag."""
    compose = root / "services" / "renovate" / "docker-compose.yml"
    if not compose.is_file():
        return False, "services/renovate/docker-compose.yml missing"
    image: str | None = None
    for line in compose.read_text().splitlines():
        match = re.search(r"image:\s*(\S+)", line)
        if match and "renovate/renovate" in match.group(1):
            image = match.group(1).strip("\"'")
            break
    if image is None:
        return False, "no renovate/renovate image: line found"
    if _RENOVATE_PIN_RE.match(image):
        return True, f"renovate image digest-pinned: {image}"
    return False, f"renovate image not digest-pinned: {image}"


def local_ci_018(root: Path) -> tuple[bool, str]:
    """CI-018: release.yml contains a SLSA provenance job."""
    release = root / ".github" / "workflows" / "release.yml"
    if not release.is_file():
        return False, ".github/workflows/release.yml missing"
    if "slsa-framework/slsa-github-generator" in release.read_text():
        return True, "SLSA provenance job present in release.yml"
    return False, "release.yml has no slsa-framework/slsa-github-generator job"


LOCAL_CHECKS: dict[str, Callable[[Path], tuple[bool, str]]] = {
    "FOUND-001": local_found_001,
    "FOUND-002": local_found_002,
    "CI-028": local_ci_028,
    "CI-043": local_ci_043,
    "CI-061": local_ci_061,
    "CI-018": local_ci_018,
}


def audit_local(path: Path, check_id: str) -> dict[str, str]:
    """Evaluate one manifest check against a local repo directory.

    Args:
        path: Path to the local repo root (e.g. a regression fixture).
        check_id: Manifest check ID; must be a key in ``LOCAL_CHECKS``.

    Returns:
        Dict with keys ``check_id``, ``path``, ``status`` ("pass"|"fail"),
        and ``detail``.

    Raises:
        KeyError: if ``check_id`` is not a locally-auditable check.
    """
    checker = LOCAL_CHECKS[check_id]
    passed, detail = checker(Path(path))
    return {
        "check_id": check_id,
        "path": str(path),
        "status": "pass" if passed else "fail",
        "detail": detail,
    }


def _run_local_audit(args: argparse.Namespace, parser: argparse.ArgumentParser) -> int:
    """Handle ``--local-path`` mode: audit one check and report the result.

    Args:
        args: Parsed CLI arguments (expects ``check_id`` and ``output``).
        parser: The argument parser, used for usage errors.

    Returns:
        Process exit code: 0 on PASS, 1 on FAIL, 2 on a usage/unknown-check
        error.
    """
    if not args.check_id:
        parser.error("--local-path requires --check-id")
    if args.check_id not in LOCAL_CHECKS:
        valid = ", ".join(sorted(LOCAL_CHECKS))
        msg = f"{args.check_id} is not locally auditable; valid: {valid}"
        if args.output == "json":
            print(
                json.dumps(
                    {
                        "check_id": args.check_id,
                        "path": args.local_path,
                        "status": "error",
                        "detail": msg,
                    }
                )
            )
        else:
            print(f"error: {msg}", file=sys.stderr)
        return 2
    result = audit_local(Path(args.local_path), args.check_id)
    if args.output == "json":
        print(json.dumps(result))
    else:
        print(f"{result['check_id']} {result['status'].upper()}: {result['detail']}")
    return 0 if result["status"] == "pass" else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Repo compliance sweep")
    parser.add_argument("--org", help="Limit to one org")
    parser.add_argument("--repo", help="Check a single repo (owner/repo)")
    parser.add_argument(
        "--local-path",
        help="Audit a local repo directory instead of live GitHub (needs --check-id)",
    )
    parser.add_argument(
        "--check-id",
        help="With --local-path, the single manifest check to evaluate",
    )
    parser.add_argument(
        "--output",
        choices=["table", "json"],
        default="table",
        help="Output format for --local-path mode (default: table)",
    )
    args = parser.parse_args()

    if args.local_path:
        return _run_local_audit(args, parser)

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

    # Applicability summary: every skipped domain is printed, never silent.
    scope_checks = load_manifest_scope_checks()
    for line in render_scope_summary(results, scope_checks):
        print(line)

    # Fleet-level reach assertion: a scope no repo satisfies is a dead domain.
    # Only meaningful across a full sweep; a single-repo run is not a fleet, and
    # asserting reach against one repo would flag every scope it is out of.
    scope_problems: list[str] = []
    if not args.repo:
        scope_problems = assert_scopes_reachable(results, scope_checks)
        for problem in scope_problems:
            print(problem, file=sys.stderr)

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
    unknown_scopes = sum(
        1
        for r in results
        if any(v.applicability is Applicability.UNKNOWN for v in r.scopes.values())
    )
    print(
        f"\n{pass_count}/{len(results)} repos fully compliant  |  {failures} with failures"
    )
    print(
        f"{unknown_scopes}/{len(results)} repos have at least one UNKNOWN applies_to "
        f"scope  |  {len(scope_problems)} unreachable scope(s)\n"
    )
    print(
        "Checks: CI-020=renovate.json present, CI-021=no dependabot.yml conflict, "
        "BP-4=signed commits, BP-5=enforce admins, "
        "API-001..005=OpenAPI/Postman compliance (api_repos only)"
    )

    # An unreachable scope fails the sweep. A domain that is never evaluated is
    # not a passing audit, and exiting 0 on one is how the MkDocs gap survived.
    return 1 if failures or scope_problems else 0


if __name__ == "__main__":
    sys.exit(main())
