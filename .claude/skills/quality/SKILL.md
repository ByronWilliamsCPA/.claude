# Code Quality Skill

Code quality validation, formatting, linting, and pre-commit checks.

## Invocation

```
/quality [scope]
```

**Scope** (optional): `all` (default), `format`, `lint`, `types`

## Activation

Auto-activates on keywords: quality, lint, format, precommit, naming, black, ruff, mypy, basedpyright, validation

## Workflows

### Formatting
- **format.md**: Code formatting with Black and Ruff

### Linting
- **lint.md**: Linting checks with Ruff
- **naming.md**: Naming convention validation

### Pre-commit
- **precommit.md**: Pre-commit hook validation

## Commands

### Check (non-destructive)

```bash
# Format check only
uv run black --check .
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
uv run black .
uv run ruff format .

# Auto-fix lint issues
uv run ruff check --fix .
```

## Quality Standards

### Python Standards
- **Line Length**: 88 characters (Black default)
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
