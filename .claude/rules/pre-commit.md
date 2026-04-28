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
- [ ] Environment validation passes: GPG and SSH keys present (run `/security` skill)
- [ ] File-specific linter has been run and passes (`/quality`): Ruff format + lint, BasedPyright strict type-check
- [ ] Pre-commit hooks execute successfully (`pre-commit run --all-files`)
- [ ] No linting warnings or errors remain
- [ ] Code formatting is consistent with project standards
- [ ] **Docstring Coverage**: `interrogate` passes at 85% threshold for `scripts/`; add missing docstrings rather than suppressing
- [ ] **Docstring Arguments**: `darglint` passes; `Args`/`Returns`/`Raises` sections match function signatures (excludes `tests/`, `scripts/`, `benchmarks/`, `tools/`, `noxfile.py`, `.claude/skills/`). Update the docstring to fix mismatches.
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
- [ ] **CodeRabbit review**: fires automatically on PR creation; address inline comments
      before merging and use `@coderabbitai` in PR comments to ask follow-up questions
- [ ] **Copilot review** (optional): for complex logic changes, request from the
      Reviewers menu on GitHub; review instructions are in `.github/copilot-instructions.md`

## Linting Alignment Invariants

These checks ensure that local pre-commit hooks and Qlty Cloud use the same linting rules, preventing files that pass locally from failing in CI.

### PC-YAMLLINT-FILE-REF

**Invariant:** The yamllint hook in `.pre-commit-config.yaml` must reference a config file (using `--config-file <file>`) rather than an inline `-d` config string. The referenced file must be the single source of truth used by both pre-commit and Qlty Cloud.

**Why:** Inline configs and file-ref configs can silently diverge. If the hook uses `-d "{rules: ...}"` and Qlty uses `.yamllint`, a YAML file can pass locally and fail in CI.

**Audit check:** In `.pre-commit-config.yaml`, find the yamllint hook. Verify `args:` contains `--config-file` (not `-d`). Verify the referenced file exists in the repo root.

**Remediation:** Change the hook `args` to `[--config-file, .yamllint]`. If no `.yamllint` file exists, create one.

### PC-MARKDOWNLINT-MD040

**Invariant:** The markdownlint hook in `.pre-commit-config.yaml` must be present and configured with a config file where MD040 (fenced-code-blocks-language) is active (set to `true` or not explicitly disabled).

**Why:** MD040 is the rule that requires every fenced code block to declare its language. Without it, bare fences accumulate silently and Qlty Cloud flags them as quality issues that pre-commit never catches.

**Audit check:** In `.pre-commit-config.yaml`, find the markdownlint hook. Verify it uses `--config <file>`. In the referenced config file, verify MD040 is not set to `false`.

**Remediation:** Add the markdownlint hook if missing. In the config file, set `"MD040": true` or remove any `"MD040": false` entry.

## Sources

- pre-commit documentation: <https://pre-commit.com/>
- Ruff pre-commit hooks: <https://docs.astral.sh/ruff/integrations/#pre-commit>
- Claude Code CLAUDE.md: <https://code.claude.com/docs/en/memory>
