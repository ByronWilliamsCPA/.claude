# Pre-Commit Checklist

Before committing ANY changes, verify all items:

## Branch & Process
- [ ] **Branch Validation**: Working on appropriate feature branch (not main/develop)
- [ ] **Branch Naming**: Branch follows `{type}/{descriptive-slug}` convention
- [ ] **TODO Management**: Was TodoWrite used for task tracking?
- [ ] **Agent Assignment**: Were tasks assigned to appropriate specialized agents?
- [ ] **Reference Files**: Were temporary reference files created for complex tasks?
- [ ] **Agent Validation**: Was all agent work reviewed and validated?
- [ ] **Assumption Verification**: Agent automatically verified critical assumptions

## Code Quality
- [ ] **OpenSSF Compliance**: Required files present (LICENSE, SECURITY.md, CONTRIBUTING.md, CHANGELOG.md)
- [ ] **Tests Pass**: Test suite passes with required coverage (`/testing`)
- [ ] **RAD Tagging**: Critical assumptions tagged where applicable (`#CRITICAL`, `#ASSUME`, `#EDGE`)
- [ ] Environment validation passes — GPG and SSH keys present (run `/security` skill)
- [ ] File-specific linter has been run and passes (`/quality`) — Ruff format + lint, BasedPyright strict type-check
- [ ] Pre-commit hooks execute successfully (`pre-commit run --all-files`)
- [ ] No linting warnings or errors remain
- [ ] Code formatting is consistent with project standards
- [ ] Commits are signed (Git signing key configured)

## Security
- [ ] **Security Scanning**: pip-audit runs automatically on pre-push when dependency files change (pyproject.toml, requirements*.txt, uv.lock). Exit code 64 = advisory found; medium+ severity blocks push. For manual audit: `uv run pip-audit`
- [ ] **Dependency Safety**: Requirements files updated if dependencies changed
- [ ] No secrets or credentials in staged files

## PR (if creating PR)
- [ ] **CI gates**: `/ci-fix` run and all gates green (or blockers documented in the PR)
- [ ] **Branch Safety**: PR preparation validates branch strategy
- [ ] **PR Creation**: Use `/git pr` skill with `--include_wtd=true`
- [ ] **Automated Review**: Run `/code-review` after PR is created to get AI review feedback (CLAUDE.md compliance + bug detection + git history analysis)
