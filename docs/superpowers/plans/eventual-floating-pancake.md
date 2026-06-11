---
schema_type: planning
title: "Merge-queue readiness + py310/TOOL-011 across the green-repo cohort"
status: draft
owner: engineering
purpose: "Extend Renovate automerge rollout (Stage 2) by adding GitHub merge queues (CI-062) and verifying py310 floor + TOOL-011 compliance across the six green-main repos. Prerequisite for widening lockFileMaintenance automerge beyond the gleif canary. gleif canary verified green 2026-06-08; five repos remain."
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

## Current state (verified live via `gh api`, 2026-06-08)

gleif is **done and verified**: all four required-check callers emit on `merge_group`, the
`merge_queue` rule is present, and a real queue cycle has gone green. This also **empirically retires
the upstream unknown** (execution-order step 1): the shared `.github/.github/workflows/python-ci.yml`
gate job demonstrably runs on `merge_group`, otherwise gleif's queue could not have passed. No
upstream risk remains for the other five.

| Repo | `merge_group` callers | queue rule | Step-1 work left | Open PRs / greenness |
| --- | --- | --- | --- | --- |
| gleif | 4 of 4 | present | DONE + verified | n/a (canary) |
| .github (org) | 0 of 3 (`ci.yml` absent, correct) | absent | 3 workflows | **0 open PRs (cleanest)** |
| rag-processor | 4 of 4 | present | DONE + verified 2026-06-09 | n/a (queue cycle green) |
| audio-processor | 4 of 4 | present | DONE + verified 2026-06-09 | n/a (queue cycle green) |
| williaby/image-generation | 4 of 4 (inert) | **BLOCKED (platform)** | n/a | merge queue is org-only; williaby is a User account |
| llc-manager | 0 of 4 | absent | 4 workflows | **8 PRs, 6 with FAILURE, #15 DIRTY (conflict)** |

No `merge_group`/merge-queue remediation PRs are in flight on any of the five; every open PR is
Renovate/Dependabot/qlty/compliance traffic. (The recurring `PENDING:3` rollup on most PRs is the
three required checks that do not yet emit on `merge_group` sitting unreported; it is not a failure
signal and clears once step 1 lands.)

**Greenness gate before enabling a queue:** a merge queue serializes and re-tests entries, so feeding
it a red or conflicted backlog is wasteful and slow. rag-processor, audio-processor, and .github are
green/empty and ready. **llc-manager is not**: 8 open PRs with failures on six and a merge conflict on
\#15. Its backlog must be triaged to green (merge/close stale PRs, resolve #15) BEFORE enabling its
queue; otherwise defer llc-manager entirely.

## Scope of this plan

In scope: piece 3 only (pieces 1+2 verified done). Repos: audio-processor, llc-manager,
rag-processor, williaby/image-generation, .github, and **re-mediating gleif** (not skipping it).

Out of scope (separate RUNBOOK stages): the actual `lockFileMaintenance`/vuln automerge flip
(Stage 2, homelab-infra global config + a week-long canary watch), and the broader Renovate
rollout stages.

## The canonical merge_queue parameters (from gleif's live ruleset)

```text
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

**CORRECTED MECHANISM (2026-06-09, learned on .github).** Do NOT PATCH the "main ruleset" to add the
rule. The default-branch baseline ruleset (`ByronWilliamsCPA-default-branch-baseline`, id 16183607)
is an **organization-level ruleset** (`source_type=Organization`); editing it would enable merge
queue on EVERY repo in the org at once, the opposite of a sequenced rollout. gleif itself does not
touch the org baseline: it carries a **separate repo-level ruleset** (`gleif-merge-queue-pilot`,
`source_type=Repository`) holding only the `merge_queue` rule. Repo-level rulesets layer additively
on top of the org baseline, enabling the queue on exactly one repo with zero blast radius.

So Step 2 is: once the workflow PR is on `main`, POST a new **repo-level** ruleset containing only the
merge_queue rule, scoped to `~DEFAULT_BRANCH`, with the canonical parameters above:

```bash
cat > /tmp/<repo>-mq.json <<'JSON'
{
  "name": "<repo>-merge-queue",
  "target": "branch",
  "enforcement": "active",
  "bypass_actors": [],
  "conditions": {"ref_name": {"exclude": [], "include": ["~DEFAULT_BRANCH"]}},
  "rules": [{"type": "merge_queue", "parameters": {
    "check_response_timeout_minutes": 60, "grouping_strategy": "ALLGREEN",
    "max_entries_to_build": 5, "max_entries_to_merge": 5, "merge_method": "SQUASH",
    "min_entries_to_merge": 1, "min_entries_to_merge_wait_minutes": 5}}]
}
JSON
gh api repos/<org>/<repo>/rulesets -X POST --input /tmp/<repo>-mq.json   # creates repo-level ruleset
gh api repos/<org>/<repo>/rules/branches/main --jq '[.[].type]'         # verify merge_queue present
```

gleif already has its repo-level pilot ruleset; for gleif, step 1 was the actual fix. **.github DONE
2026-06-09**: repo-level ruleset `dotgithub-merge-queue` (id 17456620) created; merge_queue live on
main, params match gleif, no org spillover (audio/rag/llc still show none).

### Sequencing (mandatory)

```text
For each repo:  workflow PR (merge_group) -> MERGE -> enable merge_queue rule -> observe one queue cycle
```

Enabling the rule before the workflow change is on `main` reproduces the 60-minute hang. Do the two
steps as an ordered pair per repo; do not batch all ruleset enables before the workflow PRs land.

## Risks and guardrails

- **Org-ruleset blast radius (primary, learned 2026-06-09):** the default-branch baseline ruleset is
  org-level (`source_type=Organization`, shared id 16183607 across all repos). NEVER add the
  merge_queue rule by editing it; that enables the queue org-wide in one shot. Always POST a new
  repo-level ruleset (`<repo>-merge-queue`) as gleif does. Verify `source_type=Repository` on the
  ruleset you create.
- **Hung queue:** never enable the rule on a repo whose required checks do not yet emit on
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

**Enqueue mechanics (learned on rag-processor 2026-06-09):** `gh pr merge <n> --squash` on a
queue-enabled repo prints `! The merge strategy for main is set by the merge queue` and exits 0; do
NOT read that as a failure or pass a strategy flag. Confirm the PR actually entered the queue via
GraphQL `pullRequest(number:N){ isInMergeQueue }` and `mergeQueue{ entries }`, not the gh message or
mergeStateStatus (which stays UNSTABLE while queued). GitHub then creates a
`gh-readonly-queue/main/pr-<n>-<sha>` ref; `gh run list --event merge_group` shows the four caller
workflows running on it. A clean cycle merges in 2-3 min.

## Recommended execution order and breakpoints

Steps 1-2 below are COMPLETE as of 2026-06-08 (gleif verified green; upstream reusable proven on
`merge_group`). Remaining order is **resequenced by live greenness** rather than the original
arbitrary order, easiest/cleanest first:

```text
1. [DONE] .github reusable check -- python-ci.yml gate-job runs on merge_group (proven by gleif)
2. [DONE] gleif: step 1 + step 2 + one verified queue cycle  -- canary green
   >>> breakpoint CLEARED: gleif queue confirmed working <<<
3. [DONE 2026-06-09] .github: PR #197 merged (3 callers emit merge_group); repo-level ruleset
   `dotgithub-merge-queue` (17456620) enabled. Pending: watch one queue cycle (no open PRs yet).
4. [DONE 2026-06-09] rag-processor: PR #81 merged (4 callers emit merge_group); repo-level
   ruleset `rag-processor-merge-queue` (17462423) enabled; queue cycle VERIFIED GREEN by merging
   PR #80 (uv.lock) end-to-end (all 4 required checks ran+passed on the merge_group ref; merged in
   <3 min). No org spillover (audio/llc/fragrance still show none).
5. [DONE 2026-06-09] audio-processor: PR #68 merged (3 callers; ci.yml already had merge_group);
   repo-level ruleset `audio-processor-merge-queue` (17468286) enabled; queue cycle VERIFIED GREEN
   by merging PR #67 (uv.lock) end-to-end (all 4 required checks ran+passed on merge_group ref;
   merged in ~3.5 min). No org spillover.
6. [BLOCKED - PLATFORM 2026-06-09] williaby/image-generation: step 1 PR #66 merged (4 callers emit
   merge_group), BUT step 2 is impossible: GitHub merge queue is available only on
   ORGANIZATION-owned repos (public org repos, or private org repos on Enterprise Cloud); williaby
   is a personal User account, so `POST /rulesets` with a merge_queue rule returns
   `422 Invalid rule 'merge_queue'`. The merge_group triggers now on main are inert and harmless
   (merge_group events never fire without a queue) and are forward-compatible if the repo ever moves
   to an org. No ruleset was created. Cannot be completed without transferring the repo to an org.
   (Docs: merge queue "available in any public repository owned by an organization, or in private
   repositories owned by organizations using GitHub Enterprise Cloud".)
7. llc-manager: DEFERRED (decision 2026-06-08). 8-PR backlog with 6 failures + #15 DIRTY conflict;
   excluded from this rollout. Revisit only after the backlog is triaged to green; until then it
   stays on PR-only checks with no merge queue.
```

Remaining work: NONE achievable. Active-scope rollout COMPLETE 2026-06-09 (gleif, .github,
rag-processor, audio-processor all DONE + verified). williaby/image-generation is BLOCKED by a
GitHub platform limitation (merge queue is org-only; williaby is a User account), not deferrable
without an org transfer. llc-manager remains deferred (red backlog). The two excluded repos are
excluded for unrelated reasons: image-generation = platform-impossible, llc-manager = dirty backlog. It is a focused multi-PR
effort, not a single mechanical sweep; do the two steps as an ordered pair per repo (workflow PR ->
merge -> enable -> observe one cycle), never batch all ruleset enables before the workflow PRs land.
