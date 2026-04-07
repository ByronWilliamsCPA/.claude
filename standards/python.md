# Python Development Standards

## Code Quality Requirements

### Line Length and Formatting

- **Maximum Line Length**: 88 characters (Ruff format default)
- **Formatter**: Ruff format (mandatory for all Python files)
- **Import Sorting**: Ruff isort rules (I) handle import organization

### Code Style Standards

- **Indentation**: 4 spaces (never tabs)
- **String Quotes**: Double quotes (Ruff format default)
- **Trailing Commas**: Required in multi-line structures
- **Function/Class Spacing**: 2 blank lines between top-level definitions

## Linting and Analysis

### Ruff Configuration

- **Rules**: Comprehensive rule set including:
  - `E` (pycodestyle errors)
  - `F` (Pyflakes)
  - `I` (isort)
  - `N` (pep8-naming)
  - `UP` (pyupgrade)
  - `B` (flake8-bugbear)
  - `S` (flake8-bandit security)
  - `C4` (flake8-comprehensions)

### Essential Commands

```bash
# Format code (Ruff replaces Black)
ruff format .

# Auto-fix linting issues
ruff check --fix .

# Check for remaining issues
ruff check .

# Verify formatting is correct
ruff format --check .
```

## Type Checking

### BasedPyright Requirements

- **Type Hints**: Required for all public functions and methods
- **Configuration**: Use `pyproject.toml` for BasedPyright settings under `[tool.basedpyright]`
- **Strictness**: Use `typeCheckingMode = "strict"` for new projects
- **Coverage**: Target 100% type annotation coverage
- **Strict Inference**: Enable `strictListInference`, `strictDictionaryInference`, `strictSetInference`

> **Note**: BasedPyright is a stricter fork of Pyright, providing 3-5x faster type checking than MyPy with enhanced type inference.

### Type Annotation Standards

```python
# Function signatures
def process_data(input_data: list[str], limit: int = 100) -> dict[str, Any]:
    """Process data with proper type hints."""
    pass

# Class definitions
class DataProcessor:
    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config

    def process(self, data: list[str]) -> ProcessResult:
        """Process data and return results."""
        pass
```

### Essential Commands

```bash
# Type check entire project
uv run basedpyright src

# Type check specific files
uv run basedpyright src/module.py
```

## Testing Standards

### Coverage Requirements

- **Line Coverage**: 80% minimum (all projects)
- **Branch Coverage**: 70% minimum (all projects)
- **Critical Modules**: 90% line coverage (auth, payment, data processing)
- **Patch Coverage**: 90% on new/changed lines in PRs
- **Branch Coverage**: Required (not just line coverage)
- **Missing Coverage Reports**: Must identify uncovered areas

### Test Organization

```
tests/
├── unit/           # Unit tests (fast, isolated)
├── integration/    # Integration tests (slower, with dependencies)
├── e2e/           # End-to-end tests (full system)
└── fixtures/      # Test data and fixtures
```

### Test Naming Conventions

```python
def test_should_return_valid_result_when_given_valid_input():
    """Test function with descriptive name following pattern."""
    pass

class TestDataProcessor:
    """Test class for DataProcessor."""

    def test_should_process_data_correctly(self):
        """Test method with descriptive name."""
        pass
```

### Essential Commands

```bash
# Run all tests with coverage
uv run pytest -v --cov=src --cov-report=html --cov-report=term-missing

# Run specific test categories
uv run pytest tests/unit/
uv run pytest tests/integration/

# Run tests with specific markers
uv run pytest -m "slow"
uv run pytest -m "not integration"
```

## Dependency Management

### UV Configuration

- **Dependency Specification**: Use semantic versioning constraints
- **Development Dependencies**: Separate from production dependencies in `[dependency-groups]`
- **Lock File**: Always commit `uv.lock`

### Version Constraints

```toml
[project]
requires-python = ">=3.10,<3.15"
dependencies = [
    "requests>=2.28.0,<3.0.0",
    "pydantic>=2.0.0",
]

[dependency-groups]
dev = [
    "pytest>=7.4.0",
    "ruff>=0.1.0",
    "basedpyright>=1.28.0",
]
```

### Essential Commands

```bash
# Install dependencies
uv sync --all-extras

# Add new dependency
uv add package-name

# Add development dependency
uv add --dev package-name

# Update dependencies
uv sync --upgrade

# Show dependency tree
uv tree
```

## Project Structure

### Standard Layout

```
project/
├── src/
│   └── package_name/
│       ├── __init__.py
│       ├── main.py
│       └── modules/
├── tests/
├── docs/
├── pyproject.toml
├── README.md
└── .env.example
```

### Configuration Files

- **pyproject.toml**: Primary configuration for all tools
- **py.typed**: Mark package as typed
- **.env.example**: Template for environment variables

## Security Requirements

### Code Security

- **Bandit Scanning**: Required for all security-sensitive code
- **Dependency Scanning**: Use `pip-audit` to check for vulnerabilities
- **Secret Detection**: No hardcoded secrets or API keys

### Essential Commands

```bash
# Security scanning
uv run bandit -r src

# Dependency vulnerability check
uv run pip-audit

# Check for secrets (if pre-commit configured)
pre-commit run detect-private-key --all-files
```

## Performance Guidelines

### Best Practices

- **Lazy Loading**: Use generators and lazy evaluation where appropriate
- **Memory Efficiency**: Avoid loading large datasets into memory unnecessarily
- **Async/Await**: Use for I/O-bound operations
- **Caching**: Implement appropriate caching strategies

### Profiling

```bash
# Profile with cProfile
python -m cProfile -s cumulative script.py

# Memory profiling
uv add --dev memory_profiler
uv run python -m memory_profiler script.py
```

## Environment Setup

### Python Version

- **Minimum**: Python 3.10
- **Recommended**: Python 3.12 (Ruff target version)
- **Maximum**: Python 3.14 (`requires-python = ">=3.10,<3.15"`)
- **Virtual Environment**: Always use `uv`

### IDE Configuration

- **VS Code**: Recommended extensions and settings
- **PyCharm**: Configuration for Ruff, BasedPyright integration
- **Editor Config**: Consistent formatting across editors

---

*This file contains comprehensive Python development standards. For command references, see `/commands/quality.md` and `/commands/testing.md`.*
