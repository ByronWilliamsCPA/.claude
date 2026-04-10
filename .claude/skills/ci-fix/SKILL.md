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
```

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
```

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
```

- **Yes**: invoke the `/git` skill to prepare a conventional commit
- **No**: stop — present the green status table and hand back

**Any blocker remains:**

```
5/7 gates pass. Blockers:

  ❌ pytest     — 2 tests failing in tests/unit/test_processor.py (see output above)
  ❌ bandit     — HIGH severity B608 at src/query.py:45 (see output above)

These require manual investigation before committing.
```

No commit offer when blockers remain.
