---
description: Code quality checks — Ruff format + lint and BasedPyright type checking. Triggers on "quality, lint, format".
tools: ["Read", "Bash", "Grep", "Glob"]
---

# Code Quality Skill

Code quality validation, formatting, linting, and pre-commit checks.

## Invocation

```text
/quality [scope]
```

**Scope** (optional): `all` (default), `format`, `lint`, `types`

## Activation

Auto-activates on keywords: quality, lint, format

## Workflows

### Formatting
- **workflows/format.md**: Code formatting with Ruff

### Linting
- **workflows/lint.md**: Linting checks with Ruff
- **workflows/naming.md**: Naming convention validation

### Pre-commit
- **workflows/precommit.md**: Pre-commit hook validation

## Commands

### Check (non-destructive)

```bash
# Format check only
uv run ruff format --check .

# Lint check
uv run ruff check .

# Type check
uv run basedpyright src/

# All checks via pre-commit
uv run pre-commit run --all-files
```

### Fix Issues

```bash
# Auto-fix formatting
uv run ruff format .

# Auto-fix lint issues
uv run ruff check --fix .
```

## Quality Standards

### Python Standards
- **Line Length**: 88 characters (Ruff format default)
- **Type Checking**: BasedPyright strict mode
- **Linting**: Ruff with PyStrict-aligned rules

### Rule Categories
- **BLE**: Blind except detection
- **EM**: Error message best practices
- **SLF**: Private member access violations
- **INP**: Require `__init__.py` in packages
- **T10**: No debugger statements
- **G**: Logging format strings

### Per-File Ignores
Tests and scripts have relaxed rules for pragmatic development.

## Quality Tool Behavior Notes

**qlty nesting-level and loop constructs (Obs 80):** qlty's nesting-level counter includes `for` and `while` loops in the count, not just `if`/`else` branching. A function with three nested `for` loops puts any statement in the innermost body at nesting level 4, which triggers the "Deeply nested control flow (level=4)" smell regardless of how many conditionals are present.

To resolve a nesting-4 smell on a triple loop, extract the body of the innermost loop to a helper function -- not just the innermost `if`. A minimal `if` at the innermost level is still at level 4 and will still be flagged.

**qlty runs its own ruff independently of pyproject.toml (Obs 103):** qlty has its own tool-runner layer that invokes ruff with its own configuration, independent of project-level config files (`pyproject.toml`, `.ruff.toml`). Exclusions defined in `pyproject.toml` ruff `exclude` do NOT carry over to qlty. When adding service directories or generated-code directories to `pyproject.toml` ruff exclusions, always check whether `.qlty/qlty.toml` also needs a matching `[[exclude]]` entry.
