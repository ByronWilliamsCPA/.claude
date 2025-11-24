# Project Development Guide

> This project extends the global CLAUDE.md standards. Only project-specific configurations and deviations are documented below.

## Project-Specific Standards

> **Reference**: Global standards from `~/.claude/standards/` apply unless overridden below.
>
> - **Security Standards**: See `~/.claude/standards/security.md`  
> - **Git Workflow**: See `~/.claude/standards/git-workflow.md`
> - **Linting Standards**: See `~/.claude/standards/linting.md`
> - **Python Standards**: See `~/.claude/standards/python.md` (if Python project)

### Technology Stack

#### Primary Technologies

- **Language**: [Specify: JavaScript, TypeScript, Go, Rust, etc.]
- **Framework**: [Specify: React, Vue, Express, FastAPI, etc.]
- **Database**: [Specify: PostgreSQL, MongoDB, SQLite, etc.]
- **Build Tool**: [Specify: npm, yarn, pnpm, cargo, go mod, etc.]

#### Project Structure

```
project-name/
├── src/                    # Source code
├── tests/                  # Test files
├── docs/                   # Documentation
├── scripts/                # Build and utility scripts
├── config/                 # Configuration files
├── [language-specific]/    # Package files (package.json, Cargo.toml, etc.)
├── README.md
├── .env.example
└── CLAUDE.md (this file)
```

## Environment Setup

### Prerequisites

```bash
# Install required tools
[tool] --version  # e.g., node --version, go version, rustc --version

# Project dependencies
[package-manager] install  # e.g., npm install, cargo build, go mod download
```

### Environment Variables

```bash
# .env.example
API_URL=http://localhost:3000
DATABASE_URL=your_database_connection
API_KEY=your_api_key_here
DEBUG=false
LOG_LEVEL=info
```

### Development Commands

```bash
# Setup
[setup-command]  # e.g., npm install, yarn install, cargo build

# Development server
[dev-command]    # e.g., npm run dev, cargo run, go run main.go

# Build
[build-command]  # e.g., npm run build, cargo build --release

# Test
[test-command]   # e.g., npm test, cargo test, go test ./...

# Lint
[lint-command]   # e.g., npm run lint, cargo clippy, golangci-lint run
```

## Testing Configuration

### Test Structure

```
tests/
├── unit/           # Unit tests
├── integration/    # Integration tests
├── e2e/           # End-to-end tests
└── fixtures/      # Test data and fixtures
```

### Testing Commands

```bash
# Run all tests
[test-command]

# Run specific test types
[unit-test-command]
[integration-test-command]

# Coverage reporting
[coverage-command]

# Watch mode (if available)
[watch-test-command]
```

### Test Standards

- **Coverage Target**: Minimum 80%
- **Test Naming**: Descriptive test names following `should_[expected]_when_[condition]` pattern
- **Test Organization**: Group related tests in clear modules/suites
- **Mocking**: Mock external dependencies in unit tests

## Code Quality Standards

### Language-Specific Formatting

```bash
# Code formatting
[format-command]  # e.g., prettier, rustfmt, gofmt

# Linting
[lint-command]    # e.g., eslint, clippy, golangci-lint

# Type checking (if applicable)
[typecheck-command]  # e.g., tsc, mypy
```

### Quality Gates

- [ ] All tests pass
- [ ] Code formatted consistently
- [ ] Linting passes with no warnings
- [ ] Type checking passes (if applicable)
- [ ] Security scan clean
- [ ] Documentation updated

## Security Configuration

### Security Scanning

```bash
# Dependency vulnerability scan
[security-scan-command]  # e.g., npm audit, cargo audit

# Static security analysis
[static-security-command]  # e.g., semgrep, bandit

# Secret detection
git-secrets --scan  # or detect-secrets scan
```

### Secure Development Practices

- **No Hardcoded Secrets**: Use environment variables
- **Input Validation**: Validate all user inputs
- **Error Handling**: Don't expose sensitive information in errors
- **Dependencies**: Keep dependencies updated and scan for vulnerabilities

## Documentation Standards

### Code Documentation

- **Comments**: Explain complex business logic and algorithms
- **API Documentation**: Document public APIs with examples
- **README**: Keep README.md current with setup and usage instructions
- **Changelog**: Maintain CHANGELOG.md with version history

### Documentation Structure

```
docs/
├── api/              # API documentation
├── architecture/     # System architecture docs
├── deployment/       # Deployment guides
├── troubleshooting/  # Common issues and solutions
└── contributing/     # Contribution guidelines
```

## Development Workflow

### Branch Strategy

```bash
# Feature development
git checkout -b feat/feature-name
git commit -m "feat: add new feature"
git push -u origin feat/feature-name

# Bug fixes
git checkout -b fix/bug-description
git commit -m "fix: resolve issue with component"

# Documentation
git checkout -b docs/update-readme
git commit -m "docs: update installation instructions"
```

### Commit Message Format

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`

### Pre-commit Checklist

- [ ] All tests pass
- [ ] Code formatted according to project standards
- [ ] Linting passes without warnings
- [ ] Type checking passes (if applicable)
- [ ] Security scans clean
- [ ] Documentation updated if needed
- [ ] Commit message follows conventional format

## Performance Standards

### Performance Targets (customize as needed)

- **Build Time**: < 30 seconds for development builds
- **Test Suite**: < 60 seconds for full test run
- **Application Startup**: < 5 seconds
- **Memory Usage**: < 256MB for typical operations

### Performance Monitoring

```bash
# Performance profiling
[profile-command]  # e.g., node --prof, cargo flamegraph

# Bundle analysis (web projects)
[bundle-analysis-command]  # e.g., webpack-bundle-analyzer

# Memory profiling
[memory-profile-command]
```

## Deployment

### Build Configuration

```bash
# Production build
[prod-build-command]

# Build optimization
[optimize-command]

# Asset generation
[asset-command]
```

### Environment Configuration

- **Development**: Local development with hot reload
- **Staging**: Production-like environment for testing
- **Production**: Optimized build with monitoring

### Deployment Commands

```bash
# Deploy to staging
[staging-deploy-command]

# Deploy to production
[production-deploy-command]

# Health check
[health-check-command]
```

## Monitoring and Logging

### Logging Standards

- **Log Levels**: ERROR, WARN, INFO, DEBUG
- **Structured Logging**: Use JSON format for structured logs
- **Correlation IDs**: Include request IDs for tracing
- **Sensitive Data**: Never log passwords, tokens, or PII

### Monitoring Setup

```bash
# Health check endpoint
curl [health-endpoint]

# Metrics endpoint (if applicable)
curl [metrics-endpoint]

# Log aggregation
[log-command]
```

## Troubleshooting

### Common Issues

```bash
# Dependency issues
[clean-command]  # e.g., rm -rf node_modules && npm install
[rebuild-command]

# Build issues
[clean-build-command]
[verbose-build-command]

# Test issues
[test-debug-command]
[test-verbose-command]
```

### Debug Configuration

```bash
# Debug mode
[debug-command]

# Verbose logging
[verbose-command]

# Development tools
[devtools-command]
```

## CI/CD Configuration

### GitHub Actions Example

```yaml
name: CI

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup [Language]
        uses: [setup-action]
        with:
          [language-version]: [version]
      
      - name: Install dependencies
        run: [install-command]
      
      - name: Run tests
        run: [test-command]
      
      - name: Run linting
        run: [lint-command]
      
      - name: Security scan
        run: [security-command]
```

### Quality Gates

- All tests must pass
- Code coverage above 80%
- No linting errors
- Security scan clean
- Build succeeds

## Project-Specific Notes

### Architecture Decisions
>
> Document important architectural decisions and their rationale

### External Dependencies
>
> List and document external services, APIs, and their purposes

### Known Limitations
>
> Document any known limitations or technical debt

### Future Improvements
>
> Track planned improvements and feature additions

---

*This template provides project-specific guidance while inheriting all applicable global standards from `~/.claude/`. Update sections as needed for your specific technology stack and requirements.*

*For language-specific templates, see:*

- *Python projects: `~/.claude/templates/python-project.md`*
- *Add other language templates as needed*
