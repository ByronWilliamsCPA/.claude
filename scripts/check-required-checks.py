#!/usr/bin/env python3
"""Validate manifest required_checks against workflow jobs and branch protection.

Backs the CI-022/023/024 standards manifest checks. Reads the manifest's
required_checks field, the local repo's .github/workflows/*.yml files, the
reusable-workflow-jobs registry, and (when --check-bp is passed) the branch
protection contexts via gh api. Emits JSON findings to stdout.
"""

from __future__ import annotations

import itertools
import re
from dataclasses import asdict, dataclass
from datetime import date, timedelta
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


def _prefix_with_workflow(workflow_name: str | None, label: str) -> str:
    """Prefix `label` with the workflow name when present."""
    return f"{workflow_name} / {label}" if workflow_name else label


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
    workflow_name: str | None,
    job_key: str,
    job: dict[str, Any],
    registry: dict[str, Any],
) -> set[str]:
    """Return the set of check names this single job produces."""
    uses = job.get("uses")
    if isinstance(uses, str) and ".github/workflows/" in uses:
        workflow_path = uses.split("@", 1)[0]
        entry = registry.get(workflow_path)
        if entry and isinstance(entry.get("produces"), list):
            return {str(name) for name in entry["produces"]}
        return {f"{_UNREGISTERED_PREFIX}{workflow_path}"}
    job_label_template = job.get("name") or job_key
    simple_axes = _job_simple_axes(job)
    if not simple_axes:
        # No matrix, or include-only/exclude-only matrix: emit the raw label
        # without interpolation. include-only matrices are a documented
        # limitation; the validator will likely flag them as CI-022 findings,
        # signaling the workflow needs to be modeled in the registry.
        return {_prefix_with_workflow(workflow_name, job_label_template)}
    return {
        _prefix_with_workflow(
            workflow_name, _interpolate_matrix(job_label_template, combo)
        )
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
        interpolated with the matrix values. Workflows with a top-level
        `name:` produce check names prefixed as `<workflow-name> / <job-name>`.

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
    workflow_name = doc.get("name")
    jobs = doc.get("jobs", {}) or {}
    produced: set[str] = set()
    for job_key, job in jobs.items():
        if not isinstance(job, dict):
            continue
        produced |= _produced_for_job(workflow_name, job_key, job, registry)
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


if __name__ == "__main__":
    raise SystemExit("CLI entry point implemented in a later task.")
