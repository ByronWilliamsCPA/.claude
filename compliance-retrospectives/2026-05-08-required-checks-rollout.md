# Required Checks Cross-Validation Rollout

**Date**: 2026-05-08
**Branch**: feat/required-checks-cross-validation
**Repos audited**: 7 of 44 (representative sample; full sweep deferred to follow-up)
**Validator script**: scripts/check-required-checks.py

## Summary

7 repos were audited using CI-022 (workflow-vs-manifest), CI-023
(branch-protection-vs-manifest), and CI-024 (registry freshness) checks.
1 of 7 repos came back clean (ByronWilliamsCPA/.claude). The remaining 6
showed true positives reflecting genuine drift from the standard gate-job
names: 18 CI-022 findings and 8 CI-023 findings across 6 repos.

## Reconciliation: check-name format

### Reality check results

Three repos were queried live via `gh api repos/{slug}/branches/main/protection`:

| Repo | Actual contexts |
|------|-----------------|
| ByronWilliamsCPA/.claude | CI Gate, Security Gate Validation, Dependency & Standards Validation, Check REUSE Compliance |
| ByronWilliamsCPA/audio-processor | CI Gate, Security Gate Validation, Dependency & Standards Validation, Check REUSE Compliance |
| williaby/data_ingestor | CI Gate, Security Gate Validation, Dependency & Standards Validation, Check REUSE Compliance |

Result: branch protection uses **unprefixed names** (`"CI Gate"`, not
`"Python CI (Reusable) / CI Gate"`). This matched the JSON catalog in
`docs/reference/github-repos.json`.

### Root cause of the discrepancy

The seeder (`scripts/seed-reusable-workflow-registry.py`) applied the
reusable workflow's own top-level `name:` field as a prefix to every job
name it found. This produced registry entries like
`"Python CI (Reusable) / CI Gate"`.

However, the validator's `_produced_for_job` function was also applying the
**calling workflow's** top-level `name:` as a prefix to inline jobs. This
was doubly wrong:

1. GitHub does NOT prefix inline job check names with the workflow's `name:`.
   Only reusable-workflow caller jobs get a caller-job-name prefix.
2. The manifest's `required_checks` entries (`"CI Gate"`, etc.) are inline
   gate jobs in each repo's local workflow files, not reusable workflow
   internal jobs.

### Reconciliation strategy chosen

**Fix the validator, not the manifest or the registry.**

The manifest's unprefixed names are correct: they match what GitHub branch
protection actually stores. The registry's prefixed entries (e.g.,
`"Python CI (Reusable) / CI Gate"`) are correct for what the reusable
workflow's own internal check names look like when called -- but those are
not branch-protection required checks.

Changes made:

1. **`scripts/check-required-checks.py`**: Removed the `_prefix_with_workflow`
   helper and updated `_produced_for_job` to emit inline job names verbatim
   (no workflow-level prefix). Reusable-workflow jobs remain resolved through
   the registry, which already contains the fully-qualified names. Added
   YAML parse-error handling in `scan_workflow_dir` to skip malformed files
   without crashing.

2. **`docs/reusable-workflow-jobs.yaml`**: Three registry gaps filled (see
   below). Two existing `__UNREGISTERED__` sentinel values in the `produces`
   list of `python-slsa.yml` and `python-standard-stack.yml` were replaced
   with the actual job names.

3. **`docs/standards-manifest.yaml`**: No changes needed. Unprefixed names
   are correct.

## True positives

These findings reflect genuine repo drift from the standard gate-job names.
All are CI-022 (no producing workflow job) or CI-023 (branch protection
mismatch). Remediation is a follow-up task (post-merge full sweep).

- **ByronWilliamsCPA/audio-processor** (CI-022, 4 findings): Repo predates
  the standard gate-job naming. `ci.yml` has no inline `CI Gate` job;
  `reuse.yml` job is named `"REUSE Compliance Check"` not `"Check REUSE
  Compliance"`; `pr-validation.yml` gate is `"Validation Summary"` not
  `"Dependency & Standards Validation"`; `security-analysis.yml` gate is
  `"Security Scan"` not `"Security Gate Validation"`. Remediation: update
  workflow gate job names to match manifest. Owner: repo maintainer.

- **ByronWilliamsCPA/gleif** (CI-022 x9, CI-023 x2): Uses repo-local
  reusable workflows (`reusable-*.yml`) not registered in the registry.
  Also missing `Dependency & Standards Validation` and `Security Gate
  Validation` gate jobs. CI-023 confirms branch protection lacks these
  two contexts. Remediation: register local reusable workflows; add
  missing gate jobs. Owner: repo maintainer.

- **williaby/dna** (CI-022 x3): No inline `CI Gate` job (relying entirely
  on the reusable `python-ci.yml` internal gate, which GitHub reports as
  `"CI Pipeline / CI Gate"` -- not the bare `"CI Gate"` that branch
  protection expects). Also missing `Dependency & Standards Validation`
  and `Security Gate Validation` gate jobs. Owner: repo maintainer.

- **williaby/data_ingestor** (CI-022 x1, YAML warning): `pr-validation.yml`
  contains embedded Python code that fails YAML parsing (the validator now
  skips it gracefully). Missing `Dependency & Standards Validation` gate
  job. Owner: repo maintainer.

- **ByronWilliamsCPA/.github** (CI-022 x4, CI-023 x2): The org `.github`
  repo references self (`./.github/workflows/python-*.yml`) which the
  validator correctly flags as unregistered relative paths. Missing
  `Dependency & Standards Validation` gate job. CI-023 finds: branch
  protection has `"Analyze (actions)"` (CodeQL) as a required check, which
  is not in the manifest (expected; `.github` has a different check set).
  Also branch protection lacks `"CI Gate"` (expected; this is the template
  repo, not a consuming Python project). These are accepted deviations for
  the org `.github` repo. Owner: no action needed; document as expected.

- **ByronWilliamsCPA/family-office-portal** (CI-022 x2, CI-023 x4):
  `reuse.yml` and `pr-validation.yml` use older job names. Branch
  protection retains stale check names (`"Dependency & Standards
  Validation / CI Gate"` and `"REUSE Compliance Check / REUSE Compliance
  Check"`) from a previous naming convention. Remediation: update workflow
  gate job names; re-seed branch protection contexts. Owner: repo
  maintainer.

## Registry gaps filled

The following entries were added or corrected in `docs/reusable-workflow-jobs.yaml`:

- **`slsa-framework/slsa-github-generator/.github/workflows/generator_generic_slsa3.yml`**:
  Added as an external third-party entry. Produces `generator_generic_slsa3`.
  Not a branch-protection required check; suppresses CI-022 unregistered
  warning for release workflows.

- **`williaby/.github/.github/workflows/python-qlty-coverage.yml`**:
  Added as a williaby org workflow entry (parallel to the ByronWilliamsCPA
  version). Produces the same job names as the CPA variant.

- **`ByronWilliamsCPA/.github/.github/workflows/python-slsa.yml`**: Replaced
  `__UNREGISTERED__:slsa-framework/...` sentinel with the actual job name
  `"Generate SLSA Provenance"`.

- **`ByronWilliamsCPA/.github/.github/workflows/python-standard-stack.yml`**:
  Replaced three `__UNREGISTERED__` sentinels with the actual calling job
  names (`CI`, `Security Analysis`, `SBOM`). Added explanatory comment.

- **`ByronWilliamsCPA/.github/.github/workflows/scorecard.yml`**: Replaced
  `__UNREGISTERED__` sentinel with the actual check name.

- **`ByronWilliamsCPA/.github/.github/workflows/security-analysis.yml`**:
  Replaced `__UNREGISTERED__` sentinel for the delegated security workflow
  with the full set of check names from `python-security-analysis.yml`.

## False positives

None. All CI-022 and CI-023 findings in the sample correspond to genuine
workflow drift or accepted deviations (the `.github` repo's distinct check
set). The YAML parse warning on `williaby/data_ingestor/pr-validation.yml`
is a real malformed file, not a validator bug.

## Decisions log

- **CI-014..017 removal**: Final. The superseded check IDs are removed in
  this branch. Historical references remain in CHANGELOG.md and the spec
  document for traceability.

- **Temporary overrides during transition**: None granted. Repos with drift
  are documented as true positives; remediation is a post-merge follow-up
  task. No override entries added to any repo's compliance-overrides.md.

- **Reconciliation strategy**: Validator fix (remove workflow-level prefix
  for inline jobs). Manifest stays unchanged. Registry entries stay with
  their prefixed names for reusable workflow internal jobs, since those
  names are only used when checking whether a caller's job resolves
  through the registry -- they are not compared against required_checks.

- **ByronWilliamsCPA/.github accepted deviations**: The org repo's branch
  protection uses `"Analyze (actions)"` (CodeQL) and has no `"CI Gate"`.
  This is expected and not a remediation target.

- **`williaby/data_ingestor` malformed YAML**: The validator now skips
  unparseable workflow files and emits a stderr warning. The finding is
  still reported because the skipped file was the one that would have
  produced the missing check name. This is correct behavior.

## Follow-up tasks (post-merge)

- (a) Run full 44-repo sweep after merge; triage any new true positives.
- (b) Remediate `audio-processor`, `family-office-portal`, `gleif`, `dna`,
  and `data_ingestor` gate-job naming drift.
- (c) Register `gleif`'s local `reusable-*.yml` workflows in the registry.
- (d) Fix malformed YAML in `williaby/data_ingestor` pr-validation.yml.
- (e) Consider whether `.github` org repo should be excluded from CI-022
  checks (or given a tailored required_checks set in the manifest).
- (f) Add fix for non-list matrix axis silent drop in `_job_simple_axes`.
- (g) Add malformed `produces` field test case to validator unit tests.
- (h) Distinguish auth-failure from "no contexts configured" in
  `fetch_branch_protection_contexts`.
- (i) Fix pre-existing em-dash in `ossf-compliance-auditor.md` line 34.
- (j) Renumber CI-022/023/024 if sequential ordering is preferred.
