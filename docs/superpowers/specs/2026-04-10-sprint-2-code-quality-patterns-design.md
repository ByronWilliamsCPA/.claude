---
schema_type: common
title: "Sprint 2: Code Quality Patterns"
status: draft
owner: core-maintainer
purpose: "Design spec for adding exception hierarchy guidance, golden test protection, and docstring coverage gate documentation to the global Claude implementation."
tags:
  - documentation
  - security
  - compliance
  - tooling
---

## Overview

This sprint adds three code quality patterns to the global Claude implementation,
closing gaps identified in the 2026-04-09 cross-project CLAUDE.md audit. All three
items appeared in 3+ project CLAUDE.md files but were absent from the global standard.

**Approach**: Documentation-only. All tooling (interrogate, darglint) is already wired
in `.pre-commit-config.yaml` and `pyproject.toml`. No hook changes needed.

---

## Item 1: Exception Hierarchy

**Problem**: Three or more projects document a `BaseError` typed subclass pattern, but
`rules/python.md` has no guidance on exception design. Developers default to raising
bare `Exception`, which defeats type-checked error handling and produces inconsistent
API error responses.

**Solution**: Add a `### Exception Hierarchy` subsection under
`## Code Generation: Python-Specific` in `rules/python.md`, after the Naming Standards
block and before the Documentation bullet. Approach C: guidelines plus a minimal
skeleton showing `AppError → typed subclass → to_dict()` without prescribing a full
implementation.

**Section content to add:**

```markdown
### Exception Hierarchy

Never raise bare `Exception` or `BaseException`. Define a typed exception hierarchy
rooted at a project-level base class:

    class AppError(Exception):
        def __init__(self, message: str, code: str) -> None:
            super().__init__(message)
            self.code = code

        def to_dict(self) -> dict[str, str]:
            return {"error": str(self), "code": self.code}

    class ValidationError(AppError): ...
    class NotFoundError(AppError): ...

- `to_dict()` enables consistent API error serialization without leaking tracebacks
- One base class per project; typed subclasses per error category
- The `BLE` and `TRY` Ruff rules enforce this at lint time
```

---

## Item 2: Golden Test Protection

**Problem**: Projects using snapshot/golden file testing have no global guidance against
editing golden files manually to pass failing tests. This destroys the test's value by
redefining correctness to match broken behavior.

**Solution**: Add a `## Golden File Protection` section to the `## Testing` section in
`CLAUDE.md`, after the root-cause investigation block.

**Section content to add:**

```markdown
## Golden File Protection

When tests use golden files (reference snapshots in `tests/golden/`, `tests/fixtures/`,
or `*.snap` files), never edit those files manually to make a failing test pass. Golden
files represent the verified correct output — changing them to match broken behavior
destroys the test's value.

To update golden files legitimately (behavior changed intentionally):

1. Confirm the new output is correct by inspection
2. Regenerate using the project's snapshot update command
   (e.g., `pytest --snapshot-update`, `cargo test -- --nocapture`)
3. Commit the updated golden file with a message explaining why the expected output changed
```

---

## Item 3: Docstring Coverage Gate

**Problem**: `interrogate` (85% coverage threshold) and `darglint` (argument validation,
`long` strictness) are both wired in `.pre-commit-config.yaml` and configured in
`pyproject.toml`, but neither appears in `rules/python.md` or `rules/pre-commit.md`.
Developers encounter hook failures with no documentation explaining what triggered them
or how to resolve them without suppression.

**Context**:

- `interrogate` runs at `pre-commit` stage; checks `scripts/` directory; threshold 85%
- `darglint` runs at `pre-commit` stage; excluded from `tests/`, `scripts/`,
  `benchmarks/`, `tools/`; `darglint` is in the CI skip list; `interrogate` is not
- Both require fixes, not suppressions

**Solution: `rules/python.md`**: Replace the existing two-line Documentation bullet
under `## Code Generation: Python-Specific` with the expanded block below. The bullet
is promoted to a `### Documentation` subsection heading to match the Exception Hierarchy
subsection style added in Item 1.

**Replacement content:**

```markdown
### Documentation

- **Docstrings**: Required on all public functions — purpose, args, returns, raises
  (Google style)
- **Type Hints**: Required on all function signatures (BasedPyright strict enforces this)

**Docstring coverage gate**: `interrogate` runs at pre-commit and requires 85% docstring
coverage in `scripts/`. Functions missing docstrings block the commit.

**Docstring argument validation**: `darglint` runs at pre-commit and validates that
documented `Args`, `Returns`, and `Raises` sections match the actual function signature.
Strictness: `long` — all parameters must be documented. Excluded: `tests/`, `scripts/`,
`benchmarks/`, `tools/`.

When darglint flags a mismatch, fix the docstring — do not add a `# noqa` suppression.
```

**Solution — `rules/pre-commit.md`**: Add two checklist items to the Code Quality
section, after the existing linter line.

**Checklist items to add:**

```markdown
- [ ] **Docstring Coverage**: `interrogate` passes at 85% threshold for `scripts/` — add missing docstrings rather than suppressing
- [ ] **Docstring Arguments**: `darglint` passes — documented `Args`/`Returns`/`Raises` match signatures
```

---

## Files Modified

| File | Change Type | Description |
| --- | --- | --- |
| `.claude/rules/python.md` | Documentation | Add exception hierarchy subsection; expand Documentation bullet with docstring gate details |
| `CLAUDE.md` | Documentation | Add golden file protection section to Testing section |
| `.claude/rules/pre-commit.md` | Documentation | Add two docstring gate checklist items |

---

## Verification

1. **Exception section visible**: Open a `.py` file — `rules/python.md` is context-injected, making the exception hierarchy pattern visible to Claude
2. **Golden file section present**: `grep "Golden File Protection" CLAUDE.md` returns one match
3. **Docstring gate documented**: `grep -n "interrogate\|darglint" .claude/rules/python.md` shows the new content
4. **Pre-commit checklist updated**: `grep "Docstring" .claude/rules/pre-commit.md` returns two matches
5. **Section order preserved**: Exception Hierarchy appears after Naming Standards; Documentation block expands in place
6. **All pre-commit hooks pass**: `pre-commit run --all-files`

---

## Out of Scope

- Adding interrogate or darglint to CI (separate from pre-commit; out of sprint scope)
- Removing darglint from the CI skip list (separate decision)
- Prescribing a full `BaseError` implementation (project-specific; guidelines + skeleton only)
- Covering non-file golden values (broader test quality topic; deferred)
