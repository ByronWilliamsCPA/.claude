# Testing Standards

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
├── fixtures/         # Shared test data and factories
│   ├── __init__.py
│   ├── factories.py
│   └── sample_data.py
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

## Mutation Testing

Mutation testing validates test quality by introducing small code changes (mutations) and verifying tests catch them.

```toml
# pyproject.toml
[tool.mutmut]
paths_to_mutate = "src/"
tests_dir = "tests/"
runner = "python -m pytest"
```

```bash
# Run mutation testing
uv run mutmut run

# View results
uv run mutmut results

# Show surviving mutants (tests missed these)
uv run mutmut show <id>
```

### Target Metrics

| Metric | Minimum | Excellent |
|--------|---------|-----------|
| Mutation Score | 70% | 85%+ |
| Surviving Mutants | <30% | <15% |

---

*This file contains comprehensive testing standards. For command references, see `/commands/testing.md`.*
