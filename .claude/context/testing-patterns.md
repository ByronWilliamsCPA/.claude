# Testing Patterns

Common testing patterns and best practices for this project.

## Test Structure

### AAA Pattern (Arrange-Act-Assert)
```python
def test_user_creation():
    # Arrange
    user_data = {"name": "Test User", "email": "test@example.com"}

    # Act
    user = User.create(user_data)

    # Assert
    assert user.name == "Test User"
    assert user.email == "test@example.com"
```

## Fixtures

### Basic Fixture
```python
@pytest.fixture
def sample_user():
    return User(name="Test", email="test@example.com")

def test_user_display(sample_user):
    assert sample_user.display_name == "Test"
```

### Factory Fixture
```python
@pytest.fixture
def user_factory():
    def create_user(**kwargs):
        defaults = {"name": "Test", "email": "test@example.com"}
        return User(**{**defaults, **kwargs})
    return create_user

def test_custom_user(user_factory):
    admin = user_factory(role="admin")
    assert admin.role == "admin"
```

### Async Fixture
```python
@pytest.fixture
async def async_client():
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client
```

## Mocking

### Mock External Services
```python
@pytest.fixture
def mock_api(mocker):
    return mocker.patch("module.external_api.call", return_value={"status": "ok"})

def test_with_mock(mock_api):
    result = service.process()
    mock_api.assert_called_once()
    assert result.status == "ok"
```

### Mock Database
```python
@pytest.fixture
def mock_db(mocker):
    mock_session = mocker.MagicMock()
    mocker.patch("module.get_session", return_value=mock_session)
    return mock_session
```

## Parametrized Tests

```python
@pytest.mark.parametrize("input,expected", [
    ("hello", "HELLO"),
    ("world", "WORLD"),
    ("", ""),
])
def test_uppercase(input, expected):
    assert input.upper() == expected
```

## Property-Based Testing

```python
from hypothesis import given, strategies as st

@given(st.text())
def test_encode_decode_roundtrip(text):
    encoded = encode(text)
    decoded = decode(encoded)
    assert decoded == text
```

## Test Categories

### Unit Tests
```python
@pytest.mark.unit
def test_pure_function():
    assert add(1, 2) == 3
```

### Integration Tests
```python
@pytest.mark.integration
def test_database_integration(db_session):
    user = User.create(db_session, name="Test")
    assert User.get(db_session, user.id) is not None
```

### Slow Tests
```python
@pytest.mark.slow
def test_complex_operation():
    # Takes more than 1 second
    result = expensive_computation()
    assert result is not None
```

## AI/LLM Testing Patterns

### Tier 1: Mocked LLM (unit tests)

```python
@pytest.fixture
def mock_llm_response(mocker):
    return mocker.patch(
        "module.client.messages.create",
        return_value=MockResponse(content="mocked output"),
        spec=True,
    )

def test_prompt_assembly(mock_llm_response):
    result = generate_summary("input text")
    call_args = mock_llm_response.call_args
    assert "input text" in call_args.kwargs["messages"][0]["content"]
```

### Tier 2: Recorded responses (integration tests)

```python
@pytest.mark.integration
def test_with_recorded_response(recorded_responses):
    """Uses VCR/responses library to replay API calls."""
    result = analyze_document("test doc")
    assert result.confidence > 0.8
```

### Tier 3: Live LLM evaluation

```python
@pytest.mark.llm_eval
def test_output_quality():
    """Behavioral test against live LLM — slow, non-deterministic."""
    result = generate_summary(SAMPLE_TEXT)
    assert len(result) < len(SAMPLE_TEXT)
    assert key_concept in result
```

## Security Test Naming Patterns

Security tests reference OWASP category IDs for traceability:

```python
class TestOWASPWebA01:
    """Tests for A01:2025 Broken Access Control."""

    def test_a01_horizontal_authz_user_cannot_access_other_user(self, client):
        """A01:2025 — Verify horizontal access control."""
        ...

class TestOWASPLLM01:
    """Tests for LLM01:2025 Prompt Injection."""

    @pytest.mark.parametrize("payload", INJECTION_PAYLOADS)
    def test_llm01_prompt_injection_rejected(self, payload):
        """LLM01:2025 — Verify injection payloads are filtered."""
        ...
```

## Common Commands

```bash
# Run all tests
uv run pytest

# Run specific category
uv run pytest -m "unit"
uv run pytest -m "not slow"

# Run with coverage
uv run pytest --cov=src/ --cov-report=html

# Run specific test file
uv run pytest tests/unit/test_user.py

# Run specific test function
uv run pytest tests/unit/test_user.py::test_user_creation
```
