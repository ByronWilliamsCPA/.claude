# Claude Code Configuration

## Quality & Security
[![OpenSSF Scorecard](https://api.securityscorecards.dev/projects/github.com/ByronWilliamsCPA/claude_config/badge)](https://securityscorecards.dev/viewer/?uri=github.com/ByronWilliamsCPA/claude_config)
[![REUSE Compliance](https://github.com/ByronWilliamsCPA/claude_config/actions/workflows/reuse.yml/badge.svg)](https://github.com/ByronWilliamsCPA/claude_config/actions/workflows/reuse.yml)

## CI/CD Status
[![CI Pipeline](https://github.com/ByronWilliamsCPA/claude_config/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/ByronWilliamsCPA/claude_config/actions/workflows/ci.yml?query=branch%3Amain)
[![Security Analysis](https://github.com/ByronWilliamsCPA/claude_config/actions/workflows/security-analysis.yml/badge.svg?branch=main)](https://github.com/ByronWilliamsCPA/claude_config/actions/workflows/security-analysis.yml?query=branch%3Amain)
[![Documentation](https://github.com/ByronWilliamsCPA/claude_config/actions/workflows/docs.yml/badge.svg?branch=main)](https://github.com/ByronWilliamsCPA/claude_config/actions/workflows/docs.yml?query=branch%3Amain)
[![SBOM & Security Scan](https://github.com/ByronWilliamsCPA/claude_config/actions/workflows/sbom.yml/badge.svg?branch=main)](https://github.com/ByronWilliamsCPA/claude_config/actions/workflows/sbom.yml?query=branch%3Amain)
[![PR Validation](https://github.com/ByronWilliamsCPA/claude_config/actions/workflows/pr-validation.yml/badge.svg)](https://github.com/ByronWilliamsCPA/claude_config/actions/workflows/pr-validation.yml)
[![Release](https://github.com/ByronWilliamsCPA/claude_config/actions/workflows/release.yml/badge.svg)](https://github.com/ByronWilliamsCPA/claude_config/actions/workflows/release.yml)
[![PyPI Publish](https://github.com/ByronWilliamsCPA/claude_config/actions/workflows/publish-pypi.yml/badge.svg)](https://github.com/ByronWilliamsCPA/claude_config/actions/workflows/publish-pypi.yml)

## Project Info

[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Code style: Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Contributor Covenant](https://img.shields.io/badge/Contributor%20Covenant-2.1-4baaaa.svg)](https://github.com/ByronWilliamsCPA/.github/blob/main/CODE_OF_CONDUCT.md)

| | |
|---|---|
| **Author** | Byron Williams |
| **Created** | 2025-11-23 |
| **Repository** | [ByronWilliamsCPA/.claude](https://github.com/ByronWilliamsCPA/.claude) |

---

## Overview

Global Claude Code development standards, commands, and configuration for all projects

This project provides:
- Core functionality for global claude code development standards, commands, and configuration for all projects
- Production-ready code with comprehensive testing
- Well-documented API and architecture
- Security-first development practices

## Docs Site (mkdocs)

Full docs live under `docs/` and build with `uv run mkdocs serve`. The site has two audience tracks:

- **Getting Started** (`docs/getting-started/`) — for new developers: clone, `setup.sh`, run your first agent, trigger your first skill, troubleshoot.
- **Architecture** (`docs/architecture/`) — for maintainers: mental model, hook pipeline, agent dispatch, MCP tiered loading, plus a numbered [ADR log](docs/architecture/adr/index.md) and committed [PUML diagrams](docs/architecture/diagrams/index.md) explaining *why* load-bearing decisions were made.

See [`docs/index.md`](docs/index.md) for the role-based landing page.

## Features

- **High Quality**: 80%+ test coverage enforced via CI
- **Type Safe**: Full type hints with BasedPyright strict mode
- **Well Documented**: Clear docstrings and comprehensive guides
- **Developer Friendly**: Pre-commit hooks, automated formatting, linting
- **Security First**: Dependency scanning, security analysis, SBOM generation

## Quick Start

### Prerequisites

- Python 3.10+ (tested with 3.12)
- [UV](https://docs.astral.sh/uv/) for dependency management

**Install UV**:

```bash
# macOS and Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# Or with pip/pipx
pip install uv
# or
pipx install uv
```

### Installation

```bash
# Clone repository
git clone https://github.com/ByronWilliamsCPA/.claude.git
cd claude_config

# Install dependencies (includes dev tools - REQUIRED for development)
uv sync --all-extras

# Setup pre-commit hooks (required)
uv run pre-commit install
```

### Basic Usage

```python
# Import and use the package
from claude_config import YourModule

# Example: Create an instance and use it
module = YourModule()
result = module.process()
print(result)
```

## Google Assured OSS Integration

This project uses **Google Assured OSS** as the primary package source, with PyPI as a fallback. Assured OSS provides vetted, secure open-source packages with Google's security guarantees.

### Why Assured OSS?

- **Security**: All packages are scanned and verified by Google
- **Supply Chain Protection**: Reduced risk of malicious packages
- **Compliance**: Meets enterprise security requirements
- **Automatic Fallback**: Seamlessly falls back to PyPI when needed

### Setup Instructions

1. **Copy the environment template**:
   ```bash
   cp .env.example .env
   ```

2. **Configure Google Cloud Project**:
   ```bash
   # Edit .env and set your GCP project ID
   GOOGLE_CLOUD_PROJECT=your-gcp-project-id
   ```

3. **Setup Authentication** (choose one method):

   **Option A: Service Account JSON File** (local development)
   ```bash
   # Download service account key from GCP Console
   # Set the file path in .env
   GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json
   ```

   **Option B: Base64 Encoded Credentials** (CI/CD recommended)
   ```bash
   # Encode your service account JSON
   base64 -w 0 service-account-key.json

   # Set the base64 string in .env
   GOOGLE_APPLICATION_CREDENTIALS_B64=<paste-base64-here>
   ```

4. **Validate Configuration**:
   ```bash
   # Run the validation script
   uv run python scripts/validate_assuredoss.py

   # Or use nox
   nox -s assuredoss
   ```

### Service Account Permissions

Your service account needs the following IAM role:
- `roles/artifactregistry.reader` (Artifact Registry Reader)

### Disabling Assured OSS

To use only PyPI (not recommended for production):

```bash
# In .env file
USE_ASSURED_OSS=false
```

### Troubleshooting

**Q: Packages not found in Assured OSS?**
- UV automatically falls back to PyPI for packages not in Assured OSS
- No action needed - this is expected behavior

**Q: Authentication errors?**
- Verify your service account has Artifact Registry Reader role
- Check that GOOGLE_CLOUD_PROJECT is set correctly
- Ensure credentials file/base64 is valid JSON

**Q: How to see which packages are available?**
- Run `nox -s assuredoss` to list all available packages
- Visit: https://cloud.google.com/assured-open-source-software/docs/supported-packages

## Development

### Setup Development Environment

```bash
# Install all dependencies including dev tools
uv sync --all-extras

# Setup pre-commit hooks
uv run pre-commit install

# Install Qlty CLI for unified code quality checks
curl https://qlty.sh | bash

# Run tests
uv run pytest -v

# Run with coverage
uv run pytest --cov=claude_config --cov-report=html

# Run all quality checks (using Qlty)
qlty check

# Or use pre-commit
uv run pre-commit run --all-files
```

### Code Quality Standards

All code must meet these requirements:

- **Formatting**: Ruff (88 char limit)
- **Linting**: Ruff with PyStrict-aligned rules (see below)
- **Type Checking**: BasedPyright strict mode
- **Testing**: Pytest with 80%+ coverage
- **Security**: Bandit + dependency scanning
- **Documentation**: Docstrings on all public APIs

**Unified Quality Tool**: This project uses [Qlty](https://qlty.sh) to consolidate all quality checks into a single fast tool. See [`.qlty/qlty.toml`](.qlty/qlty.toml) for configuration.

### PyStrict-Aligned Ruff Configuration

This project uses **PyStrict-aligned Ruff rules** for stricter code quality enforcement beyond standard Python linting:

| Rule | Category | Purpose |
|------|----------|---------|
| **BLE** | Blind except | Prevent bare `except:` clauses |
| **EM** | Error messages | Enforce descriptive error messages |
| **SLF** | Private access | Prevent access to private members |
| **INP** | Implicit packages | Require explicit `__init__.py` |
| **ISC** | Implicit concatenation | Prevent implicit string concatenation |
| **PGH** | Pygrep hooks | Advanced pattern-based checks |
| **RSE** | Raise statement | Proper exception raising |
| **TID** | Tidy imports | Clean import organization |
| **YTT** | sys.version | Safe version checking |
| **FA** | Future annotations | Modern annotation syntax |
| **T10** | Debugger | No debugger statements in production |
| **G** | Logging format | Safe logging string formatting |

These rules catch bugs that standard linting misses and enforce production-quality code patterns.

### Claude Code Standards: two-layer install

This repository is the source of truth for a global Claude Code configuration
that applies across every project on your machine. It uses a **two-layer
install pattern**: the repo lives in a development location (typically
`~/dev/.claude/`) while the live runtime state Claude Code reads lives at
`~/.claude/`. The two are connected by symlinks created by `setup.sh`, so
edits to tracked files propagate immediately without a copy step.

**Topology**:

```
~/.claude/  (runtime, what Claude Code reads)
├── CLAUDE.md           --sym-->  ~/dev/.claude/CLAUDE.md
├── agents/             --sym-->  ~/dev/.claude/.claude/agents/
├── skills/             --sym-->  ~/dev/.claude/.claude/skills/
├── commands/           --sym-->  ~/dev/.claude/.claude/commands/
├── rules/              --sym-->  ~/dev/.claude/.claude/rules/
├── standards/          --sym-->  ~/dev/.claude/.claude/standards/
├── scripts/            --sym-->  ~/dev/.claude/scripts/
├── reference-library/  --sym-->  ~/dev/.claude/.submodules/reference-library/
├── settings.json         (regular file, hooks merged from repo hooks.json
│                          + claudeMdExcludes merged from repo path)
├── projects/             (Claude Code runtime state, NOT tracked)
├── sessions/             (Claude Code runtime state, NOT tracked)
└── cache/, logs/, etc.   (Claude Code runtime state, NOT tracked)

~/dev/.claude/  (repo source of truth, tracked in git)
├── CLAUDE.md             Universal dev standards, re-loaded after compaction
├── hooks.json            Canonical hooks merged into runtime settings.json
├── setup.sh              Idempotent bootstrap (creates symlinks, merges hooks)
├── .claude/
│   ├── agents/           Specialized agents
│   ├── skills/           Custom slash commands (each a SKILL.md)
│   ├── commands/         Command definitions
│   ├── rules/            Cross-cutting operating rules (some path-scoped)
│   └── standards/        Specifications, thresholds, reference material
├── .submodules/
│   ├── reference-library/  External reference agents and prompts
│   ├── superpowers/        Community skills (read-only)
│   ├── anthropics-skills/  Anthropic first-party skills
│   └── anthropics-plugins/ Anthropic plugins (hookify, etc.)
└── docs/                 Project documentation for this repo
```

**Install**:

```bash
git clone --recurse-submodules https://github.com/ByronWilliamsCPA/.claude.git ~/dev/.claude
cd ~/dev/.claude && ./setup.sh
./scripts/install-vendored-plugins.sh
```

The third step registers the vendored submodules (`superpowers`,
`anthropic-agent-skills`) as local Claude Code marketplaces and installs their
plugins. Without this step, vendored skills resolve only by bare name (e.g.,
`subagent-driven-development`) and any cross-skill handoff that invokes the
namespaced form (e.g., `superpowers:subagent-driven-development`, used by
`writing-plans`) silently falls through to manual execution. The script is
idempotent and safe to re-run.

**Verify install**:

```bash
./setup.sh --doctor
```

Doctor mode prints the resolved symlink topology, flags any broken or drifted
links, checks that `hooks` and `claudeMdExcludes` are present in
`~/.claude/settings.json`, and verifies that the expected vendored plugins
are installed.

**Dry-run before applying changes**:

```bash
./setup.sh --dry-run
```

**Why symlinks instead of a subtree or submodule**: the dev-vs-runtime split
keeps the runtime directory clean of git state and lets you edit tracked
files directly from your normal working tree. Symlinks make every change
propagate instantly without a copy step, and `~/.claude/` stays free of the
session history, logs, and caches that Claude Code writes during use. The
`claudeMdExcludes` setting injected by `setup.sh` prevents the repo's own
CLAUDE.md and `.claude/**/*` files from being discovered twice (once via the
user-scope symlink, once via directory walk) when you work inside the repo
itself.

**Project-specific overrides**: any project under `~/dev/*` can ship its own
`CLAUDE.md` at the project root. When Claude Code walks up the directory
tree, the project `CLAUDE.md` loads in addition to the global standards from
`~/.claude/CLAUDE.md`, so project overrides augment rather than replace the
baseline. Per-project tool permissions go in `.claude/settings.local.json`.

#### PR review intent reminder

The `/code-review` plugin at
`.submodules/anthropics-plugins/plugins/code-review/commands/code-review.md`
is a Claude Code **command**, not a **skill**. Commands are only invoked via
the explicit slash syntax (`/code-review <PR URL>`) and do not have
auto-activation triggers like skills do. So prose phrasings such as
"review this PR" or "look at PR #14" will not reliably invoke the structured
5-agent review pipeline without the slash command.

To catch this class of user intent, `scripts/pr-review-reminder.py` is
registered as a UserPromptSubmit hook in `hooks.json`. On every user
prompt, the hook checks for a GitHub PR URL or review-intent phrasing and,
if found without an explicit `/code-review` invocation, injects a system
message telling Claude to ask the user whether they want the structured
command run.

Triggers (case-insensitive):

- GitHub PR URL regex: `https?://github\.com/[^/]+/[^/]+/pull/\d+`
- Phrase: `review (this|the)? (PR|pull request)`
- Phrase: `look at (this|the)? (PR|pull request #\d+)`
- Phrase: `check (this|the)? (PR|pull request #\d+)`
- Phrase: `review PR #\d+`
- Phrase: `PR review`

Short-circuits when `/code-review` is already present in the prompt, or
when the environment variable `PR_REVIEW_REMINDER_DISABLED=1` is set. The
hook always exits 0 and never blocks the prompt. Test scenarios are in
the script's docstring.

### Running Tests

```bash
# Run all tests
uv run pytest -v

# Run specific test file
uv run pytest tests/unit/test_module.py -v

# Run with coverage report
uv run pytest --cov=claude_config --cov-report=term-missing

# Run tests in parallel
uv run pytest -n auto
```

### Quality Checks with Qlty

**Recommended**: Use Qlty CLI for unified code quality checks.

```bash
# Run all quality checks (fast!)
qlty check

# Run checks on only changed files (fastest)
qlty check --filter=diff

# Run specific plugins only
qlty check --plugin ruff --plugin pyright

# Auto-format code
qlty fmt

# View current configuration
qlty config show
```

**Qlty runs all these tools in a single pass:**

**Python Quality:**

- Ruff (linting + formatting)
- BasedPyright (type checking)
- Bandit (security scanning)

**Security & Secrets:**

- Gitleaks (secrets detection)
- TruffleHog (entropy-based secrets detection)
- OSV Scanner (dependency vulnerabilities)
- Semgrep (advanced SAST)

**File & Configuration:**

- Markdownlint (markdown linting)
- Yamllint (YAML linting)
- Prettier (JSON, YAML, Markdown formatting)
- Actionlint (GitHub Actions workflows)
- Shellcheck (shell script linting)

**Container & Infrastructure** (if Docker enabled):

- Hadolint (Dockerfile linting)
- Trivy (container security scanning)
- Checkov (infrastructure as code security)

**Code Quality Metrics:**

- Complexity analysis (cyclomatic, cognitive)
- Code smells detection
- Maintainability scoring

### Individual Tool Commands (if needed)

```bash
# Format code
uv run ruff format src tests

# Lint and auto-fix
uv run ruff check --fix src tests

# Type checking
uv run basedpyright src

# Security scanning
uv run bandit -r src

# Dependency vulnerabilities
qlty check --plugin osv_scanner
```

## Project Structure

```
claude_config/
├── src/claude_config/     # Main package
│   ├── __init__.py
│   ├── core.py                           # Core functionality
│   └── utils/                            # Utility modules
├── tests/                                # Test suite
│   ├── unit/                             # Unit tests
│   └── integration/                      # Integration tests
├── docs/                                 # Documentation
│   ├── ADRs/                             # Architecture Decision Records
│   ├── planning/                         # Project planning docs
│   └── guides/                           # User guides
├── pyproject.toml                        # Dependencies & tool config
├── README.md                             # This file
├── CONTRIBUTING.md                       # Contribution guidelines
└── LICENSE                               # License
```

## Claude Code Resources

- **[AGENTS-AND-SKILLS.md](AGENTS-AND-SKILLS.md)**: Complete catalog of all agents and skills with descriptions and when-to-use guidance
- **[CLAUDE.md](CLAUDE.md)**: Global development standards, code quality rules, and configuration for all projects

## Documentation

- **[CONTRIBUTING.md](CONTRIBUTING.md)**: How to contribute to the project
- **[docs/ADRs/README.md](docs/ADRs/README.md)**: Architecture Decision Records documentation
- **[docs/planning/project-plan-template.md](docs/planning/project-plan-template.md)**: Project planning guide

### Writing Documentation

- Use Markdown for all documentation
- Include code examples for clarity
- Update README.md when adding major features
- Maintain architecture documentation (see [docs/ADRs/](docs/ADRs/))

## Testing

### Testing Policy

All new functionality must include tests:

- **Unit tests**: Test individual functions/classes
- **Integration tests**: Test component interactions
- **Coverage**: Maintain 80%+ coverage
- **Markers**: Use pytest markers (`@pytest.mark.unit`, `@pytest.mark.integration`)

### Test Guidelines

```bash
# Run all tests
uv run pytest -v

# Run only unit tests
uv run pytest -v -m unit

# Run only integration tests
uv run pytest -v -m integration

# Run with coverage requirements
uv run pytest --cov=claude_config --cov-fail-under=80
```

## Security

### Security-First Development

- Validate all inputs
- Use secure defaults
- Scan dependencies regularly
- Report vulnerabilities responsibly

### Reporting Security Issues

Please report security vulnerabilities to byronawilliams@gmail.com rather than using the public issue tracker.

See the [ByronWilliamsCPA Security Policy](https://github.com/ByronWilliamsCPA/.github/blob/main/SECURITY.md) for complete disclosure policy and response timelines.

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for:

- Development setup
- Code quality standards
- Testing requirements
- Git workflow and commit conventions
- Pull request process

### Quick Checklist Before Submitting PR

- [ ] Code follows style guide (Ruff format + lint)
- [ ] All tests pass with 80%+ coverage
- [ ] BasedPyright type checking passes
- [ ] Docstrings added for new public APIs
- [ ] CHANGELOG.md updated (if significant change)
- [ ] Commits follow conventional commit format

## Versioning

This project uses [Semantic Versioning](https://semver.org/):

- **MAJOR** version: Incompatible API changes
- **MINOR** version: Backwards-compatible functionality additions
- **PATCH** version: Backwards-compatible bug fixes

Current version: **1.0.0**

### Automated Releases with Semantic Release

This project uses [python-semantic-release](https://python-semantic-release.readthedocs.io/) for automated versioning based on [Conventional Commits](https://www.conventionalcommits.org/).

**How it works:**

1. **Commit messages determine version bumps:**
   - `fix:` commits trigger a **PATCH** release (1.0.0 → 1.0.1)
   - `feat:` commits trigger a **MINOR** release (1.0.0 → 1.1.0)
   - `BREAKING CHANGE:` in commit body or `!` after type triggers **MAJOR** release (1.0.0 → 2.0.0)

2. **On merge to main:**
   - Analyzes commits since last release
   - Determines appropriate version bump
   - Updates version in `pyproject.toml`
   - Generates/updates `CHANGELOG.md`
   - Creates Git tag and GitHub Release
   - Publishes to PyPI (if configured)

**Commit message examples:**

```bash
# Patch release (bug fix)
git commit -m "fix: resolve null pointer in data parser"

# Minor release (new feature)
git commit -m "feat: add CSV export functionality"

# Major release (breaking change)
git commit -m "feat!: redesign API for better ergonomics

BREAKING CHANGE: API has been redesigned for improved usability.
See migration guide in docs/migration/v2.0.0.md"
```

**Configuration:** See `[tool.semantic_release]` in `pyproject.toml` for settings.

## License

MIT License - see [LICENSE](LICENSE) for details.

## Support

- **Issues**: [GitHub Issues](https://github.com/ByronWilliamsCPA/.claude/issues)
- **Discussions**: [GitHub Discussions](https://github.com/ByronWilliamsCPA/.claude/discussions)
- **Email**: byronawilliams@gmail.com

## Acknowledgments

Thank you to all contributors and the open-source community!

---

**Made with by [Byron Williams](https://github.com/ByronWilliamsCPA)**
