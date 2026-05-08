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
from typing import Any

from ruamel.yaml import YAML

_MATRIX_VAR = re.compile(r"\$\{\{\s*matrix\.(\w+)\s*\}\}")


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
) -> set[str]:
    """Compute the set of check names a single job produces."""
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
            Reserved for reusable-workflow expansion (implemented in a later
            task). Pass an empty dict for locally-defined workflows.

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
    _ = registry  # consumed in later tasks (reusable-workflow expansion)
    doc = _yaml.load(workflow_yaml) or {}
    workflow_name = doc.get("name")
    jobs = doc.get("jobs", {}) or {}
    produced: set[str] = set()
    for job_key, job in jobs.items():
        if not isinstance(job, dict):
            continue
        produced |= _produced_for_job(workflow_name, job_key, job)
    return produced


if __name__ == "__main__":
    raise SystemExit("CLI entry point implemented in a later task.")
