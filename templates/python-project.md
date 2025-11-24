# Python Project Development Guide

> This project extends the global CLAUDE.md standards. Only project-specific configurations and deviations are documented below.

## Project-Specific Standards

> **Reference**: Global standards from `~/.claude/standards/` apply unless overridden below.
>
> - **Python Standards**: See `~/.claude/standards/python.md`
> - **Security Standards**: See `~/.claude/standards/security.md`  
> - **Git Workflow**: See `~/.claude/standards/git-workflow.md`
> - **Linting Standards**: See `~/.claude/standards/linting.md`

### Python Configuration

#### Project Structure

```
project-name/
├── src/
│   └── project_name/
│       ├── __init__.py
│       ├── main.py
│       ├── models/
│       ├── services/
│       └── utils/
├── tests/
│   ├── unit/
│   ├── integration/
│   └── fixtures/
├── docs/
├── scripts/
├── pyproject.toml
├── README.md
├── .env.example
└── CLAUDE.md (this file)
```

#### Poetry Configuration

```toml
[tool.poetry]
name = "project-name"
version = "0.1.0"
description = "Project description"
authors = ["Your Name <email@example.com>"]
packages = [{include = "project_name", from = "src"}]

[tool.poetry.dependencies]
python = "^3.11"
# Add project dependencies here

[tool.poetry.group.dev.dependencies]
pytest = "^7.4.0"
pytest-cov = "^4.1.0"
black = "^23.7.0"
ruff = "^0.0.287"
basedpyright = "^1.28.0"
pre-commit = "^3.3.3"
safety = "^2.3.4"
bandit = "^1.7.5"
```

### Project-Specific Requirements

#### Environment Variables

```bash
# .env.example
DATABASE_URL=postgresql://user:password@localhost/database
API_KEY=your_api_key_here
DEBUG=false
LOG_LEVEL=INFO
```

#### Custom Commands

```bash
# Development setup
poetry install
poetry run pre-commit install

# Run application
poetry run python -m project_name

# Development server (if web app)
poetry run python -m project_name.server --reload

# Database migrations (if applicable)
poetry run alembic upgrade head
```

## Testing Configuration

### Project-Specific Test Settings

```toml
[tool.pytest.ini_options]
minversion = "7.0"
addopts = [
    "-ra",
    "--strict-markers",
    "--strict-config",
    "--cov=src/project_name",
    "--cov-report=term-missing",
    "--cov-fail-under=80",
]
testpaths = ["tests"]
markers = [
    "unit: Unit tests",
    "integration: Integration tests with external dependencies",
    "slow: Slow tests requiring longer execution time",
    "external: Tests requiring external services",
]
```

### Test Environment

```bash
# Test with coverage
poetry run pytest -v --cov=src/project_name --cov-report=html

# Run specific test categories
poetry run pytest tests/unit/
poetry run pytest -m "unit"
poetry run pytest -m "not slow"
```

## Project-Specific Security

### Sensitive Files

- `.env` - Environment variables (encrypted with GPG)
- `secrets/` - Directory for secret files (if any)
- `certificates/` - SSL certificates (if any)

### Security Commands

```bash
# Encrypt environment file
gpg --symmetric .env

# Dependency security scan
poetry run safety check
poetry run bandit -r src/project_name
```

## Documentation

### API Documentation (if applicable)

- **Framework**: FastAPI/Flask auto-docs or Sphinx
- **Location**: `docs/api/`
- **Generation**: `poetry run sphinx-build docs docs/_build`

### Code Documentation

- **Docstring Style**: Google format
- **Type Hints**: Required for all public functions
- **Examples**: Include usage examples in docstrings

## Deployment

### Docker Configuration (if applicable)

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY pyproject.toml poetry.lock ./
RUN pip install poetry && poetry install --no-dev

COPY src/ ./src/
CMD ["poetry", "run", "python", "-m", "project_name"]
```

### Environment-Specific Settings

- **Development**: Local database, debug enabled
- **Staging**: Staging database, reduced logging
- **Production**: Production database, error tracking

## Performance Requirements

### Performance Targets (customize as needed)

- **API Response Time**: p95 < 200ms
- **Memory Usage**: < 512MB in production
- **Startup Time**: < 10 seconds
- **Test Suite**: < 30 seconds

### Monitoring (if applicable)

- **Metrics**: Prometheus/Grafana
- **Logging**: Structured logging with correlation IDs
- **Health Checks**: `/health` and `/ready` endpoints

## Architecture Notes

### Design Patterns

- **Dependency Injection**: Using dependency-injector or similar
- **Repository Pattern**: For data access abstraction
- **Service Layer**: Business logic separation
- **Event-Driven**: If using async processing

### External Dependencies

- **Database**: PostgreSQL/MySQL/SQLite
- **Cache**: Redis (if applicable)
- **Message Queue**: RabbitMQ/Celery (if applicable)
- **External APIs**: List third-party integrations

## Development Workflow

### Branch Strategy

```bash
# Feature development
git checkout -b feat/feature-name
git commit -m "feat: add new feature"
git push -u origin feat/feature-name

# Bug fixes
git checkout -b fix/bug-description
git commit -m "fix: resolve bug"
```

### Pre-commit Checklist

- [ ] All tests pass: `poetry run pytest`
- [ ] Code formatted: `poetry run black .`
- [ ] Linting clean: `poetry run ruff check .`
- [ ] Type checking: `poetry run basedpyright src`
- [ ] Security scan: `poetry run bandit -r src`
- [ ] Dependencies secure: `poetry run safety check`

### Code Review Checklist

- [ ] Functionality works as expected
- [ ] Tests cover new code (minimum 80% coverage)
- [ ] Documentation updated if needed
- [ ] No security vulnerabilities
- [ ] Performance impact considered
- [ ] Error handling implemented
- [ ] Logging added for important events

## Troubleshooting

### Common Issues

```bash
# Poetry dependency conflicts
poetry lock --no-update
poetry install

# Test failures
poetry run pytest -v --tb=short
poetry run pytest --lf  # Run last failed

# Type checking errors
poetry run basedpyright src

# Performance issues
poetry run python -m cProfile -s cumulative script.py
```

### Debug Configuration

```python
# Enable debug logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Debug with pdb
import pdb; pdb.set_trace()

# Debug with ipdb
import ipdb; ipdb.set_trace()
```

## Additional Resources

### Development Tools

- **IDE**: VS Code with Python extension
- **Database Tools**: pgAdmin, DBeaver
- **API Testing**: Postman, httpie
- **Profiling**: py-spy, memory_profiler

### External Documentation

- [Project Documentation](./docs/)
- [API Documentation](./docs/api/)
- [Deployment Guide](./docs/deployment.md)
- [Architecture Decision Records](./docs/adr/)

---

*This template provides project-specific guidance while inheriting all global standards from `~/.claude/`. Update sections as needed for your specific project requirements.*
