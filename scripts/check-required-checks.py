#!/usr/bin/env python3
"""Validate manifest required_checks against workflow jobs and branch protection.

Backs the CI-022/023/024 standards manifest checks. Reads the manifest's
required_checks field, the local repo's .github/workflows/*.yml files, the
reusable-workflow-jobs registry, and (when --check-bp is passed) the branch
protection contexts via gh api. Emits JSON findings to stdout.
"""

from __future__ import annotations

import argparse
import itertools
import json
import re
import subprocess  # nosec B404 -- intentional gh CLI invocation
import sys
from dataclasses import asdict, dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML

_MATRIX_VAR = re.compile(r"\$\{\{\s*matrix\.(\w+)\s*\}\}")

_UNREGISTERED_PREFIX = "__UNREGISTERED__:"


@dataclass(frozen=True)
class Finding:
    check_id: str
    severity: str
    message: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


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
    - Reusable-workflow caller jobs (`uses:` field): the check names come from
      the reusable workflow's jobs, prefixed by the calling job's name.
      These are resolved via the registry (which stores the fully-qualified
      check names including the caller-job prefix). For unregistered reusable
      workflows the validator emits an UNREGISTERED sentinel.
    """
    uses = job.get("uses")
    if isinstance(uses, str) and ".github/workflows/" in uses:
        workflow_path = uses.split("@", 1)[0]
        entry = registry.get(workflow_path)
        if entry and isinstance(entry.get("produces"), list):
            return {str(name) for name in entry["produces"]}
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


_yaml = YAML(typ="safe")


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
        prepend the workflow-level `name:` for inline jobs. Only
        reusable-workflow caller jobs get a caller-job-name prefix, which
        is already baked into the registry entries.

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
    doc = _yaml.load(workflow_yaml) or {}
    jobs = doc.get("jobs", {}) or {}
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
    doc = _yaml.load(manifest_path.read_text()) or {}
    entries = doc.get("required_checks", []) or []
    names = {e["name"] for e in entries}
    meta = {e["name"]: e for e in entries}
    return names, meta


def load_registry(registry_path: Path) -> dict[str, dict[str, Any]]:
    if not registry_path.exists():
        return {}
    return _yaml.load(registry_path.read_text()) or {}


def _safe_extract(path: Path, registry: dict[str, Any]) -> set[str]:
    """Extract check names from a workflow file, returning empty set on parse error."""
    try:
        return extract_produced_check_names(path.read_text(), registry)
    except Exception:
        # Malformed YAML is skipped; the file cannot be analysed but it will
        # not crash the validator. A workflow with invalid YAML cannot run in
        # CI anyway, so its check names are moot.
        print(f"Warning: could not parse {path} as YAML; skipping.", file=sys.stderr)
        return set()


def scan_workflow_dir(
    workflow_dir: Path,
    registry: dict[str, dict[str, Any]],
) -> set[str]:
    produced: set[str] = set()
    if not workflow_dir.is_dir():
        return produced
    paths = sorted(list(workflow_dir.glob("*.yml")) + list(workflow_dir.glob("*.yaml")))
    for path in paths:
        produced |= _safe_extract(path, registry)
    return produced


def fetch_branch_protection_contexts(repo_slug: str, branch: str = "main") -> list[str]:
    result = subprocess.run(  # nosec B603 B607 # noqa: S603
        [  # noqa: S607
            "gh",
            "api",
            f"repos/{repo_slug}/branches/{branch}/protection",
            "--jq",
            ".required_status_checks.contexts",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return []
    parsed = json.loads(result.stdout) if result.stdout.strip() else []
    return parsed or []


def main(argv: list[str] | None = None) -> int:
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
        help="Fetch and validate branch protection contexts",
    )
    parser.add_argument(
        "--today",
        default="",
        help="Override today's date (YYYY-MM-DD) for testing",
    )
    args = parser.parse_args(argv)

    try:
        required, meta = load_required_checks(args.manifest)
        registry = load_registry(args.registry)
    except (FileNotFoundError, KeyError) as exc:
        print(f"Error loading manifest or registry: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:
        print(f"Error parsing manifest or registry: {exc}", file=sys.stderr)
        return 2

    produced = scan_workflow_dir(args.repo_path / ".github" / "workflows", registry)

    findings: list[Finding] = []
    findings += diff_required_vs_produced(required, produced, meta)

    if args.check_bp:
        if not args.repo_slug:
            print(
                "Warning: --check-bp specified without --repo-slug; "
                "branch protection check skipped",
                file=sys.stderr,
            )
        else:
            contexts = fetch_branch_protection_contexts(
                args.repo_slug, branch=args.branch
            )
            findings += diff_required_vs_branch_protection(required, contexts)

    today_value = (
        date.fromisoformat(args.today) if args.today else date.today()  # noqa: DTZ011
    )
    findings += check_registry_freshness(registry, today_value)

    print(json.dumps([f.to_dict() for f in findings], indent=2))
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
