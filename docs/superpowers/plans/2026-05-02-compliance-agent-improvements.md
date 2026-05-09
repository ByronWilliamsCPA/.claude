---
schema_type: planning
title: "Compliance Agent Improvements: 2026-05-02 Lessons-Learned"
status: draft
owner: core-maintainer
source: "https://github.com/ByronWilliamsCPA/.claude/pull/51"
purpose: "Apply Tier 1 (execution-bug fixes) and Tier 2 (scope expansions) from the 2026-05-02 compliance retrospective to agent definitions, and gitignore lessons-learned documents in homelab-infra."
component: Development-Tools
tags:
  - compliance
  - agents
---

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Apply all Tier 1 (execution-bug fixes) and Tier 2 (scope expansions) items from the 2026-05-02 compliance retrospective, and gitignore lessons-learned documents in homelab-infra.

**Architecture:** Six independent file edits across two repositories (`homelab-infra` and `.claude`). Each task touches exactly one file and produces one commit. No new files are created; all changes are additions or replacements within existing agent definitions. Tasks 2-6 all modify agent `.md` files in `/home/byron/.claude/agents/`.

**Tech Stack:** Markdown agent definitions (plain text edits), `.gitignore` pattern addition.

**Source document:** `/home/byron/dev/homelab-infra/docs/compliance-reports/lessons-learned/2026-05-02.md`

---

## File Structure

| File | Repo | Change type |
|------|------|------------|
| `/home/byron/dev/homelab-infra/.gitignore` | homelab-infra | Add 2-line pattern block |
| `/home/byron/.claude/agents/repo-foundations-auditor.md` | .claude | Add 3 instruction blocks (TOML validation, .sh bit, `[project.scripts]` check) |
| `/home/byron/.claude/agents/pre-commit-auditor.md` | .claude | Add 3 instruction blocks (SHA pragma, em-dash pre-scan, `.secrets.baseline` check) |
| `/home/byron/.claude/agents/mkdocs-specialist.md` | .claude | Add 1 pre-check step to Gap Authoring Workflow |
| `/home/byron/.claude/agents/python-toolchain-auditor.md` | .claude | Add `[tool.interrogate]` check + remediation |
| `/home/byron/.claude/agents/ossf-compliance-auditor.md` | .claude | Expand Dependabot check to ecosystem coverage; add CI-SEC-002 |

---

## Task 1: Gitignore compliance lessons-learned in homelab-infra

**Files:**
- Modify: `/home/byron/dev/homelab-infra/.gitignore` (last line currently: `.worktrees/`)

**Why:** Lessons-learned documents are session-local retrospective notes committed inside the compliance PR branch. They should not appear as untracked files between sessions in the main working tree.

- [ ] **Step 1: Append the ignore pattern**

  Open `/home/byron/dev/homelab-infra/.gitignore`. At the very end of the file (after `.worktrees/`), append:

  ```

  # Compliance session retrospectives (committed inside compliance PRs, not tracked in main)
  docs/compliance-reports/lessons-learned/
  ```

- [ ] **Step 2: Verify the pattern is present**

  ```bash
  grep -n "lessons-learned" /home/byron/dev/homelab-infra/.gitignore
  ```
  Expected: one line containing `docs/compliance-reports/lessons-learned/`

- [ ] **Step 3: Verify git honors the pattern**

  ```bash
  cd /home/byron/dev/homelab-infra && \
  git check-ignore -v docs/compliance-reports/lessons-learned/2026-05-02.md
  ```
  Expected: `.gitignore:<line_number>:docs/compliance-reports/lessons-learned/  docs/compliance-reports/lessons-learned/2026-05-02.md`

- [ ] **Step 4: Commit**

  ```bash
  cd /home/byron/dev/homelab-infra
  git add .gitignore
  git commit -m "chore: gitignore compliance lessons-learned retrospectives"
  ```

---

## Task 2: repo-foundations-auditor -- TOML validation, .sh executable bit, [project.scripts] check

**Files:**
- Modify: `/home/byron/.claude/agents/repo-foundations-auditor.md` (62 lines)

Three execution bugs from the 2026-05-02 session, all in this one agent.

- [ ] **Step 1: Add TOML validation guard to Remediation Workflow**

  In `/home/byron/.claude/agents/repo-foundations-auditor.md`, find the line:

  ```
  Report each action taken: file created, file patched, or entry appended.
  ```

  Insert the following block **before** that line (i.e., as a new paragraph at the end of the Remediation Workflow body, before the closing "Report" sentence):

  ```markdown
  **TOML table insertion validation:** After inserting any new `[table]` section into `pyproject.toml`, validate the file parses correctly before staging:

  ```bash
  python -c "import tomllib; tomllib.load(open('pyproject.toml', 'rb'))"
  ```

  If this command fails, abort and review the insertion point before staging. Common cause: the new table was placed before an existing array-valued key inside `[project]`. Move it to after all array-valued keys in the parent section, or append it at the very end of the `[project]` block.

  **Shell script executable bit:** After creating any `.sh` file, set the executable bit before staging:

  ```bash
  git add --chmod=+x <path/to/script.sh>
  ```

  Never commit a `.sh` file without this step -- the script will be non-executable for anyone who clones the repo.

  ```

- [ ] **Step 2: Add [project.scripts] check to Audit Workflow**

  In the same file, find the line:

  ```
  Return findings as a structured list with fields: id, severity, description, status (pass or fail), current_value (what was found or not found).
  ```

  Insert the following block **before** that line:

  ```markdown
  - `cli_entrypoint` checks: use Glob to search for `src/*/cli.py`. If found, Read `pyproject.toml` and check whether a `[project.scripts]` table is present. If absent, report:
    - id: `TOOL-NEW-001`, severity: `suggested`, description: `[project.scripts] absent from pyproject.toml despite src/*/cli.py being present`

  ```

- [ ] **Step 3: Verify all three additions are present**

  ```bash
  grep -n "tomllib\|chmod.*+x\|cli_entrypoint" /home/byron/.claude/agents/repo-foundations-auditor.md
  ```
  Expected: three matching lines (one for `tomllib`, one for `chmod`, one for `cli_entrypoint`).

- [ ] **Step 4: Commit**

  ```bash
  cd /home/byron/dev/.claude
  git add .claude/agents/repo-foundations-auditor.md
  git commit -m "fix(agents): add TOML validation, .sh chmod, and cli_entrypoint check to repo-foundations-auditor"
  ```

---

## Task 3: pre-commit-auditor -- SHA pragma, em-dash pre-scan, .secrets.baseline check

**Files:**
- Modify: `/home/byron/.claude/agents/pre-commit-auditor.md` (59 lines)

Two Tier 1 execution bugs and one Tier 2 scope expansion, all in this agent.

- [ ] **Step 1: Add SHA pragma instruction to Remediation Workflow**

  In `/home/byron/.claude/agents/pre-commit-auditor.md`, find the line:

  ```
  **For unpinned rev fields:** Resolve the SHA for the current tag and replace using Edit. Add the version as a comment on the same line: `rev: <40-char-sha>  # v1.2.3`
  ```

  Replace that entire line with:

  ```markdown
  **For unpinned rev fields:** Resolve the SHA for the current tag and replace using Edit. Add the version as a comment on the same line, followed immediately by `  # pragma: allowlist secret`:

  ```yaml
  rev: "<40-char-sha>"  # v1.2.3  # pragma: allowlist secret
  ```

  The pragma is mandatory on every SHA-pinned `rev:` line. SHA hashes are 40-char hex strings that trigger `Hex High Entropy String` false positives in detect-secrets. Adding the pragma during pinning prevents a pre-commit failure that would otherwise require a second fix commit.
  ```

- [ ] **Step 2: Add no-em-dash pre-scan instruction to Remediation Workflow**

  In the same file, find the line:

  ```
  **If .pre-commit-config.yaml exists but hooks are missing:** Append only the missing hook entries; do not rewrite the file.
  ```

  Insert the following block **before** that line:

  ```markdown
  **Before adding the `no-em-dash` hook to any repo:** run a preliminary scan for pre-existing em-dashes:

  ```bash
  grep -rnP -- '\x{2014}' docs/ services/ README.md CHANGELOG.md 2>/dev/null
  ```

  If this returns matches, add an `exclude:` regex to the hook entry covering those paths **before committing**:

  ```yaml
    - id: no-em-dash
      exclude: "^services/|^docs/legacy/"
  ```

  Never add the hook without the pre-scan. Discovering pre-existing em-dashes at `pre-commit run` time requires a second commit to add the exclude pattern.

  ```

- [ ] **Step 3: Add .secrets.baseline check to Audit Workflow**

  In the same file, find the line:

  ```
  Return findings with: id, severity, description, status, current_value (list of missing hooks or list of unpinned revs).
  ```

  Insert the following block **before** that line:

  ```markdown
  For `baseline_present` (PC-NEW-001): when the `detect-secrets` hook id is present in any repo block, use Glob to check for `.secrets.baseline` at the project root. If absent or zero bytes, report:
  - id: `PC-NEW-001`, severity: `important`, description: `detect-secrets hook present but .secrets.baseline absent or empty`
  - current_value: `file not found` or `file is empty`
  - remediation note: `run: detect-secrets scan > .secrets.baseline && git add .secrets.baseline`

  ```

- [ ] **Step 4: Verify all three additions are present**

  ```bash
  grep -n "pragma: allowlist secret\|no-em-dash.*pre-scan\|baseline_present\|PC-NEW-001" \
    /home/byron/.claude/agents/pre-commit-auditor.md
  ```
  Expected: at least three matching lines.

  Also verify the pragma instruction is on the `rev:` example line:
  ```bash
  grep "pragma: allowlist secret" /home/byron/.claude/agents/pre-commit-auditor.md
  ```
  Expected: at least one match.

- [ ] **Step 5: Commit**

  ```bash
  cd /home/byron/dev/.claude
  git add .claude/agents/pre-commit-auditor.md
  git commit -m "fix(agents): add SHA pragma, em-dash pre-scan, and secrets.baseline check to pre-commit-auditor"
  ```

---

## Task 4: mkdocs-specialist -- tags.yml pre-check before authoring

**Files:**
- Modify: `/home/byron/.claude/agents/mkdocs-specialist.md` (118 lines)

One Tier 1 execution bug: new docs with undeclared tags fail the `validate_front_matter` pre-commit hook with an opaque error.

- [ ] **Step 1: Add tags pre-check as step 0 in Gap Authoring Workflow**

  In `/home/byron/.claude/agents/mkdocs-specialist.md`, find the line:

  ```
  1. Read the existing page (if stale) or examine codebase sources to understand the subject
  ```

  Insert the following as a new numbered step **before** that line (making the existing step 1 become step 2, etc.):

  ```markdown
  1. **Tags pre-check:** For each tag in the new page's planned `tags:` frontmatter list, check whether it appears in `docs/_data/tags.yml`. Read that file first; if any tag is missing, append it to `docs/_data/tags.yml` before writing the page. The `validate_front_matter` pre-commit hook rejects pages with undeclared tags with a non-obvious error message -- resolving this after the fact requires a second commit.
  ```

  Then renumber the existing steps 1-5 to 2-6.

- [ ] **Step 2: Verify the pre-check step is present**

  ```bash
  grep -n "tags.yml\|Tags pre-check\|_data/tags" /home/byron/.claude/agents/mkdocs-specialist.md
  ```
  Expected: at least one matching line containing `docs/_data/tags.yml`.

- [ ] **Step 3: Commit**

  ```bash
  cd /home/byron/dev/.claude
  git add .claude/agents/mkdocs-specialist.md
  git commit -m "fix(agents): add tags.yml pre-check to mkdocs-specialist gap authoring workflow"
  ```

---

## Task 5: python-toolchain-auditor -- [tool.interrogate] check and remediation

**Files:**
- Modify: `/home/byron/.claude/agents/python-toolchain-auditor.md` (68 lines)

One Tier 2 scope expansion: darglint is checked as a dev dependency, but no check enforces that `[tool.interrogate]` sets a `fail-under` threshold in `pyproject.toml`.

- [ ] **Step 1: Add interrogate_config check to Audit Workflow**

  In `/home/byron/.claude/agents/python-toolchain-auditor.md`, find the line:

  ```
  Return findings with: id, severity, description, status, current_value (list of missing codes for ruff checks, package name for dep checks).
  ```

  Insert the following block **before** that line:

  ```markdown
  - `interrogate_config` checks: when `darglint` or `interrogate` appears in any dev dependency section or in the pre-commit hook IDs, Read `pyproject.toml` and check for a `[tool.interrogate]` section containing a `fail-under` key. If absent, report:
    - id: `TOOL-NEW-002`, severity: `suggested`, description: `[tool.interrogate] section absent from pyproject.toml despite darglint/interrogate present in dev dependencies`

  ```

- [ ] **Step 2: Add interrogate remediation to Remediation Workflow**

  In the same file, find the line:

  ```
  After remediation, emit: "NOTE: Adding or removing dependencies and enabling new Ruff rules will surface new violations. Run the full toolchain and fix violations before committing. Do not add noqa or type: ignore suppressions."
  ```

  Insert the following block **before** that line:

  ```markdown
  - Missing `[tool.interrogate]` block: append to `pyproject.toml`:

  ```toml
  [tool.interrogate]
  fail-under = 80
  ignore-init-method = true
  ignore-init-module = true
  ignore-magic = true
  ```

  ```

- [ ] **Step 3: Verify both additions are present**

  ```bash
  grep -n "interrogate_config\|TOOL-NEW-002\|tool.interrogate\|fail-under" \
    /home/byron/.claude/agents/python-toolchain-auditor.md
  ```
  Expected: at least four matching lines (check description, TOOL-NEW-002, toml section header, fail-under key).

- [ ] **Step 4: Commit**

  ```bash
  cd /home/byron/dev/.claude
  git add .claude/agents/python-toolchain-auditor.md
  git commit -m "feat(agents): add [tool.interrogate] config check to python-toolchain-auditor"
  ```

---

## Task 6: ossf-compliance-auditor -- Dependabot ecosystem coverage and CI-SEC-002

**Files:**
- Modify: `/home/byron/.claude/agents/ossf-compliance-auditor.md` (408 lines)

Two Tier 2 scope expansions. The Dependabot check (Stage 4, line 111-115) currently only verifies file presence; it needs to also verify ecosystem coverage. CI-SEC-002 is a net-new check for `continue-on-error: true` on security gate steps.

- [ ] **Step 1: Expand the Dependabot check to include ecosystem coverage**

  In `/home/byron/.claude/agents/ossf-compliance-auditor.md`, find the exact block:

  ```
  **Dependabot configuration:**
  ```bash
  gh api "repos/${REPO_SLUG}/contents/.github/dependabot.yml" 2>/dev/null
  ```
  Also check locally: `Glob .github/dependabot.yml` and `Glob renovate.json`. If neither exists: emit SCORECARD:Dependency-Update-Tool FINDING.
  ```

  Replace it with:

  ```markdown
  **Dependabot configuration:**
  ```bash
  gh api "repos/${REPO_SLUG}/contents/.github/dependabot.yml" 2>/dev/null
  ```
  Also check locally: `Glob .github/dependabot.yml` and `Glob renovate.json`. If neither exists: emit SCORECARD:Dependency-Update-Tool FINDING.

  If `.github/dependabot.yml` exists, Read it and verify it contains at least one entry with `package-ecosystem: pip` or `package-ecosystem: uv`, AND at least one entry with `package-ecosystem: github-actions`. If either ecosystem is missing, emit:

  ```text
  FINDING:
  id: OSSF-NEW-001
  severity: important
  description: .github/dependabot.yml is missing required ecosystem entries
  status: configuration_gap
  current_value: ecosystems present: [list found]; missing: [list absent]
  remediation: |
    Add the missing ecosystem entry to .github/dependabot.yml. Required entries:
      - package-ecosystem: "pip"   # use "uv" if the project uses uv
        directory: "/"
        schedule:
          interval: "weekly"
      - package-ecosystem: "github-actions"
        directory: "/"
        schedule:
          interval: "weekly"
  ```
  ```

- [ ] **Step 2: Add CI-SEC-002 check as a new Stage 4 section**

  In the same file, find the line:

  ```
  ### Stage 5: Local File Checks (OSSF-002..005)
  ```

  Insert the following block **before** that line (as the final check inside Stage 4):

  ```markdown
  **Security gate `continue-on-error` bypass (CI-SEC-002):**

  Read all YAML files under `.github/workflows/` using Glob, then Read each one. For any workflow step that meets **both** conditions:
  1. The step's `uses:` field references one of: `anchore/scan-action`, `aquasecurity/trivy-action`, `actions/dependency-review-action`, `ossf/scorecard-action`
  2. The same step has `continue-on-error: true`

  Emit one FINDING per offending step:

  ```text
  FINDING:
  id: CI-SEC-002
  severity: critical
  description: Security gate step has continue-on-error: true, bypassing the gate on failure
  status: configuration_gap
  current_value: [workflow filename]::[job name]::[step name or uses value]
  remediation: |
    Remove `continue-on-error: true` from the [step] in [workflow file].
    If you need to capture failure output without failing the job, use a
    separate reporting step after the security step with `if: failure()`.
    Never allow a security scanning step to silently continue past a failure.
  ```

  ```

- [ ] **Step 3: Verify both additions are present**

  ```bash
  grep -n "OSSF-NEW-001\|ecosystem.*missing\|CI-SEC-002\|continue-on-error.*bypass" \
    /home/byron/.claude/agents/ossf-compliance-auditor.md
  ```
  Expected: at least four matching lines.

  Verify the Dependabot block now checks ecosystems:
  ```bash
  grep -n "package-ecosystem.*pip\|package-ecosystem.*github-actions" \
    /home/byron/.claude/agents/ossf-compliance-auditor.md
  ```
  Expected: at least two matches (one for each ecosystem example).

- [ ] **Step 4: Commit**

  ```bash
  cd /home/byron/dev/.claude
  git add .claude/agents/ossf-compliance-auditor.md
  git commit -m "feat(agents): add Dependabot ecosystem coverage check and CI-SEC-002 to ossf-compliance-auditor"
  ```

---

## Execution Notes

- Tasks 1 and 2-6 are in different repositories; do not mix their commits.
- All tasks are independent and can be executed in any order, but the suggested order (gitignore first, then agent files alphabetically by impact) keeps the two repos cleanly separated.
- No pre-commit run is needed after the agent file edits -- `.md` files in `.claude/agents/` are not linted by any hook in this repo.
- After all six commits, run `pre-commit run --all-files` in homelab-infra to confirm the `.gitignore` change does not disturb any existing hooks.
