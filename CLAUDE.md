# Claude Code Project Guidelines

> **Standard Guidelines**: See [.claude/standard/claude.md](.claude/standard/claude.md) for:
> - Universal development standards and best practices
> - Response-Aware Development (RAD) system and assumption tagging
> - Agent assignment patterns and workflow
> - Security requirements and pre-commit checks
> - Git workflow and commit conventions
>
> **User Settings**: Global Claude configuration at `~/.claude/CLAUDE.md` (user-level)
>
> This file contains **project-specific** configurations that extend the standard guidelines.

---

## Project Overview

**Name**: Claude Code Configuration
**Description**: Global Claude Code development standards, commands, and configuration for all projects
**Author**: Byron Williams <byronawilliams@gmail.com>
**Repository**: https://github.com/ByronWilliamsCPA/.claude
**Created**: 2025-11-23

## Branch Workflow Requirement (CRITICAL)

**NEVER work directly on the `main` branch.** Always create a feature branch before making any code changes.

### Before ANY Code Changes

```bash
# 1. Check current branch
git branch --show-current

# 2. If on main/master, create a feature branch FIRST
git checkout -b feat/{descriptive-slug}

# 3. Or for bug fixes
git checkout -b fix/{issue-or-description}
```

### Branch Naming Convention

| Task Type | Branch Prefix | Commit Type |
|-----------|---------------|-------------|
| New feature | `feat/` | `feat:` |
| Bug fix | `fix/` | `fix:` |
| Documentation | `docs/` | `docs:` |
| Refactoring | `refactor/` | `refactor:` |
| Performance | `perf/` | `perf:` |
| Testing | `test/` | `test:` |

**Note**: The primary branch is `main` (not `master`).

## Security-First Development (CRITICAL)

Claude MUST adopt a security-first approach in all development:

### 1. Proactive Security Suggestions

When working on this project, always suggest appropriate security measures:
- **Dependencies**: Suggest vulnerability scanning (`safety check`, `pip-audit`)
- **APIs**: Suggest authentication, rate limiting, input validation
- **Data**: Suggest encryption at rest and in transit, access controls
### 2. Never Bypass Security Issues

- **ALL security findings** from scanners (Semgrep, SonarQube, Bandit, Checkov) should be addressed, not dismissed
- If a finding is a false positive, document WHY with inline comments
- Use baseline files only for truly unavoidable exceptions with justification

### 3. Code Quality Standards

- Treat linting warnings as errors to fix, not ignore
- Address ALL type checker warnings, not just errors
- Don't accumulate technical debt by deferring quality issues

### 4. Default to Strictest Settings

- Security scanners: fail on HIGH/CRITICAL by default
- Type checking: strict mode (already configured)
- Linting: no ignored rules without documented reason

## Project Planning Documents

> **First-Time Setup**: If planning documents show "Awaiting Generation", see the [Project Setup Guide](docs/PROJECT_SETUP.md#project-planning-with-claude-code).

**Planning Documents** (in `docs/planning/`):
- [project-vision.md](docs/planning/project-vision.md) - Problem, solution, scope, success metrics
- [tech-spec.md](docs/planning/tech-spec.md) - Architecture, data model, APIs, security
- [roadmap.md](docs/planning/roadmap.md) - Phased implementation plan
- [adr/](docs/planning/adr/) - Architecture decisions with rationale
- [PROJECT-PLAN.md](docs/planning/PROJECT-PLAN.md) - Synthesized plan with git branches (after synthesis)

**References**:
- **Complete Workflow**: [Project Setup Guide](docs/PROJECT_SETUP.md#project-planning-with-claude-code)
- **Skill Reference**: `.claude/skills/project-planning/`

### Quick Start

```bash
# 1. Generate planning documents
/plan <your project description>

# 2. Synthesize into project plan
"Synthesize my planning documents into a project plan"

# 3. Review docs/planning/PROJECT-PLAN.md

# 4. Start development
/git/milestone start feat/phase-0-foundation
```

### Using Planning Documents

```text
# Load context for a task
Load from project-vision.md sections 2-3 and adr/adr-001-*.md,
then implement [feature] per tech-spec.md section [X].

# Validate code against specs
Review this code against tech-spec.md section 6 (security).

# Check phase progress
Review PROJECT-PLAN.md Phase 1 deliverables and update status.
```

## Technology Stack

- **Python**: 3.12
- **Package Manager**: UV
- **Code Quality**: Ruff (linter/formatter), BasedPyright (type checker)
- **Testing**: pytest, coverage
- **Security**: Bandit, Safety
- **Documentation**: MkDocs Material
## Project-Specific Requirements

> **Standard Requirements**: See [.claude/standard/claude.md](.claude/standard/claude.md) for universal standards

**Coverage & Quality**:
- Test coverage: Minimum 80%
- All linters must pass: `uv run ruff check .`, `uv run basedpyright src/`
- Security scans: `uv run bandit -r src`, `uv run safety check`

## Quick Start Commands

```bash
# Initial setup
uv sync --all-extras
uv run pre-commit install

# Development cycle
uv run pytest -v                           # Run tests
uv run pytest --cov=src --cov-report=html # With coverage
uv run ruff format .                       # Format code
uv run ruff check . --fix                  # Lint and fix
uv run basedpyright src/                   # Type check

# Before commit (all must pass)
uv run pytest --cov=src --cov-fail-under=80
uv run ruff check .
uv run basedpyright src/
uv run bandit -r src
pre-commit run --all-files

# Documentation
uv run mkdocs serve                        # Local preview
uv run mkdocs build                        # Build static site
```

## Project Structure

```text
src/claude_config/
├── __init__.py              # Package initialization
├── core/                    # Core business logic
│   ├── __init__.py
│   └── config.py           # Configuration (Pydantic Settings)
├── middleware/              # Middleware components
│   └── __init__.py
└── utils/                   # Utilities
    ├── __init__.py
    ├── financial.py        # Financial utilities (Decimal precision)
    └── logging.py          # Structured logging

tests/
├── unit/                   # Unit tests
├── integration/            # Integration tests
├── conftest.py            # Pytest fixtures
└── test_example.py        # Example tests

docs/                       # MkDocs documentation
├── index.md               # Home page
└── ...                    # Additional docs
```

## Code Conventions

> **Standard Conventions**: See [.claude/standard/claude.md](.claude/standard/claude.md) for universal naming and style guidelines

**Project-Specific Patterns**:
- Configuration: Use Pydantic Settings with `.env` files
- Logging: Structured logging via `src/claude_config/utils/logging.py`
- Error Handling: Custom exceptions in `src/claude_config/core/exceptions.py`

**Docstrings** (Google Style):
```python
def process_data(input_path: str, max_rows: int = 1000) -> dict[str, Any]:
    """Process data from input file.

    Args:
        input_path: Path to input file
        max_rows: Maximum rows to process (default: 1000)

    Returns:
        Dictionary with processing results

    Raises:
        FileNotFoundError: If input file doesn't exist
        ValueError: If file format is invalid
    """
```

## Configuration Management

Use Pydantic Settings for environment-based configuration:

```python
from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    project_name: str = "Claude Code Configuration"
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    debug: bool = Field(default=False, env="DEBUG")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()
```

## Git Worktree Workflow

> **Full Documentation**: See `~/.claude/CLAUDE.md` for complete worktree concepts, commands, and best practices.

**Project-Specific Paths**:
```bash
# Worktree directory for this project
../claude_config-worktrees/

# Quick reference commands
git worktree add ../claude_config-worktrees/feature-name -b feature/feature-name
git worktree add ../claude_config-worktrees/pr-42 origin/feature/pr-branch
git worktree list
git worktree remove ../claude_config-worktrees/feature-name
```

**Remember**: Each worktree needs `uv sync --all-extras` after creation (worktrees share git but not virtualenvs).

## Common Tasks

### Add Dependency
```bash
uv add package-name              # Production
uv add --dev package-name        # Development
```

### Update Dependencies
```bash
uv sync --upgrade                        # All packages
uv sync --upgrade-package package-name   # Specific package
```

### Run Specific Test
```bash
uv run pytest tests/unit/test_example.py::test_function_name -v
```

## CI/CD Pipeline

**GitHub Actions Workflows**:
1. **CI** (`.github/workflows/ci.yml`): Tests, linting, type checking
2. **Security** (`.github/workflows/security-analysis.yml`): CodeQL, Bandit, Safety
3. **Docs** (`.github/workflows/docs.yml`): Build and deploy documentation
4. **Publish** (`.github/workflows/publish-pypi.yml`): PyPI release automation

**Quality Gates** (must pass):
- ✅ All tests pass (80% coverage)
- ✅ Ruff linting (no errors)
- ✅ BasedPyright type checking
- ✅ Security scans (no high/critical)
- ✅ Pre-commit hooks
## Third-Party Integrations

### CodeRabbit (AI Code Reviews)

CodeRabbit provides automated AI-powered code reviews on every pull request.

**Configuration**: `.coderabbit.yaml`

**Features**:
- Automatic review on PR creation
- Security vulnerability detection
- Code quality suggestions
- Path-specific review instructions

**Commands**:
```bash
# In PR comments:
@coderabbitai summary      # Get high-level summary
@coderabbitai review       # Request re-review
@coderabbitai help         # Show available commands
```

**Setup**: Install the [CodeRabbit GitHub App](https://github.com/apps/coderabbitai)

## Troubleshooting

### Pre-commit Hooks Failing
```bash
pre-commit run --all-files           # Run manually
pre-commit clean                     # Clean cache
pre-commit install --install-hooks   # Reinstall
```

### UV Lock Issues
```bash
uv lock                          # Regenerate lock
uv sync --all-extras             # Reinstall dependencies (includes dev tools)
```

### BasedPyright Type Errors
```bash
uv run basedpyright src/  # Show type errors
# Add `# pyright: ignore[error-code]` for specific issues
```

## Performance Targets

| Metric | Target | Notes |
|--------|--------|-------|
| Test Suite | <30s | Full suite with coverage |
| CI Pipeline | <5min | All checks |
| Code Coverage | 80% | Enforced in CI |

## Additional Resources

- **Project README**: [README.md](README.md)
- **Contributing Guide**: [CONTRIBUTING.md](CONTRIBUTING.md)
- **Security Policy**: [SECURITY.md](SECURITY.md)
- **Standard Claude Guidelines**: [.claude/standard/claude.md](.claude/standard/claude.md)
- **UV Documentation**: https://docs.astral.sh/uv/
- **Ruff Documentation**: https://docs.astral.sh/ruff/

---

**Last Updated**: 2025-11-24
**Template Version**: 1.0.0
