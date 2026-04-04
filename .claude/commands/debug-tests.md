---
description: Debug failing tests with root-cause-first analysis
argument-hint: [test-path]
allowed-tools: [Read, Bash, Grep, Glob, Edit]
---

Debug test failures using root-cause-first analysis.

**Step 1 — Reproduce**: Run `pytest $ARGUMENTS -v --tb=long 2>&1 | head -100`

**Step 2 — Classify root cause** (investigate in order):

1. Fixtures & configuration (conftest.py, factory defaults, seed data)
2. Environment (SQLite vs Postgres, env vars, Python version)
3. Dependencies (locked version changes, breaking updates)
4. Test isolation (shared state, ordering, missing teardown)
5. Application logic (only after ruling out 1-4)

**Step 3 — Fix and verify**:

- Apply minimal fix
- Re-run failing test in isolation
- Run full suite to check for side effects

**Step 4 — Document**: Include root cause category in commit message
