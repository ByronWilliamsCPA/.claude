# Testing Command

Run tests with coverage reporting and optional test generation.

## Usage

```
/testing [action] [scope]
```

**Arguments:**
- `action` (optional): `run`, `generate`, `review`, `coverage`, `coverage analyze`, `coverage generate`, `coverage enforce`, `security` (default: `run`)
- `scope` (optional): `all`, `unit`, `integration`, `e2e` (default: `all`)

## Workflow

### Run Tests
1. Execute pytest with specified scope
2. Generate coverage report
3. Report results and coverage percentage

### Generate Tests
1. Analyze target code
2. Generate test cases for untested functions
3. Create test file with fixtures

### Review Tests
1. Analyze existing test quality
2. Identify coverage gaps
3. Suggest improvements

## Commands Executed

### Run All Tests
```bash
uv run pytest -v --tb=short
```

### Run with Coverage
```bash
uv run pytest --cov=src/claude_config --cov-report=html --cov-report=term-missing
```

### Run Unit Tests Only
```bash
uv run pytest tests/unit/ -v --tb=short
```

### Run Integration Tests
```bash
uv run pytest tests/integration/ -v --tb=short -m "integration"
```

### Run E2E Tests
```bash
uv run pytest tests/e2e/ -v --tb=short -m "e2e"
```

### Mutation Testing
```bash
uv run mutmut run --paths-to-mutate=src/
```

## Coverage Standards (v2.0)

- **Line Coverage**: 80% minimum
- **Branch Coverage**: 70% minimum
- **Critical Modules**: 90% minimum
- **Patch Coverage**: 90% minimum (new/changed code)

## Advanced Workflows

For automated coverage gap analysis and test generation, use the `test-coverage` skill:

- `/test-coverage analyze` — Parse coverage and identify gaps ranked by criticality
- `/test-coverage generate` — AI-powered test generation with iterative validation
- `/test-coverage enforce` — Block merges when coverage drops below thresholds
- `/test-coverage security` — OWASP specialist security test audit

## Test Organization

```
tests/
├── unit/           # Fast, isolated tests
├── integration/    # Service integration tests
├── e2e/           # End-to-end scenarios
├── conftest.py    # Shared fixtures
└── __init__.py
```
