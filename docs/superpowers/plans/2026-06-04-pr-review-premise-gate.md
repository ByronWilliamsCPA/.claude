---
schema_type: planning
title: "PR Review Premise Gate Implementation Plan"
status: draft
owner: core-maintainer
purpose: "Implementation plan for adding a premise gate to the /pr-review workflow. Adds two cheap risk-signal sub-steps (branch staleness, two-dimension cross-PR overlap), an Opus-backed Agent M that runs four evidence-grounded appropriateness checks and emits an OK/QUESTION/HOLD verdict, a targeted Step 6 scoring-cap exception so evidence-backed regression findings can reach Critical, a report-header verdict line, and HOLD gating of the /pr-fix handoff."
component: Development-Tools
source: "docs/superpowers/specs/2026-06-04-pr-review-premise-gate-design.md"
tags:
  - skills
  - tooling
  - automation
  - standards
  - guardrails
---

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

## Goal

Add a critical "is this change appropriate?" premise gate to the `/pr-review` workflow that catches regression-reintroduction, decision contradictions, unjustified churn, and cross-PR collisions, with scrutiny proportional to objective risk signals.

## Architecture

All changes are prose edits to two workflow markdown files plus a one-line SKILL.md note. No Python, no new scripts: the detection logic is inline `bash`/`awk` in the workflow prose, executed by the review agent at runtime. Verification is markdownlint (MD040) after each edit, plus one live acceptance check that the symbol-overlap logic flags the known rag-processor `get_file_router` collision.

## Tech Stack

Markdown workflow prose; `gh` CLI (GitHub REST + GraphQL); `jq`; `awk`; the Agent tool (Opus for Agent M); `mcp__pal__*` already wired in the workflow. Validation via `markdownlint` (pre-commit hook, `.markdownlint.json`).

## Files

- Modify: `.claude/skills/pr-review/workflows/pr-review.md` (1,127 lines): Configuration block, new Steps 2d/2e, new Agent M, Step 6 cap rule, Step 9 header, Step 10/11 gating + handoff.
- Modify: `.claude/skills/pr-review/workflows/pr-fix.md` (1,334 lines): receive and surface the forwarded premise verdict.
- Modify: `.claude/skills/pr-review/SKILL.md` (51 lines): one Design Principles bullet naming the premise gate.

## Conventions to match

- Agent headers: `### Agent {Letter}: {Name} ({Model})`.
- Fenced blocks ALWAYS carry a language (`bash`, `text`, `json`): MD040 fails otherwise.
- Findings: `[Critical|Important|Suggested|Info] {Category}: {finding}`.
- No em-dash characters anywhere (PC-011 `no-em-dash` hook blocks the commit).

## Verification command (used by most tasks)

```bash
cd /home/byron/dev/.claude/.worktrees/pr-review-premise-gate-spec
npx --yes markdownlint-cli --config .markdownlint.json \
  .claude/skills/pr-review/workflows/pr-review.md \
  .claude/skills/pr-review/workflows/pr-fix.md \
  .claude/skills/pr-review/SKILL.md
```

Expected on success: no output, exit 0. If the binary differs, use the same invocation the pre-commit hook uses (`markdownlint --config .markdownlint.json <files>`).

---

### Task 1: Add premise-gate Configuration constants

**Files:**
- Modify: `.claude/skills/pr-review/workflows/pr-review.md` (Configuration block, the `text` fence at lines 21-26)

- [ ] **Step 1: Add the two constants inside the existing Configuration `text` block**

Locate the fenced block (currently lines 21-26):

```text
PAL_CHAT_MODEL:        google/gemini-2.5-pro-preview
PAL_CONSENSUS_MODELS:  ["google/gemini-2.5-pro-preview", "openai/gpt-4o"]
PAL_TIERED_LEVEL:      1
PAL_TIERED_THINKING:   auto
```

Append two lines inside the same fence so it becomes:

```text
PAL_CHAT_MODEL:        google/gemini-2.5-pro-preview
PAL_CONSENSUS_MODELS:  ["google/gemini-2.5-pro-preview", "openai/gpt-4o"]
PAL_TIERED_LEVEL:      1
PAL_TIERED_THINKING:   auto
PREMISE_MERGED_PR_LOOKBACK:   10
PREMISE_STALENESS_HOLD_DAYS:  14
```

- [ ] **Step 2: Add their descriptions to the bullet list below the fence**

After the existing `PAL_TIERED_THINKING` bullet (line 33-34), add:

```text
- `PREMISE_MERGED_PR_LOOKBACK`: number of recently merged PRs scanned for file and
  symbol overlap in Step 2e
- `PREMISE_STALENESS_HOLD_DAYS`: branch age in days above which staleness biases
  Agent M toward a HOLD verdict on a confirmed regression
```

- [ ] **Step 3: Verify markdownlint passes**

Run the Verification command above. Expected: exit 0, no output.

- [ ] **Step 4: Commit**

```bash
git add .claude/skills/pr-review/workflows/pr-review.md
git commit -S -m "feat(pr-review): add premise-gate configuration constants"
```

---

### Task 2: Add Step 2d (branch staleness)

**depends-on: Task 1 [completion]** (shares the same file; no artifact dependency)

**Files:**
- Modify: `.claude/skills/pr-review/workflows/pr-review.md` (insert between line 173 `---` and line 175 `## Step 3`)

- [ ] **Step 1: Insert the Step 2d section before `## Step 3: Classify Changes`**

Insert this complete block (keep the surrounding `---` separators intact):

````markdown
## Step 2d: Branch staleness (parallel with Step 2c)

Compute two objective staleness signals; Agent M (Step 5) uses them as a
scan-intensity dial and a HOLD bias on confirmed regressions.

```bash
CMP=$(gh api "repos/$OWNER/$REPO/compare/$BASE_BRANCH...$HEAD_BRANCH")
COMMITS_BEHIND=$(echo "$CMP" | jq '.behind_by')
FIRST_DIVERGENT_DATE=$(echo "$CMP" | jq -r '.commits[0].commit.committer.date // empty')
if [ -n "$FIRST_DIVERGENT_DATE" ]; then
  AGE_DAYS=$(( ( $(date +%s) - $(date -d "$FIRST_DIVERGENT_DATE" +%s) ) / 86400 ))
else
  AGE_DAYS=0
fi
```

Store as `STALENESS = {commits_behind: COMMITS_BEHIND, age_days: AGE_DAYS}`. When
`AGE_DAYS` exceeds `PREMISE_STALENESS_HOLD_DAYS`, or `COMMITS_BEHIND` is large, Agent
M scans contested files more deeply and biases its verdict toward HOLD on any
regression it confirms. This step is non-blocking: if the compare call fails, set
`STALENESS = {commits_behind: 0, age_days: 0}` and note "staleness: unavailable".
````

- [ ] **Step 2: Verify markdownlint passes**

Run the Verification command. Expected: exit 0.

- [ ] **Step 3: Commit**

```bash
git add .claude/skills/pr-review/workflows/pr-review.md
git commit -S -m "feat(pr-review): add Step 2d branch-staleness signal"
```

---

### Task 3: Add Step 2e (PR-overlap targeting, two dimensions)

**depends-on: Task 2 [completion]**

**Files:**
- Modify: `.claude/skills/pr-review/workflows/pr-review.md` (insert immediately after the Step 2d block from Task 2, before `## Step 3`)

- [ ] **Step 1: Insert the Step 2e section**

Insert this complete block:

````markdown
## Step 2e: PR-overlap targeting (parallel with Step 2c)

Compare the current PR against recent and in-flight PRs along two dimensions:
file-path overlap and symbol overlap. The path dimension catches two PRs editing the
same file; the symbol dimension catches two PRs adding the same definition in
different files (the duplicate-provider smell). Path overlap alone is insufficient;
see the rag-processor acceptance fixture in the design spec.

Comparison set: the last `PREMISE_MERGED_PR_LOOKBACK` merged PRs plus all open PRs
except the current one.

```bash
gh pr list --repo "$OWNER/$REPO" --state merged --limit "$PREMISE_MERGED_PR_LOOKBACK" \
  --json number,title,mergedAt,files \
  --jq '[.[] | {number, title, mergedAt, files: [.files[].path]}]'

gh pr list --repo "$OWNER/$REPO" --state open \
  --json number,title,files \
  --jq "[.[] | select(.number != $PR_NUMBER) | {number, title, files: [.files[].path]}]"
```

### Dimension 1: file-path overlap

Intersect each comparison PR's file list with `CHANGED_FILES`. Produce
`CONTESTED_FILES`: records of `{file, overlapping_pr, pr_state, merged_at}`.

- Overlap with a merged PR whose `mergedAt` postdates the current branch's merge-base
  is a staleness / silent-revert risk: the current branch never saw that merged
  change.
- Overlap with an open PR is a collision / duplicate-work risk. Emit directly:

```text
[Important] Collision: file {f} is also modified by open PR #{n} ("{title}").
Verify the two changes do not conflict or duplicate effort before either merges.
```

Caveat: `gh pr list --json files` caps at ~100 files per PR. Acceptable for overlap
detection; note in the report if any scanned PR hit the cap.

### Dimension 2: symbol overlap

File-path overlap returns nothing when two PRs add the same symbol in different
files. Extract newly-added top-level definitions from a diff and intersect their
names across PRs, regardless of file path:

```bash
gh pr diff "$N" --repo "$OWNER/$REPO" 2>/dev/null | awk '
  /^\+\+\+ / { file=$2 }
  /^\+(async def|def|class) / {
    line=$0; sub(/^\+/,"",line);
    match(line, /^(async def|def|class)[ \t]+[A-Za-z_][A-Za-z0-9_]*/);
    print file "\t" substr(line, RSTART, RLENGTH)
  }'
```

Build `ADDED_SYMBOLS_CURRENT` for the PR under review, then run the same extraction
on the comparison set (bound cost to open PRs plus merged PRs newer than the current
branch's merge-base). A collision fires when a non-dunder, non-`test_` symbol name
added by the current PR is also added by a comparison PR in a different file:

```text
[Important] DuplicateSymbol: {symbol} is newly defined by both this PR ({file_a})
and PR #{n} ({file_b}). These are likely duplicate definitions that will need
deduplication after both merge. Confirm only one should define it.
```

Exclusions to limit false positives: dunder names (`__init__`, `__call__`), `test_*`
functions, and conventional hooks (`setUp`, `main`). Symbol collisions are
QUESTION-tier, not HOLD, because choosing the canonical definition needs human
judgment. Store all collisions as `SYMBOL_COLLISIONS` and pass to Agent M.
````

- [ ] **Step 2: Verify markdownlint passes**

Run the Verification command. Expected: exit 0.

- [ ] **Step 3: Commit**

```bash
git add .claude/skills/pr-review/workflows/pr-review.md
git commit -S -m "feat(pr-review): add Step 2e two-dimension PR-overlap targeting"
```

---

### Task 4: Validate symbol-overlap logic against the rag-processor acceptance fixture

**depends-on: Task 3 [output]** (exercises the awk extraction authored in Task 3)

This is the plan's acceptance test. It proves the symbol dimension catches the real
collision (rag-processor PRs 63/68, `get_file_router`) that path overlap misses. It
does not modify any file.

- [ ] **Step 1: Confirm file-path overlap is empty (path dimension alone misses it)**

```bash
REPO=ByronWilliamsCPA/rag-processor
gh pr view 63 --repo "$REPO" --json files --jq '[.files[].path]' > /tmp/pr63.json
gh pr view 68 --repo "$REPO" --json files --jq '[.files[].path]' > /tmp/pr68.json
comm -12 <(jq -r '.[]' /tmp/pr63.json | sort) <(jq -r '.[]' /tmp/pr68.json | sort)
```

Expected: NO output (zero shared files). This is why Dimension 1 alone is insufficient.

- [ ] **Step 2: Run the Dimension 2 extraction on both PRs**

```bash
REPO=ByronWilliamsCPA/rag-processor
for N in 63 68; do
  echo "=== PR $N added defs/classes ==="
  gh pr diff "$N" --repo "$REPO" 2>/dev/null | awk '
    /^\+\+\+ / { file=$2 }
    /^\+(async def|def|class) / {
      line=$0; sub(/^\+/,"",line);
      match(line, /^(async def|def|class)[ \t]+[A-Za-z_][A-Za-z0-9_]*/);
      print file "\t" substr(line, RSTART, RLENGTH)
    }' | grep get_file_router
done
```

Expected: PR 63 prints `b/src/rag_processor/routing/router.py` with `def get_file_router`, and PR 68 prints `b/src/rag_processor/api/dependencies.py` with `def get_file_router`. Two different files, same symbol.

- [ ] **Step 3: Confirm the collision condition holds**

The symbol `get_file_router` is non-dunder, non-`test_`, added by both PRs in different files. Per the Step 2e rule this MUST emit a `DuplicateSymbol` finding. If Step 2 shows the two file paths differ and the symbol matches, the acceptance criterion passes.

Record the result in the commit body. No code change, so commit only if a note file is desired; otherwise proceed to Task 5. (Optional) capture evidence:

```bash
git commit -S --allow-empty -m "test(pr-review): verify symbol-overlap flags rag-processor get_file_router collision"
```

---

### Task 5: Add Agent M (Premise & Regression Gate)

**depends-on: Task 3 [completion]** (Agent M consumes `CONTESTED_FILES` and `SYMBOL_COLLISIONS`)

**Files:**
- Modify: `.claude/skills/pr-review/workflows/pr-review.md` (insert between line 750, end of Agent L block, and line 752 `## Step 6`)

- [ ] **Step 1: Insert the Agent M section before `## Step 6: Confidence Scoring`**

Insert this complete block:

````markdown
### Agent M: Premise & Regression Gate (Opus)

Always active. Runs in this parallel batch so it adds no wall-clock. Opus, because
every check is a judgment call. Receives: `PR_DIFF`, `PR_TITLE`, `PR_BODY`,
`CHANGED_FILES`, `CONTEXT_FILES`, `MERGE_STATE`, `STALENESS`, `CONTESTED_FILES`,
`SYMBOL_COLLISIONS`.

```text
You are assessing whether a pull request SHOULD exist and is an improvement, not
whether it is internally correct (other agents cover correctness). Most changes in
this repo are AI-authored, so do not assume the change was intentional or ideal.

PR title: {PR_TITLE}
PR body:  {PR_BODY}
Changed files: {CHANGED_FILES}
Branch staleness: {STALENESS}
Contested files (also touched by recent/open PRs): {CONTESTED_FILES}
Pre-computed symbol collisions: {SYMBOL_COLLISIONS}
PR diff: {PR_DIFF}

Run these four checks. HARD RULE: every finding MUST cite concrete evidence. If you
cannot cite evidence, DROP the finding; do not downgrade it.

1. Regression / reverted code: does the diff re-add code, config, or patterns that a
   prior commit deliberately removed or reverted? Evidence required: a specific prior
   commit SHA whose removed lines the PR re-adds. Run the forensic scan ONLY on
   CONTESTED_FILES (fetch recent commits via
   `gh api repos/{OWNER}/{REPO}/commits?path={file}&per_page=30`, inspect
   removal/revert commits, compare removed lines to PR additions). Scan deeper when
   STALENESS is high.
2. Contradicts a recorded decision: does the change reverse something fixed in an ADR
   (docs/architecture/**, docs/ADRs/**), a CHANGELOG entry, or a prior PR review
   comment? Evidence required: the ADR path + section, the CHANGELOG line, or the PR
   comment.
3. Unjustified churn / scope creep: does each change trace to the PR's stated goal in
   PR_BODY? Evidence required: the stated-goal text plus the specific change that does
   not trace to it.
4. Better-alternative: given the change's goal, is the chosen approach clearly worse
   than a pattern THIS REPO ALREADY USES elsewhere? Evidence required: a path to the
   existing in-repo pattern. You may NEVER propose a hypothetical design.

For docs-only PRs (every changed file is .md/.rst/.txt), run only checks 1 and 2.

Also surface the pre-computed SYMBOL_COLLISIONS and any open-PR file collisions as
findings.

Emit each finding as:
  [Critical|Important|Suggested] Premise/{check}: {finding}. Evidence: {citation}.

Then emit a single verdict line as a JSON object on its own:
  { "verdict": "OK" | "QUESTION" | "HOLD", "headline": "one-line reason" }

Verdict rules:
- HOLD: hard evidence the change should not merge as-is (reintroduces code a cited
  commit removed, or reverses a cited ADR). Staleness biases borderline regressions
  toward HOLD.
- QUESTION: appropriateness concerns worth a human look but non-blocking (churn, a
  weak/inferred contradiction, a symbol or open-PR collision).
- OK: no premise concern survives the evidence rule.
```

Route Agent M's individual findings through Step 6 confidence scoring and Step 7
deduplication with `agent source: M`. Capture its verdict object as
`PREMISE_VERDICT = {verdict, headline}` for the Step 9 header and the Step 11 handoff.
````

- [ ] **Step 2: Add Agent M to the always-active list in Step 3**

In `## Step 3`, under "**Always active regardless of content:**" (lines 190-194), add a bullet:

```text
- `premise-gate` (Agent M: change appropriateness + regression + collision)
```

- [ ] **Step 3: Verify markdownlint passes**

Run the Verification command. Expected: exit 0.

- [ ] **Step 4: Commit**

```bash
git add .claude/skills/pr-review/workflows/pr-review.md
git commit -S -m "feat(pr-review): add Agent M premise and regression gate"
```

---

### Task 6: Add the regression exception to the Step 6 scoring cap

**depends-on: Task 5 [completion]**

**Files:**
- Modify: `.claude/skills/pr-review/workflows/pr-review.md` (the C/D cap paragraph, lines 773-777)

- [ ] **Step 1: Replace the cap paragraph**

Find this exact paragraph (lines 773-777):

```text
Additional constraint: If the agent source is C (Git History) or D (Prior PR
Comments) AND the finding does not point to a specific, fixable line in the
diff (it describes historical context, file churn, or past review patterns
rather than an issue in the changed code): cap the score at 20 regardless of
the rubric above.
```

Replace it with:

```text
Additional constraint: If the agent source is C (Git History) or D (Prior PR
Comments) AND the finding does not point to a specific, fixable line in the
diff (it describes historical context, file churn, or past review patterns
rather than an issue in the changed code): cap the score at 20 regardless of
the rubric above, UNLESS the finding is a regression-reintroduction that cites a
specific prior commit SHA where the now-reappearing lines were removed or reverted.
Such evidence-backed regression findings (from any agent source, including M) are
scored on the normal rubric and may reach Critical. It is the cited SHA, not the
agent identity, that lifts the cap; vague history churn stays capped.
```

- [ ] **Step 2: Verify markdownlint passes**

Run the Verification command. Expected: exit 0.

- [ ] **Step 3: Commit**

```bash
git add .claude/skills/pr-review/workflows/pr-review.md
git commit -S -m "feat(pr-review): lift score cap for SHA-cited regression findings"
```

---

### Task 7: Add the PREMISE verdict line to the Step 9 report header

**depends-on: Task 5 [completion]**

**Files:**
- Modify: `.claude/skills/pr-review/workflows/pr-review.md` (report template, lines 985-989)

- [ ] **Step 1: Add the verdict line into the report template header**

Find the header lines at the top of the `markdown` report template (lines 986-989):

```markdown
# PR Review: {PR_TITLE}
{OWNER}/{REPO}#{PR_NUMBER} | {BASE_BRANCH} ← {HEAD_BRANCH}
{DRAFT WARNING if isDraft}
```

Change to (add the PREMISE line directly below the draft warning, before the blank line and `## Review Status`):

```markdown
# PR Review: {PR_TITLE}
{OWNER}/{REPO}#{PR_NUMBER} | {BASE_BRANCH} ← {HEAD_BRANCH}
{DRAFT WARNING if isDraft}
**PREMISE {PREMISE_VERDICT.verdict}: {PREMISE_VERDICT.headline}**
```

- [ ] **Step 2: Add a rendering note after the report template fence**

Immediately after the report template's closing ``` fence (before `## Recommended Action` at line 1025), add:

```text
Render a `HOLD` premise verdict with the same prominence as `BUILD FAILING`. An `OK`
verdict may render as a single quiet line. Individual premise findings from Agent M
appear in their scored tiers above, like any other agent's findings.
```

- [ ] **Step 3: Verify markdownlint passes**

Run the Verification command. Expected: exit 0.

- [ ] **Step 4: Commit**

```bash
git add .claude/skills/pr-review/workflows/pr-review.md
git commit -S -m "feat(pr-review): surface premise verdict in report header"
```

---

### Task 8: Gate the /pr-fix handoff on a HOLD verdict

**depends-on: Task 5 [completion]**

**Files:**
- Modify: `.claude/skills/pr-review/workflows/pr-review.md` (Step 11 "Option 2 or 3" section, lines 1099-1111)

- [ ] **Step 1: Add the HOLD confirmation at the start of the pr-fix option**

Find the start of `### Option 2 or 3: Run /pr-fix` (line 1099) and its first line `Load \`workflows/pr-fix.md\` and execute it.` (line 1101). Insert this block immediately before that line:

````markdown
If `PREMISE_VERDICT.verdict` is `HOLD`, interpose one confirmation before loading the
fix workflow:

```text
Premise gate flagged HOLD: {PREMISE_VERDICT.headline}.
/pr-fix would polish a change whose existence is in question.
Proceed with the fix anyway? (y/N)
```

Do not proceed to pr-fix unless the user confirms. If they decline, stop here.
````

- [ ] **Step 2: Add the verdict to the forwarded variable list**

Find the forwarded-variable list (lines 1103-1107) and add one bullet after the `SONAR_HOTSPOTS` line:

```text
- `PREMISE_VERDICT`: the Agent M verdict object `{verdict, headline}` from Step 5
```

- [ ] **Step 3: Verify markdownlint passes**

Run the Verification command. Expected: exit 0.

- [ ] **Step 4: Commit**

```bash
git add .claude/skills/pr-review/workflows/pr-review.md
git commit -S -m "feat(pr-review): gate /pr-fix handoff on HOLD premise verdict"
```

---

### Task 9: Receive and surface the verdict in pr-fix.md

**depends-on: Task 8 [completion]**

**Files:**
- Modify: `.claude/skills/pr-review/workflows/pr-fix.md` (handoff reception, lines 12-13)

- [ ] **Step 1: Add PREMISE_VERDICT to the reception statement**

Find the reception statement (lines 12-13):

```text
**From pr-review**: `FINDINGS`, `SONAR_FINDINGS`, `OWNER`, `REPO`,
`PR_NUMBER`, and `HEAD_BRANCH` are already in context from the review.
```

Replace with:

```text
**From pr-review**: `FINDINGS`, `SONAR_FINDINGS`, `OWNER`, `REPO`,
`PR_NUMBER`, `HEAD_BRANCH`, and `PREMISE_VERDICT` (if present) are already in
context from the review. When `PREMISE_VERDICT.verdict` is `HOLD`, prepend a line to
the fix summary: "Premise gate flagged HOLD: {headline}. This fix proceeds at the
user's explicit direction." Standalone /pr-fix runs (not invoked via /pr-review) have
no `PREMISE_VERDICT`; omit the line in that case.
```

- [ ] **Step 2: Verify markdownlint passes**

Run the Verification command. Expected: exit 0.

- [ ] **Step 3: Commit**

```bash
git add .claude/skills/pr-review/workflows/pr-fix.md
git commit -S -m "feat(pr-review): surface forwarded premise verdict in pr-fix"
```

---

### Task 10: Note the premise gate in SKILL.md and final verification

**depends-on: Task 9 [completion]**

**Files:**
- Modify: `.claude/skills/pr-review/SKILL.md` (Design Principles list)

- [ ] **Step 1: Add a Design Principles bullet**

In `## Design Principles`, after the "Isolated worktree for fixes" bullet, add:

```text
- **Premise before polish.** A premise gate (Agent M) asks whether the change should
  exist and is an improvement, not just whether it is correct. It checks for
  regression-reintroduction, contradicted decisions, unjustified churn, and cross-PR
  collisions, surfaces an OK/QUESTION/HOLD verdict at the report top, and a HOLD
  interposes a confirmation before /pr-fix.
```

- [ ] **Step 2: Final markdownlint across all three files**

Run the Verification command on all three files. Expected: exit 0.

- [ ] **Step 3: Read-through coherence check**

Read Steps 2d, 2e, Agent M, and Step 6 in `pr-review.md` in order. Confirm: variable names match across steps (`STALENESS`, `CONTESTED_FILES`, `SYMBOL_COLLISIONS`, `PREMISE_VERDICT`); no fenced block is missing a language; no em-dash characters present.

```bash
grep -nP "\x{2014}" .claude/skills/pr-review/workflows/pr-review.md .claude/skills/pr-review/workflows/pr-fix.md .claude/skills/pr-review/SKILL.md || echo "no em-dash: OK"
```

Expected: `no em-dash: OK`.

- [ ] **Step 4: Commit**

```bash
git add .claude/skills/pr-review/SKILL.md
git commit -S -m "docs(pr-review): note premise gate in SKILL.md design principles"
```

---

## Self-Review

- **Spec coverage:** Configuration (Task 1) → spec Configuration additions; Step 2d (Task 2) → spec Step 2d; Step 2e both dimensions (Task 3) → spec Step 2e; acceptance fixture (Task 4) → spec Validating example; Agent M + four checks + verdict (Task 5) → spec Agent M section; cap fix (Task 6) → spec Step 6; header verdict (Task 7) → spec Step 9; pr-fix gating + handoff (Tasks 8, 9) → spec Step 10/11; SKILL.md note (Task 10) is additive. Non-goal "standalone pr-fix ungated" is honored in Task 9 Step 1. All spec sections map to a task.
- **Placeholder scan:** No "TBD/TODO"; every insertion shows full literal content.
- **Type/name consistency:** `STALENESS`, `CONTESTED_FILES`, `SYMBOL_COLLISIONS`, `PREMISE_VERDICT`, `PREMISE_MERGED_PR_LOOKBACK`, `PREMISE_STALENESS_HOLD_DAYS` are used identically in every task that references them.
- **Shell environment:** All commands use absolute repo/worktree paths or `$OWNER`/`$REPO`/`$N` already defined in the workflow context; the Task 4 fixture commands set `REPO` inline.
- **MD040:** Every inserted fenced block declares a language (`bash`, `text`, `json`, `markdown`).
- **No em-dash:** Verified by Task 10 Step 3 grep gate.

## Execution Handoff

Plan complete. Two execution options:

1. **Subagent-Driven (recommended)**: a fresh subagent per task with review between tasks.
2. **Inline Execution**: execute tasks in this session with checkpoints.

Note: tasks are mostly serial because they edit the same file, but Tasks 6, 7, and 8 each `depends-on: Task 5 [completion]` and touch disjoint regions of `pr-review.md`, so they can be authored in any order once Task 5 lands.
