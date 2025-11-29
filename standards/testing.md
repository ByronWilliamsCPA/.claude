# Testing Standards

## Core Testing Philosophy

> **Guiding Principles for All Tests**

1. **Test behavior, not implementation**: Tests should verify what code does, not how it does it
2. **Fast feedback loop**: Unit tests should complete in <30 seconds total
3. **Clear test names**: Test names describe what is being tested (action + condition + expected result)
4. **Isolated tests**: No dependencies between tests; each test runs independently
5. **Automated execution**: All tests run in CI/CD without manual intervention

## Coverage Requirements

### Minimum Thresholds

| Metric | Minimum | Target |
|--------|---------|--------|
| **Line Coverage** | 80% | 90%+ |
| **Branch Coverage** | 80% | 85%+ |
| **Docstring Coverage** | 85% | 95%+ |

### Coverage Configuration

```toml
# pyproject.toml
[tool.coverage.run]
source = ["src"]
branch = true
relative_files = true

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "if TYPE_CHECKING:",
    "if __name__ == .__main__.:",
    "@abstractmethod",
    "raise NotImplementedError",
    "class.*Protocol.*:",
]
precision = 2
fail_under = 80
show_missing = true
```

## Test Organization

### Directory Structure

```
tests/
├── unit/              # Fast, isolated tests (no external deps)
│   ├── test_models.py
│   ├── test_utils.py
│   └── test_services.py
├── integration/       # Multi-component tests (may use DB/APIs)
│   ├── test_api_endpoints.py
│   └── test_database.py
├── e2e/              # Full system tests (complete workflows)
│   └── test_user_journeys.py
├── security/         # Security validation tests
│   └── test_codeql_validation.py
├── benchmark/        # Performance and benchmarking tests
│   └── test_performance.py
├── api/              # API-specific tests
│   └── test_endpoints.py
├── fixtures/         # Shared test data and factories
│   ├── __init__.py
│   ├── factories.py
│   ├── sample_data.py
│   └── expected/     # Expected outputs for comparison
└── conftest.py       # Shared fixtures and configuration
```

### Test Tiering Strategy

| Tier | Type | Speed | Dependencies | When to Run |
|------|------|-------|--------------|-------------|
| 1 | Unit | <100ms | None | Every save, pre-commit |
| 2 | Integration | <5s | Database, cache | Pre-push, CI |
| 3 | E2E | <30s | Full system | CI, pre-release |
| 4 | Performance | Variable | Full system | Nightly, release |

## Test Patterns

### AAA Pattern (Arrange-Act-Assert)

Every test MUST follow the AAA pattern for clarity:

```python
def test_should_calculate_total_with_discount():
    """Calculate total correctly when discount is applied."""
    # Arrange - Set up test data and dependencies
    cart = ShoppingCart()
    cart.add_item(Product("Widget", price=100.00))
    discount = PercentageDiscount(10)

    # Act - Execute the code under test
    total = cart.calculate_total(discount=discount)

    # Assert - Verify the expected outcome
    assert total == 90.00
```

### Fixture Strategies

#### Basic Fixtures

```python
import pytest

@pytest.fixture
def sample_user() -> User:
    """Provide a standard test user."""
    return User(
        id=1,
        name="Test User",
        email="test@example.com",
        role=Role.MEMBER,
    )

@pytest.fixture
def authenticated_client(sample_user: User) -> TestClient:
    """Provide an authenticated test client."""
    client = TestClient(app)
    client.headers["Authorization"] = f"Bearer {sample_user.token}"
    return client
```

#### Factory Fixtures

```python
from typing import Any

@pytest.fixture
def user_factory() -> Callable[..., User]:
    """Factory for creating users with custom attributes."""
    def _create_user(**overrides: Any) -> User:
        defaults = {
            "id": 1,
            "name": "Test User",
            "email": "test@example.com",
            "role": Role.MEMBER,
        }
        return User(**{**defaults, **overrides})
    return _create_user

# Usage in test
def test_admin_can_delete_users(user_factory):
    admin = user_factory(role=Role.ADMIN)
    target = user_factory(id=2, name="Target User")
    # ...
```

#### Async Fixtures

```python
import pytest
from contextlib import asynccontextmanager

@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide a database session with automatic rollback."""
    async with async_session_maker() as session:
        async with session.begin():
            yield session
            await session.rollback()

@pytest.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """Provide an async HTTP client."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client
```

### Mocking Strategies

#### External Service Mocking

```python
from unittest.mock import AsyncMock, patch

@pytest.fixture
def mock_payment_service():
    """Mock payment service for testing."""
    with patch("app.services.payment.PaymentGateway") as mock:
        mock.return_value.charge = AsyncMock(
            return_value=PaymentResult(success=True, transaction_id="txn_123")
        )
        yield mock

def test_checkout_processes_payment(mock_payment_service):
    # Payment service is mocked, won't hit real API
    result = checkout_service.process(order)
    assert result.payment_status == "completed"
```

#### Database Mocking

```python
from unittest.mock import MagicMock

@pytest.fixture
def mock_db_session():
    """Mock database session for unit tests."""
    session = MagicMock()
    session.query.return_value.filter.return_value.first.return_value = User(
        id=1, name="Mocked User"
    )
    return session
```

### Parametrized Testing

```python
import pytest

@pytest.mark.parametrize(
    "input_value,expected",
    [
        ("hello", "HELLO"),
        ("World", "WORLD"),
        ("", ""),
        ("123", "123"),
        ("MixedCase", "MIXEDCASE"),
    ],
    ids=["lowercase", "capitalized", "empty", "numbers", "mixed"],
)
def test_uppercase_conversion(input_value: str, expected: str):
    """Verify uppercase conversion handles various inputs."""
    assert input_value.upper() == expected
```

### Property-Based Testing

```python
from hypothesis import given, strategies as st

@given(st.text())
def test_encode_decode_roundtrip(text: str):
    """Encoding then decoding should return original text."""
    encoded = encode(text)
    decoded = decode(encoded)
    assert decoded == text

@given(st.lists(st.integers()))
def test_sort_is_idempotent(items: list[int]):
    """Sorting twice should produce same result as sorting once."""
    once = sorted(items)
    twice = sorted(sorted(items))
    assert once == twice

@given(st.integers(min_value=0, max_value=100))
def test_percentage_in_valid_range(value: int):
    """Percentage calculations should stay within 0-100."""
    result = calculate_percentage(value, 100)
    assert 0 <= result <= 100
```

## Test Markers

### Standard Markers

```python
import pytest

@pytest.mark.unit
def test_pure_function():
    """Fast, isolated unit test."""
    pass

@pytest.mark.integration
def test_database_query():
    """Test requiring database connection."""
    pass

@pytest.mark.slow
def test_large_dataset_processing():
    """Test that takes significant time."""
    pass

@pytest.mark.benchmark
def test_performance_baseline():
    """Performance benchmarking test."""
    pass
```

### Marker Configuration

```toml
# pyproject.toml
[tool.pytest.ini_options]
markers = [
    "unit: Fast isolated tests with no dependencies",
    "integration: Tests requiring external services",
    "slow: Tests taking more than 5 seconds",
    "benchmark: Performance benchmarking tests",
    "e2e: End-to-end workflow tests",
    "security: Security validation tests",
    "requires_full_dataset: Tests needing large datasets (skip in CI)",
    "real_data: Tests using real fixtures rather than synthetic data",
]
```

## Naming Conventions

### Test Functions

```python
# Pattern: test_<action>_<condition>_<expected_result>

# Good examples
def test_create_user_with_valid_data_returns_user():
    pass

def test_login_with_invalid_password_raises_auth_error():
    pass

def test_calculate_total_with_empty_cart_returns_zero():
    pass

# Bad examples (avoid)
def test_user():  # Too vague
    pass

def test_1():  # No description
    pass

def testCreateUser():  # Wrong naming style
    pass
```

### Test Classes

```python
class TestUserAuthentication:
    """Tests for user authentication workflows."""

    def test_login_with_valid_credentials_succeeds(self):
        pass

    def test_login_with_invalid_password_fails(self):
        pass

    def test_logout_invalidates_session(self):
        pass


class TestShoppingCart:
    """Tests for shopping cart functionality."""

    class TestAddItem:
        """Tests for adding items to cart."""

        def test_add_single_item_increases_count(self):
            pass

        def test_add_duplicate_item_increases_quantity(self):
            pass
```

## Essential Commands

```bash
# Run all tests with coverage
uv run pytest -v --cov=src --cov-report=html --cov-report=term-missing

# Run only unit tests (fast)
uv run pytest tests/unit/ -v

# Run integration tests
uv run pytest -m integration -v

# Run tests excluding slow tests
uv run pytest -m "not slow" -v

# Run specific test file
uv run pytest tests/unit/test_models.py -v

# Run tests matching pattern
uv run pytest -k "test_user" -v

# Run with parallel execution
uv run pytest -n auto -v

# Run with verbose failure output
uv run pytest --tb=long -v

# Generate coverage report
uv run pytest --cov=src --cov-report=html
open htmlcov/index.html

# Run mutation testing
uv run mutmut run --paths-to-mutate=src/

# Check docstring coverage
uv run interrogate src/ -v
```

## Pytest Configuration

```toml
# pyproject.toml
[tool.pytest.ini_options]
minversion = "7.0"
testpaths = ["tests"]
pythonpath = [".", "src"]
python_files = ["test_*.py", "*_test.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]

# Strict configuration
addopts = [
    "-ra",                    # Show extra summary
    "--strict-markers",       # Error on unknown markers
    "--strict-config",        # Error on config issues
    "-v",                     # Verbose output
    "--tb=short",            # Short tracebacks
    "--cov=src",             # Coverage source
    "--cov-report=term-missing",
    "--cov-fail-under=80",   # Minimum coverage
]

# Filter warnings
filterwarnings = [
    "error",                  # Treat warnings as errors
    "ignore::DeprecationWarning:hypothesis.*:",
]
```

## Async Testing

```python
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_async_endpoint(async_client: AsyncClient):
    """Test async API endpoint."""
    response = await async_client.get("/api/users")
    assert response.status_code == 200
    assert len(response.json()) > 0

@pytest.mark.asyncio
async def test_concurrent_operations():
    """Test operations running concurrently."""
    async with asyncio.TaskGroup() as tg:
        task1 = tg.create_task(fetch_user(1))
        task2 = tg.create_task(fetch_user(2))

    assert task1.result().id == 1
    assert task2.result().id == 2
```

## Testing Best Practices

### Do's

- **Isolate tests**: Each test should be independent and not rely on others
- **Use descriptive names**: Test names should explain what is being tested
- **Test edge cases**: Include boundary conditions and error scenarios
- **Mock external dependencies**: Never hit real APIs/databases in unit tests
- **Keep tests fast**: Unit tests should run in milliseconds
- **Use fixtures**: Share setup code through pytest fixtures
- **Assert one thing**: Each test should verify one specific behavior

### Don'ts

- **Don't test implementation details**: Test behavior, not internal structure
- **Don't use sleep()**: Use proper async patterns or mocking
- **Don't share state between tests**: Each test should start fresh
- **Don't ignore flaky tests**: Fix or quarantine them immediately
- **Don't test external libraries**: Assume dependencies work correctly
- **Don't write tests without assertions**: Every test needs verification

### Code Under Test Principles

```python
# Design for testability

# ❌ Hard to test - hidden dependency
class UserService:
    def __init__(self):
        self.db = DatabaseConnection()  # Hidden dependency

# ✅ Easy to test - explicit dependency
class UserService:
    def __init__(self, db: DatabaseConnection):
        self.db = db  # Injected, can be mocked

# ❌ Hard to test - global state
_cache = {}
def get_user(id: int) -> User:
    if id in _cache:
        return _cache[id]
    # ...

# ✅ Easy to test - explicit cache
def get_user(id: int, cache: dict | None = None) -> User:
    cache = cache or {}
    if id in cache:
        return cache[id]
    # ...
```

## CI/CD Integration

```yaml
# .github/workflows/test.yml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.11", "3.12", "3.13"]

    steps:
      - uses: actions/checkout@v4

      - name: Install uv
        uses: astral-sh/setup-uv@v4

      - name: Set up Python ${{ matrix.python-version }}
        run: uv python install ${{ matrix.python-version }}

      - name: Install dependencies
        run: uv sync --all-extras

      - name: Run unit tests
        run: uv run pytest tests/unit/ -v --cov=src

      - name: Run integration tests
        run: uv run pytest tests/integration/ -v

      - name: Upload coverage
        uses: codecov/codecov-action@v4
        with:
          file: ./coverage.xml
          fail_ci_if_error: true
```

## Security Testing

Security tests validate that security tooling (CodeQL, Semgrep, Bandit) correctly identifies vulnerabilities.

### Security Test Structure

```python
# tests/security/test_codeql_validation.py
"""
Intentional security vulnerabilities for CodeQL validation.

This file contains DELIBERATE security issues to verify CodeQL detection.
DO NOT use these patterns in production code.
"""
import pytest

class TestCodeQLValidation:
    """Verify CodeQL detects common vulnerability patterns."""

    @pytest.mark.security
    def test_sql_injection_detection(self, tmp_path):
        """CodeQL should detect SQL injection (CWE-89)."""
        # Intentional vulnerable pattern for validation
        user_input = "'; DROP TABLE users; --"
        query = f"SELECT * FROM users WHERE name = '{user_input}'"  # noqa: S608
        # CodeQL should flag this as sql-injection

    @pytest.mark.security
    def test_command_injection_detection(self):
        """CodeQL should detect command injection (CWE-78)."""
        import subprocess
        user_path = "/etc/passwd"
        # Intentional vulnerable pattern
        subprocess.run(f"cat {user_path}", shell=True)  # noqa: S602, S605

    @pytest.mark.security
    def test_path_traversal_detection(self, tmp_path):
        """CodeQL should detect path traversal (CWE-22)."""
        user_file = "../../../etc/passwd"
        # Intentional vulnerable pattern
        full_path = tmp_path / user_file  # noqa: S108
```

### CWE Mapping Reference

| CWE | Vulnerability | Test Method |
|-----|--------------|-------------|
| CWE-78 | Command Injection | `test_command_injection_detection` |
| CWE-89 | SQL Injection | `test_sql_injection_detection` |
| CWE-22 | Path Traversal | `test_path_traversal_detection` |
| CWE-327 | Weak Cryptography | `test_weak_crypto_detection` |
| CWE-502 | Insecure Deserialization | `test_pickle_detection` |
| CWE-95 | Unsafe Eval | `test_eval_detection` |

## Performance Testing

Performance tests validate execution speed and throughput meet requirements.

### Environment-Aware Thresholds

```python
# tests/benchmark/test_performance.py
import os
import time
import pytest

def is_ci_environment() -> bool:
    """Detect CI/container environments for relaxed thresholds."""
    ci_indicators = [
        os.getenv("CI") in ("true", "1", "yes"),
        os.getenv("GITHUB_ACTIONS") == "true",
        os.path.exists("/.dockerenv"),
        os.getenv("RELAXED_PERF_TESTS") == "true",
    ]
    return any(ci_indicators)

# Thresholds: (CI/relaxed, local/strict)
PERF_THRESHOLDS = {
    "operation_a": (500, 150),   # ms
    "operation_b": (3000, 1000), # ms
    "throughput": (0.3, 1.0),    # ops/sec
}

@pytest.fixture
def performance_target():
    """Return appropriate threshold based on environment."""
    is_ci = is_ci_environment()
    def get_target(operation: str) -> float:
        ci_target, local_target = PERF_THRESHOLDS[operation]
        return ci_target if is_ci else local_target
    return get_target
```

### Timing Methodology

```python
@pytest.mark.benchmark
def test_operation_performance(performance_target, sample_data):
    """Verify operation completes within threshold."""
    # Warm-up run (not measured)
    _ = process_data(sample_data)

    # Measured runs
    iterations = 5
    times = []
    for _ in range(iterations):
        start = time.perf_counter()
        process_data(sample_data)
        elapsed = (time.perf_counter() - start) * 1000  # ms
        times.append(elapsed)

    # Assertions
    avg_time = sum(times) / len(times)
    p95_time = sorted(times)[int(len(times) * 0.95)]

    threshold = performance_target("operation_a")
    assert avg_time < threshold, f"Avg {avg_time:.1f}ms exceeds {threshold}ms"
    assert p95_time < threshold * 1.5, f"P95 {p95_time:.1f}ms exceeds limit"
```

### Performance Fixture Patterns

```python
@pytest.fixture(scope="session")
def realistic_document_image():
    """Create realistic test document (300 DPI letter size)."""
    import numpy as np
    # 2550x3300 = 300 DPI letter size
    img = np.zeros((3300, 2550, 3), dtype=np.uint8)
    img.fill(255)  # White background
    # Add simulated text content
    # ...
    return img

@pytest.fixture(scope="session")
def batch_test_data(realistic_document_image):
    """Generate batch of 10 documents for throughput testing."""
    return [realistic_document_image.copy() for _ in range(10)]
```

## Test Data Management

### Storage Strategy

| File Size | Storage Method | Example |
|-----------|----------------|---------|
| <1 MB | Commit to repo | `tests/fixtures/sample.json` |
| 1-100 MB | Git LFS | `tests/fixtures/large_dataset.parquet` |
| >100 MB | External download | Document in `tests/fixtures/README.md` |

### Fixture Organization

```
tests/fixtures/
├── README.md           # Document data sources and generation
├── small/              # Committed files (<1MB)
│   ├── sample_input.json
│   └── config.yaml
├── expected/           # Expected outputs for comparison
│   ├── processed_output.json
│   └── report.html
├── generated/          # .gitignored, created by scripts
│   └── .gitkeep
└── scripts/            # Data generation scripts
    └── generate_test_data.py
```

### Data Generation Documentation

```python
# tests/fixtures/scripts/generate_test_data.py
"""
Test Data Generation Script

Usage:
    uv run python tests/fixtures/scripts/generate_test_data.py

Generates:
    - tests/fixtures/generated/large_dataset.parquet (50MB)
    - tests/fixtures/generated/sample_images/ (100 images)

Requirements:
    - pandas, pillow (included in dev dependencies)
"""
```

## Optional Dependency Handling

Handle optional dependencies gracefully to allow partial test execution.

### conftest.py Pattern

```python
# tests/conftest.py
import sys
from pathlib import Path

import pytest

# Check optional dependencies
try:
    import cv2
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False

try:
    import torch
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False

# Modules requiring specific dependencies
CV2_MODULES = {"test_image_processing", "test_detection"}
TORCH_MODULES = {"test_ml_models", "test_inference"}

def pytest_collection_modifyitems(config, items):
    """Skip tests when optional dependencies are missing."""
    skip_cv2 = pytest.mark.skip(reason="OpenCV (cv2) not installed")
    skip_torch = pytest.mark.skip(reason="PyTorch not installed")

    for item in items:
        module_name = Path(item.fspath).stem
        if not HAS_CV2 and module_name in CV2_MODULES:
            item.add_marker(skip_cv2)
        if not HAS_TORCH and module_name in TORCH_MODULES:
            item.add_marker(skip_torch)
```

### Session-Scoped Dataset Fixtures

```python
@pytest.fixture(scope="session")
def dataset_path() -> Path | None:
    """Provide dataset path if available, skip otherwise."""
    path = Path("tests/fixtures/large_dataset")
    if not path.exists():
        pytest.skip("Large dataset not available")
    return path

@pytest.fixture(scope="session")
def sample_files(dataset_path: Path) -> list[Path]:
    """Collect sample files with fallback skip logic."""
    files = list(dataset_path.glob("*.json"))
    if not files:
        pytest.skip("No sample files found in dataset")
    return files
```

## Troubleshooting

### Local vs CI Failures

| Symptom | Likely Cause | Solution |
|---------|--------------|----------|
| Tests pass locally, fail in CI | Environment differences | Check Python version, dependencies |
| Timing assertions fail in CI | CI resource constraints | Use environment-aware thresholds |
| Fixture not found | Path differences | Use `Path(__file__).parent` for relative paths |
| Random test failures | Test isolation issues | Check for shared state, add `--randomly-seed` |

### Coverage Gap Analysis

```bash
# Generate detailed HTML report
uv run pytest --cov=src --cov-report=html

# Open and analyze
open htmlcov/index.html

# Look for:
# - Red lines (uncovered code)
# - Yellow lines (partial branch coverage)
# - Missing edge case tests
```

### Slow Test Profiling

```bash
# Find slowest tests
uv run pytest --durations=20

# Profile specific test
uv run pytest tests/slow_test.py --profile

# Run only fast tests during development
uv run pytest -m "not slow and not benchmark"
```

### Debugging Flaky Tests

```python
# Add retry for known flaky tests (use sparingly)
@pytest.mark.flaky(reruns=3, reruns_delay=1)
def test_network_dependent_operation():
    """Test that occasionally fails due to network."""
    pass

# Better: Fix the root cause
@pytest.fixture
def stable_mock_network():
    """Mock network calls for deterministic tests."""
    with responses.RequestsMock() as rsps:
        rsps.add(responses.GET, "https://api.example.com", json={"status": "ok"})
        yield rsps
```

## Mutation Testing

Mutation testing validates test quality by introducing small code changes (mutations) and verifying tests catch them.

### Configuration

```toml
# pyproject.toml
[tool.mutmut]
paths_to_mutate = "src/"
tests_dir = "tests/"
backup = false
runner = "uv run pytest -x --assert=plain -o addopts=''"
dict_synonyms = "Struct, NamedStruct"
```

### Mutation Status Reference

| Status | Meaning | Action Required |
|--------|---------|-----------------|
| **killed** | Test detected the mutation | Test is effective |
| **survived** | Test missed the mutation | Enhance test coverage |
| **timeout** | Mutation caused infinite loop | Usually acceptable |
| **suspicious** | Unexpected test behavior | Investigate |
| **skipped** | Mutation excluded by config | Usually acceptable |

### Score Calculation

```
Mutation Score = (killed / total) × 100
```

| Score | Quality | Action |
|-------|---------|--------|
| >80% | Excellent | Maintain |
| 60-80% | Good | Improve critical paths |
| <60% | Needs work | Prioritize test enhancement |

### Module-Specific Targets

| Module Type | Target Score | Priority |
|-------------|--------------|----------|
| Core/schema | >85% | High |
| Business logic | >80% | High |
| Ingestion/IO | >75% | Medium |
| Utilities | >70% | Low |
| Logging/formatting | >60% | Low |

### Commands

```bash
# Full mutation run
uv run mutmut run

# Specific module (faster)
uv run mutmut run --paths-to-mutate=src/core/

# View results
uv run mutmut results

# Inspect specific mutant
uv run mutmut show 42

# Generate HTML report
uv run mutmut html

# Show statistics
uv run mutmut show-stats
```

### Script-Based Execution

```bash
# scripts/run_mutation_tests.sh
#!/bin/bash
set -e

case "${1:-}" in
    --fast)
        # Critical modules only
        uv run mutmut run --paths-to-mutate=src/core/,src/schema.py
        ;;
    --module=*)
        module="${1#--module=}"
        uv run mutmut run --paths-to-mutate="src/${module}/"
        ;;
    --report)
        uv run mutmut html
        open html/index.html
        ;;
    *)
        uv run mutmut run
        ;;
esac
```

### Prioritization Strategy

**Focus mutation testing on:**
1. Core business logic and validation
2. Security-sensitive code paths
3. Financial/payment processing
4. Data transformation functions

**Lower priority (acceptable survivors):**
- Logging statements
- Error message formatting
- UI/display code
- Debug utilities

### Documenting Justified Survivors

```python
# .mutmut-allowlist
# Format: mutant_id: reason

# 42: Log message formatting - no business impact
# 58: Debug-only code path - not in production
# 73: Equivalent mutation - same behavior
```

## Test Compliance Verification

Ensure testing standards are consistently applied across repositories.

### Directory Structure Validation

```python
# scripts/verify_test_structure.py
"""Verify test directory structure matches standards."""
from pathlib import Path
import sys

REQUIRED_DIRS = ["unit", "integration", "fixtures"]
RECOMMENDED_DIRS = ["e2e", "security", "benchmark", "api"]

def verify_structure(tests_path: Path) -> tuple[list[str], list[str]]:
    """Check for required and recommended test directories."""
    missing_required = []
    missing_recommended = []

    for dir_name in REQUIRED_DIRS:
        if not (tests_path / dir_name).is_dir():
            missing_required.append(dir_name)

    for dir_name in RECOMMENDED_DIRS:
        if not (tests_path / dir_name).is_dir():
            missing_recommended.append(dir_name)

    return missing_required, missing_recommended

if __name__ == "__main__":
    tests_path = Path("tests")
    missing_req, missing_rec = verify_structure(tests_path)

    if missing_req:
        print(f"ERROR: Missing required directories: {missing_req}")
        sys.exit(1)
    if missing_rec:
        print(f"WARNING: Missing recommended directories: {missing_rec}")

    print("✓ Test structure verification passed")
```

### Test Marker Coverage

```python
# conftest.py - Add to existing conftest
import pytest
from collections import Counter

# Track marker usage
_marker_counts: Counter[str] = Counter()
_unmarked_tests: list[str] = []

REQUIRED_MARKERS = {"unit", "integration", "e2e", "benchmark", "security"}

def pytest_collection_finish(session):
    """Analyze test marker distribution after collection."""
    for item in session.items:
        markers = {m.name for m in item.iter_markers()}
        relevant = markers & REQUIRED_MARKERS

        if relevant:
            for marker in relevant:
                _marker_counts[marker] += 1
        else:
            _unmarked_tests.append(item.nodeid)

def pytest_terminal_summary(terminalreporter, exitstatus, config):
    """Report marker coverage in test summary."""
    if not _marker_counts and not _unmarked_tests:
        return

    terminalreporter.write_sep("=", "Test Marker Coverage")

    total = sum(_marker_counts.values()) + len(_unmarked_tests)
    for marker, count in sorted(_marker_counts.items()):
        pct = (count / total) * 100
        terminalreporter.write_line(f"  {marker}: {count} ({pct:.1f}%)")

    if _unmarked_tests:
        terminalreporter.write_line(
            f"  UNMARKED: {len(_unmarked_tests)} ({len(_unmarked_tests)/total*100:.1f}%)"
        )
        if len(_unmarked_tests) <= 10:
            for test in _unmarked_tests:
                terminalreporter.write_line(f"    - {test}")
```

### Test Ratio Enforcement

```python
# scripts/check_test_ratios.py
"""Enforce healthy test pyramid ratios."""
import subprocess
import json
import sys

# Target ratios (unit:integration:e2e)
TARGET_RATIOS = {
    "unit": 0.70,        # 70% unit tests
    "integration": 0.20,  # 20% integration tests
    "e2e": 0.10,         # 10% e2e tests
}

TOLERANCE = 0.10  # Allow 10% deviation

def get_test_counts() -> dict[str, int]:
    """Count tests by marker."""
    result = subprocess.run(
        ["uv", "run", "pytest", "--collect-only", "-q", "--no-header"],
        capture_output=True, text=True
    )

    counts = {"unit": 0, "integration": 0, "e2e": 0, "other": 0}

    # Run pytest with marker filter to count each type
    for marker in ["unit", "integration", "e2e"]:
        result = subprocess.run(
            ["uv", "run", "pytest", "--collect-only", "-q", "-m", marker],
            capture_output=True, text=True
        )
        # Count lines that look like test items
        counts[marker] = len([
            l for l in result.stdout.split("\n")
            if "::" in l and "test_" in l
        ])

    return counts

def check_ratios(counts: dict[str, int]) -> list[str]:
    """Check if test ratios are within tolerance."""
    total = sum(counts.values())
    if total == 0:
        return ["ERROR: No tests found"]

    violations = []
    for marker, target in TARGET_RATIOS.items():
        actual = counts.get(marker, 0) / total
        if actual < target - TOLERANCE:
            violations.append(
                f"{marker}: {actual:.1%} (target: {target:.0%}, need {int((target - actual) * total)} more)"
            )

    return violations

if __name__ == "__main__":
    counts = get_test_counts()
    print(f"Test counts: {counts}")

    violations = check_ratios(counts)
    if violations:
        print("\nTest ratio violations:")
        for v in violations:
            print(f"  ⚠ {v}")
        sys.exit(1)

    print("✓ Test ratios within acceptable range")
```

### Module Coverage Audit

```python
# scripts/audit_test_coverage.py
"""Audit which source modules have corresponding tests."""
from pathlib import Path
import sys

def find_untested_modules(src_path: Path, tests_path: Path) -> list[Path]:
    """Find source modules without corresponding test files."""
    untested = []

    for src_file in src_path.rglob("*.py"):
        if src_file.name.startswith("_"):
            continue

        # Expected test file patterns
        relative = src_file.relative_to(src_path)
        test_patterns = [
            tests_path / "unit" / f"test_{relative}",
            tests_path / "unit" / relative.parent / f"test_{relative.name}",
            tests_path / f"test_{relative.stem}.py",
        ]

        if not any(p.exists() for p in test_patterns):
            untested.append(src_file)

    return untested

def generate_report(untested: list[Path], src_path: Path) -> str:
    """Generate coverage audit report."""
    total_modules = len(list(src_path.rglob("*.py")))
    tested = total_modules - len(untested)
    coverage = (tested / total_modules) * 100 if total_modules else 0

    report = [
        "# Test Coverage Audit Report",
        "",
        f"**Module Coverage**: {tested}/{total_modules} ({coverage:.1f}%)",
        "",
    ]

    if untested:
        report.extend([
            "## Untested Modules",
            "",
            *[f"- `{p}`" for p in sorted(untested)],
        ])

    return "\n".join(report)

if __name__ == "__main__":
    src_path = Path("src")
    tests_path = Path("tests")

    untested = find_untested_modules(src_path, tests_path)
    report = generate_report(untested, src_path)
    print(report)

    # Fail if less than 80% modules have tests
    total = len(list(src_path.rglob("*.py")))
    if len(untested) / total > 0.20:
        sys.exit(1)
```

### CI/CD Integration

```yaml
# .github/workflows/test-compliance.yml
name: Test Compliance

on: [push, pull_request]

jobs:
  verify-structure:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v4

      - name: Verify test structure
        run: uv run python scripts/verify_test_structure.py

      - name: Check test ratios
        run: uv run python scripts/check_test_ratios.py

      - name: Audit module coverage
        run: uv run python scripts/audit_test_coverage.py

  marker-coverage:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v4
      - run: uv sync --all-extras

      - name: Run tests with marker report
        run: |
          uv run pytest --tb=no -q 2>&1 | tee test-output.txt

          # Check for unmarked tests
          if grep -q "UNMARKED:" test-output.txt; then
            UNMARKED=$(grep "UNMARKED:" test-output.txt | grep -oP '\d+')
            if [ "$UNMARKED" -gt 10 ]; then
              echo "ERROR: Too many unmarked tests ($UNMARKED)"
              exit 1
            fi
          fi
```

### Pre-commit Hook

```yaml
# .pre-commit-config.yaml (add to existing)
repos:
  - repo: local
    hooks:
      - id: verify-test-structure
        name: Verify test structure
        entry: uv run python scripts/verify_test_structure.py
        language: system
        pass_filenames: false
        stages: [pre-push]

      - id: new-code-has-tests
        name: New code has tests
        entry: |
          python -c "
          import subprocess
          import sys

          # Get changed Python files
          result = subprocess.run(
              ['git', 'diff', '--cached', '--name-only', '--diff-filter=A'],
              capture_output=True, text=True
          )
          new_files = [f for f in result.stdout.strip().split('\n')
                       if f.startswith('src/') and f.endswith('.py')]

          # Check each has a corresponding test
          missing = []
          for src_file in new_files:
              test_file = src_file.replace('src/', 'tests/unit/test_')
              if not Path(test_file).exists():
                  missing.append(src_file)

          if missing:
              print('New files without tests:')
              for f in missing:
                  print(f'  - {f}')
              sys.exit(1)
          "
        language: system
        pass_filenames: false
```

### Weekly Audit Report

```python
# scripts/weekly_test_audit.py
"""Generate weekly test health report."""
import subprocess
import json
from datetime import datetime
from pathlib import Path

def run_audit() -> dict:
    """Collect all test metrics."""
    metrics = {
        "timestamp": datetime.now().isoformat(),
        "structure": {},
        "ratios": {},
        "coverage": {},
        "mutation_score": None,
    }

    # Structure check
    result = subprocess.run(
        ["uv", "run", "python", "scripts/verify_test_structure.py"],
        capture_output=True, text=True
    )
    metrics["structure"]["passed"] = result.returncode == 0

    # Coverage
    result = subprocess.run(
        ["uv", "run", "pytest", "--cov=src", "--cov-report=json", "-q"],
        capture_output=True, text=True
    )
    if Path("coverage.json").exists():
        with open("coverage.json") as f:
            cov_data = json.load(f)
            metrics["coverage"] = {
                "line": cov_data["totals"]["percent_covered"],
                "branch": cov_data["totals"].get("branch_percent_covered", 0),
            }

    return metrics

def format_report(metrics: dict) -> str:
    """Format metrics as markdown report."""
    return f"""# Weekly Test Audit Report

**Generated**: {metrics['timestamp']}

## Summary

| Metric | Value | Status |
|--------|-------|--------|
| Structure Valid | {metrics['structure'].get('passed', 'N/A')} | {'✅' if metrics['structure'].get('passed') else '❌'} |
| Line Coverage | {metrics['coverage'].get('line', 0):.1f}% | {'✅' if metrics['coverage'].get('line', 0) >= 80 else '❌'} |
| Branch Coverage | {metrics['coverage'].get('branch', 0):.1f}% | {'✅' if metrics['coverage'].get('branch', 0) >= 80 else '❌'} |

## Recommendations

{generate_recommendations(metrics)}
"""

def generate_recommendations(metrics: dict) -> str:
    """Generate actionable recommendations."""
    recs = []

    if metrics['coverage'].get('line', 0) < 80:
        recs.append("- Increase line coverage to meet 80% minimum")
    if metrics['coverage'].get('branch', 0) < 80:
        recs.append("- Add tests for uncovered branches")
    if not metrics['structure'].get('passed'):
        recs.append("- Fix test directory structure")

    return "\n".join(recs) if recs else "All checks passing!"

if __name__ == "__main__":
    metrics = run_audit()
    report = format_report(metrics)

    # Save report
    Path("reports").mkdir(exist_ok=True)
    report_path = Path(f"reports/test-audit-{datetime.now():%Y%m%d}.md")
    report_path.write_text(report)
    print(f"Report saved to {report_path}")
    print(report)
```

### Minimum Test Requirements by Project Type

| Project Type | Unit | Integration | E2E | Security | Benchmark |
|--------------|------|-------------|-----|----------|-----------|
| Library/SDK | 80% | 15% | 5% | Required | Optional |
| API Service | 60% | 30% | 10% | Required | Required |
| CLI Tool | 70% | 20% | 10% | Optional | Optional |
| ML Pipeline | 50% | 30% | 20% | Optional | Required |

### Quick Commands

```bash
# Verify test structure
uv run python scripts/verify_test_structure.py

# Check test ratios
uv run python scripts/check_test_ratios.py

# Audit module coverage
uv run python scripts/audit_test_coverage.py

# Generate weekly report
uv run python scripts/weekly_test_audit.py

# Run with marker coverage report
uv run pytest --tb=short 2>&1 | grep -A 20 "Test Marker Coverage"
```

---

*This file contains comprehensive testing standards. For command references, see `/commands/testing.md`.*
