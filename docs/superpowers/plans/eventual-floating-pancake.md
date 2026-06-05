---
schema_type: planning
title: "Merge-queue readiness + py310/TOOL-011 across the green-repo cohort"
status: draft
owner: engineering
purpose: "Extend Renovate automerge rollout (Stage 2) by adding GitHub merge queues (CI-062) and verifying py310 floor + TOOL-011 compliance across the six green-main repos. Prerequisite for widening lockFileMaintenance automerge beyond the gleif canary."
component: Development-Tools
source: "docs/reference/renovate-architecture.md"
tags:
  - ci_cd
  - compliance
  - automation
  - planning
---

## Context

The Renovate automerge rollout (`~/dev/_dep-analysis-handoff/RUNBOOK.md`, Stage 2) cannot widen
the `lockFileMaintenance` automerge flip beyond the gleif canary until the other green-main repos
have a GitHub **merge queue** (CI-062). Without it, N auto-merging Renovate PRs trigger an
N(N+1)/2 CI-cost cascade. The user asked to apply, across six repos, three things "where missing,
skip where present": **(1) move the Python floor to 3.10, (2) satisfy TOOL-011, (3) add the merge
queue.**

Read-only assessment of `origin/main` for all six changed two of the three pieces into no-ops and
exposed a latent defect in the "working" canary:

| Repo | requires-python | ruff target | TOOL-011 | merge_queue | `merge_group` coverage |
| --- | --- | --- | --- | --- | --- |
| audio-processor | >=3.11 | py311 | PASS | absent | ci.yml only (1 of 4 checks) |
| gleif (canary) | >=3.11 | py311 | PASS | **present** | ci.yml only (1 of 4 checks) |
| llc-manager | >=3.12 | py312 | PASS | absent | none |
| rag-processor | >=3.11 | py312 | PASS | absent | none |
| williaby/image-generation | >=3.10 | py310 | PASS | absent | none |
| .github (org config) | no pyproject | N/A | N/A | absent | none |

**Conclusions:**

1. **Pieces 1 + 2 (py310 floor + TOOL-011) are a fleet-wide no-op.** Every Python repo already has
   `requires-python >= 3.10` and `ruff target-version >= py310`; `.github` has no `pyproject.toml`.
   There is NO modernization sweep to run (unlike xero-crypto, which was stale py39). Nothing to do.
2. **Piece 3 (merge queue) is the real work, and it is not just a ruleset toggle.** The four required
   status checks (`CI Gate`, `Security Analysis / Security Gate Validation`,
   `Dependency & Standards Validation`, `Check REUSE Compliance`) are produced by four separate
   per-repo workflows that are **callers of org reusable workflows** in `.github`
   (e.g. `pr-validation.yml` -> `ByronWilliamsCPA/.github/.github/workflows/python-ci.yml`). Only
   `ci.yml` emits on `merge_group`. The other three caller workflows are `pull_request`-only.
3. **gleif's queue has a latent hang.** Even gleif (queue already enabled) emits `merge_group` only
   from `ci.yml`; 3 of its 4 required checks would never report in the queue and time out after
   `check_response_timeout_minutes: 60`. gleif is **not** a verified-green canary; it is configured
   but unexercised. It needs the same `merge_group` additions, not a skip.

Per CI-040, "workflows must emit on `merge_group` or the queue waits forever." So the unit of work
is: add `merge_group` to every required-check caller workflow (CI-040), confirm those jobs pass in
the `merge_group` context, THEN enable the queue rule (CI-062).

## Scope of this plan

In scope: piece 3 only (pieces 1+2 verified done). Repos: audio-processor, llc-manager,
rag-processor, williaby/image-generation, .github, and **re-mediating gleif** (not skipping it).

Out of scope (separate RUNBOOK stages): the actual `lockFileMaintenance`/vuln automerge flip
(Stage 2, homelab-infra global config + a week-long canary watch), and the broader Renovate
rollout stages.

## The canonical merge_queue parameters (from gleif's live ruleset)

```
check_response_timeout_minutes: 60
grouping_strategy: ALLGREEN
max_entries_to_build: 5
max_entries_to_merge: 5
merge_method: SQUASH
min_entries_to_merge: 1
min_entries_to_merge_wait_minutes: 5
```

## Per-repo pattern (apply to all six, including gleif)

### Step 1 - workflow PR: add `merge_group` to required-check callers (CI-040)

For each repo, map its required status checks to the caller workflow that produces each, then add
`merge_group:` to that workflow's `on:` block. Representative mapping (audio-processor / gleif;
confirm names per repo at execution, image-generation's check is `Security Gate Validation` without
the `Security Analysis /` prefix, and `.github` requires only 3 checks, no `CI Gate`):

| Required check | Caller workflow | Has merge_group today |
| --- | --- | --- |
| CI Gate | `.github/workflows/ci.yml` | yes (audio, gleif); add elsewhere |
| Security Analysis / Security Gate Validation | `.github/workflows/security-analysis.yml` | no, add |
| Dependency & Standards Validation | `.github/workflows/pr-validation.yml` | no, add |
| Check REUSE Compliance | `.github/workflows/reuse.yml` | no, add |

Use `ci.yml` (already correct) as the in-repo template for the trigger form. Critical per-workflow
validation: these jobs run in the `merge_group` event context where `github.event.pull_request.*`
is null. Each required job must still RUN and PASS on `merge_group`; any PR-only step (PR comments,
PR-number lookups) must be guarded with `if: github.event_name != 'merge_group'`, never gate the
whole gate job out. Confirm the called org reusable (`python-ci.yml`) does not skip its gate jobs on
non-PR events; if it does, that reusable in `.github` must be fixed first (it is a shared dependency
of every caller).

- Branch `ci/merge-group-triggers` (or `fix/merge-queue-readiness`) from the repo's `origin/main`,
  in `.worktrees/<slug>`. Signed commits, Conventional Commits, no em-dash. `pre-commit run
  --all-files` clean. `gh pr create` (fallback `gh api repos/<org>/<repo>/pulls -X POST` if denied).
- Stage explicit paths only (shared-clone whole-file hazard; never `git add -A`).
- Conventional type: `ci:`.

### Step 2 - enable the merge queue (CI-062), AFTER step 1 merges

Only once the workflow PR is merged to `main` (so the required checks actually emit on
`merge_group`), add the merge_queue rule to the main ruleset. Find the main ruleset id and PATCH its
rules to append a `merge_queue` rule with the canonical parameters above:

```
gh api repos/<org>/<repo>/rulesets --jq '.[] | select(.target=="branch") | {id,name}'
gh api repos/<org>/<repo>/rulesets/<id>            # read current rules
gh api repos/<org>/<repo>/rulesets/<id> -X PUT ...  # add merge_queue rule, preserve all others
```

gleif already has the rule; for gleif, step 2 is verify-only (its parameters already match). For
gleif, step 1 is the actual fix.

### Sequencing (mandatory)

```
For each repo:  workflow PR (merge_group) -> MERGE -> enable merge_queue rule -> observe one queue cycle
```

Enabling the rule before the workflow change is on `main` reproduces the 60-minute hang. Do the two
steps as an ordered pair per repo; do not batch all ruleset enables before the workflow PRs land.

## Risks and guardrails

- **Hung queue (primary):** never enable the rule on a repo whose required checks do not yet emit on
  `merge_group`. This is why gleif is re-mediated, not skipped.
- **merge_group event context:** gate jobs must pass without PR context; validate per workflow.
- **Shared reusable:** if `.github/.github/workflows/python-ci.yml` skips gate jobs on non-PR events,
  fix that reusable first; it is the upstream of every caller.
- **Outward-facing on a financial fleet:** ruleset edits and workflow changes are visible and
  trigger CI; do them per repo with verification, not as a blind batch.
- **Path restrictions:** workflow files may sit under a restricted-path ruleset (seen on xero-crypto
  pyproject); expect a bypass notice and surface it.
- **No-op pieces:** do NOT touch `requires-python` or `ruff target-version` anywhere; they already
  pass. Do not introduce `[tool.mypy]`/`[tool.black]` targets (TOOL-002/003 require those absent).

## Verification (per repo)

1. After the step-1 PR merges, open a trivial test PR (or use the next Renovate PR) and confirm the
   four required checks report on the `merge_group` ref, not just `pull_request`. Concretely: enable
   the queue, add the PR to the queue, and confirm all four checks run and report within the 60-min
   timeout (they should finish in minutes).
2. `gh api repos/<org>/<repo>/rules/branches/main --jq '[.[].type]'` includes `merge_queue`.
3. Watch one real merge-queue cycle end-to-end (gleif first, as the now-properly-covered canary)
   before relying on automerge widening.

## Recommended execution order and breakpoints

```
1. .github reusable check (does python-ci.yml gate-job run on merge_group?)  -- upstream gate
2. gleif: step 1 (merge_group PR) -> merge -> verify its existing queue now passes  -- fix the canary
   >>> breakpoint: watch one gleif queue cycle before widening <<<
3. audio-processor, llc-manager, rag-processor, image-generation: step 1 PR -> merge -> step 2 enable
4. .github: step 1 PR (3 checks, no CI Gate) -> merge -> step 2 enable
```

This is roughly 5-6 workflow PRs + 5 ruleset enables + gleif verification, sequenced and
outward-facing. It is a focused multi-PR effort, not a single mechanical sweep; given the canary
verification spans a real merge cycle, it cannot fully "complete" in one sitting.
