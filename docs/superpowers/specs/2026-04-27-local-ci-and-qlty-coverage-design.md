---
schema_type: common
title: Local CI Strategy and Qlty Coverage Reporting Design
status: published
owner: engineering
purpose: >
  Design for reducing GitHub Actions minute burn via local-first CI (nox sessions + pre-push hook)
  and adding Qlty coverage reporting on PR open/reopen events.
tags: [ci_cd, github_actions, coverage, testing, hooks, automation]
---

**Date:** 2026-04-27 | **Status:** Approved | **Branch:** new branch off main (does not interrupt `feat/gate-jobs-implementation`)

## Problem

Two related friction points in the development workflow:

1. **GitHub Actions minute burn:** Every commit pushed to a feature branch with an open PR triggers `ci.yml` and `pr-validation.yml` (via `pull_request: synchronize`). When iterating to fix CI failures, each intermediate push consumes a full CI run before the code is actually ready.

2. **Coverage visibility gap:** Qlty is used for code quality review, but coverage data is not available there. Codecov is the primary source and SonarCloud also shows it, but having coverage visible directly in Qlty simplifies the review workflow when already working in that tool.

## Decisions

- Local CI uses **nox sessions** (not a new tool like `just`) to stay consistent with the existing task runner.
- Qlty coverage upload fires on **PR opened/reopened only** (not synchronize) to keep it lightweight and non-blocking.
- The pre-push hook source is **tracked in `.github/hooks/`** and installed via a script, so changes to what it enforces go through code review.

## Section 1: Local CI Nox Sessions

### New sessions in `noxfile.py`

**`ci_local` (Python 3.12)**

Mirrors `ci.yml` step for step in the same order:

1. `pytest -v --cov=src --cov-report=xml --cov-report=lcov:reports/lcov.info --cov-report=term-missing --cov-fail-under=80`
2. `basedpyright src/`
3. `ruff check src/ tests/`
4. `bandit -r src/ -c pyproject.toml`

This is the session the pre-push hook runs. Blocks the push if any step fails.

**`ci_full`**

Chains the existing multi-version sessions without reimplementing them:

1. `nox -s test` (Python 3.10-3.14, pytest with coverage)
2. `nox -s lint` (Python 3.10-3.14, ruff + type hints check)
3. `nox -s typecheck` (Python 3.10-3.14, basedpyright)

Use before opening a PR or merging to get the same coverage as the GitHub matrix.

### Pre-push hook

**`.github/hooks/pre-push`** (tracked in git):

```sh
#!/usr/bin/env bash
set -e
echo "Running local CI checks before push..."
nox -s ci_local
```

**`scripts/install-hooks.sh`** (tracked in git):

```sh
#!/usr/bin/env bash
set -e
cp .github/hooks/pre-push .git/hooks/pre-push
chmod +x .git/hooks/pre-push
echo "Pre-push hook installed."
```

The hook can be bypassed with `git push --no-verify` for explicit WIP pushes.

## Section 2: Qlty Coverage Upload

### Coverage format

Add `--cov-report=lcov:reports/lcov.info` to the pytest step in `ci.yml` alongside the existing `--cov-report=xml`. This keeps Codecov working unchanged while producing the lcov file Qlty expects.

### New job in `pr-validation.yml`

```yaml
qlty-coverage:
  name: Qlty Coverage Upload
  runs-on: ubuntu-latest
  if: github.event.action == 'opened' || github.event.action == 'reopened'
  permissions:
    contents: read
  steps:
    - name: Harden the runner
      uses: step-security/harden-runner@...
      with:
        egress-policy: audit
    - name: Checkout repository
      uses: actions/checkout@...
    - name: Install uv
      uses: astral-sh/setup-uv@...
      with:
        enable-cache: true
    - name: Set up Python
      run: uv python install 3.12
    - name: Install dependencies
      run: uv sync --all-extras
    - name: Run tests with coverage
      run: uv run pytest --cov=src --cov-report=lcov:reports/lcov.info --cov-fail-under=80
    - name: Upload coverage to Qlty
      uses: qltysh/qlty-action/coverage@v2
      with:
        token: ${{ secrets.QLTY_COVERAGE_TOKEN }}
        files: reports/lcov.info
```

The job fires only on `opened` and `reopened` events, not `synchronize`. It appears in the `validation-summary` `needs:` list for visibility but does not block the gate.

### Required secret

`QLTY_COVERAGE_TOKEN` must be added to the repository's GitHub Actions secrets before this job will succeed.

## Section 3: Supporting Changes

### `.gitignore`

Add `reports/` to prevent generated coverage files from being staged.

### `validation-summary` gate update

Add `qlty-coverage` to the `needs:` array in the `validation-summary` job so its result appears in the PR summary. Do not add it to the `BLOCK=1` logic; it is informational, consistent with how `link-check` is handled.

### No trigger changes to `ci.yml`

The existing triggers (push to main/master/develop, plus PR events) are correct. Minute savings come from running `nox -s ci_local` locally before pushing, not from restricting when GitHub CI fires.

## Section 4: Cross-repo Linting Alignment

### Root cause

This repo has a `.yamllint` config file but no yamllint hook in `.pre-commit-config.yaml` (the hook entry exists only as a comment). Markdownlint is also commented out. Qlty Cloud runs both tools against the default rulesets, so findings accumulate there without pre-commit ever catching them locally. The reference library (`.submodules/reference-library/`) has no `.pre-commit-config.yaml` at all.

### Immediate fix in this repo

Two hooks added to `.pre-commit-config.yaml`:

**yamllint**: using `--config-file .yamllint` so local checks use the same config Qlty is pointed at. The `.yamllint` file's `min-spaces-from-content: 1` setting must be verified against Qlty's effective config; if they differ, update `.yamllint` to be the authoritative source and fix any violations in the workflow files.

**markdownlint**: added with a config that keeps MD040 (fenced code language) active. The two README.md fences at lines 7 and 11 get language specifiers added as part of this fix.

### Standards update

A new rule block in `.claude/rules/pre-commit.md` (or `.claude/standards/linting-alignment.md` if it warrants its own file) documents the invariant:

- yamllint must reference a file (not inline config), and that file must be the single source of truth for both pre-commit and Qlty
- markdownlint must keep MD040 active
- The repo-compliance manifest gets two new check IDs (`PC-YAMLLINT-FILE-REF`, `PC-MARKDOWNLINT-MD040`) so the auditor can verify compliance in any repo

### Reference library update

The reference library's template pre-commit config is updated to include both hooks with correct configuration so repos created from or synced with the reference library ship aligned. Implementation will need to locate where the reference library stores its pre-commit template (no `.pre-commit-config.yaml` currently found in `.submodules/reference-library/`).

## File Inventory

| File | Change |
|---|---|
| `noxfile.py` | Add `ci_local` and `ci_full` sessions |
| `.github/hooks/pre-push` | New tracked hook source file |
| `scripts/install-hooks.sh` | New hook install script |
| `.github/workflows/ci.yml` | Add `--cov-report=lcov:reports/lcov.info` to pytest step |
| `.github/workflows/pr-validation.yml` | Add `qlty-coverage` job; add to `validation-summary` needs |
| `.gitignore` | Add `reports/` entry |
| `.pre-commit-config.yaml` | Add yamllint and markdownlint hooks |
| `.yamllint` | Verify/align with Qlty Cloud ruleset; fix any delta |
| `README.md` | Add language specifiers to 2 fenced code blocks |
| `.claude/rules/pre-commit.md` or new standards file | Add yamllint file-ref and MD040 invariants + compliance check IDs |
| Reference library pre-commit template | Add yamllint and markdownlint hooks (location TBD during implementation) |

## Out of Scope

- Changing `ci.yml` push triggers or adding path filters to feature branches
- Modifying Codecov configuration
- Changes to the `python-compatibility.yml` matrix workflow
- Active remediation of existing repos (fixing repos already created from the template)
