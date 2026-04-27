---
title: "Testing"
schema_type: common
status: published
owner: core-maintainer
purpose: "Testing guide for Claude Code Configuration."
tags:
  - development
  - testing
---

This guide covers the testing strategy and patterns for Claude Code Configuration.

## Running Tests

### Full Test Suite

```bash
# Run all tests with coverage
uv run pytest -v --cov=src --cov-report=term-missing

# Run with nox across Python versions
nox -s test
```

### Unit Tests Only

```bash
uv run pytest -m unit -v
```

### Integration Tests

```bash
uv run pytest -m integration -v
```

## Test Structure

```text
tests/
├── conftest.py          # Shared fixtures
├── unit/                # Unit tests
│   ├── test_config.py
│   └── test_logging.py
└── integration/         # Integration tests
    └── ...
```

## Coverage Requirements

- **Line coverage**: 80% minimum overall
- **Branch coverage**: 70% minimum
- **Critical modules**: 90% (auth, payment, data pipelines)
- **Patch coverage**: 90% (new code)

## Writing Tests

### Test Markers

```python
import pytest

@pytest.mark.unit
def test_unit_example():
    """Unit test example."""
    pass

@pytest.mark.integration
def test_integration_example():
    """Integration test example."""
    pass

@pytest.mark.slow
def test_slow_example():
    """Slow test - excluded from fast runs."""
    pass
```

## Continuous Integration

Tests run automatically on:
- Pull request creation
- Push to main/develop branches
- Scheduled nightly builds
