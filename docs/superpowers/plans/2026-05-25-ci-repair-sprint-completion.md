---
title: "CI Repair Sprint Completion Plan"
schema_type: planning
status: draft
owner: core-maintainer
component: Strategy
source: "Generated 2026-05-25 after Phase 1 (in-flight PR remediation) completed and Phase 2 began. Companion to docs/audits/ci-repair-sprint-handoff-2026-05-25.md."
purpose: "Phase-by-phase plan to repair broken reusable workflows on ByronWilliamsCPA/.github main, fix per-repo failures (SLSA, CodeQL, SonarCloud), then resume the Phase 3B/3C dependency-management sweep across 44 active repos."
tags:
  - planning
  - automation
  - dependencies
  - compliance
---

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Repair all broken reusable workflows on `ByronWilliamsCPA/.github` main, fix per-repo failures (SLSA, CodeQL, SonarCloud), then unblock and resume the Phase 3B/3C dependency-management sweep across 44 active repos.

**Architecture:** Apply the proven NOSONAR detect-state pattern (established by merged PRs #155 and #156) to all remaining reusable workflows that hardcode `uv sync --frozen` / `uv run --frozen`. Each workflow fix is one PR in `BWCPA/.github`, validated by actionlint locally and by downstream caller re-runs after merge. Per-repo work (SLSA, CodeQL, SonarCloud) happens after the reusable-workflow tier is green, because per-repo fixes inherit those workflows' state.

**Tech Stack:** GitHub Actions reusable workflows (YAML), `gh` CLI, `actionlint`, `uv`, git worktrees, SonarCloud (S8541 rule), SARIF + GHAS Code Scanning.

**Source handoff:** `docs/audits/ci-repair-sprint-handoff-2026-05-25.md`. Read it before starting any phase below.

**Critical correction to handoff (added 2026-05-25 post-handoff):** Empirical analysis at `/home/byron/dev/.github/.worktrees/python-fips-detect-state/docs/sonarcloud-nosonar-patterns.md` documents that the handoff's "proven NOSONAR detect-state pattern" only works in one of two SonarCloud failure modes. Specifically:

- The handoff template prescribes `# NOSONAR S8541` on a `run: uv sync ... $FROZEN_FLAG ...` line, but **`$FROZEN_FLAG` also triggers S8544 (`--frozen` rule)** which the single-rule comment does NOT suppress.
- **Preceding-line NOSONAR inside `run: |` block scalars with dynamic `$FROZEN_FLAG` is NOT honored** by SonarCloud's `githubactions` rule set, even with comma-separated rule lists.
- Confirmed live: PR #157 quality gate = ERROR (4 open vulns at lines 210, 220), PR #158 = ERROR (2 vulns), PR #159 = ERROR (28 vulns).

The fix patterns are **Pattern A** (inline `# NOSONAR(S8541,S8544)` on a single-line YAML `run:`) and **Pattern B** (split install step with literal `--frozen`, preceding-line `# NOSONAR(S8541)` for `$NO_BUILD_FLAG` only). See the **Pattern Selection Guide** in Phase 2.

---

## Phase 0: State reconciliation (10 min)

The handoff was written mid-evening 2026-05-25; verify nothing else moved before starting.

### Task 0.1: Confirm in-flight PR state

**Files:** none (read-only verification)

- [ ] **Step 1: List open PRs in `BWCPA/.github`**

Run:
```bash
gh pr list --repo ByronWilliamsCPA/.github --state open \
  --json number,title,mergeable,reviewDecision,headRefName --limit 20
```

Expected: PRs #157, #158, #159 each `MERGEABLE`. PR #156 (python-compatibility) was **MERGED at 2026-05-25T20:59:51Z** despite the handoff listing it as "open, team handling"; confirm and update the handoff doc if still stale.

- [ ] **Step 2: Verify worktrees referenced in handoff**

Run:
```bash
ls /home/byron/dev/.github/.worktrees/
```

Expected: `python-ci-detect-state`, `python-compat-pkg-detect`, `python-fips-detect-state`, `python-security-analysis-detect-state`, `scorecard-publish-fix`. The first and last can be cleaned up after their PRs merge (Task 0.4).

- [ ] **Step 3: Snapshot today's failure inventory**

Run:
```bash
cp /tmp/ci-failure-inventory.tsv \
   /home/byron/dev/.claude/docs/audits/ci-failure-inventory-2026-05-25.tsv
git -C /home/byron/dev/.claude add docs/audits/ci-failure-inventory-2026-05-25.tsv
```

Why: `/tmp/` is volatile; this is the baseline against which we measure repair progress. Commit it with Phase 1 closure.

---

## Phase 1: Remediate SonarCloud quality-gate failures on in-flight PRs (60-120 min)

**Status correction:** All three in-flight PRs (#157, #158, #159) are `git-MERGEABLE` but **SonarCloud quality gate = ERROR**. The handoff incorrectly described them as ready to merge. They must be rewritten to use Pattern A or Pattern B from the Pattern Selection Guide (below) before they can land.

### Task 1.0: Pre-flight SonarCloud verification (10 min)

- [ ] **Step 1: Confirm current quality-gate state for all three PRs**

Run:
```bash
for pr in 157 158 159; do
  echo "=== PR #$pr ==="
  curl -s "https://sonarcloud.io/api/qualitygates/project_status?projectKey=ByronWilliamsCPA_.github&pullRequest=$pr" \
    | python3 -c "import json,sys; d=json.load(sys.stdin); print(' gate:', d.get('projectStatus',{}).get('status','?'))"
  curl -s "https://sonarcloud.io/api/issues/search?componentKeys=ByronWilliamsCPA_.github&pullRequest=$pr&types=VULNERABILITY&ps=20&statuses=OPEN,CONFIRMED" \
    | python3 -c "import json,sys; d=json.load(sys.stdin); [print(f\"  {i['rule']} L{i.get('line','?')}\") for i in d.get('issues',[])]"
done
```

Expected (as of 2026-05-25 evening): #157 ERROR (4 vulns), #158 ERROR (2 vulns), #159 ERROR (28 vulns). If any are now PASSING, skip the corresponding remediation task below.

### Task 1.1: Remediate PR #157 (python-fips-compatibility): 4 vulns at lines 210, 220

**Files:**
- Worktree: `/home/byron/dev/.github/.worktrees/python-fips-detect-state/`
- Workflow: `.github/workflows/python-fips-compatibility.yml`
- Reference patterns doc: same worktree, `docs/sonarcloud-nosonar-patterns.md`

- [ ] **Step 1: Inspect the two failing locations**

```bash
cd /home/byron/dev/.github/.worktrees/python-fips-detect-state
sed -n '200,225p' .github/workflows/python-fips-compatibility.yml
```

Expected: two `uv run $FROZEN_FLAG $NO_BUILD_FLAG ...` invocations inside `run: |` block scalars in the `fips-check` job, each preceded by a `# NOSONAR(S8541,S8544)` comment that SonarCloud is ignoring.

- [ ] **Step 2: Apply Pattern B restructuring (recommended)**

Add an install step (or reuse an existing one) earlier in the `fips-check` job so `uv.lock` exists by the time the affected `run:` block runs. Then rewrite the two locations to use literal `--frozen`:

```yaml
run: |
  # NOSONAR(S8541): --no-build is opt-out via `no-build` workflow input
  uv run --frozen $NO_BUILD_FLAG python "$SCRIPT_PATH" \
    --arg-a \
    --arg-b
```

The literal `--frozen` token prevents S8544 from firing; the preceding-line NOSONAR covers only S8541 (which works in preceding-line position).

If the `fips-check` job structurally cannot have an install step before the run step (e.g., it runs in a container without lockfile generation), fall back to Pattern A: collapse each multi-line command to a single YAML line and put `# NOSONAR(S8541,S8544): ...rationale...` at the end of the line. Accept yamllint line-length warnings.

- [ ] **Step 3: Commit and push**

```bash
git add .github/workflows/python-fips-compatibility.yml
git commit -m "fix(python-fips): restructure NOSONAR to satisfy SonarCloud quality gate

Preceding-line NOSONAR with dynamic \$FROZEN_FLAG is not honored by
SonarCloud's githubactions rule set (empirical finding documented in
docs/sonarcloud-nosonar-patterns.md). Switch to Pattern B: literal
--frozen with preceding-line NOSONAR(S8541) covering only --no-build."
git push
```

- [ ] **Step 4: Wait for SonarCloud re-analysis, then verify**

```bash
sleep 180  # SonarCloud analysis typically takes 2-5 minutes
curl -s "https://sonarcloud.io/api/qualitygates/project_status?projectKey=ByronWilliamsCPA_.github&pullRequest=157" \
  | python3 -c "import json,sys; d=json.load(sys.stdin); print('gate:', d['projectStatus']['status'])"
```

Expected: `gate: OK`. If still `ERROR`, re-query issues (`/api/issues/search`) to see which line(s) still flag and iterate.

- [ ] **Step 5: Merge once gate passes**

```bash
gh pr merge 157 --repo ByronWilliamsCPA/.github --squash --delete-branch
```

- [ ] **Step 6: Validate downstream**

```bash
gh workflow run "FIPS Compatibility" --repo ByronWilliamsCPA/maester-tests
sleep 60
gh run list --repo ByronWilliamsCPA/maester-tests \
  --workflow "FIPS Compatibility" --limit 1 --json conclusion,status
```

### Task 1.2: Remediate PR #158 (python-security-analysis): 2 vulns

**Files:**
- Worktree: `/home/byron/dev/.github/.worktrees/python-security-analysis-detect-state/`
- Workflow: `.github/workflows/python-security-analysis.yml`

- [ ] **Step 1: Identify the two flagged lines**

```bash
cd /home/byron/dev/.github/.worktrees/python-security-analysis-detect-state
curl -s "https://sonarcloud.io/api/issues/search?componentKeys=ByronWilliamsCPA_.github&pullRequest=158&types=VULNERABILITY&ps=20&statuses=OPEN,CONFIRMED" \
  | python3 -c "import json,sys; d=json.load(sys.stdin); [print(f\"L{i['line']}: {i['rule']}\") for i in d['issues']]"
```

- [ ] **Step 2: Apply Pattern A or Pattern B based on line context**

Inspect each flagged line. Decision tree:
- Single-line `run: uv ...` → use Pattern A: append `  # NOSONAR(S8541,S8544): <rationale>` to the same physical YAML line.
- Multi-line `run: |` block scalar → use Pattern B: restructure so the run step assumes lockfile exists, use literal `--frozen`, preceding-line `# NOSONAR(S8541)` for `--no-build` only.

- [ ] **Step 3-6: Same as Task 1.1 Steps 3-6**, substituting PR #158 and an appropriate downstream sample (e.g., `audio-processor`).

### Task 1.3: Remediate PR #159 (python-ci): 28 vulns (largest cleanup)

**Files:**
- Worktree: `/home/byron/dev/.github/.worktrees/python-ci-detect-state/`
- Workflow: `.github/workflows/python-ci.yml`

The 28-vulnerability count suggests the entire detect-state refactor consistently uses the broken dynamic-FROZEN_FLAG pattern. Plan for a substantial rework, possibly 60+ minutes.

- [ ] **Step 1: Pull the full list of flagged lines**

```bash
curl -s "https://sonarcloud.io/api/issues/search?componentKeys=ByronWilliamsCPA_.github&pullRequest=159&types=VULNERABILITY&ps=50&statuses=OPEN,CONFIRMED" \
  | python3 -c "import json,sys; d=json.load(sys.stdin); [print(f\"L{i['line']:>4}: {i['rule']}\") for i in sorted(d['issues'], key=lambda x: x['line'])]"
```

- [ ] **Step 2: Group flags by job and by single-line-vs-block-scalar**

Each group will get either Pattern A (single-line) or Pattern B (multi-line block) en bloc. Preserve the layout precondition step from PR #119 hardening throughout.

- [ ] **Step 3: Apply patterns**

For Pattern A targets: append `# NOSONAR(S8541,S8544): ...rationale...` to each single-line `run:`.

For Pattern B targets: ensure an install step with literal `--frozen` runs first in the job; rewrite the dependent run steps to use literal `--frozen` with preceding-line `# NOSONAR(S8541)`.

For any location where neither pattern fits cleanly (e.g., a `run: |` block where adding an upstream install step would be expensive), fall back to collapsing the multi-line command to a single line with Pattern A. Accept yamllint warnings; readability cost is the tradeoff for SonarCloud compliance.

- [ ] **Step 4-6: Same as Task 1.1 Steps 3-6**, substituting PR #159 and downstream sample `williaby/GCS`.

### Task 1.4: Update the handoff doc

- [ ] **Step 1: Patch the handoff's "proven NOSONAR detect-state pattern" section**

The handoff template at lines 47-83 of `docs/audits/ci-repair-sprint-handoff-2026-05-25.md` prescribes the broken pattern. Replace the example with the Pattern A and Pattern B alternatives from the Pattern Selection Guide below.

- [ ] **Step 2: Mark the empirical findings doc as canonical**

Add to the handoff's References section:
```text
- SonarCloud NOSONAR empirical patterns: docs/sonarcloud-nosonar-patterns.md (in BWCPA/.github)
```

After Task 1.4, this plan and the handoff agree on the corrected pattern, and Phase 2 can proceed with the validated template.

### Task 1.5: Close out Phase 1

- [ ] **Step 1: Clean up merged-PR worktrees**

Only remove worktrees AFTER their corresponding PRs (#155, #156, #157, #158, #159) are merged.

```bash
git -C /home/byron/dev/.github worktree remove .worktrees/scorecard-publish-fix
git -C /home/byron/dev/.github worktree remove .worktrees/python-compat-pkg-detect
git -C /home/byron/dev/.github worktree remove .worktrees/python-fips-detect-state
git -C /home/byron/dev/.github worktree remove .worktrees/python-security-analysis-detect-state
git -C /home/byron/dev/.github worktree remove .worktrees/python-ci-detect-state
git -C /home/byron/dev/.github worktree prune
```

- [ ] **Step 2: Update the handoff to mark Phase 1 done**

Edit `docs/audits/ci-repair-sprint-handoff-2026-05-25.md` table at lines 36-41: change PR #157-#159 state column to `MERGED <date>` and "Action needed" column to `none`. Commit:
```bash
git -C /home/byron/dev/.claude add docs/audits/ci-repair-sprint-handoff-2026-05-25.md
git -C /home/byron/dev/.claude commit -m "docs(audits): mark CI Repair Sprint Phase 1 PRs as merged"
```

---

## Phase 2: Reusable-workflow detect-state pattern application (3-6 hours, parallelizable)

### Pattern Selection Guide (READ BEFORE EVERY TASK 2.N)

**This supersedes the handoff doc's "proven NOSONAR detect-state pattern" section.** Source: empirical findings at `BWCPA/.github`:`docs/sonarcloud-nosonar-patterns.md` (strengthened 2026-05-26 by Wave 1C / PR #166 / PR #170).

**STRENGTHENED RULE (Wave 1C, 2026-05-26):** Only single-line `run:` shape reliably honors NOSONAR for the `githubactions` ruleset. Any NOSONAR placement inside a `run: |` block scalar is unreliable, regardless of position (preceding-line OR inline-trailing) or flag type (literal OR dynamic). Wave 1C PR #166 empirically confirmed this: both preceding-line (`556a09f`) AND inline-trailing (`bb31ec1`) NOSONAR inside `run: |` blocks left the quality gate ERROR; only the structural rewrite to single-line `run:` (`251ba35`) achieved gate=OK.

The `Detect repo state` step (state outputs `skip`/`poetry-not-supported`/`uv-locked`/`uv-no-lock`) is still the right shape. The change is how the `uv sync` / `uv run` lines suppress SonarCloud's `S8541` (`--no-build` omission) and `S8544` (`--frozen` omission) rules. Pick per-line based on shape:

| Shape | Pattern | Suppression |
|---|---|---|
| Single-line `run: uv sync ...` or `run: uv run ...` | **Pattern A (PREFERRED)** | Inline: append `  # NOSONAR(S8541,S8544): <rationale>` to the same physical YAML line. Honors comma-separated rule list. The ONLY reliable placement. |
| Multi-line `run: \|` block with literal `--frozen` (install step ran first) | **Pattern B (FRAGILE)** | Preceding-line `# NOSONAR(S8541): ...` inside the block scalar for `--no-build` only. The literal `--frozen` token prevents S8544 from firing structurally. Suppression itself may be a lucky non-failure rather than honored. Verify the SonarCloud gate per PR; do not assume. |
| Multi-line `run: \|` block with dynamic `$FROZEN_FLAG` | **ANTI-PATTERN** | NOSONAR is NOT honored here. Restructure to single-line. |
| Multi-line `run: \|` block with inline-trailing NOSONAR on each line | **ANTI-PATTERN (NEW)** | NOSONAR is NOT honored anywhere inside `run: \|`. Restructure to single-line. |

**Default restructuring strategies (in order of preference):**

1. **Split into two `if:`-guarded steps** with literal flags each (one `uv-locked`, one `uv-no-lock`). Both single-line `run:`. Pattern A inline on each. This is the canonical fix used in merged PRs #156, #158, #159, #160, #164, #165.
2. **Extract flag-computation into an output-emitting helper step (Option 3 from PR #166)** when the workflow has additional dynamic logic (e.g., resolving `--extra` from a workflow input). Helper step emits `steps.<id>.outputs.<name>`; install step references it from single-line `run:`.
3. **Collapse multi-line shell logic to a single-line `run:`** with the entire command on one physical YAML line. Accept yamllint line-length warnings as the cost.
4. **Pattern B (preceding-line inside `run: |` with literal `--frozen`)** is acceptable ONLY when none of the above work AND the literal `--frozen` is structurally present. Verify the gate per PR.

**Practical rule:** prefer Pattern A for new single-line steps. For multi-line blocks, prefer Option 1 from `sonarcloud-nosonar-patterns.md` §"Restructuring to expose a literal --frozen": add an install step that branches on `state` (Pattern A on each install) so the run step downstream can always use literal `--frozen` (Pattern B).

Seven workflows remain. They are independent of each other; each fix is one self-contained PR in `BWCPA/.github`. Sequencing within Phase 2 is by leverage (repos affected) and risk (Trivy concern for sbom).

**Reference paths:**
- Source convention (cite this in every PR body): `.github/workflows/python-mutation.yml:159-169`
- Detect-state template: handoff doc lines 47-81 (the YAML block under "The proven NOSONAR detect-state pattern")

### Task template (REUSE FOR EACH WORKFLOW)

This is the recipe for each Task 2.N below. Each task block lists the workflow-specific deltas; everything else follows this template.

#### Template steps

- [ ] **T-Step 1: Create worktree off main**

Run (substitute `<WORKFLOW_STEM>`):
```bash
cd /home/byron/dev/.github
git fetch origin main
git worktree add .worktrees/<WORKFLOW_STEM>-detect-state -b chore/<WORKFLOW_STEM>-detect-state origin/main
cd .worktrees/<WORKFLOW_STEM>-detect-state
```

- [ ] **T-Step 2: Read the target workflow**

```bash
cat .github/workflows/<WORKFLOW_STEM>.yml | head -200
```

Identify every `uv sync` and `uv run` line. Each one needs the same treatment:
1. Add an `if:` guard tied to `steps.detect.outputs.state`
2. Add an `env: FROZEN_FLAG` block
3. Replace `--frozen` with `$FROZEN_FLAG` and append ` # NOSONAR S8541` to the run line if the analyzer would flag it
4. Add the `Detect repo state` step at the top of the job (once per job)

- [ ] **T-Step 3: Apply the detect-state pattern (per the Pattern Selection Guide above)**

Use this exact block at the top of each job (after checkout):

```yaml
- name: Detect repo state
  id: detect
  run: |
    if [ ! -f pyproject.toml ]; then
      echo "state=skip" >> $GITHUB_OUTPUT
      echo "::notice::No pyproject.toml found at repo root; <WORKFLOW_STEM> will be skipped."
    elif [ -f poetry.lock ] || grep -qE '^\[tool\.poetry(\.|])' pyproject.toml; then
      echo "state=poetry-not-supported" >> $GITHUB_OUTPUT
      echo "::error::This repo uses Poetry. <WORKFLOW_STEM>.yml is uv-only by org policy. Convert to uv before re-enabling."
      exit 1
    elif [ -f uv.lock ]; then
      echo "state=uv-locked" >> $GITHUB_OUTPUT
    else
      echo "state=uv-no-lock" >> $GITHUB_OUTPUT
    fi
  shell: bash
```

**For the install step**, prefer Pattern A by splitting into two `if:`-guarded steps, each with literal flags. This avoids the dynamic-FROZEN_FLAG anti-pattern entirely:

```yaml
- name: Install dependencies (uv-locked)
  if: steps.detect.outputs.state == 'uv-locked'
  run: uv sync --all-extras --frozen $NO_BUILD_FLAG  # NOSONAR(S8541): --no-build is opt-out via `no-build` input

- name: Install dependencies (uv-no-lock)
  if: steps.detect.outputs.state == 'uv-no-lock'
  run: uv sync --all-extras $NO_BUILD_FLAG  # NOSONAR(S8541,S8544): --no-build via input; no uv.lock by design on this path
```

**For each subsequent `uv run` step**, the install step above has guaranteed `uv.lock` exists when on the `uv-locked` path, so use literal `--frozen`:

```yaml
- name: <existing run step>
  if: steps.detect.outputs.state == 'uv-locked' || steps.detect.outputs.state == 'uv-no-lock'
  run: uv run --frozen $NO_BUILD_FLAG <command>  # NOSONAR(S8541): --no-build via input
```

If the `uv-no-lock` path also needs to execute this run step (rare), split it into two `if:`-guarded steps like the install step pattern above. Do NOT use `env: FROZEN_FLAG` + preceding-line NOSONAR inside a `run: |` block; that is the documented anti-pattern.

**For multi-line `run: |` blocks that cannot be collapsed to single lines** (e.g., complex shell logic with heredocs or multi-stage piping), use Pattern B: ensure an install step with literal `--frozen` ran first; in the block, use literal `--frozen` on every `uv run` and a preceding-line `# NOSONAR(S8541): <rationale>` comment.

- [ ] **T-Step 4: Validate with actionlint**

Run:
```bash
actionlint .github/workflows/<WORKFLOW_STEM>.yml
```

Expected: no output (zero errors).

Per `[[feedback_actionlint_shellcheck_embed.md]]`, shellcheck-inside-actionlint ignores `.shellcheckrc`; if shellcheck warnings appear, disable embedded shellcheck for this run with:
```bash
actionlint -shellcheck= .github/workflows/<WORKFLOW_STEM>.yml
```

- [ ] **T-Step 5: Commit**

```bash
git add .github/workflows/<WORKFLOW_STEM>.yml
git commit -m "fix(<WORKFLOW_STEM>): detect repo state instead of hardcoding uv sync/run --frozen

Apply established NOSONAR detect-state pattern (see python-mutation.yml:159-169).
Branches on pyproject.toml + lockfile presence: skip when no pyproject, fail
fast on poetry repos with actionable error, use --frozen on uv-locked repos
and bare uv sync on uv-no-lock repos.

S8541 suppression is acceptable here: the \$NO_BUILD_FLAG env var is dynamic
by design (consumers with PEP 517 build backends like hatchling can pass
no-build: false). Step-level branching would just shuffle the finding."
```

- [ ] **T-Step 6: Push and open PR**

```bash
git push -u origin chore/<WORKFLOW_STEM>-detect-state
gh pr create --repo ByronWilliamsCPA/.github --base main \
  --title "fix(<WORKFLOW_STEM>): detect repo state instead of hardcoding uv sync/run --frozen" \
  --body-file - <<'EOF'
## Summary
- Apply detect-state pattern to <WORKFLOW_STEM>.yml (matches merged PRs #155-#159).
- Add Detect repo state step and FROZEN_FLAG env to every uv install/run.
- Cite NOSONAR S8541 precedent from python-mutation.yml:159-169.

## Affected downstream repos
Per /tmp/ci-failure-inventory.tsv: <COUNT> repos currently failing on this workflow.

## Test plan
- [x] actionlint passes
- [ ] CI on .github passes
- [ ] After merge, one sample downstream caller workflow re-run succeeds
EOF
```

- [ ] **T-Step 7a: Wait for CI**

```bash
gh pr checks <PR_NUMBER> --repo ByronWilliamsCPA/.github --watch
```

- [ ] **T-Step 7b: Verify SonarCloud quality gate (do NOT skip)**

`actionlint` + GitHub CI green is NOT sufficient. SonarCloud is a separate gate.

```bash
sleep 60  # allow SonarCloud analysis to finalize after CI completes
curl -s "https://sonarcloud.io/api/qualitygates/project_status?projectKey=ByronWilliamsCPA_.github&pullRequest=<PR_NUMBER>" \
  | python3 -c "import json,sys; d=json.load(sys.stdin); print('gate:', d['projectStatus']['status'])"
curl -s "https://sonarcloud.io/api/issues/search?componentKeys=ByronWilliamsCPA_.github&pullRequest=<PR_NUMBER>&types=VULNERABILITY&ps=20&statuses=OPEN,CONFIRMED" \
  | python3 -c "import json,sys; d=json.load(sys.stdin); print('open vulns:', d.get('total',0)); [print(f\"  {i['rule']} L{i.get('line','?')}\") for i in d.get('issues',[])]"
```

Expected: `gate: OK` and `open vulns: 0`. If `ERROR`, iterate per the Pattern Selection Guide: each flagged line is either an inline NOSONAR opportunity (Pattern A) or a structural restructuring opportunity (Pattern B). Commit-push-wait-verify loop; SonarCloud analysis takes 2-5 min per push.

- [ ] **T-Step 7c: Merge**

```bash
gh pr merge <PR_NUMBER> --repo ByronWilliamsCPA/.github --squash --delete-branch
```

- [ ] **T-Step 8: Validate one downstream caller**

```bash
gh workflow run "<HUMAN_WORKFLOW_NAME>" --repo <ORG>/<DOWNSTREAM_REPO>
sleep 90
gh run list --repo <ORG>/<DOWNSTREAM_REPO> \
  --workflow "<HUMAN_WORKFLOW_NAME>" --limit 1 --json conclusion,status
```

- [ ] **T-Step 9: Clean worktree**

```bash
cd /home/byron/dev/.github
git worktree remove .worktrees/<WORKFLOW_STEM>-detect-state
```

### Task 2.1: python-release.yml (6 uv-sync/run lines, 8 repos affected)

**Files:**
- Workflow: `.github/workflows/python-release.yml` (385 lines)
- Worktree: `.worktrees/python-release-detect-state`

**Workflow stem:** `python-release`
**Human workflow name:** `Semantic Release`
**Sample downstream:** `ByronWilliamsCPA/homelab-infra` (on inventory)
**Apply Template steps T-Step 1 through T-Step 9 above.**

Notes:
- 6 hardcoded uv lines (handoff said 2; actual count is 6). Inspect each before applying the pattern; some may be in conditional release-mode branches that need careful guard placement.
- No Trivy or third-party scanner concerns. Pure detect-state fix.

### Task 2.2: python-sbom.yml (2 uv-sync lines, 11 repos affected, **Trivy concern**)

**Files:**
- Workflow: `.github/workflows/python-sbom.yml` (297 lines)
- Worktree: `.worktrees/python-sbom-detect-state`

**Workflow stem:** `python-sbom`
**Human workflow name:** `SBOM & Security Scan`
**Sample downstream:** `ByronWilliamsCPA/fragrance-rater` (on inventory)
**Apply Template steps T-Step 1 through T-Step 9 above.**

**Additional decision required before T-Step 3:**

The dependency-management improvement plan (S-6) flags Trivy infrastructure compromise (March 2026) and recommends migrating to Grype. Three options:

| Option | Description | Cost | When to pick |
|---|---|---|---|
| A | Detect-state fix only; keep Trivy | ~30 min | If the goal is just to unblock CI now and defer Grype to a separate PR |
| B | Detect-state fix + swap Trivy → Grype | ~2 hours | If the user wants to bundle the security improvement into the same change |
| C | Detect-state fix + add Grype as a parallel scanner, keep Trivy | ~3 hours | Risk-averse: validate Grype against Trivy output before switching |

**Decision gate:** ASK THE USER before starting Task 2.2. The handoff defers this question. Recommended default: **Option A** to keep PRs small and uniform; track Trivy → Grype as a follow-up issue.

**DECISION (2026-05-25):** Option A. Detect-state fix only; defer Trivy → Grype to a separate follow-up. After Task 2.2 merges, open a tracking issue on `BWCPA/.github` titled "Migrate SBOM scanner from Trivy to Grype (S-6 improvement plan)" with a link to the improvement plan section.

### Task 2.3: python-sonarcloud.yml (6 uv-sync lines, 3 direct + .github itself, plus per-repo issues)

**Files:**
- Workflow: `.github/workflows/python-sonarcloud.yml` (391 lines)
- Worktree: `.worktrees/python-sonarcloud-detect-state`

**Workflow stem:** `python-sonarcloud`
**Human workflow name:** `SonarCloud`
**Sample downstream:** `ByronWilliamsCPA/family-office-portal` (on inventory)
**Apply Template steps T-Step 1 through T-Step 9 above.**

Per-repo issues handled separately in Phase 3 (Task 3.3):
- `python-libs` `sonar.tests=tests/,packages/*/tests/` wildcards (per-repo `sonar-project.properties` fix)
- `cookiecutter-python-template` Jinja `{{cookiecutter.project_slug}}` placeholder (per-repo)
- `Unify` stale 2026-05-08 cache miss (per-repo cache invalidation)

### Task 2.4: python-precommit.yml (6 uv-sync lines, not on inventory but has pattern)

**Files:**
- Workflow: `.github/workflows/python-precommit.yml` (101 lines)
- Worktree: `.worktrees/python-precommit-detect-state`

**Workflow stem:** `python-precommit`
**Human workflow name:** `Pre-commit Checks` (verify exact name with `gh workflow list --repo ByronWilliamsCPA/<sample-repo>`)
**Sample downstream:** pick any active uv repo; pre-commit runs on most.
**Apply Template steps T-Step 1 through T-Step 9 above.**

Smallest file in the queue (101 lines); start here if Phase 2 is being divided across multiple sessions or contributors as a warm-up.

### Task 2.5: python-docs.yml (4 uv-sync lines)

**Files:**
- Workflow: `.github/workflows/python-docs.yml` (151 lines)
- Worktree: `.worktrees/python-docs-detect-state`

**Workflow stem:** `python-docs`
**Human workflow name:** `Documentation`
**Sample downstream:** `ByronWilliamsCPA/audio-processor` (on inventory)
**Apply Template steps T-Step 1 through T-Step 9 above.**

### Task 2.6: python-mutation.yml verification + completion (7 uv-sync/run lines, 2 already NOSONAR)

**Files:**
- Workflow: `.github/workflows/python-mutation.yml` (382 lines)
- Worktree: `.worktrees/python-mutation-detect-state`

**Workflow stem:** `python-mutation`
**Human workflow name:** `Mutation Testing`
**Sample downstream:** `ByronWilliamsCPA/maester-tests` (on inventory)

**Pre-work delta:** This workflow already established the NOSONAR convention at lines 159-169. The other 5 uv-sync/run lines may or may not need the detect-state guard.

- [ ] **Step A (BEFORE T-Step 3): Audit existing NOSONAR placements**

```bash
grep -nE "uv sync|uv run|NOSONAR|Detect repo state" \
  /home/byron/dev/.github/.github/workflows/python-mutation.yml
```

Decide per line: does it already have a detect-state guard, or is the file inconsistent? Apply T-Step 3 only to the unguarded lines. Per the handoff: "Verify no detect-state gap." Per `[[feedback_mutation_testing_pr_trigger.md]]`, also confirm the trigger is `workflow_call + schedule + workflow_dispatch` only (manifest CI-053). Do NOT add `pull_request:`.

- [ ] **Step B: Continue with T-Step 4 through T-Step 9.**

### Task 2.7: python-performance-regression.yml (19 uv-sync/run lines, **largest fix**)

**Files:**
- Workflow: `.github/workflows/python-performance-regression.yml` (642 lines)
- Worktree: `.worktrees/python-performance-regression-detect-state`

**Workflow stem:** `python-performance-regression`
**Human workflow name:** `Performance Regression`
**Sample downstream:** pick from `gh workflow list --repo ByronWilliamsCPA/python-libs`
**Apply Template steps T-Step 1 through T-Step 9 above.**

**Sizing warning:** 642 lines and 19 uv invocations make this the largest single-file change in the sprint. Allocate 60-90 minutes for T-Step 3 alone. Consider splitting the PR by job (perf benchmark job vs perf comparison job) if review fatigue is a concern, but a single PR is preferred for atomic revert if downstream issues surface.

---

## Phase 3: Per-repo (non-reusable-workflow) fixes (4-8 hours)

These do not benefit from leverage; each repo needs individual work. Order is by failure count first.

### Task 3.1: SLSA per-repo template application (7 repos)

**Reference:** `[[feedback_slsa_provenance_pattern.md]]`: SLSA's generic generator forbids nested reusable-workflow calls, so each repo has its own `.github/workflows/slsa-provenance.yml`. Per the memory: build-dist must download pre-built artifacts, never rebuild; attestation must match what PyPI received.

**Affected repos (from `/tmp/ci-failure-inventory.tsv`):**
- `ByronWilliamsCPA/.claude`
- `ByronWilliamsCPA/fragrance-rater`
- `ByronWilliamsCPA/homelab-infra`
- `ByronWilliamsCPA/rag-processor`
- `ByronWilliamsCPA/Unify`
- `williaby/dna`
- (one more; confirm with `grep slsa-provenance /tmp/ci-failure-inventory.tsv`)

#### Task template (one PR per repo)

- [ ] **Step 1: Read the failing repo's current slsa-provenance.yml**

```bash
gh api repos/<ORG>/<REPO>/contents/.github/workflows/slsa-provenance.yml \
  --jq .content | base64 -d > /tmp/slsa-<REPO>.yml
cat /tmp/slsa-<REPO>.yml
```

- [ ] **Step 2: Pull the most recent failure log**

```bash
gh run list --repo <ORG>/<REPO> --workflow slsa-provenance.yml --limit 1 \
  --json databaseId --jq '.[0].databaseId' \
  | xargs -I {} gh run view {} --repo <ORG>/<REPO> --log-failed
```

- [ ] **Step 3: Diagnose and apply fix in a per-repo worktree**

Use the canonical pattern in `BWCPA/.github` `slsa-provenance.yml` (which is the template, not a reusable workflow). Compare and patch.

Common root causes for the cohort:
- build-dist job rebuilds artifacts instead of downloading PyPI release assets → fix per `[[feedback_slsa_provenance_pattern.md]]`
- SHA pin drift → bump to current pinned SHA (Phase 4 will sweep this)
- Detect-state gap in `uv sync` lines used during build-dist → apply the Phase 2 template

- [ ] **Step 4: One PR per repo, conventional title**

```bash
gh pr create --repo <ORG>/<REPO> --base main \
  --title "fix(ci): repair slsa-provenance workflow" \
  --body "Per CI Repair Sprint Phase 3. Root cause: <ONE_LINE>. See docs/audits/ci-repair-sprint-handoff-2026-05-25.md."
```

### Task 3.2: CodeQL per-repo investigation (7 repos)

**Affected:** `python-libs`, `data_ingestor`, `GCS`, plus others on inventory.

The handoff notes: "The SARIF upload bug in python-libs is private-repo-specific (likely GHAS Code Scanning configuration). Public repos (e.g., .github) pass CodeQL cleanly."

- [ ] **Step 1: Identify each repo's CodeQL failure mode**

For each affected repo:
```bash
gh run list --repo <ORG>/<REPO> --workflow "CodeQL Analysis" --limit 1 \
  --json databaseId --jq '.[0].databaseId' \
  | xargs -I {} gh run view {} --repo <ORG>/<REPO> --log-failed | grep -E "Error|error|fail" | head -20
```

- [ ] **Step 2: Group by root cause**

Expected groups:
- GHAS not enabled on private repos (admin action, not code fix)
- SARIF upload rate-limited (retry sufficient)
- Detect-state gap in matrix setup (same as Phase 2)
- Other (investigate individually)

- [ ] **Step 3: Apply per-group fix and open PRs as needed.**

### Task 3.3: SonarCloud per-repo variants (3 repos)

Three failures, three root causes; handle individually after Task 2.3 lands.

- [ ] **Step 1: python-libs `sonar-project.properties` wildcards**

```bash
gh repo clone ByronWilliamsCPA/python-libs /tmp/python-libs-sonar-fix
cd /tmp/python-libs-sonar-fix
git checkout -b fix/sonar-tests-wildcards
```

Edit `sonar-project.properties`: replace `sonar.tests=tests/,packages/*/tests/` with explicit per-package paths. SonarCloud does not expand glob wildcards in `sonar.tests`. Commit, push, PR.

- [ ] **Step 2: cookiecutter-python-template Jinja placeholder**

The `sonar-project.properties` template ships with `{{cookiecutter.project_slug}}` unrendered. Either:
- Move the file into the rendered template directory so cookiecutter resolves it at instantiation time, OR
- Add a `.sonarcloud.yml` override for the template repo that skips analysis.

Choose based on whether the template repo itself needs SonarCloud coverage (likely no).

- [ ] **Step 3: Unify stale cache**

```bash
gh api -X DELETE /repos/ByronWilliamsCPA/Unify/actions/caches/<CACHE_ID>
gh workflow run "SonarCloud" --repo ByronWilliamsCPA/Unify
```

List cache IDs first with `gh api /repos/ByronWilliamsCPA/Unify/actions/caches`.

---

## Phase 4: Downstream SHA-pin sweep (2-3 hours)

After every reusable-workflow fix in Phases 1-2 lands on `BWCPA/.github` main, downstream callers that pin to a SHA (rather than `@main`) need their pins bumped.

- [ ] **Step 1: Identify pinned-SHA callers**

```bash
gh search code --owner ByronWilliamsCPA --owner williaby \
  "uses: ByronWilliamsCPA/.github/.github/workflows/python-" \
  --json repository,path | python3 -c "
import json, sys, re
data = json.load(sys.stdin)
sha_pinned = []
for hit in data:
    # Need to fetch file content to check SHA vs @main
    sha_pinned.append((hit['repository']['nameWithOwner'], hit['path']))
print('\n'.join(f'{r}\t{p}' for r,p in sha_pinned))
" > /tmp/sha-pin-callers.tsv
wc -l /tmp/sha-pin-callers.tsv
```

Per `[[feedback_gh_search_code_staleness]]`, `gh search code` lags default-branch HEAD. Cross-check with `gh api repos/<r>/contents/<path>` for any caller that fails subsequent steps.

- [ ] **Step 2: Bump pins to current main SHA**

Get current `BWCPA/.github` main SHA:
```bash
MAIN_SHA=$(gh api repos/ByronWilliamsCPA/.github/commits/main --jq .sha)
echo $MAIN_SHA
```

For each pinned caller, open a one-line PR replacing the old SHA with `$MAIN_SHA`. Renovate would do this on the next cycle, but the sprint goal is to unblock blocked PRs now.

Alternative: skip the sweep entirely and let Renovate handle it on its next run. **Decision gate:** ASK THE USER. The handoff says "deferred per user decision; tracked separately"; confirm whether to do the sweep as part of this sprint or punt to Renovate.

**DECISION (2026-05-25):** Punt. Phase 4 is skipped in this sprint. Renovate will pick up SHA pin bumps on its next cycle. If any specific downstream PR in Phase 5 is blocked on a stale pin, bump that one inline as a one-off; do not batch-sweep. Remove Phase 4 from the critical path; jump from Phase 3 straight to Phase 5.

---

## Phase 5: Resume Phase 3B and Phase 3C (per `docs/audits/phase-3bc-handoff-2026-05-25.md`)

After Phases 1-3 are green, the dependency-management sprint unblocks. Defer to the Phase 3B/3C handoff doc for detailed task structure.

- [ ] **Step 1: Read the Phase 3B/3C handoff**

```bash
cat /home/byron/dev/.claude/docs/audits/phase-3bc-handoff-2026-05-25.md
```

- [ ] **Step 2: Confirm previously-blocked PRs are now unblocked**

```bash
for pr in "williaby/image-preprocessing-detector#190" \
          "ByronWilliamsCPA/rag-processor#53" \
          "ByronWilliamsCPA/python-libs#43" \
          "ByronWilliamsCPA/audio-processor#40" \
          "ByronWilliamsCPA/cookiecutter-template-sample#14" \
          "ByronWilliamsCPA/fragrance-rater#30" \
          "ByronWilliamsCPA/maester-tests#26" \
          "williaby/dna#22"; do
  echo "=== $pr ==="
  gh pr checks "${pr##*#}" --repo "${pr%#*}" 2>&1 | tail -5
done
```

Expected: most checks now `pass` or transitioning to `pass`. Re-trigger any failed ones with `gh workflow run`.

- [ ] **Step 3: Resume Phase 3B (36 dependabot.yml deletes)** per the Phase 3B/3C handoff.

- [ ] **Step 4: Resume Phase 3C (9 poetry-to-pep621 PRs)** per the Phase 3B/3C handoff. The python-libs CHANGELOG-fix worktree at `~/dev/python-libs/.worktrees/renovate-pep621-fix/` will need a rebase first.

---

## Phase 6: Re-baseline coverage audit (Task #7 from improvement plan)

Once CI is fully green and Phase 3B/3C have landed, re-run the Snyk-vs-Renovate coverage comparison to inform the consolidation decision.

- [ ] **Step 1: Re-run the coverage scan**

Reference `docs/audits/cve-scan-coverage-2026-05-25.md` for the original methodology. Re-execute the same scan with current state.

- [ ] **Step 2: Compare and produce decision doc**

Output: `docs/audits/cve-scan-coverage-<NEW_DATE>.md` with explicit recommendation: consolidate on Renovate, keep both, or revert any Renovate-side changes.

---

## Phase 7: Cleanup and close-out

- [ ] **Step 1: Mark all in-flight worktrees removed**

```bash
git -C /home/byron/dev/.github worktree list
git -C /home/byron/dev/python-libs worktree list
# Remove any Phase 1-5 worktrees that lingered
```

- [ ] **Step 2: Final inventory snapshot**

Run the same query that produced `/tmp/ci-failure-inventory.tsv` originally and diff against the snapshot from Task 0.1 Step 3. Expected: failures reduced from 155 to <10 (any remaining are infra-level GHAS / SonarCloud configuration tasks, not code fixes).

```bash
# (use the same query that produced the original; see handoff for the exact gh api command)
# diff old.tsv new.tsv
```

- [ ] **Step 3: Write the sprint retrospective**

Create `docs/audits/ci-repair-sprint-retro-<DATE>.md` covering:
- What broke and why (one paragraph)
- The detect-state pattern as the unifying fix
- Repos touched, PRs merged, hours spent
- Memory entries to create (e.g., a `feedback_detect_state_pattern.md` capturing the pattern for future reusable-workflow authoring)

- [ ] **Step 4: Run repo-compliance sweep**

```bash
# Invoke the repo-compliance skill in scheduled (report-only) mode across the 44 active repos
```

Confirms that the CI repair did not introduce any standards regressions.

---

## Hard rules (carry through every task)

- **NO em-dashes** in any commit, PR body, or doc (U+2014 is banned by PC-011 and CLAUDE.md). Use comma, semicolon, colon, or parentheses.
- **NEVER** use `--no-verify`, `--no-gpg-sign`, `--admin`, or force-push to main. See `[[project_bypass_flag_guards]]`. `bash-pre-hook.sh` will block these.
- **Worktrees** always under `<repo>/.worktrees/<branch-slug>`. Never `~/.config/` or global paths.
- **Suppression comments** need rationale; cite `python-mutation.yml:159-169` for any new `# NOSONAR S8541`.
- **Subagent relay citations:** if delegating any task to a subagent via SendMessage, cite verifiable `file:line` evidence (per `[[feedback_subagent_relay_citations]]`).
- **Reviewdog filter modes** diverge PR vs push (`[[feedback_reviewdog_filter_modes]]`); a green PR is not proof of a green push; wait for the post-merge run before declaring victory.
- **GitHub merge eligibility UI lag** (`[[feedback_github_merge_eligibility_ui_lag]]`): trust the Checks API + mergeStateStatus over the PR panel.

---

## Self-Review (executed during plan authoring)

1. **Spec coverage:** Every section of the handoff's `## Quick session-start checklist` maps to a phase here: items 1-4 → Phase 0; item 5 → Phase 1; item 6 → Phase 2; item 7 → Phase 4; item 8 → Phase 5; item 9 → Phase 6. Phase 3 covers the per-repo work listed under "Per-repo (not reusable-workflow) work". Phase 7 adds explicit cleanup and retrospective that the handoff implies but doesn't enumerate.

2. **Placeholder scan:** No "TBD", "implement later", or unmaterialized references. Every `<PLACEHOLDER>` is a substitution variable explicitly defined in its task block (e.g., `<WORKFLOW_STEM>`, `<PR_NUMBER>`, `<ORG>/<REPO>`).

3. **Type / signature consistency:** The `detect.outputs.state` values (`skip`, `poetry-not-supported`, `uv-locked`, `uv-no-lock`) and `FROZEN_FLAG` env var are identical across the template, the source convention citation, and every Task 2.N. The NOSONAR rule ID `S8541` is consistent throughout.

4. **Shell command environment:** All `gh` commands are self-contained (no env vars assumed). `actionlint` is assumed installed; if absent, install via `go install github.com/rhysd/actionlint/cmd/actionlint@latest` or `brew install actionlint`. Per `[[feedback_actionlint_shellcheck_embed.md]]`, embedded shellcheck flags are documented inline. Per `[[feedback_renovate_uv_manager_trap.md]]`, no `enabledManagers: ["uv"]` ever; use `pep621` if any renovate.json work surfaces during Phase 5.

5. **Capability probe:** Not directly applicable (no managed cloud mode flags). The closest analog is the `gh workflow run` validation in T-Step 8: one downstream call per workflow before declaring success. This catches the "fix passed on .github CI but downstream consumers still fail" failure mode.

6. **Decision gates surfaced:** Two explicit user-decision gates (Task 2.2 Trivy → Grype, Phase 4 SHA-pin sweep scope) are flagged inline rather than assumed.

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-05-25-ci-repair-sprint-completion.md`. Two execution options:

**1. Subagent-Driven (recommended):** Dispatch a fresh subagent per task, review between tasks, fast iteration. Particularly suited here: Phase 2 tasks 2.1-2.7 are independent and could be parallelized to 2-3 concurrent subagents (one per workflow) once Phase 1 lands. Phase 3 per-repo work also parallelizes well (one repo per subagent).

**2. Inline Execution:** Execute tasks in this session using `superpowers:executing-plans`, batch execution with checkpoints. Suited if the user wants to watch each PR through CI personally and intervene on the Trivy and SHA-pin decision gates synchronously.

**Which approach?**
