---
schema_type: common
title: Required Checks Cross-Validation Design
status: draft
owner: engineering
tags: [compliance, ci_cd, github_actions, agents, standards]
purpose: Design for cross-validating manifest required_checks against GitHub branch protection contexts and workflow job names to detect drift that hangs PRs on never-reporting status checks.
---

**Date**: 2026-05-08
**Status**: Draft
**Author**: Byron Williams

---

## Problem

Branch protection rules in GitHub list required status checks by exact string
name. Workflow files define jobs that produce these check names through a
combination of the workflow's `name:` field, each job's `name:` field (or job
key if absent), and matrix expansions. When any of these drift apart, the
required check never reports a result and PRs hang indefinitely waiting for a
status that will never arrive.

The current standards manifest (`~/.claude/docs/standards-manifest.yaml`)
checks both sides independently:

- CI-014, CI-015, CI-016 verify that specific job names appear inside specific
  workflow files via `content_present`.
- CI-017 verifies that specific strings appear in the branch protection
  contexts list.

Neither check cross-validates the two sides. Drift is invisible to the audit
until a PR sits stuck on a never-reporting check.

A common variation: jobs that produce the required check live in an
organization-level reusable workflow (for example,
`ByronWilliamsCPA/.github/.github/workflows/python-ci.yml`), so a static
parser of the local workflow only sees a `uses:` line, not a job name. Any
fix has to handle this indirection.

## Goals

- Make manifest the single source of truth for which check names are
  required across all repositories.
- Detect drift between manifest, workflow job names, and branch protection
  contexts during `/repo-audit`.
- Resolve reusable-workflow `uses:` references through a maintained registry
  so the validator sees check names that org-level workflows produce.
- Support remediation on either side (workflow file or branch protection)
  with confirmation gates appropriate to the blast radius of each change.
- Preserve the existing audit dispatch architecture; no new agent registration.

## Non-goals

- Live reconciliation against GitHub's actually-reported check names from
  recent commits. Static analysis covers the common cases; live reconciliation
  is a possible later iteration if static analysis leaves gaps.
- Auto-remediation without human confirmation. All side effects flow through
  the existing `/repo-audit` interactive remediation prompts.
- Validating workflows that are not registered for branch protection (those
  remain governed by other CI-* checks).

## Architecture

### Manifest schema

A new top-level field is added to `~/.claude/docs/standards-manifest.yaml`:

```yaml
required_checks:
  - name: "CI Gate"
    produced_by: "ByronWilliamsCPA/.github/.github/workflows/python-ci.yml"
    matrix_expansion: false
  - name: "Security Gate Validation"
    produced_by: "ByronWilliamsCPA/.github/.github/workflows/security-analysis.yml"
  - name: "Dependency & Standards Validation"
    produced_by: ".github/workflows/pr-validation.yml"
  - name: "Check REUSE Compliance"
    produced_by: ".github/workflows/reuse.yml"
```

Field semantics:

- `name` is the exact string that must appear in branch protection contexts
  and that some workflow job must produce.
- `produced_by` is either a path inside the audited repo
  (`.github/workflows/<file>.yml`) or a fully-qualified path into a known
  reusable workflow (`<org>/<repo>/.github/workflows/<file>.yml`).
- `matrix_expansion` is optional, defaults `false`. When `true`, the
  validator allows multiple actual produced names that match the pattern
  `<name> (<param>, ...)`.

### Reusable-workflow job registry

A separate registry file at
`~/.claude/docs/reusable-workflow-jobs.yaml` maps each known reusable
workflow to the check names it produces:

```yaml
ByronWilliamsCPA/.github/.github/workflows/python-ci.yml:
  produces: ["CI Gate"]
  source_repo: ByronWilliamsCPA/.github
  last_verified: 2026-05-08
ByronWilliamsCPA/.github/.github/workflows/security-analysis.yml:
  produces: ["Security Gate Validation"]
  source_repo: ByronWilliamsCPA/.github
  last_verified: 2026-05-08
```

The registry is the lookup the validator consults when it encounters a
`uses:` line in a local workflow.

### New manifest checks

Three new check IDs are added; they supersede CI-014, CI-015, CI-016, and
CI-017, which are removed in the same change.

- **CI-022 `required_checks_have_producer`** (severity: high,
  `override_eligible: false`). Every entry in `required_checks` either
  points to a local workflow file that defines a job with that name, or
  points to a reusable workflow whose registry entry includes that name.
- **CI-023 `branch_protection_matches_required_checks`** (severity: high,
  `override_eligible: false`). Branch protection contexts equal
  `required_checks[].name` exactly (set equality).
- **CI-024 `registry_freshness`** (severity: medium,
  `override_eligible: false`). Every reusable workflow listed in the
  registry has a `last_verified` date within 90 days of the audit date.

### Validation logic

The new function `verify_required_checks(repo_path, manifest)` is added to
the existing `ossf-compliance-auditor`. It runs once per audit and emits
findings for CI-022, CI-023, and CI-024.

#### Step 1: build the `expected` set

`expected = {entry.name for entry in manifest.required_checks}`.

#### Step 2: build the `produced` set from local workflows

For each `.yml` file in `<repo>/.github/workflows/`:

1. Parse the YAML.
2. The workflow's top-level `name:` is recorded for diagnostic purposes
   only; it is NOT used as a check-name prefix for inline jobs (see note
   below).
3. For each job:
   - If the job has a `uses:` field referencing a reusable workflow, look
     it up in `reusable-workflow-jobs.yaml`. Add every name in `produces`
     to the produced set. If the reusable workflow is not in the registry,
     emit a CI-022 finding noting the unregistered reference.
   - Otherwise (locally-defined job):
     - Without `strategy.matrix`: produced name is `job.name` if present,
       else the job key.
     - With `strategy.matrix`: emit one produced name per matrix
       combination using the format `<job-name> (<param1>, <param2>, ...)`.
       The job name comes from `job.name` interpolated with matrix
       variables. Limitation: only direct `${{ matrix.<key> }}`
       references are interpolated; complex template expressions
       (functions, fromJSON, conditionals) are not. Workflows using
       complex matrix templates should be modeled in the registry
       instead of parsed from source.

> **Empirical correction (Task 10 dry-run, 2026-05-08):** GitHub does NOT
> prefix inline job check names with the workflow's top-level `name:`
> field. Only reusable-workflow CALLER jobs receive a prefix
> (`<calling-job-name> / <called-job-name>`). The validator's
> `_produced_for_job` was corrected accordingly; the earlier text in this
> spec that suggested workflow-level prefixing for inline jobs was wrong.
> Verified by querying live `gh api repos/{slug}/branches/main/protection`
> across multiple repos: branch protection contexts use unprefixed names
> like `"CI Gate"` and `"Security Gate Validation"`.

#### Step 3: build the `actual` set from branch protection

Reuse the existing call:

```bash
gh api repos/{slug}/branches/main/protection \
  --jq '.required_status_checks.contexts'
```

The `actual` set is the array returned.

#### Step 4: emit findings

- CI-022 fails if `expected - produced` is non-empty:
  `"Required check '<name>' has no producing workflow job. Manifest expects
  it to come from <produced_by>."`
- CI-023 fails if `expected != actual`. For each name in `expected -
  actual`: `"Required check '<name>' missing from branch protection
  contexts."` For each name in `actual - expected`: `"Branch protection
  requires '<name>' but manifest does not list it as a required check."`
- CI-024 fails for any registry entry where `last_verified` is older than
  90 days as of the audit date.

#### Edge cases

- Job with `if: false` or other job-level conditional: still treated as
  producing the check, since GitHub reports skipped checks as completed
  and that satisfies branch protection.
- Workflow with no top-level `name:`: produced check name is the job
  name alone. The same is true when a top-level `name:` is present: GitHub
  does NOT prefix inline job check names with the workflow's `name:` (see
  the empirical correction note in Step 2).
- Multiple workflows defining a job with the same name: produced set is
  deduplicated, no conflict flagged.
- Empty workflow file or invalid YAML: produces an empty contribution to
  the set and emits a separate parsing-error finding (does not crash the
  audit).

## Remediation flow

When `/repo-audit` runs in interactive mode and CI-022 or CI-023 findings
exist, the existing remediation prompt loop gains specialized handlers per
finding type.

### Finding type 1 - workflow missing a required check (CI-022)

User selects a fix via `AskUserQuestion`:

- **Add a job to the local workflow.** When `produced_by` is a local path,
  generate a stub job with the required `name:` and a TODO body, append to
  that file. User reviews the diff before commit.
- **Update the registry.** When `produced_by` is a reusable workflow whose
  registry entry is incomplete, add the missing name to
  `reusable-workflow-jobs.yaml` and bump `last_verified`.
- **Remove from manifest.** When the required check is no longer required,
  remove the entry from `manifest.required_checks`. Highest blast radius;
  requires explicit typed confirmation including a reason.

### Finding type 2 - branch protection drift (CI-023)

User selects a fix via `AskUserQuestion`:

- **Update branch protection contexts.** Issue
  `gh api repos/{slug}/branches/main/protection/required_status_checks
  --method PATCH --field contexts='[...]'` with the manifest's
  `required_checks[].name` list. Visible-to-others action; requires a
  diff-display and typed `yes` confirmation.
- **Update the manifest.** When live branch protection is correct and
  manifest is stale, edit `manifest.required_checks` to match. Same
  cross-repo blast-radius warning as the type 1 manifest fix.

### Finding type 3 - registry staleness (CI-024)

- **Re-verify the reusable workflow.** Fetch the workflow from
  `ByronWilliamsCPA/.github` and re-parse, or prompt the user to confirm
  the `produces` list manually. On confirmation, bump `last_verified` to
  the audit date.

### Confirmation gates

- Workflow-file edits: diff display, single confirmation.
- Registry edits: diff display, single confirmation.
- Manifest `required_checks` edits: diff display, single confirmation,
  flagged as cross-repo impact.
- Branch protection API calls: full PATCH payload display, typed `yes`
  required to proceed.

### Batch mode

When multiple findings share a fix shape (for example, three required
checks all missing from branch protection), the prompt offers a single
"fix all branch protection drift in one PATCH" option to consolidate
confirmations.

## Bootstrap and migration

The new checks must not ship with empty data; the existing CI-014..017
checks must be removed in the same change. Five steps:

1. **Seed `required_checks` in the manifest.** Pull the contract from
   CI-017's existing `branch_protection_contexts` value and the implied
   jobs in CI-014/015/016. Commit the new field with a clear message.
2. **Seed `~/.claude/docs/reusable-workflow-jobs.yaml`.** Run a one-shot
   script (`scripts/seed-reusable-workflow-registry.py`) that clones
   `ByronWilliamsCPA/.github` and parses each
   `.github/workflows/*.yml` to emit registry entries. Output reviewed
   and committed.
3. **Remove superseded checks.** Delete CI-014, CI-015, CI-016, CI-017 in
   the same commit that adds CI-022, CI-023, CI-024. Migrate any
   `compliance-overrides.md` entries that reference the old IDs.
4. **Dry-run across all repos.** Before merging, run
   `/repo-audit --scheduled` against the 44-repo catalog. Investigate
   every finding: real problem the old checks missed, or registry gap
   needing seeding. Adjust seeded data, then merge.
5. **Update affected documentation.** The standards manifest (the
   migration itself), repo-compliance skill workflow files if they
   reference CI-014..017 by ID, and a migration note in
   `~/.claude/docs/reference/compliance-changes.md`.

## Testing strategy

Three layers, each catching a different kind of regression.

### Layer 1: unit tests on validator pure logic

Each step of the validation logic becomes a testable function with
file-fixture inputs and JSON-fixture expected outputs:

- `extract_produced_check_names(workflow_yaml: str, registry: dict) ->
  set[str]`. Fixtures cover single job no `name:`, single job with
  `name:`, top-level workflow `name:`, matrix one parameter, matrix two
  parameters, registered reusable workflow lookup, unregistered reusable
  workflow (must warn), `if: false` job, empty workflow.
- `diff_required_vs_produced(required, produced) -> list[Finding]`. Set
  algebra; trivial coverage.
- `diff_required_vs_branch_protection(required, contexts) ->
  list[Finding]`. Same.

Coverage target: 90% line coverage on the validator module, 100% on the
two diff functions (contract enforcers).

Fixture locations: `tests/fixtures/workflows/`,
`tests/fixtures/registries/`.

### Layer 2: integration tests against fake repos

A `tests/fixtures/fake-repo/` directory contains minimal
`.github/workflows/` trees for each scenario (compliant, missing job,
drifted name, matrix mismatch). Tests invoke `verify_required_checks`
against each, asserting expected finding IDs and messages.

The `gh api` branch-protection call is mocked at the subprocess
boundary; mocks return hand-crafted JSON per fixture.

### Layer 3: dry-run validation against real repos

After unit and integration tests pass, `/repo-audit --scheduled` runs
against the 44-repo catalog. Output is the final gate: every finding
must be justified. False positives block merge.

### Deliberate exclusions

- Interactive remediation prompts are validated manually on a seeded
  repo. Mocking `AskUserQuestion` flows is brittle and the underlying
  validator is already covered.
- Live `gh api PATCH` calls for branch protection are dry-run only in
  tests; real execution is gated by the typed-confirmation step.

## Open questions

None at this time. All design questions resolved during brainstorming.

## Decisions log

- Manifest is single source of truth for required check names (vs.
  branch protection or workflow files winning).
- Static analysis with matrix awareness is the validation depth (vs.
  static-only or live-API reconciliation).
- Manual registry file maps reusable workflows to produced check names
  (vs. dynamic resolution via `gh api` or no resolution).
- Auto-remediation supports both sides with appropriate confirmation
  gates per blast radius (vs. report-only or workflow-only).
- New checks live in `ossf-compliance-auditor` (vs. a new dedicated
  agent or a split across multiple agents).
