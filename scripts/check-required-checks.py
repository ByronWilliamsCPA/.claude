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
# This module shells out to the gh CLI (fetch_branch_protection_contexts) and
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
from typing import Any

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


class BranchProtectionFetchError(Exception):
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


def diff_required_vs_branch_protection(
    required: set[str],
    contexts: list[str],
) -> list[Finding]:
    """CI-023: branch protection contexts equal required_checks set exactly."""
    actual = set(contexts)
    findings: list[Finding] = [
        Finding(
            check_id="CI-023",
            severity="critical",
            message=(
                f"Required check '{name}' missing from branch protection contexts."
            ),
        )
        for name in sorted(required - actual)
    ]
    findings.extend(
        Finding(
            check_id="CI-023",
            severity="critical",
            message=(
                f"Branch protection requires '{name}' but manifest does "
                f"not list it as a required check."
            ),
        )
        for name in sorted(actual - required)
    )
    return findings


def check_registry_freshness(
    registry: dict[str, dict[str, Any]],
    today: date,
    max_age_days: int = 90,
) -> list[Finding]:
    """CI-024: every registry entry has last_verified within max_age_days."""
    findings: list[Finding] = []
    cutoff = today - timedelta(days=max_age_days)
    for path, entry in sorted(registry.items()):
        last_verified_raw = entry.get("last_verified")
        if isinstance(last_verified_raw, date):
            last_verified = last_verified_raw
        elif isinstance(last_verified_raw, str):
            try:
                last_verified = date.fromisoformat(last_verified_raw)
            except ValueError:
                findings.append(
                    Finding(
                        check_id="CI-024",
                        severity="important",
                        message=(
                            f"Registry entry {path} has unparseable "
                            f"last_verified value: {last_verified_raw!r}"
                        ),
                    )
                )
                continue
        else:
            findings.append(
                Finding(
                    check_id="CI-024",
                    severity="important",
                    message=f"Registry entry {path} missing last_verified field.",
                )
            )
            continue
        if last_verified < cutoff:
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


def load_required_checks(
    manifest_path: Path,
) -> tuple[set[str], dict[str, dict[str, Any]]]:
    """Parse manifest required_checks entries.

    Args:
        manifest_path: Path to docs/standards-manifest.yaml.

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
    doc = _yaml_safe().load(manifest_path.read_text())
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
        if not isinstance(entry, dict):
            raise ValueError(
                f"required_checks[{idx}] must be a mapping, got {type(entry).__name__}"
            )
        name = entry.get("name")
        if not isinstance(name, str) or not name.strip():
            raise ValueError(
                f"required_checks[{idx}] missing or empty 'name' field: {entry!r}"
            )
        names.add(name)
        meta[name] = entry
    return names, meta


def load_registry(registry_path: Path) -> dict[str, dict[str, Any]]:
    """Load the reusable-workflow registry YAML.

    Returns an empty dict for missing or empty files. Raises ValueError if
    the file exists but is structurally not a mapping.
    """
    if not registry_path.exists():
        return {}
    doc = _yaml_safe().load(registry_path.read_text())
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


def fetch_branch_protection_contexts(
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
        result = subprocess.run(  # nosec B603 B607  # noqa: S603 -- list args, shell=False; tracked: PR #74.
            [  # noqa: S607 -- gh resolved via PATH; tracked: PR #74.
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
        "--today",
        default="",
        help="Override today's date (YYYY-MM-DD) for testing",
    )
    args = parser.parse_args(argv)
    if args.check_bp and not args.repo_slug:
        parser.error("--check-bp requires --repo-slug")
    return args


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)

    try:
        required, meta = load_required_checks(args.manifest)
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
            contexts = fetch_branch_protection_contexts(
                args.repo_slug, branch=args.branch
            )
        except BranchProtectionFetchError as exc:
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
            findings += diff_required_vs_branch_protection(required, contexts)

    today_value = (
        date.fromisoformat(args.today) if args.today else date.today()  # noqa: DTZ011 -- local TZ acceptable for 90-day cutoff; tracked: PR #74.
    )
    findings += check_registry_freshness(registry, today_value)

    print(json.dumps([f.to_dict() for f in findings], indent=2))
    if bp_failure_exit:
        return bp_failure_exit
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
