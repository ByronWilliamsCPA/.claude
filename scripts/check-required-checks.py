#!/usr/bin/env python3
"""Validate manifest required_checks against workflow jobs and branch protection.

Backs the CI-022/023/024 standards manifest checks. Reads the manifest's
required_checks field, the local repo's .github/workflows/*.yml files, the
reusable-workflow-jobs registry, and (when --check-bp is passed) the branch
protection contexts via gh api. Emits JSON findings to stdout.

Exit codes:
    0  validator ran cleanly, no findings
    1  validator ran cleanly, findings emitted to stdout
    2  configuration error (missing/malformed manifest, missing flag combo,
       branch protection fetch failed). Findings JSON is still emitted.
"""

# #CRITICAL: external resource dependency
# This module shells out to the gh CLI (fetch_classic_protection_contexts) and
# parses YAML from disk. Both surfaces are subject to upstream behavior changes
# (gh schema, ruamel.yaml strictness). #VERIFY: when upgrading either tool,
# rerun the integration test suite and the real-data dry-run against the
# 7-repo catalog (see compliance-retrospectives/2026-05-08-required-checks-rollout.md).

from __future__ import annotations

import argparse
import itertools
import json
import re
import subprocess  # nosec B404 -- intentional gh CLI invocation; tracked: PR #74 Critical-tier review.
import sys
from dataclasses import asdict, dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Any, TypeAlias

from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

# #ASSUME: GitHub matrix axis names use [A-Za-z0-9_.-] only.
# Real workflows commonly use hyphenated names (python-version, node-version);
# also dotted names appear (build.os). Underscores are also valid.
# #VERIFY: if a workflow author uses other punctuation in axis names, the
# regex below will not interpolate them and CI-022 will emit raw template
# strings.
_MATRIX_VAR = re.compile(r"\$\{\{\s*matrix\.([\w.-]+)\s*\}\}")

_UNREGISTERED_PREFIX = "__UNREGISTERED__:"

_GH_TIMEOUT_SECONDS = 30


class GhCliError(RuntimeError):
    """Base error for any failure invoking the gh CLI."""


class BranchProtectionFetchError(GhCliError):
    """Raised when branch protection contexts cannot be fetched reliably.

    Distinct from `[]` (which means the branch has zero required contexts).
    Callers should surface this as a Critical finding; treating an opaque
    failure as an empty contexts list silently floods CI-023 with false
    positives.
    """


@dataclass(frozen=True)
class Finding:
    check_id: str
    severity: str
    message: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# Exactly one element is non-None: date on parse success, Finding on failure.
_LastVerifiedResult: TypeAlias = tuple[date, None] | tuple[None, Finding]


def _yaml_safe() -> YAML:
    """Return a fresh ruamel YAML safe loader.

    A new instance per call avoids state accumulation in the loader's
    resolver/constructor caches that can interact poorly with concurrent
    test execution (pytest-xdist) and prevents subtle parse-result
    determinism issues.
    """
    return YAML(typ="safe")


def _expand_matrix_combinations(
    matrix: dict[str, list[Any]],
) -> list[dict[str, Any]]:
    """Cartesian product of matrix axes. Returns a list of dicts."""
    keys = list(matrix.keys())
    value_lists = [matrix[k] for k in keys]
    return [
        dict(zip(keys, combo, strict=False))
        for combo in itertools.product(*value_lists)
    ]


def _interpolate_matrix(template: str, combo: dict[str, Any]) -> str:
    """Replace ${{ matrix.<key> }} with the corresponding value from combo."""

    def _sub(match: re.Match[str]) -> str:
        key = match.group(1)
        return str(combo.get(key, match.group(0)))

    return _MATRIX_VAR.sub(_sub, template)


def _job_simple_axes(job: dict[str, Any]) -> dict[str, list[Any]]:
    """Return the matrix's simple axes (excluding include/exclude).

    Returns an empty dict when the job has no matrix or only include/exclude
    entries.
    """
    strategy = job.get("strategy") or {}
    if not isinstance(strategy, dict):
        return {}
    matrix = strategy.get("matrix")
    if not isinstance(matrix, dict) or not matrix:
        return {}
    return {
        k: v
        for k, v in matrix.items()
        if isinstance(v, list) and k not in ("include", "exclude")
    }


def _produced_for_job(
    job_key: str,
    job: dict[str, Any],
    registry: dict[str, Any],
) -> set[str]:
    """Return the set of check names this single job produces.

    GitHub check-name rules:
    - Inline jobs (no `uses:` field): the check name is exactly the job's
      `name:` field (or job key if `name:` is absent). The workflow-level
      `name:` is NOT prepended by GitHub for inline jobs.
    - Reusable-workflow caller jobs (`uses:` field): the check name is
      `{caller_job_name} / {reusable_internal_check_name}`. The registry
      stores the reusable workflow's UNPREFIXED check names (so the same
      registry entry is reusable across repos with different caller-job
      names); the validator applies the caller-job-name prefix here at
      compare time. For unregistered reusable workflows the validator emits
      an UNREGISTERED sentinel.
    """
    uses = job.get("uses")
    if isinstance(uses, str) and ".github/workflows/" in uses:
        workflow_path = uses.split("@", 1)[0]
        entry = registry.get(workflow_path)
        if entry and isinstance(entry.get("produces"), list):
            caller_prefix = job.get("name") or job_key
            return {f"{caller_prefix} / {name}" for name in entry["produces"]}
        return {f"{_UNREGISTERED_PREFIX}{workflow_path}"}
    # Inline job: GitHub uses the job's `name:` (or key) verbatim -- no
    # workflow-level prefix.
    job_label_template = job.get("name") or job_key
    simple_axes = _job_simple_axes(job)
    if not simple_axes:
        # No matrix, or include-only/exclude-only matrix: emit the raw label
        # without interpolation. include-only matrices are a documented
        # limitation; the validator will likely flag them as CI-022 findings,
        # signaling the workflow needs to be modeled in the registry.
        return {job_label_template}
    return {
        _interpolate_matrix(job_label_template, combo)
        for combo in _expand_matrix_combinations(simple_axes)
    }


def extract_produced_check_names(
    workflow_yaml: str,
    registry: dict[str, Any],
) -> set[str]:
    """Return the set of GitHub check names a workflow produces.

    Args:
        workflow_yaml: Raw YAML contents of a single workflow file.
        registry: Reusable-workflow registry (path -> {produces: [names]}).
            Used to resolve jobs with a `uses:` field pointing to a reusable
            workflow. Pass an empty dict for locally-defined workflows.

    Returns:
        Set of check names. For matrix jobs the set is expanded across
        every matrix combination; the job's `name:` field is treated as
        a template and any `${{ matrix.<key> }}` references are
        interpolated with the matrix values.

        Inline jobs use the job `name:` verbatim -- GitHub does NOT
        prepend the workflow-level `name:` for inline jobs. Reusable-
        workflow caller jobs apply a `{caller_job_name} / ` prefix to
        each registry-stored unprefixed check name; the registry is
        therefore portable across repos with different caller-job names.

        Limitations:
        - Only direct `${{ matrix.<key> }}` references are interpolated;
          complex template expressions (functions, fromJSON, conditionals)
          are not. Workflows with complex matrix templates should be
          modeled in the registry instead of parsed from source.
        - Jobs that rely on GitHub's automatic parenthetical suffix
          (job `name:` with NO matrix variables but a matrix strategy)
          are not currently supported. Use explicit `${{ matrix.x }}`
          references in the job name to make this validator handle them.
        - Matrices with ONLY `include` (and/or `exclude`) entries, with no
          top-level axes, cannot be expanded; the validator emits the
          raw `name:` template without interpolation. Such workflows
          should be modeled in the registry instead of parsed from source.
    """
    doc = _yaml_safe().load(workflow_yaml)
    if not isinstance(doc, dict):
        return set()
    jobs = doc.get("jobs", {}) or {}
    if not isinstance(jobs, dict):
        return set()
    produced: set[str] = set()
    for job_key, job in jobs.items():
        if not isinstance(job, dict):
            continue
        produced |= _produced_for_job(job_key, job, registry)
    return produced


def diff_required_vs_produced(
    required: set[str],
    produced: set[str],
    required_checks_meta: dict[str, dict[str, Any]],
) -> list[Finding]:
    """CI-022: every required check has a producing workflow job."""
    unregistered = {p for p in produced if p.startswith(_UNREGISTERED_PREFIX)}
    findings: list[Finding] = [
        Finding(
            check_id="CI-022",
            severity="critical",
            message=(
                f"Reusable workflow '{path.removeprefix(_UNREGISTERED_PREFIX)}' "
                f"is referenced but missing from "
                f"docs/reusable-workflow-jobs.yaml; add it or remove the reference."
            ),
        )
        for path in sorted(unregistered)
    ]
    cleaned_produced = produced - unregistered
    findings.extend(
        Finding(
            check_id="CI-022",
            severity="critical",
            message=(
                f"Required check '{name}' has no producing workflow job. "
                f"Manifest expects it to come from "
                f"{required_checks_meta.get(name, {}).get('produced_by', '<unspecified>')}."
            ),
        )
        for name in sorted(required - cleaned_produced)
    )
    return findings


def diff_required_vs_effective(
    required: set[str],
    effective: set[str],
    provenance: dict[str, list[str]],
) -> list[Finding]:
    """Diff manifest required-checks set vs effective protection contexts.

    Emits one Critical Finding per missing or extra context, with provenance
    appended to the message so operators know which source needs patching.
    Also emits a Critical Finding for any source that failed to load (per
    "<source>:error" key in provenance).

    Args:
        required: Manifest required-checks set.
        effective: Effective contexts present in protection (union of sources).
        provenance: Map of source-id to contexts contributed; "<source>:error"
            keys carry an error message instead of a contexts list.

    Returns:
        List of Finding objects (one per missing context, one per extra context,
        one per failed source).
    """
    sources = (
        ", ".join(
            f"{k}={v}"
            for k, v in sorted(provenance.items())
            if not k.endswith(":error")
        )
        or "(no protection sources found)"
    )

    missing = required - effective
    extra = effective - required

    findings: list[Finding] = [
        Finding(
            check_id="CI-023",
            severity="critical",
            message=(
                f"Required check '{name}' is missing from effective protection. "
                f"Sources: {sources}"
            ),
        )
        for name in sorted(missing)
    ]
    findings.extend(
        Finding(
            check_id="CI-023",
            severity="critical",
            message=(
                f"Extra context '{name}' is enforced but not in required_checks. "
                f"Sources: {sources}"
            ),
        )
        for name in sorted(extra)
    )
    findings.extend(
        Finding(
            check_id="CI-023",
            severity="critical",
            message=(
                f"Could not read protection source '{err_key.split(':')[0]}': "
                f"{provenance[err_key][0]}"
            ),
        )
        for err_key in ("classic:error", "rulesets:error")
        if err_key in provenance
    )
    return findings


def _parse_last_verified(path: str, entry: dict[str, Any]) -> _LastVerifiedResult:
    """Parse the last_verified field from a registry entry.

    Args:
        path: Registry key (workflow path string) used in error messages.
        entry: Registry entry dict to inspect.

    Returns:
        A _LastVerifiedResult: (date, None) on success, or (None, Finding)
        when the field is missing or unparseable.
    """
    last_verified_raw = entry.get("last_verified")
    if isinstance(last_verified_raw, date):
        return last_verified_raw, None
    if isinstance(last_verified_raw, str):
        try:
            return date.fromisoformat(last_verified_raw), None
        except ValueError:
            return None, Finding(
                check_id="CI-024",
                severity="important",
                message=(
                    f"Registry entry {path} has unparseable "
                    f"last_verified value: {last_verified_raw!r}"
                ),
            )
    return None, Finding(
        check_id="CI-024",
        severity="important",
        message=f"Registry entry {path} missing last_verified field.",
    )


def check_registry_freshness(
    registry: dict[str, dict[str, Any]],
    today: date,
    max_age_days: int = 90,
) -> list[Finding]:
    """CI-024: every registry entry has last_verified within max_age_days.

    Args:
        registry: Mapping from workflow path to entry dict.
        today: Reference date for age calculation.
        max_age_days: Maximum allowed age in days before a finding is emitted.

    Returns:
        List of findings for missing, unparseable, or stale last_verified fields.
    """
    findings: list[Finding] = []
    cutoff = today - timedelta(days=max_age_days)
    for path, entry in sorted(registry.items()):
        last_verified, parse_finding = _parse_last_verified(path, entry)
        if parse_finding is not None:
            findings.append(parse_finding)
            continue
        # `last_verified is not None` is always True here: the _LastVerifiedResult
        # invariant guarantees the (date, None) branch when parse_finding is None.
        # The guard exists because BasedPyright narrows on the second element and
        # does not deduce last_verified: date from parse_finding being None.
        if last_verified is not None and last_verified < cutoff:
            findings.append(
                Finding(
                    check_id="CI-024",
                    severity="important",
                    message=(
                        f"Registry entry {path} last_verified {last_verified} "
                        f"is older than {max_age_days} days; re-verify."
                    ),
                )
            )
    return findings


def _validate_and_include_entry(
    idx: int,
    entry: Any,
    repo_type: str,
) -> tuple[str, dict[str, Any]] | None:
    """Validate a single required_checks entry and return it if applicable.

    Args:
        idx: Zero-based index of the entry in the required_checks list (for error messages).
        entry: Raw entry value from the manifest (expected to be a dict).
        repo_type: Repository type filter; empty string means include all entries.

    Returns:
        Tuple of (name, entry) if the entry is valid and applies to repo_type,
        or None if the entry is filtered out by repo_type.

    Raises:
        ValueError: If entry is not a mapping, or its name field is missing or empty.
    """
    if not isinstance(entry, dict):
        raise ValueError(
            f"required_checks[{idx}] must be a mapping, got {type(entry).__name__}"
        )
    name = entry.get("name")
    if not isinstance(name, str) or not name.strip():
        raise ValueError(
            f"required_checks[{idx}] missing or empty 'name' field: {entry!r}"
        )
    applies_to = entry.get("applies_to_types")
    if repo_type and applies_to is not None and repo_type not in applies_to:
        return None
    return name, entry


def load_required_checks(
    manifest_path: Path,
    repo_type: str = "",
) -> tuple[set[str], dict[str, dict[str, Any]]]:
    """Parse manifest required_checks entries, optionally filtered by repo type.

    Args:
        manifest_path: Path to docs/standards-manifest.yaml.
        repo_type: Repository type string (e.g. "python-package", "docs-only").
            When non-empty, entries whose ``applies_to_types`` list does not
            include this type are silently excluded.  Entries without an
            ``applies_to_types`` field apply to all repo types.

    Returns:
        Tuple of (set of required check names, mapping from check name to
        the full entry dict).

    Raises:
        FileNotFoundError: manifest_path does not exist.
        ValueError: manifest is malformed or an entry lacks a `name` field.
        ruamel.yaml.YAMLError: manifest is not parseable as YAML.
    """
    if not manifest_path.exists():
        raise FileNotFoundError(f"Manifest not found: {manifest_path}")
    doc = _yaml_safe().load(manifest_path.read_text(encoding="utf-8"))
    if doc is None:
        return set(), {}
    if not isinstance(doc, dict):
        raise ValueError(
            f"Manifest {manifest_path} top-level must be a mapping, got {type(doc).__name__}"
        )
    entries = doc.get("required_checks", []) or []
    if not isinstance(entries, list):
        raise ValueError(
            f"Manifest required_checks must be a list, got {type(entries).__name__}"
        )
    names: set[str] = set()
    meta: dict[str, dict[str, Any]] = {}
    for idx, entry in enumerate(entries):
        result = _validate_and_include_entry(idx, entry, repo_type)
        if result is not None:
            name, validated_entry = result
            names.add(name)
            meta[name] = validated_entry
    return names, meta


def load_registry(registry_path: Path) -> dict[str, dict[str, Any]]:
    """Load the reusable-workflow registry YAML.

    Returns an empty dict for missing or empty files. Raises ValueError if
    the file exists but is structurally not a mapping.
    """
    if not registry_path.exists():
        return {}
    doc = _yaml_safe().load(registry_path.read_text(encoding="utf-8"))
    if doc is None:
        return {}
    if not isinstance(doc, dict):
        raise ValueError(
            f"Registry {registry_path} top-level must be a mapping, got {type(doc).__name__}"
        )
    return doc


def _safe_extract(path: Path, registry: dict[str, Any]) -> set[str]:
    """Extract check names from a workflow file.

    Returns an empty set on YAML or filesystem read errors after logging to
    stderr. Re-raises programmer-error types (TypeError, AttributeError) so
    bugs in the parser surface during testing.

    A workflow file that cannot be parsed cannot run in CI either, so its
    check names are moot for CI-022 purposes.
    """
    try:
        return extract_produced_check_names(path.read_text(), registry)
    except (YAMLError, OSError, UnicodeDecodeError) as exc:
        print(
            f"Warning: could not parse {path}: {exc.__class__.__name__}: {exc}",
            file=sys.stderr,
        )
        return set()


def scan_workflow_dir(
    workflow_dir: Path,
    registry: dict[str, dict[str, Any]],
) -> set[str]:
    """Scan a directory for *.yml/*.yaml workflow files and aggregate check names.

    Deduplicates files on case-insensitive filesystems by collecting paths
    into a set keyed on the resolved path before iteration.
    """
    produced: set[str] = set()
    if not workflow_dir.is_dir():
        return produced
    paths = {
        p.resolve()
        for p in workflow_dir.iterdir()
        if p.is_file() and p.suffix.lower() in (".yml", ".yaml")
    }
    for path in sorted(paths):
        produced |= _safe_extract(path, registry)
    return produced


def fetch_classic_protection_contexts(
    repo_slug: str,
    branch: str = "main",
    timeout: int = _GH_TIMEOUT_SECONDS,
) -> list[str]:
    """Fetch branch protection required contexts via the gh CLI.

    Args:
        repo_slug: GitHub `owner/repo` slug.
        branch: Branch name (default: main).
        timeout: Per-call timeout in seconds.

    Returns:
        List of required status check context names. Empty list means the
        branch protection rule exists but has zero required contexts (or
        the rule defines `required_status_checks: null`, which gh's --jq
        emits as the JSON literal `null`).

    Raises:
        BranchProtectionFetchError: gh CLI exited non-zero, timed out,
            returned malformed JSON, or returned a non-list/non-null value.
            Distinct from "branch has zero contexts" so the caller can emit
            a dedicated finding instead of silently treating fetch failure
            as drift.
    """
    try:
        result = subprocess.run(  # nosec B603 B607
            [
                "gh",
                "api",
                f"repos/{repo_slug}/branches/{branch}/protection",
                "--jq",
                ".required_status_checks.contexts",
            ],
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        raise BranchProtectionFetchError(
            f"gh API timed out after {timeout}s for {repo_slug}@{branch}"
        ) from exc
    except FileNotFoundError as exc:
        raise BranchProtectionFetchError(
            "gh CLI not found on PATH; install gh or run without --check-bp"
        ) from exc

    if result.returncode != 0:
        stderr_lower = result.stderr.lower()
        # 404 indicates the branch has no classic protection (e.g., the
        # repo has migrated to rulesets-only). That is "no classic
        # contexts," not a fetch failure; return [] so audit modes that
        # combine classic+rulesets do not mis-report it as Critical drift.
        if "404" in stderr_lower or "not protected" in stderr_lower:
            return []
        raise BranchProtectionFetchError(
            f"gh API failed for {repo_slug}@{branch} "
            f"(exit {result.returncode}): {result.stderr.strip() or result.stdout.strip()}"
        )

    stdout = result.stdout.strip()
    if not stdout:
        return []
    try:
        parsed = json.loads(stdout)
    except json.JSONDecodeError as exc:
        raise BranchProtectionFetchError(
            f"gh API returned non-JSON output for {repo_slug}@{branch}: "
            f"{stdout[:200]!r}"
        ) from exc

    if parsed is None:
        return []
    if not isinstance(parsed, list):
        raise BranchProtectionFetchError(
            f"gh API returned unexpected type ({type(parsed).__name__}) "
            f"for {repo_slug}@{branch}; expected list or null"
        )
    return [str(item) for item in parsed]


def _run_gh(args: list[str], timeout: int) -> tuple[str, str, int]:
    """Invoke the gh CLI with the given args and return (stdout, stderr, returncode).

    Args:
        args: Command-line arguments passed to the gh CLI (excluding the
            leading "gh" token itself).
        timeout: Maximum seconds to wait for the process to complete.

    Returns:
        A 3-tuple of (stdout, stderr, returncode). stdout and stderr are
        decoded text strings. returncode is the process exit code.

    Raises:
        GhCliError: The gh binary was not found on PATH or the process timed
            out. Callers should catch this or let it propagate as a
            configuration error.
    """
    try:
        result = subprocess.run(  # nosec B603 B607
            ["gh", *args],
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        raise GhCliError(f"gh CLI timed out after {timeout}s") from exc
    except FileNotFoundError as exc:
        raise GhCliError(
            "gh CLI not found on PATH; install gh or run without ruleset checks"
        ) from exc
    return result.stdout, result.stderr, result.returncode


class RulesetFetchError(GhCliError):
    """Raised when ruleset evaluation cannot be fetched from gh."""


def fetch_ruleset_contexts(
    repo_slug: str,
    branch: str = "main",
    timeout: int = _GH_TIMEOUT_SECONDS,
) -> tuple[set[str], dict[str, list[str]]]:
    """Return (contexts, provenance) from all rulesets targeting this branch.

    provenance maps "<source_type>:<source>/<id>" to the contexts that
    ruleset contributes. source_type is "Repository" or "Organization".

    Args:
        repo_slug: GitHub "owner/repo" slug.
        branch: Branch name to evaluate rulesets against (default: main).
        timeout: Maximum seconds to wait for the gh CLI call.

    Returns:
        A 2-tuple of (contexts, provenance) where contexts is the union of
        all required-status-check context names across every ruleset and
        provenance maps each ruleset key to the list of contexts it
        contributes.

    Raises:
        RulesetFetchError: gh CLI exited non-zero, timed out, was not found
            on PATH, or returned malformed JSON.
    """
    args = ["api", f"repos/{repo_slug}/rules/branches/{branch}"]
    try:
        out, err, rc = _run_gh(args, timeout)
    except GhCliError as exc:
        raise RulesetFetchError(str(exc)) from exc
    if rc != 0:
        raise RulesetFetchError(
            f"Could not fetch ruleset evaluation: {err.strip() or out.strip()}"
        )
    try:
        rules = json.loads(out) if out.strip() else []
    except json.JSONDecodeError as exc:
        raise RulesetFetchError(f"Malformed ruleset JSON: {exc}") from exc

    contexts: set[str] = set()
    provenance: dict[str, list[str]] = {}
    for rule in rules:
        if rule.get("type") != "required_status_checks":
            continue
        params = rule.get("parameters", {}) or {}
        rule_contexts = [
            entry.get("context", "")
            for entry in params.get("required_status_checks", [])
            if entry.get("context")
        ]
        source_type = rule.get("ruleset_source_type", "Unknown")
        source = rule.get("ruleset_source", "?")
        ruleset_id = rule.get("ruleset_id", "?")
        key = f"{source_type}:{source}/{ruleset_id}"
        provenance.setdefault(key, []).extend(rule_contexts)
        contexts.update(rule_contexts)
    return contexts, provenance


def fetch_effective_required_contexts(
    repo_slug: str,
    branch: str,
    source_mode: str,
) -> tuple[set[str], dict[str, list[str]]]:
    """Return effective required-checks set and provenance per source_mode.

    Args:
        repo_slug: GitHub owner/repo slug.
        branch: Branch name.
        source_mode: One of "classic", "rulesets", "union".

    Returns:
        Tuple of (effective_contexts, provenance). Provenance always
        includes a "<source>:error" key for any source that raised, so
        callers can emit a Critical finding for the failed source while
        still validating what they got.

    Raises:
        ValueError: If source_mode is not one of the allowed values.
        BranchProtectionFetchError: If source_mode is "classic" and the
            classic fetcher fails.
        RulesetFetchError: If source_mode is "rulesets" and the ruleset
            fetcher fails.
    """
    if source_mode not in {"classic", "rulesets", "union"}:
        raise ValueError(f"Invalid source_mode: {source_mode!r}")

    contexts: set[str] = set()
    provenance: dict[str, list[str]] = {}

    if source_mode in {"classic", "union"}:
        try:
            classic = list(fetch_classic_protection_contexts(repo_slug, branch))
            contexts.update(classic)
            provenance["classic"] = classic
        except BranchProtectionFetchError as exc:
            if source_mode == "classic":
                raise
            provenance["classic:error"] = [str(exc)]

    if source_mode in {"rulesets", "union"}:
        try:
            rs_contexts, rs_prov = fetch_ruleset_contexts(repo_slug, branch)
            contexts.update(rs_contexts)
            provenance.update(rs_prov)
        except RulesetFetchError as exc:
            if source_mode == "rulesets":
                raise
            provenance["rulesets:error"] = [str(exc)]

    return contexts, provenance


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-path", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--registry", type=Path, required=True)
    parser.add_argument("--repo-slug", default="")
    parser.add_argument(
        "--branch",
        default="main",
        help="Branch to check protection on (default: main)",
    )
    parser.add_argument(
        "--check-bp",
        action="store_true",
        help="Fetch and validate branch protection contexts (requires --repo-slug)",
    )
    parser.add_argument(
        "--source",
        choices=("classic", "rulesets", "union"),
        default="union",
        help="Which protection source to validate against (default: union).",
    )
    parser.add_argument(
        "--repo-type",
        default="",
        help=(
            "Repository type (e.g. python-package, docs-only). "
            "When set, required_checks entries whose applies_to_types list does "
            "not include this type are excluded from evaluation."
        ),
    )
    parser.add_argument(
        "--today",
        default=None,
        type=date.fromisoformat,
        help="Override today's date (YYYY-MM-DD) for testing",
    )
    args = parser.parse_args(argv)
    if args.check_bp and not args.repo_slug:
        parser.error("--check-bp requires --repo-slug")
    return args


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)

    try:
        required, meta = load_required_checks(args.manifest, repo_type=args.repo_type)
        registry = load_registry(args.registry)
    except (FileNotFoundError, ValueError, YAMLError) as exc:
        print(f"Error loading manifest or registry: {exc}", file=sys.stderr)
        return 2

    findings: list[Finding] = []

    produced = scan_workflow_dir(args.repo_path / ".github" / "workflows", registry)
    findings += diff_required_vs_produced(required, produced, meta)

    bp_failure_exit = 0
    if args.check_bp:
        try:
            effective, provenance = fetch_effective_required_contexts(
                args.repo_slug, args.branch, args.source
            )
        except (BranchProtectionFetchError, RulesetFetchError) as exc:
            findings.append(
                Finding(
                    check_id="CI-023",
                    severity="critical",
                    message=(
                        f"Could not fetch branch protection contexts: {exc}. "
                        f"CI-023 was not validated; treat with caution."
                    ),
                )
            )
            bp_failure_exit = 2
        else:
            findings += diff_required_vs_effective(required, effective, provenance)

    today_value = args.today if args.today is not None else date.today()
    findings += check_registry_freshness(registry, today_value)

    print(json.dumps([f.to_dict() for f in findings], indent=2))
    if bp_failure_exit:
        return bp_failure_exit
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
