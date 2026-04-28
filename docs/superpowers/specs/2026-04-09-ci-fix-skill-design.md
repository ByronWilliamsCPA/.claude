---
schema_type: common
title: "/ci-fix Skill - Full Gate CI Fix Loop"
status: draft
owner: core-maintainer
purpose: "Design spec for a /ci-fix skill that runs a consistent 7-gate quality sequence, auto-fixes where possible, and asks to commit when all gates are green."
tags:
  - tooling
  - specifications
  - automation
  - ci_cd
---

> **Date**: 2026-04-09
> **Status**: Approved
> **Scope**: Global `~/.claude` tooling (dev repo at `~/dev/.claude`)

## Problem

Usage report analysis identified 9+ recurring session patterns where Claude ran quality gates
in inconsistent order, missed gates entirely, or re-ran individual gates manually after each
fix. No standard sequence existed for "fix everything until green before committing."

The new `py310-compat-check.sh` hook fires per file edit, but pytest failures, bandit issues,
and qlty complexity violations still require a coordinated fix loop that no single skill covers.

## Goals

- Run a consistent 7-gate sequence in the same order every time
- Auto-fix mechanical failures (ruff format/lint); Claude fixes reasoning-required failures
  (pytest, bandit, qlty complexity)
- Track and display a running status table after each gate
- Offer a commit when all gates pass (via `/git` skill)
- Surface a reminder before PR creation so gates are always green at merge time

## Non-Goals

- No hook implementation - gates requiring Claude judgment cannot run in a hook context
- No scope flags (`/ci-fix lint`) - full sweep is the only mode
- No parallel gate execution - gates run sequentially; some fixes affect later gates
- Does not replace pre-commit (which runs as a hook on file edits automatically)

## Architecture

Single SKILL.md. No workflows subdirectory. Three file changes total:

| File | Action |
|------|--------|
| `.claude/skills/ci-fix/SKILL.md` | New skill |
| `.claude/skills/git/SKILL.md` | Add `/ci-fix` prerequisite to PR workflow section |
| `.claude/rules/pre-commit.md` | Add `/ci-fix` checkbox to PR preparation checklist |

## Gate Sequence

Gates run in this fixed order. Each gate re-runs after fixes to confirm green before advancing.

| # | Gate | Command | Auto-fix strategy |
|---|------|---------|-------------------|
| 1 | ruff format | `uv run ruff format --check .` | `uv run ruff format .` (deterministic) |
| 2 | ruff lint | `uv run ruff check .` | `uv run ruff check --fix .`; unfixable rules: Claude edits manually |
| 3 | qlty check | `qlty check` | No auto-fix - Claude refactors functions exceeding complexity/nesting thresholds |
| 4 | pre-commit | `pre-commit run --all-files` | Re-run after ruff fixes; remaining failures Claude fixes and re-runs |
| 5 | pytest | `uv run pytest` | Claude reads failure output, fixes test/implementation issues, re-runs |
| 6 | bandit | `uv run bandit -r src/ -c pyproject.toml` | Claude fixes code issues; false positives: `# nosec` + open tracking reference |
| 7 | pip-audit | `uv run pip-audit` | Report only - dependency upgrades require user decision |

**Blocker definition**: a gate that fails and cannot be resolved by the auto-fix strategy in
one attempt. The skill continues running remaining gates (does not stop at first blocker) to
give a full picture of the codebase state.

**pip-audit special case**: findings are always reported but never block the commit offer,
since dependency upgrades require deliberate user action outside the fix loop.

## Status Display

After each gate completes, print the full status table:

```bash
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
```

Status values: `⏳ PENDING` → `🔧 FIXING` → `✅ PASS` / `❌ BLOCKER`

## Completion Behavior

**All gates pass** (blockers = 0, pip-audit may have findings):

```text
All 7 gates green. Commit now? (yes/no)
```

- Yes: invoke `/git` skill for conventional commit (git skill handles staging, signing, message)
- No: stop and hand back with the green status table

**Blockers remain**:

```text
5/7 gates pass. Blockers:

  ❌ pytest     - 2 tests failing in tests/unit/test_processor.py (see above)
  ❌ bandit     - HIGH severity B608 at src/query.py:45 (see above)

These require manual investigation before committing.
```

No commit offer is made when blockers remain.

## PR Reminder

Two touch points ensure `/ci-fix` runs before every PR:

**In `/git` SKILL.md PR workflow**: Add as a prerequisite step before PR creation:
> "Confirm `/ci-fix` has been run and all gates are green. If not, run it now before creating
> the PR."

**In `pre-commit.md` checklist**: Add to the PR section:
> `- [ ] **CI gates**: `/ci-fix` run and all gates green (or blockers documented)`

## Invocation

```text
/ci-fix
```

No arguments. Always runs the full 7-gate sequence.

## Testing

Manual verification with three scenarios:

1. **All green**: Run on a clean repo state - all 7 gates pass, commit offer appears
2. **Ruff failure**: Introduce a formatting violation - gate 1 auto-fixes, re-runs green
3. **pytest failure**: Introduce a failing test - skill reads failure, attempts fix, reports
   blocker if fix fails after one attempt

## File Locations

| File | Purpose |
|------|---------|
| `.claude/skills/ci-fix/SKILL.md` | Skill definition and workflow |
| `.claude/skills/git/SKILL.md` | PR workflow prerequisite reminder |
| `.claude/rules/pre-commit.md` | PR checklist `/ci-fix` checkbox |
