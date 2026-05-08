---
schema_type: common
title: Required Checks Cross-Validation Implementation Plan
status: draft
owner: engineering
tags: [compliance, ci_cd, github_actions, agents, standards]
purpose: Bite-sized TDD tasks to implement CI-022/023/024 cross-validation between manifest required_checks, workflow job names, and branch protection contexts.
---

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add CI-022/023/024 to the standards manifest so `/repo-audit` detects drift between manifest `required_checks`, workflow job names, and branch protection contexts before it hangs PRs.

**Architecture:** A new Python script (`scripts/check-required-checks.py`) does the static analysis (parse local workflow YAML, expand matrices, resolve reusable workflows via a registry, diff against manifest and branch protection). The `ossf-compliance-auditor` agent shells out to this script and consumes JSON findings. Migration removes the superseded CI-014..017 in the same change.

**Tech Stack:** Python 3.12 (stdlib + `ruamel.yaml` from dev deps), pytest 80% coverage gate, `gh api` for branch protection, agent prompt updates only (no new agent registration).

**Spec:** [docs/superpowers/specs/2026-05-08-required-checks-cross-validation-design.md](../specs/2026-05-08-required-checks-cross-validation-design.md)

---

## File Structure

| File | Action | Responsibility |
| --- | --- | --- |
| `docs/standards-manifest.yaml` | Modify | Add `required_checks` top-level, add CI-022/023/024, remove CI-014/015/016/017 |
| `docs/reusable-workflow-jobs.yaml` | Create | Registry mapping reusable workflow paths to produced check names |
| `scripts/check-required-checks.py` | Create | Validation logic: parse workflows, expand matrices, resolve registry, diff |
| `scripts/seed-reusable-workflow-registry.py` | Create | One-shot script to populate the registry from a local clone of `ByronWilliamsCPA/.github` |
| `.claude/agents/ossf-compliance-auditor.md` | Modify | Add CI-022/023/024 dispatch logic and remediation prompts |
| `tests/unit/test_check_required_checks.py` | Create | Unit tests on the validator's pure functions |
| `tests/integration/test_check_required_checks_integration.py` | Create | Integration tests against fake-repo fixtures with mocked `gh api` |
| `data/test_fixtures/required_checks/` | Create | Fixture workflows, registries, and expected findings |
| `.claude/compliance-overrides.md` | Modify (if needed) | Migrate any existing CI-014..017 overrides to new check IDs |

---

## Task 1: Manifest schema migration and registry seeding

This task makes the data changes only. No script code yet. The audit will start failing for repos until subsequent tasks land the validator, which is intentional: the new checks have no implementation yet, so the auditor reports them as "not yet implemented" findings, never green-lighting.

**Files:**
- Modify: `docs/standards-manifest.yaml` (replace CI-014/015/016/017 with required_checks and CI-022/023/024)
- Create: `docs/reusable-workflow-jobs.yaml`

- [ ] **Step 1: Read current CI-014, CI-015, CI-016, CI-017 entries**

Run: `grep -B1 -A6 "id: CI-01[4567]" docs/standards-manifest.yaml`

Confirm the four IDs exist with these `verify:` directives (from the brainstorming exploration):

- CI-014: `content_present: .github/workflows/ci.yml, CI Gate`
- CI-015: `content_present: .github/workflows/security-analysis.yml, Security Gate Validation`
- CI-016: `content_present: .github/workflows/pr-validation.yml, Dependency & Standards Validation`
- CI-017: `branch_protection_contexts: CI Gate, Security Gate Validation, Dependency & Standards Validation, Check REUSE Compliance`

- [ ] **Step 2: Add the `required_checks` top-level field to the manifest**

Insert at the top level of `docs/standards-manifest.yaml`, before the `checks:` array:

```yaml
required_checks:
  - name: "CI Gate"
    produced_by: "ByronWilliamsCPA/.github/.github/workflows/python-ci.yml"
    matrix_expansion: false
  - name: "Security Gate Validation"
    produced_by: "ByronWilliamsCPA/.github/.github/workflows/security-analysis.yml"
    matrix_expansion: false
  - name: "Dependency & Standards Validation"
    produced_by: ".github/workflows/pr-validation.yml"
    matrix_expansion: false
  - name: "Check REUSE Compliance"
    produced_by: ".github/workflows/reuse.yml"
    matrix_expansion: false
```

- [ ] **Step 3: Replace CI-014/015/016/017 with CI-022/023/024**

Delete the four old CI-* entries. Add these three in their place:

```yaml
  - id: CI-022
    domain: ci
    severity: critical
    description: >-
      Every entry in required_checks has a workflow job that produces it,
      either locally or via a registered reusable workflow.
    verify: "required_checks_have_producer: docs/standards-manifest.yaml, docs/reusable-workflow-jobs.yaml"  # yamllint disable-line rule:line-length
    override_eligible: false

  - id: CI-023
    domain: ci
    severity: critical
    description: >-
      Branch protection contexts exactly match required_checks names
      (set equality, not subset).
    verify: "branch_protection_matches_required_checks: docs/standards-manifest.yaml"
    override_eligible: false

  - id: CI-024
    domain: ci
    severity: important
    description: >-
      Every reusable workflow registered in
      docs/reusable-workflow-jobs.yaml has last_verified within 90 days.
    verify: "registry_freshness: docs/reusable-workflow-jobs.yaml, max_age_days=90"
    override_eligible: false
```

- [ ] **Step 4: Create the seed registry file**

Create `docs/reusable-workflow-jobs.yaml` with content:

```yaml
# Registry of reusable GitHub Actions workflows and the check names they produce.
# Maintained by scripts/seed-reusable-workflow-registry.py and updated when
# org-level workflow changes ship. CI-024 enforces 90-day freshness.

ByronWilliamsCPA/.github/.github/workflows/python-ci.yml:
  produces: ["CI Gate"]
  source_repo: ByronWilliamsCPA/.github
  last_verified: 2026-05-08

ByronWilliamsCPA/.github/.github/workflows/security-analysis.yml:
  produces: ["Security Gate Validation"]
  source_repo: ByronWilliamsCPA/.github
  last_verified: 2026-05-08
```

- [ ] **Step 5: Validate YAML parses**

Run: `python -c "from ruamel.yaml import YAML; y = YAML(); y.load(open('docs/standards-manifest.yaml')); y.load(open('docs/reusable-workflow-jobs.yaml')); print('OK')"`

Expected: prints `OK`. Any YAML error means a syntax mistake in step 2, 3, or 4.

- [ ] **Step 6: Run pre-commit on changed files**

Run: `pre-commit run --files docs/standards-manifest.yaml docs/reusable-workflow-jobs.yaml`

Expected: all hooks pass (yamllint, frontmatter validators if applicable, em-dash check).

- [ ] **Step 7: Commit**

```bash
git add docs/standards-manifest.yaml docs/reusable-workflow-jobs.yaml
git commit -m "feat(standards): add required_checks field and CI-022/023/024

Replaces hardcoded CI-014..017 with manifest-driven cross-validation
backed by a reusable-workflow registry. Validator implementation lands
in subsequent commits.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Task 2: Validator skeleton + first unit test (single locally-defined job, no name field)

Set up the script file and test file with one passing test for the simplest case. This establishes the module shape and verifies the test infrastructure works.

**Files:**
- Create: `scripts/check-required-checks.py`
- Create: `tests/unit/test_check_required_checks.py`
- Create: `data/test_fixtures/required_checks/`

- [ ] **Step 1: Create fixtures directory and a minimal workflow fixture**

Create `data/test_fixtures/required_checks/single_job_no_name.yml`:

```yaml
name: Pipeline
on: [push]
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - run: echo hello
```

GitHub will report this as check name `build` (job key, since no `name:` field on the job). With the workflow's top-level `name: Pipeline`, the actual check is `Pipeline / build`. The validator must produce `Pipeline / build`.

- [ ] **Step 2: Write the failing test**

Create `tests/unit/test_check_required_checks.py`:

```python
"""Unit tests for scripts/check-required-checks.py validator logic."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import importlib.util

spec = importlib.util.spec_from_file_location(
    "check_required_checks",
    SCRIPTS_DIR / "check-required-checks.py",
)
crc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(crc)

FIXTURES = PROJECT_ROOT / "data" / "test_fixtures" / "required_checks"


@pytest.mark.unit
def test_single_job_no_name_produces_workflow_prefixed_check() -> None:
    workflow_yaml = (FIXTURES / "single_job_no_name.yml").read_text()
    produced = crc.extract_produced_check_names(workflow_yaml, registry={})
    assert produced == {"Pipeline / build"}
```

- [ ] **Step 3: Run the test to verify it fails**

Run: `pytest tests/unit/test_check_required_checks.py -v`

Expected: FAIL with `ModuleNotFoundError` or `AttributeError: module ... has no attribute 'extract_produced_check_names'`.

- [ ] **Step 4: Write minimal implementation**

Create `scripts/check-required-checks.py`:

```python
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

    Returns:
        Set of check names. For matrix jobs the set is expanded across
        every matrix combination using the format `<job-name> (<param>, ...)`.
        Workflows with a top-level `name:` produce check names prefixed as
        `<workflow-name> / <job-name>`.
    """
    doc = _yaml.load(workflow_yaml) or {}
    workflow_name = doc.get("name")
    jobs = doc.get("jobs", {}) or {}
    produced: set[str] = set()
    for job_key, job in jobs.items():
        job_label = job_key
        check_name = (
            f"{workflow_name} / {job_label}" if workflow_name else job_label
        )
        produced.add(check_name)
    return produced


if __name__ == "__main__":
    raise SystemExit("CLI entry point implemented in a later task.")
```

- [ ] **Step 5: Run the test to verify it passes**

Run: `pytest tests/unit/test_check_required_checks.py -v`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add scripts/check-required-checks.py tests/unit/test_check_required_checks.py data/test_fixtures/required_checks/single_job_no_name.yml
git commit -m "feat(scripts): add check-required-checks validator skeleton

Implements extract_produced_check_names for the simplest case
(single locally-defined job, no job-level name field, with workflow
top-level name producing the prefix).

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Task 3: Job `name:` field and absent workflow `name:`

Cover the two remaining locally-defined-job cases: job has explicit `name:`, and workflow has no top-level `name:` (so no prefix).

**Files:**
- Modify: `scripts/check-required-checks.py`
- Modify: `tests/unit/test_check_required_checks.py`
- Create: `data/test_fixtures/required_checks/single_job_with_name.yml`
- Create: `data/test_fixtures/required_checks/no_workflow_name.yml`

- [ ] **Step 1: Create fixtures**

`data/test_fixtures/required_checks/single_job_with_name.yml`:

```yaml
name: Pipeline
on: [push]
jobs:
  build:
    name: CI Gate
    runs-on: ubuntu-latest
    steps:
      - run: echo hello
```

Expected produced: `{"Pipeline / CI Gate"}`.

`data/test_fixtures/required_checks/no_workflow_name.yml`:

```yaml
on: [push]
jobs:
  reuse-check:
    name: Check REUSE Compliance
    runs-on: ubuntu-latest
    steps:
      - run: echo
```

Expected produced: `{"Check REUSE Compliance"}` (no prefix because no top-level `name:`).

- [ ] **Step 2: Write the failing tests**

Append to `tests/unit/test_check_required_checks.py`:

```python
@pytest.mark.unit
def test_job_with_name_uses_name_field() -> None:
    workflow_yaml = (FIXTURES / "single_job_with_name.yml").read_text()
    produced = crc.extract_produced_check_names(workflow_yaml, registry={})
    assert produced == {"Pipeline / CI Gate"}


@pytest.mark.unit
def test_workflow_without_name_omits_prefix() -> None:
    workflow_yaml = (FIXTURES / "no_workflow_name.yml").read_text()
    produced = crc.extract_produced_check_names(workflow_yaml, registry={})
    assert produced == {"Check REUSE Compliance"}
```

- [ ] **Step 3: Run tests, expect failure**

Run: `pytest tests/unit/test_check_required_checks.py -v`

Expected: `test_job_with_name_uses_name_field` FAILS (validator returns the job key, not the `name:` field).

- [ ] **Step 4: Update `extract_produced_check_names`**

In `scripts/check-required-checks.py`, replace the `for job_key, job in jobs.items():` block with:

```python
    for job_key, job in jobs.items():
        if not isinstance(job, dict):
            continue
        job_label = job.get("name") or job_key
        check_name = (
            f"{workflow_name} / {job_label}" if workflow_name else job_label
        )
        produced.add(check_name)
```

- [ ] **Step 5: Run tests, expect pass**

Run: `pytest tests/unit/test_check_required_checks.py -v`

Expected: 3 passed.

- [ ] **Step 6: Commit**

```bash
git add scripts/check-required-checks.py tests/unit/test_check_required_checks.py data/test_fixtures/required_checks/single_job_with_name.yml data/test_fixtures/required_checks/no_workflow_name.yml
git commit -m "feat(scripts): handle job-level name and workflow-without-name cases

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Task 4: Matrix expansion (one and two parameters)

Real-world workflows almost always use matrices. The validator must produce one check name per matrix combination using GitHub's `<job-name> (<param>, ...)` format.

**Files:**
- Modify: `scripts/check-required-checks.py`
- Modify: `tests/unit/test_check_required_checks.py`
- Create: `data/test_fixtures/required_checks/matrix_one_param.yml`
- Create: `data/test_fixtures/required_checks/matrix_two_params.yml`

- [ ] **Step 1: Create fixtures**

`data/test_fixtures/required_checks/matrix_one_param.yml`:

```yaml
name: Tests
on: [push]
jobs:
  test:
    name: Test Python ${{ matrix.python }}
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python: ["3.10", "3.11", "3.12"]
    steps:
      - run: echo
```

Expected produced: `{"Tests / Test Python 3.10", "Tests / Test Python 3.11", "Tests / Test Python 3.12"}`.

`data/test_fixtures/required_checks/matrix_two_params.yml`:

```yaml
on: [push]
jobs:
  test:
    name: Test ${{ matrix.os }} ${{ matrix.python }}
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: ["ubuntu-latest", "macos-latest"]
        python: ["3.11", "3.12"]
    steps:
      - run: echo
```

Expected produced: 4 names: `Test ubuntu-latest 3.11`, `Test ubuntu-latest 3.12`, `Test macos-latest 3.11`, `Test macos-latest 3.12`.

- [ ] **Step 2: Write the failing tests**

Append to `tests/unit/test_check_required_checks.py`:

```python
@pytest.mark.unit
def test_matrix_one_param_expands() -> None:
    workflow_yaml = (FIXTURES / "matrix_one_param.yml").read_text()
    produced = crc.extract_produced_check_names(workflow_yaml, registry={})
    assert produced == {
        "Tests / Test Python 3.10",
        "Tests / Test Python 3.11",
        "Tests / Test Python 3.12",
    }


@pytest.mark.unit
def test_matrix_two_params_cartesian_expansion() -> None:
    workflow_yaml = (FIXTURES / "matrix_two_params.yml").read_text()
    produced = crc.extract_produced_check_names(workflow_yaml, registry={})
    assert produced == {
        "Test ubuntu-latest 3.11",
        "Test ubuntu-latest 3.12",
        "Test macos-latest 3.11",
        "Test macos-latest 3.12",
    }
```

- [ ] **Step 3: Run tests, expect failure**

Run: `pytest tests/unit/test_check_required_checks.py -v`

Expected: matrix tests FAIL with assertion errors (current code produces just one name with literal `${{ matrix.python }}`).

- [ ] **Step 4: Add matrix-expansion logic**

In `scripts/check-required-checks.py`, add at module level:

```python
import itertools
import re

_MATRIX_VAR = re.compile(r"\$\{\{\s*matrix\.(\w+)\s*\}\}")


def _expand_matrix_combinations(
    matrix: dict[str, list[Any]],
) -> list[dict[str, Any]]:
    """Cartesian product of matrix axes. Returns a list of dicts."""
    keys = list(matrix.keys())
    value_lists = [matrix[k] for k in keys]
    return [dict(zip(keys, combo)) for combo in itertools.product(*value_lists)]


def _interpolate_matrix(template: str, combo: dict[str, Any]) -> str:
    """Replace ${{ matrix.<key> }} with the corresponding value from combo."""
    def _sub(match: re.Match[str]) -> str:
        key = match.group(1)
        return str(combo.get(key, match.group(0)))
    return _MATRIX_VAR.sub(_sub, template)
```

Replace the `for job_key, job in jobs.items():` block:

```python
    for job_key, job in jobs.items():
        if not isinstance(job, dict):
            continue
        job_label_template = job.get("name") or job_key
        strategy = job.get("strategy") or {}
        matrix = strategy.get("matrix") if isinstance(strategy, dict) else None
        if isinstance(matrix, dict) and matrix:
            simple_axes = {
                k: v for k, v in matrix.items()
                if isinstance(v, list) and k not in ("include", "exclude")
            }
            for combo in _expand_matrix_combinations(simple_axes):
                expanded = _interpolate_matrix(job_label_template, combo)
                check_name = (
                    f"{workflow_name} / {expanded}" if workflow_name else expanded
                )
                produced.add(check_name)
        else:
            check_name = (
                f"{workflow_name} / {job_label_template}"
                if workflow_name
                else job_label_template
            )
            produced.add(check_name)
```

- [ ] **Step 5: Run tests, expect pass**

Run: `pytest tests/unit/test_check_required_checks.py -v`

Expected: 5 passed.

- [ ] **Step 6: Commit**

```bash
git add scripts/check-required-checks.py tests/unit/test_check_required_checks.py data/test_fixtures/required_checks/matrix_one_param.yml data/test_fixtures/required_checks/matrix_two_params.yml
git commit -m "feat(scripts): expand matrix jobs into per-combination check names

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Task 5: Reusable workflow registry resolution

When a job uses `uses: <org>/<repo>/.github/workflows/<file>.yml@<ref>`, the validator looks up the path in the registry and adds the registered `produces` names to the produced set. Unregistered references emit a warning sentinel.

**Files:**
- Modify: `scripts/check-required-checks.py`
- Modify: `tests/unit/test_check_required_checks.py`
- Create: `data/test_fixtures/required_checks/reusable_registered.yml`
- Create: `data/test_fixtures/required_checks/reusable_unregistered.yml`

- [ ] **Step 1: Create fixtures**

`data/test_fixtures/required_checks/reusable_registered.yml`:

```yaml
on: [push]
jobs:
  ci:
    uses: ByronWilliamsCPA/.github/.github/workflows/python-ci.yml@abc123
```

`data/test_fixtures/required_checks/reusable_unregistered.yml`:

```yaml
on: [push]
jobs:
  ci:
    uses: SomeOrg/private-actions/.github/workflows/build.yml@v1
```

- [ ] **Step 2: Write the failing tests**

Append to `tests/unit/test_check_required_checks.py`:

```python
@pytest.mark.unit
def test_registered_reusable_workflow_resolved_via_registry() -> None:
    workflow_yaml = (FIXTURES / "reusable_registered.yml").read_text()
    registry = {
        "ByronWilliamsCPA/.github/.github/workflows/python-ci.yml": {
            "produces": ["CI Gate"],
            "source_repo": "ByronWilliamsCPA/.github",
            "last_verified": "2026-05-08",
        },
    }
    produced = crc.extract_produced_check_names(workflow_yaml, registry=registry)
    assert produced == {"CI Gate"}


@pytest.mark.unit
def test_unregistered_reusable_workflow_returns_sentinel() -> None:
    workflow_yaml = (FIXTURES / "reusable_unregistered.yml").read_text()
    produced = crc.extract_produced_check_names(workflow_yaml, registry={})
    assert any(name.startswith("__UNREGISTERED__:") for name in produced)
    assert "__UNREGISTERED__:SomeOrg/private-actions/.github/workflows/build.yml" in produced
```

- [ ] **Step 3: Run tests, expect failure**

Run: `pytest tests/unit/test_check_required_checks.py -v`

Expected: both new tests FAIL.

- [ ] **Step 4: Add reusable-workflow handling**

In `scripts/check-required-checks.py`, modify the job loop to handle `uses:` first:

```python
    for job_key, job in jobs.items():
        if not isinstance(job, dict):
            continue
        uses = job.get("uses")
        if isinstance(uses, str) and ".github/workflows/" in uses:
            workflow_path = uses.split("@", 1)[0]
            entry = registry.get(workflow_path)
            if entry and isinstance(entry.get("produces"), list):
                for name in entry["produces"]:
                    produced.add(str(name))
            else:
                produced.add(f"__UNREGISTERED__:{workflow_path}")
            continue
        # ... (existing locally-defined-job logic from Task 4 unchanged)
```

- [ ] **Step 5: Run tests, expect pass**

Run: `pytest tests/unit/test_check_required_checks.py -v`

Expected: 7 passed.

- [ ] **Step 6: Commit**

```bash
git add scripts/check-required-checks.py tests/unit/test_check_required_checks.py data/test_fixtures/required_checks/reusable_registered.yml data/test_fixtures/required_checks/reusable_unregistered.yml
git commit -m "feat(scripts): resolve reusable workflow uses via registry

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Task 6: Diff functions and finding emission

Three pure functions that take the `expected` (manifest), `produced` (workflows), and `actual` (branch protection contexts) sets and produce structured findings. Plus the registry-staleness check (CI-024).

**Files:**
- Modify: `scripts/check-required-checks.py`
- Modify: `tests/unit/test_check_required_checks.py`

- [ ] **Step 1: Define the Finding dataclass and stub functions**

Add to `scripts/check-required-checks.py` (near the top, after imports):

```python
from dataclasses import dataclass, asdict
from datetime import date, timedelta


@dataclass(frozen=True)
class Finding:
    check_id: str
    severity: str
    message: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


def diff_required_vs_produced(
    required: set[str],
    produced: set[str],
    required_checks_meta: dict[str, dict[str, Any]],
) -> list[Finding]:
    """CI-022: every required check has a producing workflow job."""
    findings: list[Finding] = []
    unregistered = {p for p in produced if p.startswith("__UNREGISTERED__:")}
    for path in unregistered:
        findings.append(
            Finding(
                check_id="CI-022",
                severity="critical",
                message=(
                    f"Reusable workflow '{path.removeprefix('__UNREGISTERED__:')}' "
                    f"is referenced but missing from "
                    f"docs/reusable-workflow-jobs.yaml; add it or remove the reference."
                ),
            )
        )
    cleaned_produced = produced - unregistered
    for name in sorted(required - cleaned_produced):
        meta = required_checks_meta.get(name, {})
        produced_by = meta.get("produced_by", "<unspecified>")
        findings.append(
            Finding(
                check_id="CI-022",
                severity="critical",
                message=(
                    f"Required check '{name}' has no producing workflow job. "
                    f"Manifest expects it to come from {produced_by}."
                ),
            )
        )
    return findings


def diff_required_vs_branch_protection(
    required: set[str],
    contexts: list[str],
) -> list[Finding]:
    """CI-023: branch protection contexts equal required_checks set exactly."""
    findings: list[Finding] = []
    actual = set(contexts)
    for name in sorted(required - actual):
        findings.append(
            Finding(
                check_id="CI-023",
                severity="critical",
                message=(
                    f"Required check '{name}' missing from branch protection contexts."
                ),
            )
        )
    for name in sorted(actual - required):
        findings.append(
            Finding(
                check_id="CI-023",
                severity="critical",
                message=(
                    f"Branch protection requires '{name}' but manifest does "
                    f"not list it as a required check."
                ),
            )
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
```

- [ ] **Step 2: Write tests for each diff function**

Append to `tests/unit/test_check_required_checks.py`:

```python
@pytest.mark.unit
def test_diff_required_vs_produced_flags_missing_producer() -> None:
    findings = crc.diff_required_vs_produced(
        required={"CI Gate", "REUSE"},
        produced={"CI Gate"},
        required_checks_meta={
            "REUSE": {"produced_by": ".github/workflows/reuse.yml"},
        },
    )
    assert len(findings) == 1
    assert findings[0].check_id == "CI-022"
    assert "REUSE" in findings[0].message
    assert ".github/workflows/reuse.yml" in findings[0].message


@pytest.mark.unit
def test_diff_required_vs_produced_flags_unregistered_reusable() -> None:
    findings = crc.diff_required_vs_produced(
        required={"CI Gate"},
        produced={"CI Gate", "__UNREGISTERED__:SomeOrg/x/.github/workflows/y.yml"},
        required_checks_meta={},
    )
    assert any(
        "missing from docs/reusable-workflow-jobs.yaml" in f.message
        for f in findings
    )


@pytest.mark.unit
def test_diff_required_vs_branch_protection_missing_and_extra() -> None:
    findings = crc.diff_required_vs_branch_protection(
        required={"CI Gate", "REUSE"},
        contexts=["CI Gate", "Stale Check"],
    )
    messages = [f.message for f in findings]
    assert any("REUSE" in m and "missing" in m for m in messages)
    assert any("Stale Check" in m and "does not list" in m for m in messages)


@pytest.mark.unit
def test_diff_required_vs_branch_protection_exact_match_no_findings() -> None:
    findings = crc.diff_required_vs_branch_protection(
        required={"CI Gate"},
        contexts=["CI Gate"],
    )
    assert findings == []


@pytest.mark.unit
def test_registry_freshness_flags_stale_entries() -> None:
    from datetime import date
    registry = {
        "fresh": {"last_verified": "2026-05-01"},
        "stale": {"last_verified": "2025-01-01"},
        "missing": {},
    }
    findings = crc.check_registry_freshness(
        registry=registry,
        today=date(2026, 5, 8),
        max_age_days=90,
    )
    paths = [f.message for f in findings]
    assert any("stale" in m for m in paths)
    assert any("missing" in m and "last_verified" in m for m in paths)
    assert not any("fresh" in m for m in paths)
```

- [ ] **Step 3: Run tests**

Run: `pytest tests/unit/test_check_required_checks.py -v`

Expected: 12 passed.

- [ ] **Step 4: Commit**

```bash
git add scripts/check-required-checks.py tests/unit/test_check_required_checks.py
git commit -m "feat(scripts): add diff functions for CI-022/023 and registry freshness for CI-024

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Task 7: CLI entry point and integration test against fake repo

Wire the pure functions together into a CLI that reads the manifest, scans `.github/workflows/`, fetches branch protection contexts, and emits JSON findings to stdout. Mock `gh api` at the subprocess boundary in the integration test.

**Files:**
- Modify: `scripts/check-required-checks.py`
- Create: `tests/integration/test_check_required_checks_integration.py`
- Create: `data/test_fixtures/required_checks/fake_repo/` (a small repo tree with workflows and a manifest)

- [ ] **Step 1: Build the fake-repo fixture**

Create the following file tree under `data/test_fixtures/required_checks/fake_repo/`:

```
fake_repo/
├── .github/
│   └── workflows/
│       ├── ci.yml
│       └── reuse.yml
└── manifest_input.yaml
```

`fake_repo/.github/workflows/ci.yml`:

```yaml
on: [push]
jobs:
  ci:
    uses: ByronWilliamsCPA/.github/.github/workflows/python-ci.yml@abc
```

`fake_repo/.github/workflows/reuse.yml`:

```yaml
on: [push]
jobs:
  reuse-check:
    name: Check REUSE Compliance
    runs-on: ubuntu-latest
    steps:
      - run: echo
```

`fake_repo/manifest_input.yaml`:

```yaml
required_checks:
  - name: "CI Gate"
    produced_by: "ByronWilliamsCPA/.github/.github/workflows/python-ci.yml"
  - name: "Check REUSE Compliance"
    produced_by: ".github/workflows/reuse.yml"
```

A registry fixture at `data/test_fixtures/required_checks/registry_input.yaml`:

```yaml
ByronWilliamsCPA/.github/.github/workflows/python-ci.yml:
  produces: ["CI Gate"]
  source_repo: ByronWilliamsCPA/.github
  last_verified: 2026-05-01
```

- [ ] **Step 2: Add CLI entry point and supporting helpers**

Append to `scripts/check-required-checks.py`:

```python
import argparse
import json
import subprocess  # nosec B404 -- intentional gh CLI invocation
from pathlib import Path


def load_required_checks(manifest_path: Path) -> tuple[set[str], dict[str, dict[str, Any]]]:
    doc = _yaml.load(manifest_path.read_text()) or {}
    entries = doc.get("required_checks", []) or []
    names = {e["name"] for e in entries}
    meta = {e["name"]: e for e in entries}
    return names, meta


def load_registry(registry_path: Path) -> dict[str, dict[str, Any]]:
    if not registry_path.exists():
        return {}
    return _yaml.load(registry_path.read_text()) or {}


def scan_workflow_dir(
    workflow_dir: Path,
    registry: dict[str, dict[str, Any]],
) -> set[str]:
    produced: set[str] = set()
    if not workflow_dir.is_dir():
        return produced
    for path in sorted(workflow_dir.glob("*.yml")):
        produced |= extract_produced_check_names(path.read_text(), registry)
    return produced


def fetch_branch_protection_contexts(repo_slug: str) -> list[str]:
    result = subprocess.run(  # nosec B603 B607
        [
            "gh", "api",
            f"repos/{repo_slug}/branches/main/protection",
            "--jq", ".required_status_checks.contexts",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return []
    return json.loads(result.stdout) if result.stdout.strip() else []


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-path", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--registry", type=Path, required=True)
    parser.add_argument("--repo-slug", default="")
    parser.add_argument("--check-bp", action="store_true",
                        help="Fetch and validate branch protection contexts")
    parser.add_argument("--today", default="",
                        help="Override today's date (YYYY-MM-DD) for testing")
    args = parser.parse_args(argv)

    required, meta = load_required_checks(args.manifest)
    registry = load_registry(args.registry)
    produced = scan_workflow_dir(args.repo_path / ".github" / "workflows", registry)

    findings: list[Finding] = []
    findings += diff_required_vs_produced(required, produced, meta)

    if args.check_bp and args.repo_slug:
        contexts = fetch_branch_protection_contexts(args.repo_slug)
        findings += diff_required_vs_branch_protection(required, contexts)

    today_value = (
        date.fromisoformat(args.today) if args.today else date.today()
    )
    findings += check_registry_freshness(registry, today_value)

    print(json.dumps([f.to_dict() for f in findings], indent=2))
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
```

Note: replace the earlier `if __name__ == "__main__": raise SystemExit("CLI entry point implemented in a later task.")` with the new entry point above.

- [ ] **Step 3: Write integration tests**

Create `tests/integration/test_check_required_checks_integration.py`:

```python
"""Integration tests: full validator run against fake-repo fixture."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

spec = importlib.util.spec_from_file_location(
    "check_required_checks", SCRIPTS_DIR / "check-required-checks.py",
)
crc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(crc)

FIXTURES = PROJECT_ROOT / "data" / "test_fixtures" / "required_checks"
FAKE_REPO = FIXTURES / "fake_repo"
MANIFEST = FAKE_REPO / "manifest_input.yaml"
REGISTRY = FIXTURES / "registry_input.yaml"


@pytest.mark.integration
def test_compliant_repo_emits_no_findings(capsys: pytest.CaptureFixture[str]) -> None:
    with patch.object(
        crc, "fetch_branch_protection_contexts",
        return_value=["CI Gate", "Check REUSE Compliance"],
    ):
        exit_code = crc.main([
            "--repo-path", str(FAKE_REPO),
            "--manifest", str(MANIFEST),
            "--registry", str(REGISTRY),
            "--repo-slug", "fake/repo",
            "--check-bp",
            "--today", "2026-05-08",
        ])
    captured = capsys.readouterr()
    findings = json.loads(captured.out)
    assert findings == []
    assert exit_code == 0


@pytest.mark.integration
def test_branch_protection_drift_emits_ci023(capsys: pytest.CaptureFixture[str]) -> None:
    with patch.object(
        crc, "fetch_branch_protection_contexts",
        return_value=["CI Gate"],  # missing "Check REUSE Compliance"
    ):
        exit_code = crc.main([
            "--repo-path", str(FAKE_REPO),
            "--manifest", str(MANIFEST),
            "--registry", str(REGISTRY),
            "--repo-slug", "fake/repo",
            "--check-bp",
            "--today", "2026-05-08",
        ])
    findings = json.loads(capsys.readouterr().out)
    ci023 = [f for f in findings if f["check_id"] == "CI-023"]
    assert len(ci023) == 1
    assert "Check REUSE Compliance" in ci023[0]["message"]
    assert "missing from branch protection" in ci023[0]["message"]
    assert exit_code == 1
```

- [ ] **Step 4: Run integration tests**

Run: `pytest tests/integration/test_check_required_checks_integration.py -v`

Expected: 2 passed.

- [ ] **Step 5: Run full test suite to confirm no regressions**

Run: `pytest tests/unit/test_check_required_checks.py tests/integration/test_check_required_checks_integration.py -v --cov=scripts.check_required_checks --cov-report=term-missing`

Expected: 14 passed, coverage 90%+ on the validator module.

- [ ] **Step 6: Commit**

```bash
git add scripts/check-required-checks.py tests/integration/test_check_required_checks_integration.py data/test_fixtures/required_checks/fake_repo/ data/test_fixtures/required_checks/registry_input.yaml
git commit -m "feat(scripts): wire CLI entry point and add integration tests

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Task 8: Wire validation into ossf-compliance-auditor agent

Update the agent prompt to invoke the new script for CI-022/023/024 and consume its JSON output. Add the remediation prompt logic per the spec's Section 3.

**Files:**
- Modify: `.claude/agents/ossf-compliance-auditor.md`

- [ ] **Step 1: Read the current agent prompt to identify where to insert**

Run: `grep -n "CI-017\|CI-014\|branch_protection_contexts\|FINDING template" .claude/agents/ossf-compliance-auditor.md | head -20`

Note the line numbers where CI-017 logic currently lives. The new logic replaces it.

- [ ] **Step 2: Replace the CI-014..017 audit logic**

In `.claude/agents/ossf-compliance-auditor.md`, find the section that handles CI-014/015/016/017. Replace it with a section titled "CI-022/023/024: Required Checks Cross-Validation" containing:

```markdown
### CI-022/023/024: Required Checks Cross-Validation

These three checks are validated by a single Python script. Invoke it once per audit:

```bash
python scripts/check-required-checks.py \
  --repo-path "${REPO_PATH}" \
  --manifest "${HOME}/.claude/docs/standards-manifest.yaml" \
  --registry "${HOME}/.claude/docs/reusable-workflow-jobs.yaml" \
  --repo-slug "${REPO_SLUG}" \
  --check-bp
```

The script emits a JSON array of findings to stdout. Parse it and emit each as a standard FINDING block. Exit code 0 means no findings; non-zero means at least one finding was emitted.

#### Remediation Prompts

When findings exist and the user is in interactive remediation mode:

**For CI-022 findings (workflow has no producing job):**

Use AskUserQuestion to offer:
- "Add a stub job to the local workflow file" (when produced_by is a local path)
- "Update the registry" (when produced_by is a reusable workflow path and the registry just needs the new name)
- "Remove from manifest" (when the required check is no longer required; requires typed reason)

**For CI-023 findings (branch protection drift):**

Use AskUserQuestion to offer:
- "Update branch protection contexts to match manifest" (visible-to-others action; require typed `yes` to proceed; show the full PATCH payload first)
- "Update manifest to match branch protection" (when live state is correct and manifest is stale)

The PATCH command is:

```bash
gh api repos/${REPO_SLUG}/branches/main/protection/required_status_checks \
  --method PATCH \
  --field 'contexts[]=<name1>' \
  --field 'contexts[]=<name2>' \
  --field 'strict=true'
```

**For CI-024 findings (registry staleness):**

Offer:
- "Re-verify the reusable workflow now" (fetch from source repo, re-parse, bump last_verified to today)
- "Mark as still accurate" (if user has manually verified; bump last_verified)

When multiple CI-023 findings exist with the same fix shape (all branch-protection drift), offer a "fix all in one PATCH" batch option.
```

- [ ] **Step 3: Update CI-001/CI-002 cross-references if they referenced CI-017**

Run: `grep -n "CI-017\|CI-014\|CI-015\|CI-016" .claude/agents/ossf-compliance-auditor.md`

Expected: no remaining references after step 2. If any remain, replace them with `CI-022` (for workflow producer checks) or `CI-023` (for branch protection contexts).

- [ ] **Step 4: Validate the agent prompt parses (markdown only, no schema)**

Run: `pre-commit run --files .claude/agents/ossf-compliance-auditor.md`

Expected: markdownlint and em-dash checks pass.

- [ ] **Step 5: Commit**

```bash
git add .claude/agents/ossf-compliance-auditor.md
git commit -m "feat(agents): wire CI-022/023/024 into ossf-compliance-auditor

Replaces inline CI-014..017 audit logic with a script invocation
and adds AskUserQuestion remediation prompts per the design spec.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Task 9: Registry seed script + dry-run validation

A one-shot script populates `docs/reusable-workflow-jobs.yaml` from a local clone of `ByronWilliamsCPA/.github`. Used during initial setup and re-run for CI-024 staleness fixes.

**Files:**
- Create: `scripts/seed-reusable-workflow-registry.py`
- Create: `tests/unit/test_seed_reusable_workflow_registry.py`

- [ ] **Step 1: Create test fixture for the seeder**

Create `data/test_fixtures/required_checks/seed_input/.github/workflows/example.yml`:

```yaml
name: Example
on: workflow_call
jobs:
  build:
    name: CI Gate
    runs-on: ubuntu-latest
    steps:
      - run: echo
```

- [ ] **Step 2: Write the failing test**

Create `tests/unit/test_seed_reusable_workflow_registry.py`:

```python
"""Test the registry seed script."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest
from ruamel.yaml import YAML

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

spec = importlib.util.spec_from_file_location(
    "seed_registry", SCRIPTS_DIR / "seed-reusable-workflow-registry.py",
)
seed = importlib.util.module_from_spec(spec)
spec.loader.exec_module(seed)

FIXTURES = PROJECT_ROOT / "data" / "test_fixtures" / "required_checks"


@pytest.mark.unit
def test_scan_org_repo_extracts_check_names(tmp_path: Path) -> None:
    output = tmp_path / "registry.yaml"
    seed.scan_org_repo(
        clone_path=FIXTURES / "seed_input",
        org_slug="ByronWilliamsCPA/.github",
        output_path=output,
        today="2026-05-08",
    )
    yaml = YAML(typ="safe")
    data = yaml.load(output.read_text())
    key = "ByronWilliamsCPA/.github/.github/workflows/example.yml"
    assert key in data
    assert data[key]["produces"] == ["Example / CI Gate"]
    assert data[key]["last_verified"] == "2026-05-08"
```

- [ ] **Step 3: Run test, expect failure**

Run: `pytest tests/unit/test_seed_reusable_workflow_registry.py -v`

Expected: FAIL (script does not exist).

- [ ] **Step 4: Implement the seed script**

Create `scripts/seed-reusable-workflow-registry.py`:

```python
#!/usr/bin/env python3
"""Populate docs/reusable-workflow-jobs.yaml from a local clone of an org repo.

Walks <clone-path>/.github/workflows/*.yml, extracts check names produced
by each workflow using the same parser as check-required-checks.py, and
writes a YAML registry file. Re-run when reusable workflows change.
"""
from __future__ import annotations

import argparse
import importlib.util
import sys
from datetime import date
from pathlib import Path

from ruamel.yaml import YAML

_SELF_DIR = Path(__file__).resolve().parent
_validator_spec = importlib.util.spec_from_file_location(
    "check_required_checks", _SELF_DIR / "check-required-checks.py",
)
_validator = importlib.util.module_from_spec(_validator_spec)
_validator_spec.loader.exec_module(_validator)


def scan_org_repo(
    clone_path: Path,
    org_slug: str,
    output_path: Path,
    today: str,
) -> None:
    """Walk clone_path/.github/workflows/*.yml and write a registry YAML."""
    workflow_dir = clone_path / ".github" / "workflows"
    if not workflow_dir.is_dir():
        raise FileNotFoundError(f"No workflow directory at {workflow_dir}")

    registry: dict[str, dict[str, object]] = {}
    for path in sorted(workflow_dir.glob("*.yml")):
        produced = _validator.extract_produced_check_names(
            path.read_text(), registry={}
        )
        if not produced:
            continue
        key = f"{org_slug}/.github/workflows/{path.name}"
        registry[key] = {
            "produces": sorted(produced),
            "source_repo": org_slug,
            "last_verified": today,
        }

    yaml = YAML()
    yaml.default_flow_style = False
    with output_path.open("w") as fh:
        yaml.dump(registry, fh)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--clone-path", type=Path, required=True,
                        help="Local clone of the org repo (e.g., ByronWilliamsCPA/.github)")
    parser.add_argument("--org-slug", required=True,
                        help="Org repo slug (e.g., ByronWilliamsCPA/.github)")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--today", default=date.today().isoformat())
    args = parser.parse_args(argv)
    scan_org_repo(args.clone_path, args.org_slug, args.output, args.today)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 5: Run test, expect pass**

Run: `pytest tests/unit/test_seed_reusable_workflow_registry.py -v`

Expected: PASS.

- [ ] **Step 6: Real-data dry-run against a clone of `ByronWilliamsCPA/.github`**

```bash
TMPDIR=$(mktemp -d)
gh repo clone ByronWilliamsCPA/.github "${TMPDIR}/dot-github"
python scripts/seed-reusable-workflow-registry.py \
  --clone-path "${TMPDIR}/dot-github" \
  --org-slug ByronWilliamsCPA/.github \
  --output /tmp/seeded-registry.yaml
diff -u docs/reusable-workflow-jobs.yaml /tmp/seeded-registry.yaml || true
```

Expected: the diff shows any net-new reusable workflows or check names that weren't in the hand-seeded version from Task 1. If the diff reveals new entries, copy them into `docs/reusable-workflow-jobs.yaml` and stage them.

- [ ] **Step 7: Commit**

```bash
git add scripts/seed-reusable-workflow-registry.py tests/unit/test_seed_reusable_workflow_registry.py data/test_fixtures/required_checks/seed_input/
# only stage docs/reusable-workflow-jobs.yaml if step 6 produced new entries
git diff --staged docs/reusable-workflow-jobs.yaml >/dev/null 2>&1 && \
  git add docs/reusable-workflow-jobs.yaml || true
git commit -m "feat(scripts): add seed-reusable-workflow-registry script

Reuses the validator's extract_produced_check_names parser for
consistency between seeding and validation.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Task 10: Migration validation across the catalog

Run the audit against all 44 cataloged repos and triage every finding before merging the branch.

**Files:**
- Create: `compliance-retrospectives/2026-05-08-required-checks-rollout.md` (a new retrospective entry)

- [ ] **Step 1: Run the audit in scheduled mode against every cataloged repo**

Run: `/repo-audit --scheduled`

(This invokes the `repo-compliance` skill's scheduled-mode workflow, which iterates over `docs/reference/github-repos.json` and dispatches the auditor per repo.)

Capture the output to `/tmp/required-checks-audit.txt`.

- [ ] **Step 2: Triage findings**

For each finding, classify as one of:

- **True positive** (real drift the old checks missed): document in the retrospective, leave to be fixed by the affected repo's normal interactive remediation flow.
- **Registry gap** (reusable workflow not in registry): re-run `seed-reusable-workflow-registry.py` to fill the gap, commit the registry change, re-run audit.
- **False positive** (validator bug): file an issue with reproducer in the retrospective; do NOT merge until fixed.

If any false positives exist, return to whichever earlier task introduced the bug, fix it (with a new failing test first), and re-run this triage.

- [ ] **Step 3: Migrate compliance-overrides.md if needed**

Run: `grep -rn "CI-014\|CI-015\|CI-016\|CI-017" . --include="*.md" 2>/dev/null`

Expected: no matches outside the retrospective and the spec/plan documents themselves. If any repo's `.claude/compliance-overrides.md` references the old IDs, edit each one to map to CI-022 or CI-023 as appropriate.

- [ ] **Step 4: Write the retrospective**

Create `compliance-retrospectives/2026-05-08-required-checks-rollout.md` (under 200 lines):

```markdown
---
schema_type: common
title: Required Checks Cross-Validation Rollout
status: published
owner: engineering
tags: [compliance, ci_cd, github_actions, agents, standards]
purpose: Retrospective for the CI-022/023/024 rollout dry-run, including triaged findings and registry gaps discovered.
---

# Required Checks Cross-Validation Rollout

**Date**: 2026-05-08
**Repos audited**: 44 (full ByronWilliamsCPA + williaby catalog)

## Summary

[1-2 sentences: how many findings, breakdown by check ID]

## True positives

[Bulleted list: repo, check ID, finding message, recommended remediation owner]

## Registry gaps filled

[Bulleted list: reusable workflows added or check names added during the dry-run]

## False positives

[Should be empty. If non-empty, mark plan as blocked and link to fix.]

## Decisions log

- Whether CI-014..017 removal is final or staged.
- Whether any repo gets a temporary override during transition.
```

Fill the placeholders with real data from step 2.

- [ ] **Step 5: Commit retrospective**

```bash
git add compliance-retrospectives/2026-05-08-required-checks-rollout.md
git commit -m "docs(compliance): retrospective for CI-022/023/024 rollout

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

- [ ] **Step 6: Push branch and open PR**

```bash
git push -u origin feat/required-checks-cross-validation
gh pr create --title "feat: required checks cross-validation (CI-022/023/024)" --body "$(cat <<'EOF'
## Summary

- Replaces hardcoded CI-014..017 with manifest-driven CI-022/023/024
- Adds reusable-workflow-jobs registry to resolve org-level workflow references
- New `scripts/check-required-checks.py` validates manifest, workflows, and branch protection contexts in one pass
- New `scripts/seed-reusable-workflow-registry.py` populates the registry from a local clone
- Wired into `ossf-compliance-auditor` agent with remediation prompts

## Test plan

- [ ] `pytest tests/unit/test_check_required_checks.py tests/integration/test_check_required_checks_integration.py tests/unit/test_seed_reusable_workflow_registry.py -v --cov=scripts`
- [ ] Manual `/repo-audit` against one ByronWilliamsCPA repo with intentional branch protection drift, confirm CI-023 finding fires
- [ ] Manual `/repo-audit` against compliant repo, confirm zero findings

## Spec and plan

- Spec: `docs/superpowers/specs/2026-05-08-required-checks-cross-validation-design.md`
- Plan: `docs/superpowers/plans/2026-05-08-required-checks-cross-validation.md`
- Retrospective: `compliance-retrospectives/2026-05-08-required-checks-rollout.md`

Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

---

## Self-Review Notes

Spec coverage check:

- Section 1 (manifest schema) → Task 1
- Section 2 (validation logic, all four steps) → Tasks 2, 3, 4, 5, 6, 7
- Section 3 (remediation flow) → Task 8 (agent prompt updates)
- Section 4 (bootstrap and migration) → Task 1 (seed manifest), Task 9 (seed script), Task 10 (dry-run + override migration)
- Section 5 (testing strategy: three layers) → Layer 1 in Tasks 2-6, Layer 2 in Task 7, Layer 3 in Task 10

No spec section without a covering task. No placeholder steps.

Type and signature consistency: `extract_produced_check_names(workflow_yaml: str, registry: dict) -> set[str]` is used identically in Tasks 2, 3, 4, 5, 7, and 9. `Finding` dataclass introduced in Task 6 is used in 7. Diff function signatures match between definition (Task 6) and consumption in CLI (Task 7).
