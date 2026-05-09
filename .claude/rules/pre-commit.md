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

### Review tier (choose one)

**Solo / personal project** (single-contributor, no external users):
- [ ] Run `/code-review` for AI review feedback (5 agents, ~5 min)
- [ ] CodeRabbit inline comments are advisory; address or dismiss at your discretion

**Production / OSS / client** (external users, revenue-bearing, or multi-contributor):
- [ ] **Full review**: Run `/pr-review <url>` (8 agents + Copilot + SonarQube, ~15 min)
- [ ] **CodeRabbit review**: address inline comments before merging; use `@coderabbitai` for follow-ups
- [ ] **Copilot review** (optional): for complex logic, request from the Reviewers menu; instructions in `.github/copilot-instructions.md`

**Spike branch** (`spike/` prefix):
- [ ] No PR review required; linting and secrets scanning are sufficient

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

### PC-HOOK-STAGED-SCOPE

**Invariant:** Every secret-scanning, lint, or content-check hook in `.pre-commit-config.yaml` must scope its analysis to staged files only. Full git-history modes (e.g., TruffleHog `git file://. --since-commit HEAD`, gitleaks `--log-opts="--all"`, detect-secrets with no path filter on a fresh `--baseline` regenerate) must NOT appear at the pre-commit stage.

**Why:** A pre-commit hook runs against the developer's local working copy. The local git object store typically contains commits from fetched remote branches (`origin/feature-x`, `origin/dependabot/...`, abandoned `claude/...` work) that are not reachable from `HEAD` and have never been merged. Full-history secret scanners then surface placeholder credentials, test fixtures, and known-fake examples from those branches as findings on every developer's commit, blocking work that is unrelated to the credentials. Concrete example: TruffleHog flagged `postgresql://<user>:<password>@<host>:5432` from the unmerged `claude/security-analysis-overseer-MODEz` branch (commit dated 2026-05-01) on every commit in the 2026-05-07 family-office-portal session until the hook was rescoped. Full-history scanning is a CI concern, not a pre-commit concern: CI runs against a clean clone with controlled remote refs.

**Audit check:** In `.pre-commit-config.yaml`, for each hook whose entry/command references the git history (e.g., `git file://`, `--since-commit`, `--all`, `--log-opts`), verify the hook is gated to a CI stage (`stages: [pre-push]` or omitted from local hooks via `default_install_hook_types`). For TruffleHog specifically, the staged-files form is `git diff --cached -z --diff-filter=d --name-only | xargs -0 -r trufflehog filesystem` (the `-z` and `-0` handle filenames with spaces; `--diff-filter=d` excludes deletions).

**Remediation:** Replace `--since-commit HEAD` (and equivalents) with a staged-file invocation. If full-history scanning is desired, move the check to a CI workflow (`.github/workflows/secret-scan.yml`) where the runner clones with no extraneous remote refs. For new hooks: scope to staged paths from day one; treat git-history mode as a CI feature, not a pre-commit feature.

## Sources

- pre-commit documentation: <https://pre-commit.com/>
- Ruff pre-commit hooks: <https://docs.astral.sh/ruff/integrations/#pre-commit>
- Claude Code CLAUDE.md: <https://code.claude.com/docs/en/memory>
