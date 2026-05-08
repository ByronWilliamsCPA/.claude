#!/usr/bin/env python3
"""Validate manifest required_checks against workflow jobs and branch protection.

Backs the CI-022/023/024 standards manifest checks. Reads the manifest's
required_checks field, the local repo's .github/workflows/*.yml files, the
reusable-workflow-jobs registry, and (when --check-bp is passed) the branch
protection contexts via gh api. Emits JSON findings to stdout.
"""

from __future__ import annotations

from typing import Any

from ruamel.yaml import YAML

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
        every matrix combination using the format `<job-name> (<param>, ...)`.
        Workflows with a top-level `name:` produce check names prefixed as
        `<workflow-name> / <job-name>`.
    """
    _ = registry  # consumed in later tasks (matrix, reusable-workflow expansion)
    doc = _yaml.load(workflow_yaml) or {}
    workflow_name = doc.get("name")
    jobs = doc.get("jobs", {}) or {}
    produced: set[str] = set()
    for job_key, job in jobs.items():
        if not isinstance(job, dict):
            continue
        job_label = job.get("name") or job_key
        check_name = f"{workflow_name} / {job_label}" if workflow_name else job_label
        produced.add(check_name)
    return produced


if __name__ == "__main__":
    raise SystemExit("CLI entry point implemented in a later task.")
