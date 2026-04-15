---
paths:
  - "**/test_*.py"
  - "**/*_test.py"
  - "**/tests/**"
  - "**/conftest.py"
  - "**/*.snap"
  - "tests/golden/**"
---

# Testing Rules

These rules load only when Claude works with test files, fixtures, or snapshot
files. Universal test policy (coverage thresholds, CI gates, framework choice)
lives in `.claude/standards/testing.md` and loads unconditionally.

## Clarify scope before touching tests

When asked to fix or improve tests, clarify scope first. These are different
tasks:

- Adding missing tests
- Fixing failing tests
- Improving test depth

Do not silently convert a "fix this failing test" request into a test rewrite.
Ask before broadening scope.

## Root-cause order for failing tests

When tests fail, investigate root causes in this order before proposing a fix.
Jumping to a fix before identifying the layer wastes time on the wrong problem.

1. **Test fixtures and configuration**: missing seed data, incorrect factory
   defaults, conftest.py issues, test isolation problems
2. **Environment mismatches**: SQLite vs Postgres differences (JSONB, UUID,
   pool_size), Python version differences, operating system differences
3. **Dependency drift**: an updated library changed behavior, version
   constraint mismatch between lockfile and runtime
4. **Test isolation**: shared state between tests, ordering dependencies,
   missing teardown, parallel execution races

If the failure is reproducible in isolation but not in the full suite (or vice
versa), isolation is the most likely cause regardless of the surface symptom.

## Golden file protection

Golden files and output snapshots represent the verified correct output. They
are the authoritative record against which production changes are measured.

**Do not edit files in `tests/golden/` or `*.snap` files to make a failing
test pass.** Changing them to match broken behavior destroys the test's value
and can mask regressions indefinitely.

`tests/fixtures/` files are often test inputs, not output snapshots. Editing
an input fixture to correct wrong test data is legitimate; this rule targets
output snapshot files only.

To update golden files when behavior changes intentionally:

1. Confirm the new output is correct by inspection, not by assuming the
   failing test is wrong
2. Regenerate using the project's snapshot update command
   (`pytest --snapshot-update`, `cargo insta update`, or equivalent)
3. Commit the updated golden file with a message explaining why the expected
   output changed, with enough context that a future reviewer can verify the
   change was intentional rather than accidental

## Verification means runtime observation

When verifying that code works, passing tests are not sufficient evidence.
Tests are written by the same agent that wrote the code and may share the
same errors. Verification means: build the artifact, run it, drive it to
the path that exercises the changed code, and observe actual output.

Prohibited as the sole basis for a correctness verdict:

- Running the test suite (CI already does this; it does not replace
  runtime observation)
- Reading the source and reasoning that it looks correct
- Importing the module and calling internal functions from a scratch script
- Relying on type checks or linters to confirm behavior

When verification is blocked (no runtime, no harness, no observable
surface), report BLOCKED with the specific blocker. Do not silently
degrade to code inspection and call it verified.

## Sources

- Claude Code sub-agents: <https://code.claude.com/docs/en/sub-agents>
- Claude Code tools overview: <https://code.claude.com/docs/en/tools>
