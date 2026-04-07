---
name: debug-tests
description: >
  Debug failing tests with root-cause-first analysis. Auto-activates on: failing test,
  test failure, debug test, test error, pytest error, test broken, tests failing
argument-hint: "[test-path]"
allowed-tools:
  - Read
  - Bash
  - Grep
  - Glob
  - Edit
---

# Debug Tests Skill

Debug test failures using root-cause-first analysis. Investigates structural causes
before touching application code.

## Invocation

```
/debug-tests [test-path]
```

**Example**: `/debug-tests tests/unit/test_auth.py`

If no path is provided, run the full suite to identify failures first.

## Workflow

### Step 1 — Reproduce

```bash
pytest $ARGUMENTS -v --tb=long 2>&1 | head -100
```

Capture the full error output before drawing conclusions.

### Step 2 — Classify Root Cause

Investigate in this order (do not skip ahead to application logic):

1. **Fixtures & configuration** — conftest.py issues, missing seed data, incorrect
   factory defaults, fixture scope problems
2. **Environment mismatches** — SQLite vs Postgres differences (JSONB, UUID, pool_size),
   missing env vars, Python version incompatibility
3. **Dependency drift** — a locked dependency changed behavior, version constraint mismatch,
   breaking change in an updated library
4. **Test isolation** — shared state between tests, ordering dependencies, missing teardown,
   leaked side effects
5. **Application logic** — only investigate here after ruling out 1–4

### Step 3 — Fix and Verify

- Apply the minimal fix targeting the classified root cause
- Re-run the failing test in isolation:
  ```bash
  pytest path/to/test_file.py::test_name -v
  ```
- Run the full suite to check for side effects:
  ```bash
  uv run pytest --tb=short
  ```

### Step 4 — Document

Include the root cause category in the commit message:

```
fix(tests): repair auth fixture after session scope change

Root cause: Category 1 (fixture scope) — conftest session fixture
was sharing state across test classes.
```
