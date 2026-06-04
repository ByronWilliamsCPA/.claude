---
schema_type: common
title: PR Review Premise Gate Design
status: draft
owner: engineering
tags: [skills, tooling, automation, standards, guardrails]
purpose: Design for a "premise gate" added to the /pr-review workflow that critically assesses whether an AI-authored change is appropriate and an improvement, not just internally correct. Adds an Opus-backed Agent M running four evidence-grounded checks (regression/reverted code, contradicts-recorded-decision, unjustified churn, better-alternative), fed by two cheap risk signals, branch staleness and cross-PR overlap. Overlap detection spans two dimensions, file-path and symbol, because the validating real example (rag-processor PRs 63/68/73) shows two PRs defining the same symbol in different files, which path-only overlap misses. The gate emits an OK/QUESTION/HOLD verdict at the report top and a HOLD interposes one confirmation before /pr-fix; a targeted scoring-cap fix lets evidence-backed regression findings reach Critical.
---

## Problem

The `/pr-review` workflow runs 12 parallel agents (A through L) that collectively
answer one kind of question: **is this change internally correct?** They scan the
diff for bugs, silent failures, type design, security, performance, CLAUDE.md
compliance, and architectural quality. Every one of them accepts the premise that
the change *should exist*.

In a codebase where most work is AI-developed, that premise cannot be assumed. An
AI-authored branch can:

- Reintroduce code, config, or patterns that a prior commit deliberately removed or
  reverted (stale-branch regression).
- Reverse a decision recorded in an ADR, CHANGELOG, or prior PR review.
- Add lateral churn, speculative generality, or scope nobody asked for.
- Solve a real problem in a way that is clearly worse than a pattern the repo
  already uses elsewhere.
- Collide with a concurrent open PR touching the same files (duplicate or competing
  work; post-merge breakage even when each branch is independently green).

No current agent asks **"should this change exist, and is it actually an improvement
over what is there now?"** The one signal that could catch the regression case,
Agent C (Git History), is actively suppressed: the Step 6 scoring rubric caps any
C or D finding at score 20 unless it points to a specific fixable diff line, so a
"this re-adds code that commit X removed" finding lands in Informational and is never
seen.

## Goal

Add a critical premise assessment to `/pr-review` that challenges whether a change is
appropriate and an improvement, **without** relitigating every intentional design
decision. The discipline that reconciles those two aims is **risk-proportional
scrutiny**: cheap, objective signals (branch staleness, file contestedness) decide
how hard the gate looks, and every appropriateness finding must cite concrete
evidence or be dropped.

## Non-Goals

- Blocking merges. The gate informs and can interpose one confirmation before
  `/pr-fix`; it never hard-blocks.
- Revalidating architectural decisions that have no recorded contradiction (that
  remains Agent L's bounded role).
- Gating standalone `/pr-fix` runs (those invoked directly, not as a follow-up to
  `/pr-review`). Noted as a future enhancement.

## Design

### Overview

A new **Agent M ("Premise & Regression Gate")** joins the Step 5 parallel batch, fed
by two new lightweight pre-steps that compute objective risk signals. Agent M emits a
structured verdict (OK / QUESTION / HOLD) surfaced at the top of the report, plus
individual findings that flow through the normal tiers. A targeted change to the
Step 6 scoring cap lets evidence-backed regression findings reach Critical. A HOLD
verdict interposes one confirmation before `/pr-fix`.

### Configuration additions

Add to the Configuration block at the top of `workflows/pr-review.md`:

```text
PREMISE_MERGED_PR_LOOKBACK:  10   # number of recently merged PRs scanned for file overlap
PREMISE_STALENESS_HOLD_DAYS: 14   # branch age (days) above which staleness biases toward HOLD
```

### Step 2d: Branch staleness (new)

After Step 2 metadata is fetched, compute two objective staleness metrics via `gh
api`:

- **commits behind base:** compare `HEAD_BRANCH` against `BASE_BRANCH` merge-base.
- **branch age:** age of the branch's first divergent commit.

Store as `STALENESS = {commits_behind, age_days}`. These feed Agent M as a
scan-intensity dial: when `age_days > PREMISE_STALENESS_HOLD_DAYS` or commits_behind
is large, Agent M scans deeper and biases its verdict toward HOLD on any confirmed
regression.

### Step 2e: PR-overlap targeting (new)

Compare the current PR against recent and in-flight PRs along **two dimensions**:
file-path overlap and symbol overlap. The path dimension catches two PRs editing the
same file; the symbol dimension catches two PRs adding the *same definition in
different files* (the duplicate-provider smell). The rag-processor case below proves
the path dimension alone is insufficient.

The comparison set for both dimensions is: the last `PREMISE_MERGED_PR_LOOKBACK`
merged PRs, plus all open PRs except the current one.

```bash
# Last N merged PRs with files and merge timing
gh pr list --repo "$OWNER/$REPO" --state merged --limit "$PREMISE_MERGED_PR_LOOKBACK" \
  --json number,title,mergedAt,files \
  --jq '[.[] | {number, title, mergedAt, files: [.files[].path]}]'

# All open PRs (excluding the current one) with files
gh pr list --repo "$OWNER/$REPO" --state open \
  --json number,title,files \
  --jq "[.[] | select(.number != $PR_NUMBER) | {number, title, files: [.files[].path]}]"
```

#### Dimension 1: file-path overlap (cheap, one list call)

Intersect each comparison PR's file list with `CHANGED_FILES`. Produce
`CONTESTED_FILES`: a list of `{file, overlapping_pr, pr_state, merged_at}` records.

- **Overlap with merged PRs** whose `mergedAt` postdates the current branch's
  merge-base = staleness / silent-revert risk. The current branch never saw that
  merged change, so it may silently undo it.
- **Overlap with open PRs** = collision / duplicate-work risk. Emits a finding
  directly:
  `[Important] Collision: file {f} is also modified by open PR #{n} ("{title}"). Verify the two changes do not conflict or duplicate effort before either merges.`

Caveat: `gh pr list --json files` caps at ~100 files per PR. Acceptable for overlap
detection; note in the report if any scanned PR hit the cap.

#### Dimension 2: symbol overlap (bounded, diff-level)

File-path overlap returns nothing when two PRs add the same symbol in different
files. To catch that, extract newly-added top-level definitions from the current
PR's diff and intersect their *names* against the same definitions added by
comparison PRs, regardless of file path.

Extract added definitions (column-0 `def`/`class`, including `async def`) from a
diff:

```bash
gh pr diff "$N" --repo "$OWNER/$REPO" 2>/dev/null | awk '
  /^\+\+\+ / { file=$2 }
  /^\+(async def|def|class) / {
    line=$0; sub(/^\+/,"",line);
    match(line, /^(async def|def|class)[ \t]+[A-Za-z_][A-Za-z0-9_]*/);
    print file "\t" substr(line, RSTART, RLENGTH)
  }'
```

Build `ADDED_SYMBOLS_CURRENT` for the PR under review, then fetch diffs for the
comparison set (bound cost to open PRs plus merged PRs newer than the current
branch's merge-base, since those are the staleness-relevant ones) and build their
added-symbol sets. A symbol collision fires when a non-dunder, non-`test_` symbol
name added by the current PR is also added by a comparison PR in a **different**
file. Emit:

```text
[Important] DuplicateSymbol: {symbol} is newly defined by both this PR ({file_a})
and PR #{n} ({file_b}). These are likely duplicate definitions that will need
deduplication after both merge. Confirm only one should define it.
```

Exclusions to control false positives: dunder names (`__init__`, `__call__`, etc.),
`test_*` functions, and conventional framework hooks (`setUp`, `main`) that
legitimately recur. Symbol collisions are QUESTION-tier, not HOLD, because resolving
them needs human judgment about which definition is canonical.

Store all collisions as `SYMBOL_COLLISIONS` and pass to Agent M.

### Agent M: Premise & Regression Gate (Step 5, model: Opus)

Always-on. Runs in the parallel batch so it adds no wall-clock. Opus because every
check is a judgment call. Receives: `PR_DIFF`, `PR_TITLE`, `PR_BODY`, `CHANGED_FILES`,
`CONTEXT_FILES`, `MERGE_STATE`, `STALENESS`, `CONTESTED_FILES`,
`SYMBOL_COLLISIONS`.

**Hard rule for every check: cite concrete evidence or drop the finding. Do not
downgrade an unsourced finding; remove it.**

| Check | Evidence required to fire |
| --- | --- |
| Regression / reverted code | A specific prior commit SHA whose removed lines the PR re-adds |
| Contradicts recorded decision | An ADR path + section, a CHANGELOG line, or a prior PR review comment |
| Unjustified churn / scope creep | The PR's own stated goal text + the specific change that does not trace to it |
| Better-alternative | A path to a pattern the repo *already uses elsewhere* (never an invented design) |

**Forensic scan scope:** the deep commit/line history scan (fetch recent commits per
file via `gh api repos/.../commits?path={file}`, inspect removal/revert commits,
compare removed lines to PR additions) runs **only on `CONTESTED_FILES`**, not on
every changed file. Scan depth scales with `STALENESS`.

**Better-alternative discipline:** this check may only fire by pointing to a concrete
pattern the repo already uses in another file. It may never propose a hypothetical
design. This is what keeps it from revalidating architecture.

**Docs-only PRs:** when every changed file is `.md`/`.rst`/`.txt`, Agent M runs only
the regression and contradicts-decision checks; churn and better-alternative are
skipped.

**Agent M returns**, in addition to findings, a structured verdict:

```json
{ "verdict": "OK | QUESTION | HOLD", "headline": "one-line reason" }
```

- **HOLD**: hard evidence the change should not merge as-is: reintroduces code a
  cited commit removed, or reverses a cited ADR. Staleness biases borderline
  regression findings toward HOLD.
- **QUESTION**: appropriateness concerns worth a human look but non-blocking:
  unjustified churn, a weak or inferred contradiction, an open-PR collision.
- **OK**: no premise concerns survive the evidence rule.

Individual Agent M findings are routed through Step 6 scoring and Step 7
deduplication with `agent source: M`, like every other agent.

### Step 6: Scoring cap fix

Current rule caps C/D findings at 20 unless they point to a specific fixable diff
line. Change to:

> If the agent source is C (Git History) or D (Prior PR Comments) AND the finding
> does not point to a specific, fixable line in the diff: cap the score at 20,
> **unless** the finding is a regression-reintroduction that cites a specific prior
> commit SHA where the now-reappearing lines were removed or reverted. Such
> evidence-backed regression findings are scored on the normal rubric and may reach
> Critical.

The exception is source-agnostic in spirit (it is the cited-SHA evidence that lifts
the cap, not the agent identity), so an Agent M or Agent C regression finding with a
SHA both qualify, while vague history churn stays capped.

### Step 9: Report header verdict

Add a leading line to the report header, above the existing status block:

```text
**PREMISE {verdict}: {headline}**
```

Render `HOLD` prominently (same weight as `BUILD FAILING`). `OK` may render as a
single quiet line. Individual premise findings appear in their scored tiers as usual.

### Step 10 / 11: pr-fix gating

When the user selects a `/pr-fix` option (2 or 3) and the premise verdict is
**HOLD**, interpose one confirmation before loading `pr-fix.md`:

```text
Premise gate flagged HOLD: {headline}.
/pr-fix would polish a change whose existence is in question.
Proceed with the fix anyway? (y/N)
```

Pass the verdict and headline forward to `pr-fix.md` alongside the existing
handoff variables, so the fix workflow can surface it in its own summary.

## Risk-proportional scrutiny (the unifying principle)

Staleness (Step 2d) and contestedness (Step 2e) are cheap, objective signals that
gate how hard Agent M looks:

- Fresh PR, no contested files → light premise pass, OK verdict likely.
- Stale branch editing files that merged and open PRs also touch → full forensic
  scan, HOLD bias.

This is what lets the gate honor both halves of the original tension: it never
assumes the change was intentional, yet it never relitigates a low-risk design,
because effort is spent in proportion to evidence of risk rather than uniformly.

## Validating example (acceptance fixture)

`ByronWilliamsCPA/rag-processor` PRs 63, 68, and 73 are a real instance of the
collision class this gate targets, and they are the reason symbol-overlap exists in
the design:

- PR 63 (`claude/tier-3-findings`) added `def get_file_router() -> FileRouter:` in
  `src/rag_processor/routing/router.py`.
- PR 68 (`feat/salvage-pr60-pipeline-extras`) added the same
  `def get_file_router() -> FileRouter:` in `src/rag_processor/api/dependencies.py`.
- Both merged within 35 minutes of each other on 2026-06-04; neither branch saw the
  other's new definition.
- The duplicate DI provider surfaced only after both merged, forcing PR 73
  (`refactor: remove duplicate get_file_router DI provider`).

Verification facts for the implementation:

- File-path intersection of PR 63 and PR 68 is **empty** (17 vs. 12 changed files,
  zero shared). Dimension 1 alone does **not** flag this case.
- `get_file_router` is an added column-0 `def` in both diffs, in different files.
  Dimension 2 (symbol overlap) **does** flag it.

Acceptance criterion: running the Step 2e symbol-overlap logic with PR 68 as the
current PR and PR 63 in the merged-lookback set must emit a `DuplicateSymbol` finding
for `get_file_router`. This pair should be encoded as a test fixture for the
implementation.

## Affected files

- `.claude/skills/pr-review/workflows/pr-review.md`: Configuration block, new
  Steps 2d and 2e, new Agent M in Step 5, Step 6 cap rule, Step 9 header, Step 10/11
  gating, Step 11 handoff to pr-fix.
- `.claude/skills/pr-review/workflows/pr-fix.md`: accept and surface the forwarded
  premise verdict.

## Open questions / future enhancements

- Standalone `/pr-fix` (not preceded by `/pr-review`) is ungated. A lightweight
  premise check could be added to standalone pr-fix later.
- The forensic line-level regression scan is bounded by the commit history window
  available via `gh api`. Removals older than the window, or hidden behind a
  since-renamed file, can be missed. The PR-overlap targeting layer partially
  compensates by surfacing the contested file regardless of how old its history is.
