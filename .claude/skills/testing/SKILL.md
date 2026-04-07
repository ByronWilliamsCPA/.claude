---
name: testing
description: >
  Automated test generation, review, and execution for pytest-based projects.
  Use when users want to write new tests, run the test suite, set up test
  infrastructure (fixtures, conftest, markers), review test quality, add
  integration/e2e/property-based/mutation testing, or run pytest with specific
  options. Covers test creation, execution, and review workflows — NOT coverage
  gap analysis (use test-coverage), NOT debugging a specific failing test
  (use debug-tests), NOT linting/formatting (use quality).
---

# Testing Skill

Automated test generation, review, and execution for pytest-based projects.

## Invocation

```
/testing [action] [scope]
```

**Actions** (optional): `run` (default), `generate`, `review`, `coverage analyze`,
`coverage generate`, `coverage enforce`, `security`

**Scopes** (optional): `all` (default), `unit`, `integration`, `e2e`

## Workflows

### Test Generation
- **workflows/generate.md**: Generate test cases — naming, parametrize, spec=, AsyncMock, edge cases

### Test Review
- **workflows/review.md**: Review existing tests — 6-item quality checklist with concrete fixes

### Specialized Testing
- **workflows/e2e.md**: End-to-end testing — CLI, API integration, pipeline, data integrity
- **workflows/security.md**: Security testing — OWASP Top 10, injection, path traversal, DoS
- **workflows/performance.md**: Performance testing — benchmarks, memory limits, latency SLAs

## Context Files

- **context/pytest-commands.md**: Common pytest commands and configuration
- **context/pytest-patterns.md**: Patterns reference — naming, parametrize, spec=, AsyncMock, fixtures

## Context Loading Guide

Based on the user's request, proactively note these requirements before generating:

| Request type | Pre-generate checklist |
|-------------|----------------------|
| Async functions | Remind: AsyncMock for coroutines, `@pytest.mark.asyncio`, `.await_count` not `.call_count`; `spec=` must target the actual injected dependency (e.g. `spec=FragranceService` if routes receive a service via `Depends`, not always `spec=AsyncSession`) |
| File I/O | First check whether the module actually performs file I/O; if yes: `tmp_path` fixture, no hardcoded paths; if no file I/O: omit `tmp_path` — do not add it mechanically |
| HTTP clients | Remind: `spec=httpx.AsyncClient`, AsyncMock for `.get`/`.post` methods |
| Pydantic models | Remind: parametrize valid + missing-required + wrong-type scenarios |
| Review request | Reference: 6-item checklist in workflows/review.md by number |

## Commands

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=src/claude_config --cov-report=html --cov-report=term-missing

# Run by scope
uv run pytest tests/unit/ -v --tb=short
uv run pytest tests/integration/ -v --tb=short -m "integration"
uv run pytest tests/e2e/ -v --tb=short -m "e2e"

# Run specific test categories (markers)
uv run pytest -m "not slow"
uv run pytest -m "unit"

# Run with verbose output
uv run pytest -v --tb=short

# Run mutation testing
uv run mutmut run --paths-to-mutate=src/

# Run property-based tests
uv run pytest --hypothesis-show-statistics
```

## Coverage Standards (v2.0)

- **Line Coverage**: 80% minimum
- **Branch Coverage**: 70% minimum
- **Critical Modules**: 90% minimum
- **Patch Coverage**: 90% minimum (new/changed code)
- **Coverage Report**: HTML and terminal output

## Advanced Workflows

For automated coverage gap analysis, test generation, and enforcement,
use the **test-coverage** skill (`/test-coverage`). It orchestrates
the test-writer and test-reviewer subagents with an iterative
generate->run->fix->review loop.

## Test Organization

```
tests/
├── unit/           # Unit tests (fast, isolated)
├── integration/    # Integration tests (may use external services)
├── e2e/           # End-to-end tests (full system)
├── security/      # Security-focused tests
├── performance/   # Performance and load tests
└── conftest.py    # Shared fixtures
```

## Testing Patterns

### AAA Pattern (Arrange-Act-Assert)
```python
def test_example():
    # Arrange
    input_data = create_test_data()

    # Act
    result = function_under_test(input_data)

    # Assert
    assert result == expected_output
```

### Fixtures
```python
@pytest.fixture
def sample_data():
    return {"key": "value"}

def test_with_fixture(sample_data):
    assert sample_data["key"] == "value"
```
