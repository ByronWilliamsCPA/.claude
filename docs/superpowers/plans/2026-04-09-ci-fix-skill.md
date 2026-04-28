---
schema_type: planning
title: "/ci-fix Skill Implementation"
status: draft
owner: core-maintainer
purpose: "Implementation plan for the /ci-fix skill: 7-gate CI fix loop with auto-fix, status table, commit offer, and PR reminder wiring."
component: Development-Tools
source: "docs/superpowers/specs/2026-04-09-ci-fix-skill-design.md"
tags:
  - automation
  - tooling
  - ci_cd
---

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a `/ci-fix` skill that runs a consistent 7-gate quality sequence, auto-fixes where possible, and offers to commit when all gates are green.

**Architecture:** Three file changes: a new `ci-fix/SKILL.md`, a prerequisite step added to `git/workflows/pr.md`, and a checkbox added to `rules/pre-commit.md`. No scripts, no hooks, no additional infrastructure.

**Tech Stack:** Markdown (skill definition), bash commands referenced inline (ruff, qlty, pre-commit, pytest, bandit, pip-audit, uv)

---

### Task 1: Create the ci-fix SKILL.md

**Files:**
- Create: `/home/byron/dev/.claude/.claude/skills/ci-fix/SKILL.md`

- [ ] **Step 1: Verify the target directory does not already exist**

```bash
ls /home/byron/dev/.claude/.claude/skills/ci-fix/ 2>/dev/null || echo "directory does not exist — safe to create"
```

Expected: "directory does not exist — safe to create"

- [ ] **Step 2: Create the SKILL.md**

Create `/home/byron/dev/.claude/.claude/skills/ci-fix/SKILL.md` with this exact content:

```markdown
---
description: >
  Full CI gate sequence with auto-fix loop. Runs ruff format, ruff lint, qlty check,
  pre-commit, pytest, bandit, and pip-audit in order — fixing what it can and reporting
  blockers. Triggers on: ci-fix, fix ci, fix gates, all gates green, pre-commit failing,
  tests failing, ci failing, fix everything, gates failing.
tools: ["Read", "Bash", "Grep", "Glob", "Edit", "Write"]
---

# CI Fix Skill

Run a consistent 7-gate quality sequence, auto-fix where possible, and offer to commit when
all gates are green.

## Invocation

```
/ci-fix
```markdown

No arguments. Always runs the full gate sequence.

## Gate Sequence

Run gates in this fixed order. After each fix attempt, re-run the gate before advancing.
Never skip a gate. Never change the order.

| # | Gate | Command | Auto-fix strategy |
|---|------|---------|-------------------|
| 1 | ruff format | `uv run ruff format --check .` | `uv run ruff format .` (deterministic) |
| 2 | ruff lint | `uv run ruff check .` | `uv run ruff check --fix .`; remaining unfixable rules: edit manually |
| 3 | qlty check | `qlty check` | No auto-fix — refactor functions exceeding complexity/nesting thresholds |
| 4 | pre-commit | `pre-commit run --all-files` | Re-run after ruff fixes; remaining failures: fix and re-run |
| 5 | pytest | `uv run pytest` | Read failure output, fix test or implementation issues, re-run |
| 6 | bandit | `uv run bandit -r src/ -c pyproject.toml` | Fix code issues; false positives: add `# nosec` with an open tracking reference |
| 7 | pip-audit | `uv run pip-audit` | Report only — dependency upgrades require user decision |

## Status Table

Print the full table after each gate completes. Always print all 7 rows regardless of
how many have completed.

```
CI Fix Status
─────────────────────────────────────────────────────
Gate          Status       Notes
─────────────────────────────────────────────────────
ruff format   ✅ PASS
ruff lint     ✅ PASS      4 issues auto-fixed
qlty check    🔧 FIXING    2 functions exceed complexity threshold
pre-commit    ⏳ PENDING
pytest        ⏳ PENDING
bandit        ⏳ PENDING
pip-audit     ⏳ PENDING
─────────────────────────────────────────────────────
```markdown

Status values:
- `⏳ PENDING` — not yet run
- `🔧 FIXING` — fix in progress
- `✅ PASS` — gate green (include note if fixes were applied)
- `❌ BLOCKER` — failed after fix attempt; manual intervention required

## Blocker Behavior

When a gate fails and cannot be resolved in one fix attempt:
- Mark it `❌ BLOCKER` in the table
- Continue running the remaining gates — report the full picture
- Do not stop early

pip-audit findings are always reported but never count as a blocker for the commit offer.

## Completion

**All non-pip-audit gates green:**

```
All 7 gates green. Commit now? (yes/no)
```text

- **Yes**: invoke the `/git` skill to prepare a conventional commit
- **No**: stop — present the green status table and hand back

**Any blocker remains:**

```
5/7 gates pass. Blockers:

  ❌ pytest     — 2 tests failing in tests/unit/test_processor.py (see output above)
  ❌ bandit     — HIGH severity B608 at src/query.py:45 (see output above)

These require manual investigation before committing.
```text

No commit offer when blockers remain.
```

- [ ] **Step 3: Verify the file was created and reads correctly**

```bash
head -20 /home/byron/dev/.claude/.claude/skills/ci-fix/SKILL.md
```

Expected: frontmatter block starting with `---`, description field present, no truncation.

- [ ] **Step 4: Commit**

```bash
git -C /home/byron/dev/.claude add .claude/skills/ci-fix/SKILL.md
git -C /home/byron/dev/.claude commit -m "feat: add /ci-fix skill — 7-gate CI fix loop with auto-fix and commit offer"
```

---

### Task 2: Add /ci-fix prerequisite to git PR workflow

**Files:**
- Modify: `/home/byron/dev/.claude/.claude/skills/git/workflows/pr.md`

- [ ] **Step 1: Verify the exact anchor text before the insertion point**

```bash
grep -n "Gather Context\|### 1" /home/byron/dev/.claude/.claude/skills/git/workflows/pr.md
```

Expected: a line matching `### 1. Gather Context` — the prerequisite block goes immediately before it.

- [ ] **Step 2: Insert the /ci-fix prerequisite before step 1**

In `/home/byron/dev/.claude/.claude/skills/git/workflows/pr.md`, replace:

```markdown
### 1. Gather Context
```

With:

```markdown
### 0. Confirm CI gates are green

Before creating the PR, confirm `/ci-fix` has been run and all gates are green. If not,
run it now:

```
/ci-fix
```markdown

Do not proceed with PR creation until all blockers are resolved. pip-audit findings
should be documented in the PR description if they cannot be resolved immediately.

### 1. Gather Context
```

- [ ] **Step 3: Verify the insertion reads correctly**

```bash
grep -n -A 10 "### 0\." /home/byron/dev/.claude/.claude/skills/git/workflows/pr.md
```

Expected: the new step 0 block with the `/ci-fix` invocation, followed by `### 1. Gather Context`.

- [ ] **Step 4: Commit**

```bash
git -C /home/byron/dev/.claude add .claude/skills/git/workflows/pr.md
git -C /home/byron/dev/.claude commit -m "feat: add /ci-fix prerequisite to git PR workflow"
```

---

### Task 3: Add /ci-fix checkbox to pre-commit checklist

**Files:**
- Modify: `/home/byron/dev/.claude/.claude/rules/pre-commit.md`

- [ ] **Step 1: Verify the exact anchor text in the PR section**

```bash
grep -n "## PR\|Branch Safety\|PR Creation" /home/byron/dev/.claude/.claude/rules/pre-commit.md
```

Expected: `## PR (if creating PR)` section with `Branch Safety` as the first checklist item.

- [ ] **Step 2: Add the CI gates checkbox as the first item in the PR section**

In `/home/byron/dev/.claude/.claude/rules/pre-commit.md`, replace:

```markdown
## PR (if creating PR)
- [ ] **Branch Safety**: PR preparation validates branch strategy
```

With:

```markdown
## PR (if creating PR)
- [ ] **CI gates**: `/ci-fix` run and all gates green (or blockers documented in the PR)
- [ ] **Branch Safety**: PR preparation validates branch strategy
```

- [ ] **Step 3: Verify the section reads correctly**

```bash
grep -n -A 5 "## PR" /home/byron/dev/.claude/.claude/rules/pre-commit.md
```

Expected: CI gates checkbox is the first item under `## PR (if creating PR)`, followed by Branch Safety.

- [ ] **Step 4: Run pre-commit on modified file**

```bash
cd /home/byron/dev/.claude && pre-commit run --files .claude/rules/pre-commit.md
```

Expected: all hooks pass.

- [ ] **Step 5: Commit**

```bash
git -C /home/byron/dev/.claude add .claude/rules/pre-commit.md
git -C /home/byron/dev/.claude commit -m "feat: add /ci-fix gate check to PR pre-commit checklist"
```

---

### Task 4: Integration verification

**Files:** Read-only.

- [ ] **Step 1: Verify ci-fix SKILL.md has all 7 gates**

```bash
grep -c "uv run\|qlty check\|pre-commit" /home/byron/dev/.claude/.claude/skills/ci-fix/SKILL.md
```

Expected: at least 7 matches (one per gate command).

- [ ] **Step 2: Verify git PR workflow has the prerequisite**

```bash
grep -n "ci-fix\|### 0" /home/byron/dev/.claude/.claude/skills/git/workflows/pr.md
```

Expected: at least 2 matches — the step header and the skill invocation.

- [ ] **Step 3: Verify pre-commit.md has the checkbox**

```bash
grep -n "ci-fix" /home/byron/dev/.claude/.claude/rules/pre-commit.md
```

Expected: 1 match in the `## PR` section.

- [ ] **Step 4: Verify all three commits are present**

```bash
git -C /home/byron/dev/.claude log --oneline -5
```

Expected: the three commits from Tasks 1-3 in recent history.
