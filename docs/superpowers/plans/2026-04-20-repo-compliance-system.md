---
schema_type: planning
title: "Repo Compliance System Implementation Plan"
status: draft
owner: core-maintainer
purpose: "Implementation plan for the repo compliance system: standards manifest, six domain agents, expanded devops-deployment-agent, and coordinator skill with interactive and scheduled modes."
component: Development-Tools
source: "docs/superpowers/specs/2026-04-20-repo-compliance-design.md"
tags:
  - compliance
  - agents
  - standards
  - automation
---

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a self-improving multi-agent system that audits any repository against global standards, remediates approved gaps, and captures lessons to improve future runs.

**Architecture:** A standards manifest (YAML) drives six domain agents that audit repos against defined checks. A coordinator skill orchestrates audit, approval, and remediation in interactive mode, and report-only in scheduled mode. A retrospective agent captures patterns across runs and proposes manifest improvements. Tasks 3-9 are independent and can be parallelized.

**Tech Stack:** YAML (manifest and configs), Markdown (agents, skill, templates), GitHub CLI (`gh`) for repo discovery, Claude Code skill/agent system, `pre-commit` for validation.

---

## Phase 1: Standards Foundation

### Task 1: Create standards manifest

**Files:**
- Create: `docs/standards-manifest.yaml`

- [ ] **Step 1: Write the manifest**

```yaml
# docs/standards-manifest.yaml
version: "1.0"
last_updated: "2026-04-20"

# verify field is a hint to the domain agent, not executable DSL.
# Agents interpret it using their own tools (Grep, Read, Glob, Bash).

checks:

  # ── Foundations ─────────────────────────────────────────────────────────────

  - id: FOUND-001
    domain: foundations
    severity: critical
    description: "SECURITY.md present at project root"
    verify: "file_exists: SECURITY.md"
    source_template: "/home/byron/dev/.github/SECURITY.md"
    override_eligible: false

  - id: FOUND-002
    domain: foundations
    severity: critical
    description: "CONTRIBUTING.md present at project root"
    verify: "file_exists: CONTRIBUTING.md"
    source_template: "/home/byron/dev/.github/CONTRIBUTING.md"
    override_eligible: false

  - id: FOUND-003
    domain: foundations
    severity: important
    description: "CHANGELOG.md present at project root"
    verify: "file_exists: CHANGELOG.md"
    override_eligible: true

  - id: FOUND-004
    domain: foundations
    severity: important
    description: "CODEOWNERS present at .github/CODEOWNERS"
    verify: "file_exists: .github/CODEOWNERS"
    override_eligible: true

  - id: FOUND-005
    domain: foundations
    severity: important
    description: ".worktrees/ entry present in .gitignore"
    verify: "content_present: .gitignore, .worktrees/"
    override_eligible: true

  - id: FOUND-006
    domain: foundations
    severity: important
    description: "docs/compliance-reports/ entry present in .gitignore"
    verify: "content_present: .gitignore, docs/compliance-reports/"
    override_eligible: false

  - id: FOUND-007
    domain: foundations
    severity: suggested
    description: "pyproject.toml author email is not a placeholder"
    verify: "metadata_value: pyproject.toml, authors[0].email, not_contains: example.com"
    override_eligible: true

  - id: FOUND-008
    domain: foundations
    severity: suggested
    description: "pyproject.toml requires-python upper bound is <3.15 or unset"
    verify: "metadata_value: pyproject.toml, requires-python, not_contains: <3.13"
    override_eligible: true

  - id: FOUND-009
    domain: foundations
    severity: important
    description: "docs/known-vulnerabilities.md present"
    verify: "file_exists: docs/known-vulnerabilities.md"
    source_template: "/home/byron/dev/.claude/docs/known-vulnerabilities-template.md"
    override_eligible: true

  - id: FOUND-010
    domain: foundations
    severity: important
    description: "AGENTS.md present at project root (not in docs/)"
    verify: "file_exists: AGENTS.md"
    override_eligible: true

  - id: FOUND-011
    domain: foundations
    severity: suggested
    description: "GEMINI.md present at project root (not in docs/)"
    verify: "file_exists: GEMINI.md"
    override_eligible: true

  # ── Toolchain ────────────────────────────────────────────────────────────────

  - id: TOOL-001
    domain: toolchain
    severity: critical
    description: "ruff present in dev dependencies"
    verify: "dep_present: ruff"
    override_eligible: false

  - id: TOOL-002
    domain: toolchain
    severity: important
    description: "black absent from dependencies (replaced by ruff format)"
    verify: "dep_absent: black"
    override_eligible: false

  - id: TOOL-003
    domain: toolchain
    severity: important
    description: "mypy absent from dependencies (replaced by basedpyright)"
    verify: "dep_absent: mypy"
    override_eligible: false

  - id: TOOL-004
    domain: toolchain
    severity: important
    description: "safety absent from dependencies (replaced by pip-audit)"
    verify: "dep_absent: safety"
    override_eligible: false

  - id: TOOL-005
    domain: toolchain
    severity: critical
    description: "basedpyright present in dev dependencies"
    verify: "dep_present: basedpyright"
    override_eligible: true

  - id: TOOL-006
    domain: toolchain
    severity: critical
    description: "pip-audit present in dev dependencies"
    verify: "dep_present: pip-audit"
    override_eligible: false

  - id: TOOL-007
    domain: toolchain
    severity: important
    description: "darglint present in dev dependencies"
    verify: "dep_present: darglint"
    override_eligible: true

  - id: TOOL-008
    domain: toolchain
    severity: important
    description: "interrogate present in dev dependencies"
    verify: "dep_present: interrogate"
    override_eligible: true

  - id: TOOL-009
    domain: toolchain
    severity: important
    description: ".qlty/qlty.toml configuration file present"
    verify: "file_exists: .qlty/qlty.toml"
    override_eligible: true

  - id: TOOL-010
    domain: toolchain
    severity: important
    description: "Ruff rule set contains all PyStrict-aligned codes"
    verify: "ruff_rules_include: BLE,EM,SLF,INP,ISC,PGH,RSE,TID,YTT,FA,T10,G,ANN,TCH,FBT,TRY,ERA,FURB,LOG,ASYNC"
    override_eligible: true

  - id: TOOL-011
    domain: toolchain
    severity: suggested
    description: "Ruff target-version set in pyproject.toml"
    verify: "content_present: pyproject.toml, target-version"
    override_eligible: true

  - id: TOOL-012
    domain: toolchain
    severity: important
    description: "[tool.basedpyright] block present with typeCheckingMode = strict"
    verify: "content_present: pyproject.toml, typeCheckingMode"
    override_eligible: true

  # ── Pre-commit ───────────────────────────────────────────────────────────────

  - id: PC-001
    domain: pre_commit
    severity: critical
    description: ".pre-commit-config.yaml present at project root"
    verify: "file_exists: .pre-commit-config.yaml"
    override_eligible: false

  - id: PC-002
    domain: pre_commit
    severity: critical
    description: "ruff hook present in .pre-commit-config.yaml"
    verify: "hook_present: .pre-commit-config.yaml, ruff"
    override_eligible: false

  - id: PC-003
    domain: pre_commit
    severity: important
    description: "basedpyright hook present in .pre-commit-config.yaml"
    verify: "hook_present: .pre-commit-config.yaml, basedpyright"
    override_eligible: true

  - id: PC-004
    domain: pre_commit
    severity: important
    description: "bandit hook present in .pre-commit-config.yaml"
    verify: "hook_present: .pre-commit-config.yaml, bandit"
    override_eligible: false

  - id: PC-005
    domain: pre_commit
    severity: important
    description: "detect-secrets hook present in .pre-commit-config.yaml"
    verify: "hook_present: .pre-commit-config.yaml, detect-secrets"
    override_eligible: false

  - id: PC-006
    domain: pre_commit
    severity: important
    description: "darglint hook present in .pre-commit-config.yaml"
    verify: "hook_present: .pre-commit-config.yaml, darglint"
    override_eligible: true

  - id: PC-007
    domain: pre_commit
    severity: important
    description: "interrogate hook present in .pre-commit-config.yaml"
    verify: "hook_present: .pre-commit-config.yaml, interrogate"
    override_eligible: true

  - id: PC-008
    domain: pre_commit
    severity: important
    description: "commitizen hook present in .pre-commit-config.yaml"
    verify: "hook_present: .pre-commit-config.yaml, commitizen"
    override_eligible: true

  - id: PC-009
    domain: pre_commit
    severity: suggested
    description: "yamllint hook present in .pre-commit-config.yaml"
    verify: "hook_present: .pre-commit-config.yaml, yamllint"
    override_eligible: true

  - id: PC-010
    domain: pre_commit
    severity: suggested
    description: "markdownlint hook present in .pre-commit-config.yaml"
    verify: "hook_present: .pre-commit-config.yaml, markdownlint"
    override_eligible: true

  - id: PC-011
    domain: pre_commit
    severity: important
    description: "no-em-dash hook present in .pre-commit-config.yaml"
    verify: "hook_present: .pre-commit-config.yaml, no-em-dash"
    override_eligible: false

  - id: PC-012
    domain: pre_commit
    severity: important
    description: "All hook rev fields are 40-character SHA pins, not mutable tags"
    verify: "sha_pinned: .pre-commit-config.yaml, all_rev_fields"
    override_eligible: false

  # ── CI ────────────────────────────────────────────────────────────────────────

  - id: CI-001
    domain: ci
    severity: important
    description: "CI workflow uses org reusable python-ci.yml"
    verify: "content_present: .github/workflows/ci.yml, williaby/.github"
    override_eligible: true

  - id: CI-002
    domain: ci
    severity: important
    description: "Security workflow uses org reusable security analysis workflow"
    verify: "content_present: .github/workflows/security.yml, williaby/.github"
    override_eligible: true

  - id: CI-003
    domain: ci
    severity: important
    description: "SonarCloud integration workflow present"
    verify: "file_exists: .github/workflows/sonarcloud.yml"
    override_eligible: true

  - id: CI-004
    domain: ci
    severity: important
    description: "Qlty coverage workflow present (replaces Codecov)"
    verify: "file_exists: .github/workflows/coverage.yml"
    override_eligible: true

  - id: CI-005
    domain: ci
    severity: critical
    description: "All GitHub Action uses: references are 40-character SHA pins"
    verify: "sha_pinned: .github/workflows/*.yml, all_uses_fields"
    override_eligible: false

  - id: CI-006
    domain: ci
    severity: important
    description: "harden-runner present as first step in all workflow jobs"
    verify: "content_present: .github/workflows/*.yml, harden-runner"
    override_eligible: false

  - id: CI-007
    domain: ci
    severity: important
    description: "Security scan jobs have no continue-on-error: true"
    verify: "content_absent: .github/workflows/security.yml, continue-on-error"
    override_eligible: false

  - id: CI-008
    domain: ci
    severity: suggested
    description: ".github/copilot-instructions.md present"
    verify: "file_exists: .github/copilot-instructions.md"
    override_eligible: true

  # ── Claude and Docs ──────────────────────────────────────────────────────────

  - id: CLAUDE-001
    domain: claude_docs
    severity: important
    description: "Project CLAUDE.md present at project root"
    verify: "file_exists: CLAUDE.md"
    override_eligible: true

  - id: CLAUDE-002
    domain: claude_docs
    severity: important
    description: "CLAUDE.md contains Model Selection section"
    verify: "section_present: CLAUDE.md, Model Selection"
    override_eligible: true

  - id: CLAUDE-003
    domain: claude_docs
    severity: important
    description: "CLAUDE.md contains Response-Aware Development (RAD) section"
    verify: "section_present: CLAUDE.md, Response-Aware Development"
    override_eligible: true

  - id: CLAUDE-004
    domain: claude_docs
    severity: suggested
    description: "CLAUDE.md contains cross-references to global rule files"
    verify: "content_present: CLAUDE.md, ~/.claude/.claude/rules/"
    override_eligible: true

  - id: CLAUDE-005
    domain: claude_docs
    severity: important
    description: ".claude/settings.json present with permissions block"
    verify: "file_exists: .claude/settings.json"
    override_eligible: true

  - id: CLAUDE-006
    domain: claude_docs
    severity: important
    description: "CLAUDE.md Essential Commands do not reference removed tools (black, mypy, safety)"
    verify: "content_absent_any: CLAUDE.md, black,mypy,safety check"
    override_eligible: true

  - id: CLAUDE-007
    domain: claude_docs
    severity: critical
    description: "No em-dash characters in docs/**/*.md files"
    verify: "em_dash_absent: docs/**/*.md"
    override_eligible: false

  - id: CLAUDE-008
    domain: claude_docs
    severity: suggested
    description: "No AI blacklist pattern words in formal docs (leverage, seamless, robust, comprehensive, holistic, crucial, pivotal, vital)"
    verify: "ai_patterns_absent: docs/**/*.md"
    override_eligible: true
```

- [ ] **Step 2: Validate YAML syntax**

```bash
cd /home/byron/dev/.claude
python3 -c "import yaml; yaml.safe_load(open('docs/standards-manifest.yaml'))" && echo "YAML valid"
```

Expected: `YAML valid`

- [ ] **Step 3: Commit**

```bash
git add docs/standards-manifest.yaml
git commit -m "feat(compliance): add standards manifest with 52 checks across 5 domains"
```

---

### Task 2: Create support files

**Files:**
- Create: `docs/compliance-exclusions.yaml`
- Create: `docs/compliance-reports/.gitignore`
- Create: `.claude/compliance-overrides.md`

- [ ] **Step 1: Write compliance-exclusions.yaml**

```yaml
# docs/compliance-exclusions.yaml
# Repos excluded from scheduled compliance sweeps.
# 'repo' matches against the repo slug (basename of git remote or local dir).

exclusions:
  - repo: cookiecutter-python-template
    reason: "template source, not a generated project"
  - repo: .claude
    reason: "this repo is the standards source, not a downstream project"
```

- [ ] **Step 2: Write compliance-reports/.gitignore**

Create `docs/compliance-reports/.gitignore` with this content:

```
# All compliance reports are local only -- never pushed.
*
!.gitignore
```

Also create the `lessons-learned/` subdirectory placeholder:

```bash
mkdir -p /home/byron/dev/.claude/docs/compliance-reports/lessons-learned
touch /home/byron/dev/.claude/docs/compliance-reports/lessons-learned/.gitkeep
```

Add to .gitignore so the .gitkeep is also excluded -- the wildcard already covers it.

- [ ] **Step 3: Write compliance-overrides.md template**

Create `.claude/compliance-overrides.md` with:

```markdown
---
schema_type: internal
title: Compliance Overrides
status: published
owner: engineering
tags: [compliance]
purpose: Documents intentional deviations from global standards for this repository. Each entry suppresses the named check during compliance audits.
---

## Compliance Overrides

Add one row per intentional deviation. Only checks marked `override_eligible: true`
in the standards manifest can be suppressed here. Critical security checks
(`override_eligible: false`) are always enforced regardless of entries here.

| Check ID | Reason | Approved By | Date |
|----------|--------|-------------|------|
| | | | |

## How to Add an Override

1. Find the check ID in `~/.claude/docs/standards-manifest.yaml`
2. Confirm `override_eligible: true` for that check
3. Add a row above with the check ID, business reason, your name, and today's date
4. Commit the change with message: `chore(compliance): add override for <CHECK-ID>`
```

- [ ] **Step 4: Validate all YAML files**

```bash
cd /home/byron/dev/.claude
python3 -c "import yaml; yaml.safe_load(open('docs/compliance-exclusions.yaml'))" && echo "exclusions: YAML valid"
```

Expected: `exclusions: YAML valid`

- [ ] **Step 5: Run pre-commit**

```bash
cd /home/byron/dev/.claude
uv run pre-commit run --all-files
```

Expected: all hooks pass (frontmatter validation will check compliance-overrides.md)

- [ ] **Step 6: Commit**

```bash
git add docs/compliance-exclusions.yaml docs/compliance-reports/ .claude/compliance-overrides.md
git commit -m "feat(compliance): add support files -- exclusions, report gitignore, override template"
```

---

## Phase 2: Domain Agents

> Tasks 3-8 are independent. They can be executed in parallel.

### Task 3: Create repo-foundations-auditor agent

**Files:**
- Create: `.claude/agents/repo-foundations-auditor.md`

- [ ] **Step 1: Write the agent file**

```markdown
---
name: repo-foundations-auditor
description: Repository foundations compliance auditor and remediator. Checks OpenSSF required files (SECURITY.md, CONTRIBUTING.md, CHANGELOG.md), CODEOWNERS, .gitignore entries, pyproject.toml metadata, and docs structure against FOUND-* checks in the standards manifest. In audit mode returns a findings list. In remediation mode creates or patches files.
model: sonnet
tools: ["Read", "Write", "Edit", "Bash", "Grep", "Glob"]
---

# Repo Foundations Auditor

Compliance auditor and remediator for repository foundation files: OpenSSF required files, .gitignore, pyproject.toml metadata, CODEOWNERS, and docs structure.

## Core Responsibilities

- **Audit mode**: Evaluate each FOUND-* check passed by the coordinator against the target repo; return a structured findings list with pass/fail status and current state
- **Remediation mode**: For each approved finding, create missing files from source templates, patch pyproject.toml metadata values, and append missing .gitignore entries
- **Override awareness**: Skip any check whose ID is listed in the repo's `.claude/compliance-overrides.md` with a valid entry

## Audit Workflow

Receive the coordinator prompt containing: target repo path, list of FOUND-* checks to evaluate, and override entries. For each check:

- `file_exists` checks: use Glob to confirm the file is present at the specified path
- `content_present` checks: use Grep to confirm the string appears in the target file
- `content_absent` checks: use Grep to confirm the string is absent
- `metadata_value` checks: Read pyproject.toml and compare the field value against the condition

Return findings as a structured list with fields: id, severity, description, status (pass or fail), current_value (what was found or not found).

## Remediation Workflow

Receive the approved findings list from the coordinator. For each failing check:

- `file_exists` with source_template: Read the template, adapt project-specific fields (project name, author), Write to the target path
- `content_present` with .gitignore: append the missing entry using Edit
- `metadata_value` for pyproject.toml: patch the specific field using Edit; preserve surrounding context

Report each action taken: file created, file patched, or entry appended.

## Output Format

Audit mode findings (emit one block per failing check):

```
FINDING:
  id: FOUND-001
  severity: critical
  description: SECURITY.md absent from project root
  status: fail
  current_value: file not found
```

Remediation mode (emit one line per action):

```
ACTION: Created SECURITY.md from template /home/byron/dev/.github/SECURITY.md
ACTION: Appended .worktrees/ to .gitignore
```

## Use Cases

Invoked by the repo-compliance coordinator skill for the foundations domain in both audit and remediation modes.
```

- [ ] **Step 2: Run pre-commit to validate frontmatter**

```bash
cd /home/byron/dev/.claude
uv run pre-commit run validate-front-matter --files .claude/agents/repo-foundations-auditor.md
```

Expected: `Validate documentation front matter.....Passed`

- [ ] **Step 3: Commit**

```bash
git add .claude/agents/repo-foundations-auditor.md
git commit -m "feat(compliance): add repo-foundations-auditor agent"
```

---

### Task 4: Create python-toolchain-auditor agent

**Files:**
- Create: `.claude/agents/python-toolchain-auditor.md`

- [ ] **Step 1: Write the agent file**

```markdown
---
name: python-toolchain-auditor
description: Python toolchain compliance auditor and remediator. Checks dev dependency presence/absence (ruff, basedpyright, pip-audit, darglint, interrogate), Ruff rule set completeness against PyStrict-aligned codes, BasedPyright config block, qlty config, and target-version setting against TOOL-* checks in the standards manifest.
model: sonnet
tools: ["Read", "Write", "Edit", "Bash", "Grep", "Glob"]
---

# Python Toolchain Auditor

Compliance auditor and remediator for Python project toolchain configuration: dev dependencies, Ruff rules, BasedPyright config, qlty setup, and related pyproject.toml settings.

## Core Responsibilities

- **Audit mode**: Evaluate each TOOL-* check against the target repo's pyproject.toml and config files; return findings with pass/fail and current state
- **Remediation mode**: Edit pyproject.toml to add or remove dependencies and config blocks; does NOT resolve resulting lint or type errors (flags those as follow-on work)
- **Override awareness**: Skip checks listed in `.claude/compliance-overrides.md`

## Audit Workflow

Receive the coordinator prompt with: target repo path, list of TOOL-* checks, and override entries. For each check:

- `dep_present` checks: Read pyproject.toml, search dev dependency sections for the package name
- `dep_absent` checks: Confirm the package name does not appear in any dependency section
- `ruff_rules_include` checks: Read the `[tool.ruff.lint]` select list; diff it against the required codes listed in the verify field; report which codes are missing
- `content_present` checks on pyproject.toml: Grep for the string in pyproject.toml
- `file_exists` checks: use Glob

For `ruff_rules_include`, the required PyStrict-aligned codes are:
`BLE, EM, SLF, INP, ISC, PGH, RSE, TID, YTT, FA, T10, G, ANN, TCH, FBT, TRY, ERA, FURB, LOG, ASYNC`

Return findings with: id, severity, description, status, current_value (list of missing codes for ruff checks, package name for dep checks).

## Remediation Workflow

For approved findings:

- `dep_absent` (remove forbidden dep): Remove the dep line from pyproject.toml using Edit
- `dep_present` (add missing dep): Add the dep to the appropriate dev section using Edit
- Missing Ruff codes: Append the missing codes to the `select` list in `[tool.ruff.lint]`
- Missing `[tool.basedpyright]` block: Append the following block to pyproject.toml:

```toml
[tool.basedpyright]
pythonVersion = "3.11"
pythonPlatform = "All"
typeCheckingMode = "strict"
strictListInference = true
strictDictionaryInference = true
strictSetInference = true
```

- Missing `.qlty/qlty.toml`: Create it with:

```toml
[plugins]
enabled = ["ruff", "basedpyright", "bandit"]
```

After remediation, emit: "NOTE: Adding/removing dependencies and enabling new Ruff rules will surface new violations. Run the full toolchain and fix violations before committing. Do not add noqa or type: ignore suppressions."

## Output Format

Same structure as repo-foundations-auditor: FINDING blocks in audit mode, ACTION lines in remediation mode.

## Use Cases

Invoked by the repo-compliance coordinator for the toolchain domain in both modes.
```

- [ ] **Step 2: Validate frontmatter**

```bash
cd /home/byron/dev/.claude
uv run pre-commit run validate-front-matter --files .claude/agents/python-toolchain-auditor.md
```

Expected: `Validate documentation front matter.....Passed`

- [ ] **Step 3: Commit**

```bash
git add .claude/agents/python-toolchain-auditor.md
git commit -m "feat(compliance): add python-toolchain-auditor agent"
```

---

### Task 5: Create pre-commit-auditor agent

**Files:**
- Create: `.claude/agents/pre-commit-auditor.md`

- [ ] **Step 1: Write the agent file**

```markdown
---
name: pre-commit-auditor
description: Pre-commit configuration compliance auditor and remediator. Checks .pre-commit-config.yaml presence, required hook inventory (ruff, basedpyright, bandit, detect-secrets, darglint, interrogate, commitizen, yamllint, markdownlint, no-em-dash), and SHA pinning of all rev fields against PC-* checks in the standards manifest.
model: sonnet
tools: ["Read", "Write", "Edit", "Bash", "Grep", "Glob"]
---

# Pre-commit Auditor

Compliance auditor and remediator for `.pre-commit-config.yaml`: hook presence, hook inventory against the required list, and SHA pinning of all rev fields.

## Core Responsibilities

- **Audit mode**: Check for .pre-commit-config.yaml; if present, inventory hooks against PC-* checks; verify all rev fields are 40-character hex SHAs
- **Remediation mode**: Create .pre-commit-config.yaml if absent; patch in missing hooks; resolve rev SHAs from GitHub releases at run time
- **Override awareness**: Skip checks listed in `.claude/compliance-overrides.md`

## Audit Workflow

For PC-001 (`file_exists`): use Glob to check for `.pre-commit-config.yaml`. If absent, report all other PC-* checks as not-evaluated (the file must exist before hooks can be checked).

For `hook_present` checks: Read `.pre-commit-config.yaml`; search for the hook id string in the repos/hooks list.

For PC-012 (`sha_pinned`): Read all `rev:` lines in `.pre-commit-config.yaml`. A valid SHA pin is exactly 40 hexadecimal characters. Flag any rev that is a version tag (starts with `v` or contains only digits and dots).

Return findings with: id, severity, description, status, current_value (list of missing hooks or list of unpinned revs).

## Remediation Workflow

**If .pre-commit-config.yaml is absent:** Create the file with the full required hook set. For each hook, resolve the current SHA by running:

```bash
git ls-remote https://github.com/<owner>/<repo>.git refs/tags/<version> | cut -f1
```

The required hook repositories and their hook IDs are:
- `https://github.com/astral-sh/ruff-pre-commit`: `ruff`, `ruff-format`
- `https://github.com/DetachHead/basedpyright`: `basedpyright`
- `https://github.com/PyCQA/bandit`: `bandit`
- `https://github.com/Yelp/detect-secrets`: `detect-secrets`
- `https://github.com/terrencepreilly/darglint`: `darglint`
- `https://github.com/econchick/interrogate`: `interrogate`
- `https://github.com/commitizen-tools/commitizen`: `commitizen`
- `https://github.com/adrienverge/yamllint`: `yamllint`
- `https://github.com/igorshubovych/markdownlint-cli`: `markdownlint`
- local repo with pygrep entry for em-dash (`\u2014`)

**If .pre-commit-config.yaml exists but hooks are missing:** Append only the missing hook entries; do not rewrite the file.

**For unpinned rev fields:** Resolve the SHA for the current tag and replace using Edit. Add the version as a comment on the same line: `rev: <40-char-sha>  # v1.2.3`

## Output Format

FINDING blocks in audit mode, ACTION lines in remediation mode. Include the full list of missing or unpinned items in the current_value field.

## Use Cases

Invoked by the repo-compliance coordinator for the pre_commit domain in both modes.
```

- [ ] **Step 2: Validate frontmatter**

```bash
cd /home/byron/dev/.claude
uv run pre-commit run validate-front-matter --files .claude/agents/pre-commit-auditor.md
```

Expected: `Validate documentation front matter.....Passed`

- [ ] **Step 3: Commit**

```bash
git add .claude/agents/pre-commit-auditor.md
git commit -m "feat(compliance): add pre-commit-auditor agent"
```

---

### Task 6: Create claude-docs-auditor agent

**Files:**
- Create: `.claude/agents/claude-docs-auditor.md`

- [ ] **Step 1: Write the agent file**

```markdown
---
name: claude-docs-auditor
description: Claude configuration and documentation compliance auditor and remediator. Checks CLAUDE.md section presence (Model Selection, RAD, cross-references), .claude/settings.json, AGENTS.md and GEMINI.md file locations, and delegates em-dash and AI pattern scanning to writing-style-editor. Covers CLAUDE-* checks in the standards manifest.
model: sonnet
tools: ["Read", "Write", "Edit", "Bash", "Grep", "Glob"]
---

# Claude Docs Auditor

Compliance auditor and remediator for Claude configuration and project documentation: CLAUDE.md sections, `.claude/settings.json`, agent runner file locations, and writing quality checks.

## Core Responsibilities

- **Audit mode**: Check CLAUDE-* items from the manifest; delegate em-dash and AI pattern checks to `writing-style-editor`; return unified findings list
- **Remediation mode**: Append missing CLAUDE.md sections, create .claude/settings.json, relocate AGENTS.md/GEMINI.md to project root, apply writing fixes
- **Override awareness**: Skip checks listed in `.claude/compliance-overrides.md`

## Audit Workflow

For `section_present` checks on CLAUDE.md: Read the file and search for the section heading using Grep. A section is present if a `## <name>` heading exists anywhere in the file.

For `file_exists` checks (CLAUDE.md, .claude/settings.json): use Glob.

For AGENTS.md/GEMINI.md location: Glob for both `AGENTS.md` and `docs/**/AGENTS.md`. If found only in a subdirectory and not at root, report FOUND-010/011 as failing.

For CLAUDE-006 (Essential Commands reference removed tools): Grep CLAUDE.md for `black`, `mypy`, and `safety check`. Any match is a failure.

For CLAUDE-007 (em-dash scan) and CLAUDE-008 (AI patterns): invoke `writing-style-editor` as a subagent with the following prompt: "Scan all .md files in docs/, .github/, and the project root for em-dash characters and AI blacklist pattern words (leverage, seamless, robust, comprehensive, holistic, crucial, pivotal, vital). Return a list of file paths and line numbers for each match. Audit only -- do not edit any files."

Merge the writing-style-editor results into your findings list under CLAUDE-007 and CLAUDE-008.

## Remediation Workflow

**Missing CLAUDE.md sections:** Append the following blocks. Read the current CLAUDE.md first; do not duplicate sections that already exist.

For missing Model Selection section, append:
```markdown
## Model Selection

| Task type | Model | When |
| --- | --- | --- |
| Architecture, planning, ADRs | Opus 4.7 | Multi-step decisions, deep code review |
| Standard development | Sonnet 4.6 | Most coding and editing |
| Read-only exploration | Haiku 4.5 | File scanning, quick lookups |
```

For missing RAD section, append:
```markdown
## Response-Aware Development (RAD)

Tag assumptions that could cause production failures using `#CRITICAL`, `#ASSUME`,
and `#EDGE` comment markers paired with `#VERIFY` instructions. Mandatory categories:
timing dependencies, external resources, data integrity, concurrency, security,
payment and financial.

See `docs/response-aware-development.md` for full tagging syntax and examples.
```

**Missing .claude/settings.json:** Create with a minimal permissions block:
```json
{
  "permissions": {
    "allow": []
  }
}
```

Note: the allow list should be populated based on the project's actual tool usage. Flag this to the user after creation.

**Misplaced AGENTS.md/GEMINI.md:** Move from current location to project root using Bash `mv`. Update any internal cross-references in the moved file.

**Em-dash fixes (CLAUDE-007):** Use Edit to replace each em-dash with a comma, semicolon, colon, or restructured sentence as context requires.

**AI pattern fixes (CLAUDE-008):** Replace flagged words with specific, measurable language. Use Edit per file.

## Output Format

FINDING blocks in audit mode, ACTION lines in remediation mode. For CLAUDE-007 and CLAUDE-008, include file path and line number in current_value.

## Use Cases

Invoked by the repo-compliance coordinator for the claude_docs domain in both modes.
```

- [ ] **Step 2: Validate frontmatter**

```bash
cd /home/byron/dev/.claude
uv run pre-commit run validate-front-matter --files .claude/agents/claude-docs-auditor.md
```

Expected: `Validate documentation front matter.....Passed`

- [ ] **Step 3: Commit**

```bash
git add .claude/agents/claude-docs-auditor.md
git commit -m "feat(compliance): add claude-docs-auditor agent"
```

---

### Task 7: Create general-compliance-auditor agent

**Files:**
- Create: `.claude/agents/general-compliance-auditor.md`

- [ ] **Step 1: Write the agent file**

```markdown
---
name: general-compliance-auditor
description: Freeform compliance auditor for gaps outside the standards manifest. Receives the manifest check IDs already covered by domain agents as a negative filter, then performs a broad LLM review of the repo against global standards. Returns unclassified candidate findings with proposed domain and severity for retrospective review. Audit only -- no remediation mode.
model: sonnet
tools: ["Read", "Bash", "Grep", "Glob"]
---

# General Compliance Auditor

Freeform auditor that identifies compliance gaps not yet captured in the standards manifest. Operates after domain agents so it can focus on what they did not cover.

## Core Responsibilities

- **Audit only**: Perform a broad review of the repo for any deviation from global standards in `~/.claude/CLAUDE.md`, `~/.claude/.claude/rules/`, and `~/.claude/.claude/standards/`
- **Negative filtering**: Use the covered check IDs passed by the coordinator to avoid re-flagging what domain agents already found
- **Candidate generation**: Output findings tagged `unclassified` with a proposed domain and severity -- these are candidates for the retrospective, not confirmed violations

## Audit Workflow

Receive from the coordinator: target repo path, list of check IDs already covered by domain agents, and any override entries.

1. Read `~/.claude/CLAUDE.md` to load current global standards
2. Read each rule file in `~/.claude/.claude/rules/` (python.md, git-workflow.md, pre-commit.md, testing.md, writing.md, supervisor.md, settings-and-permissions.md)
3. Read `~/.claude/.claude/standards/packages.md`
4. Scan the target repo structure: README.md, pyproject.toml, .github/, src/, tests/, docs/
5. Compare what you observe against the standards, excluding anything covered by the provided check IDs
6. For each gap found, propose: a check ID candidate (e.g., FOUND-012), domain, severity, description, and how to verify it

Return all candidates clearly labeled as unclassified. Do not assert they are definitive violations -- the retrospective agent will pattern-match across repos to determine if they warrant manifest entries.

## Output Format

```
CANDIDATE:
  proposed_id: FOUND-012
  domain: foundations
  severity: suggested
  description: ".editorconfig absent from project root"
  observed: "no .editorconfig found; global standards do not require it but it is present in all other reviewed repos"
  verify_hint: "file_exists: .editorconfig"
```

## Use Cases

Invoked by the repo-compliance coordinator after domain agents complete. Not intended for direct user invocation. Audit mode only -- passing remediation mode has no effect.
```

- [ ] **Step 2: Validate frontmatter**

```bash
cd /home/byron/dev/.claude
uv run pre-commit run validate-front-matter --files .claude/agents/general-compliance-auditor.md
```

Expected: `Validate documentation front matter.....Passed`

- [ ] **Step 3: Commit**

```bash
git add .claude/agents/general-compliance-auditor.md
git commit -m "feat(compliance): add general-compliance-auditor agent"
```

---

### Task 8: Create compliance-retrospective agent

**Files:**
- Create: `.claude/agents/compliance-retrospective.md`

- [ ] **Step 1: Write the agent file**

```markdown
---
name: compliance-retrospective
description: Post-run compliance retrospective agent. Reads all findings from the current session (domain agent findings plus general-compliance-auditor candidates), groups unclassified candidates by pattern, identifies checks appearing in three or more repos as manifest candidates, and writes a lessons-learned document with proposed manifest entries as ready-to-paste YAML snippets.
model: sonnet
tools: ["Read", "Write", "Bash", "Grep", "Glob"]
---

# Compliance Retrospective

Post-run agent that synthesizes compliance findings across all repos reviewed in a session into a lessons-learned document with actionable manifest improvement proposals.

## Core Responsibilities

- **Pattern detection**: Group unclassified candidates from the general auditor by description similarity; any pattern appearing in three or more repos is flagged as a manifest candidate
- **Manifest proposals**: Format each candidate as a ready-to-paste YAML snippet following the standards-manifest.yaml schema
- **Scope expansion flags**: Identify domain agents that should expand their scope based on patterns observed
- **Document output**: Write one lessons-learned file per session to `docs/compliance-reports/lessons-learned/YYYY-MM-DD.md`

## Workflow

Receive from the coordinator: session date, list of repos reviewed, all domain agent findings, and all general-compliance-auditor candidates.

1. Summarize: repos reviewed count, total findings by severity, overrides applied
2. Group unclassified candidates by description similarity (same file missing, same config gap, same pattern)
3. Any group appearing in 3+ repos: promote to manifest candidate with a proposed check entry
4. Review domain findings for patterns (e.g., CI-005 failing in 80% of repos = high-priority remediation target)
5. Note any domain where the general auditor found many items not in the manifest = scope expansion candidate
6. Write the lessons-learned doc using the template below

## Output Document Template

Write to `docs/compliance-reports/lessons-learned/<YYYY-MM-DD>.md`:

```markdown
# Compliance Retrospective: <YYYY-MM-DD>

## Session Summary

| Metric | Value |
|--------|-------|
| Repos reviewed | N |
| Total findings (net of overrides) | N |
| Critical | N |
| Important | N |
| Suggested | N |
| Unclassified candidates | N |

## Patterns Observed

<List each pattern with repo count. Example: ".editorconfig absent -- 5 of 7 repos">

## Proposed Manifest Additions

For each pattern promoted to candidate status, include a ready-to-paste YAML block:

```yaml
- id: FOUND-012
  domain: foundations
  severity: suggested
  description: ".editorconfig absent from project root"
  verify: "file_exists: .editorconfig"
  override_eligible: true
```

## Agent Scope Expansion Candidates

<List any domain agent and the type of check it should add. Example: "python-toolchain-auditor: consider adding a check for [tool.interrogate] fail-under threshold value (currently only checks presence).">

## High-Frequency Existing Checks

<List checks from the manifest that failed in 50% or more of repos reviewed this session. These warrant prioritized remediation.>
```

## Use Cases

Invoked by the repo-compliance coordinator as the final step after all repos in a session have been audited. Runs in both interactive and scheduled modes.
```

- [ ] **Step 2: Validate frontmatter**

```bash
cd /home/byron/dev/.claude
uv run pre-commit run validate-front-matter --files .claude/agents/compliance-retrospective.md
```

Expected: `Validate documentation front matter.....Passed`

- [ ] **Step 3: Commit**

```bash
git add .claude/agents/compliance-retrospective.md
git commit -m "feat(compliance): add compliance-retrospective agent"
```

---

## Phase 3: Expand devops-deployment-agent

### Task 9: Add CI compliance audit mode to devops-deployment-agent

**Files:**
- Modify: `.claude/agents/devops-deployment-agent.md`

- [ ] **Step 1: Read the current file**

Read `.claude/agents/devops-deployment-agent.md` in full before editing.

- [ ] **Step 2: Add CI Compliance Audit section**

Append the following section before the `## Use Cases` line:

```markdown
## CI Compliance Audit Mode

When invoked by the repo-compliance coordinator with audit or remediation mode context, this agent evaluates or remediates CI-* checks from the standards manifest.

### Audit Workflow

Receive from the coordinator: target repo path, list of CI-* checks to evaluate, and override entries. For each check:

- `content_present` checks on workflow files: use Grep across `.github/workflows/*.yml`
- `file_exists` checks: use Glob
- `sha_pinned` checks: Read each workflow file; find all `uses:` lines; a valid pin is `owner/repo@<40-hex-chars>`. Flag any ref using a version tag (e.g., `@v4`, `@main`, `@master`)
- `content_absent` checks: use Grep to confirm the string does not appear

For CI-006 (harden-runner): read each job in each workflow file; confirm `step-security/harden-runner` appears as the first step. Report each job that is missing it.

Return FINDING blocks for each failing check, including the workflow file path and line number in current_value where applicable.

### Remediation Workflow

For approved CI findings:

**CI-001 to CI-004 (reusable workflow migration):** Replace inline workflow content with caller stubs. The org reusable workflows are at `williaby/.github`. Stub format:

```yaml
# .github/workflows/ci.yml
jobs:
  ci:
    uses: williaby/.github/.github/workflows/python-ci.yml@main
    with:
      python-versions: '["3.11", "3.12"]'
    secrets:
      CODECOV_TOKEN: ${{ secrets.CODECOV_TOKEN }}
```

**CI-005 (SHA pinning):** For each unpinned `uses:` reference, resolve the SHA by running:

```bash
git ls-remote https://github.com/<owner>/<repo>.git refs/tags/<version> | cut -f1
```

Replace the tag ref with the 40-char SHA and add the version as a comment: `@<sha>  # v1.2.3`

**CI-006 (harden-runner):** Insert as the first step in each non-compliant job:

```yaml
- name: Harden runner
  uses: step-security/harden-runner@<current-sha>  # v2.x.x
  with:
    egress-policy: audit
```

**CI-007 (blocking security scan):** Remove `continue-on-error: true` from security workflow jobs using Edit.

**CI-008 (copilot-instructions.md):** Create `.github/copilot-instructions.md` with:

```markdown
# GitHub Copilot Code Review Instructions

Focus on: business logic correctness, error handling completeness, edge cases,
concurrency issues, and security logic flaws.

Exclude from review: code style, formatting, and whitespace. These are enforced
by pre-commit hooks and ruff -- do not flag them.
```

### Output Format

FINDING blocks in audit mode (include file path and line number in current_value). ACTION lines in remediation mode.
```

- [ ] **Step 3: Validate frontmatter**

```bash
cd /home/byron/dev/.claude
uv run pre-commit run validate-front-matter --files .claude/agents/devops-deployment-agent.md
```

Expected: `Validate documentation front matter.....Passed`

- [ ] **Step 4: Commit**

```bash
git add .claude/agents/devops-deployment-agent.md
git commit -m "feat(compliance): add CI compliance audit mode to devops-deployment-agent"
```

---

## Phase 4: Coordinator Skill

### Task 10: Create repo-compliance skill entry point

**Files:**
- Create: `.claude/skills/repo-compliance/SKILL.md`

- [ ] **Step 1: Create the skill directory and SKILL.md**

```bash
mkdir -p /home/byron/dev/.claude/.claude/skills/repo-compliance/workflows
mkdir -p /home/byron/dev/.claude/.claude/skills/repo-compliance/templates
```

Write `.claude/skills/repo-compliance/SKILL.md`:

```markdown
---
description: >
  Repo compliance coordinator. Audits any repository against the standards
  manifest, presents findings by severity, applies approved remediations, and
  runs the retrospective. Interactive mode: full audit-approve-remediate-PR
  flow. Scheduled mode: report-only for org-wide sweeps.
  Triggers on: /repo-audit, repo audit, compliance check, standards audit.
tools: ["Read", "Write", "Edit", "Bash", "Grep", "Glob", "Agent", "TodoWrite"]
---

# Repo Compliance Skill

Orchestrates a full compliance audit and optional remediation run against any repository.

## Invocation

```
/repo-audit                          # interactive mode, current directory
/repo-audit /path/to/repo            # interactive mode, specified path
/repo-audit --scheduled              # report-only mode for cron trigger
```

## Mode Selection

- Default (no flag): interactive mode -- see `workflows/interactive-mode.md`
- `--scheduled`: scheduled mode -- see `workflows/scheduled-mode.md`

## Workflow

Follow the appropriate workflow file for the selected mode. Both modes share these steps:

1. Load `~/.claude/docs/standards-manifest.yaml`
2. Load target repo's `.claude/compliance-overrides.md` (if present)
3. Dispatch domain agents in parallel (see workflow file for agent list and prompts)
4. Merge findings, filter overrides, sort by severity
5. Run `compliance-retrospective` after all repos are processed

## Domain Agents

| Domain | Agent | Checks |
|--------|-------|--------|
| foundations | `repo-foundations-auditor` | FOUND-* |
| toolchain | `python-toolchain-auditor` | TOOL-* |
| pre_commit | `pre-commit-auditor` | PC-* |
| ci | `devops-deployment-agent` (CI audit mode) | CI-* |
| claude_docs | `claude-docs-auditor` | CLAUDE-* |
| general | `general-compliance-auditor` | unclassified |

## Coordinator Prompt Template

When dispatching each domain agent, include in the prompt:

```
Mode: <audit|remediation>
Target repo: <absolute path>
Manifest checks for this domain:
<paste the relevant check entries from standards-manifest.yaml>
Override entries (skip these check IDs):
<paste entries from compliance-overrides.md, or "none">
```
```

- [ ] **Step 2: Validate skill frontmatter**

```bash
cd /home/byron/dev/.claude
uv run pre-commit run validate-front-matter --files .claude/skills/repo-compliance/SKILL.md
```

Expected: `Validate documentation front matter.....Passed`

- [ ] **Step 3: Commit**

```bash
git add .claude/skills/repo-compliance/SKILL.md
git commit -m "feat(compliance): add repo-compliance skill entry point"
```

---

### Task 11: Write interactive mode workflow

**Files:**
- Create: `.claude/skills/repo-compliance/workflows/interactive-mode.md`

- [ ] **Step 1: Write the workflow file**

```markdown
# Interactive Mode Workflow

Full audit-approve-remediate-PR flow for a single target repo.

## Steps

### 1. Setup

```bash
# Resolve target repo path
TARGET_REPO="${1:-$(pwd)}"
cd "$TARGET_REPO"
git status  # confirm it is a git repo
```

Read `~/.claude/docs/standards-manifest.yaml`.
Read `$TARGET_REPO/.claude/compliance-overrides.md` if it exists; extract the Check ID column.

### 2. Parallel Audit Dispatch

Use TodoWrite to track agent dispatch. Dispatch all six domain agents in parallel using the Agent tool. Pass each agent the coordinator prompt template from SKILL.md populated with:
- Mode: audit
- Target repo: resolved absolute path
- Manifest checks: the subset for that domain
- Override entries: IDs from compliance-overrides.md

Agents to dispatch simultaneously:
- `repo-foundations-auditor` (FOUND-* checks)
- `python-toolchain-auditor` (TOOL-* checks)
- `pre-commit-auditor` (PC-* checks)
- `devops-deployment-agent` in CI audit mode (CI-* checks)
- `claude-docs-auditor` (CLAUDE-* checks)
- `general-compliance-auditor` (all checks as negative filter, freeform review)

### 3. Merge and Present Findings

Collect all FINDING blocks. Filter out any finding whose ID is in the override list. Sort by severity: Critical first, then Important, then Suggested. Present unclassified candidates in a separate section.

Present findings in this format:

```
COMPLIANCE AUDIT: <repo-name>
Standards version: <manifest last_updated>
Overrides applied: N

CRITICAL (N findings)
  [FOUND-001] SECURITY.md absent from project root
  [CI-005] 6 action refs use mutable tags instead of SHA pins

IMPORTANT (N findings)
  [FOUND-005] .worktrees/ absent from .gitignore
  ...

SUGGESTED (N findings)
  ...

UNCLASSIFIED CANDIDATES (N items -- for retrospective review)
  [candidate] .editorconfig absent -- proposed domain: foundations, severity: suggested
  ...
```

### 4. Approval Loop

Ask: "Which findings would you like to remediate? Options:
  A) All critical and important
  B) All critical, important, and suggested
  C) Select specific check IDs (comma-separated)
  D) Skip remediation -- report only"

Wait for user response. Parse the selection into an approved findings list.

### 5. Remediation Dispatch

For each approved finding, route to the owning domain agent in remediation mode. Use the same coordinator prompt template with Mode: remediation and only the approved findings list.

Dispatch agents by domain in dependency order:
1. `repo-foundations-auditor` (foundations -- no dependencies)
2. `python-toolchain-auditor` (toolchain -- no dependencies)
3. `pre-commit-auditor` (pre_commit -- depends on toolchain being correct)
4. `devops-deployment-agent` CI audit mode (ci -- no dependencies)
5. `claude-docs-auditor` (claude_docs -- no dependencies)

Collect ACTION lines from each agent and present a summary of all changes made.

### 6. Open PR

```bash
cd "$TARGET_REPO"
git add -A
git commit -m "chore(compliance): apply standards alignment from repo-compliance audit

Remediations applied:
<list check IDs that were remediated>

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"

git push -u origin HEAD

gh pr create \
  --title "chore(compliance): standards alignment $(date +%Y-%m-%d)" \
  --body "$(cat <<'EOF'
## Compliance Remediations

Applied by the repo-compliance system against standards manifest v<version>.

### Changes Made
<list of ACTION lines>

### Checks Resolved
<list of check IDs>

### Remaining (not approved for this run)
<list of skipped findings>
EOF
)"
```

### 7. Retrospective

Dispatch `compliance-retrospective` with: session date, target repo path, all domain findings, all unclassified candidates.

After it writes the lessons-learned doc, print:
"Retrospective written to docs/compliance-reports/lessons-learned/<date>.md -- review before the next scheduled run."
```

- [ ] **Step 2: Commit**

```bash
git add .claude/skills/repo-compliance/workflows/interactive-mode.md
git commit -m "feat(compliance): add interactive mode workflow"
```

---

### Task 12: Write scheduled mode workflow and report templates

**Files:**
- Create: `.claude/skills/repo-compliance/workflows/scheduled-mode.md`
- Create: `.claude/skills/repo-compliance/templates/compliance-report.md`

- [ ] **Step 1: Write scheduled-mode.md**

```markdown
# Scheduled Mode Workflow

Report-only org-wide sweep. No approval loop and no remediation.

## Steps

### 1. Discover Repos

```bash
# Local repos
find ~/dev -maxdepth 2 -name ".git" -type d \
  | grep -v "/.worktrees/" \
  | xargs -I{} dirname {} \
  | sort > /tmp/local-repos.txt

# Remote repos -- williaby org
gh repo list williaby --limit 100 --json nameWithOwner,sshUrl \
  | jq -r '.[].sshUrl' >> /tmp/remote-repos.txt

# Remote repos -- ByronWilliamsCPA org
gh repo list ByronWilliamsCPA --limit 100 --json nameWithOwner,sshUrl \
  | jq -r '.[].sshUrl' >> /tmp/remote-repos.txt

sort -u /tmp/local-repos.txt /tmp/remote-repos.txt > /tmp/all-repos.txt
```

Read `~/.claude/docs/compliance-exclusions.yaml`. For each exclusion entry, remove matching repos from the list.

### 2. For Each Repo

For local repos: use the path directly.
For remote-only repos: clone to a temp directory under `/tmp/compliance-<date>/`.

Run steps 2-4 from interactive-mode.md (parallel audit dispatch, merge findings, sort by severity). Skip the approval loop, remediation dispatch, and PR creation.

Write one report file per repo using the template at `templates/compliance-report.md`.
Path: `~/.claude/docs/compliance-reports/<YYYY-MM-DD>-<repo-slug>.md`

### 3. Retrospective

After all repos are processed, dispatch `compliance-retrospective` with all findings from the full session.

Output path: `~/.claude/docs/compliance-reports/lessons-learned/<YYYY-MM-DD>.md`

Print: "Scheduled run complete. Reports written to ~/.claude/docs/compliance-reports/. Review lessons-learned/<date>.md before next run."

### 4. Cleanup

```bash
rm -rf /tmp/compliance-<date>/
rm -f /tmp/local-repos.txt /tmp/remote-repos.txt /tmp/all-repos.txt
```
```

- [ ] **Step 2: Write compliance-report.md template**

```markdown
# Compliance Report: {{repo_name}}

**Date**: {{date}}
**Repo path**: {{repo_path}}
**Standards version**: {{manifest_last_updated}}
**Overrides applied**: {{override_count}}

## Summary

| Severity | Found | Overridden | Net |
|----------|-------|------------|-----|
| Critical | {{critical_found}} | {{critical_overridden}} | {{critical_net}} |
| Important | {{important_found}} | {{important_overridden}} | {{important_net}} |
| Suggested | {{suggested_found}} | {{suggested_overridden}} | {{suggested_net}} |
| Unclassified | {{unclassified_count}} | 0 | {{unclassified_count}} |

## Critical Findings

{{critical_findings_list}}

## Important Findings

{{important_findings_list}}

## Suggested Findings

{{suggested_findings_list}}

## Unclassified Candidates

{{unclassified_candidates_list}}

---

*Generated by repo-compliance system. To remediate, run `/repo-audit {{repo_path}}` in interactive mode.*
```

- [ ] **Step 3: Commit**

```bash
git add .claude/skills/repo-compliance/workflows/scheduled-mode.md \
        .claude/skills/repo-compliance/templates/compliance-report.md
git commit -m "feat(compliance): add scheduled mode workflow and report template"
```

---

## Phase 5: Registration and Integration

### Task 13: Register all new components in AGENTS-AND-SKILLS.md

**Files:**
- Modify: `AGENTS-AND-SKILLS.md`

- [ ] **Step 1: Read the current AGENTS-AND-SKILLS.md**

Read `AGENTS-AND-SKILLS.md` to understand the existing structure and find the right insertion points.

- [ ] **Step 2: Add new agents to the agents section**

Find the `## Agents` or `### Code Review & Quality Gates` section (or the most relevant grouping). Add entries for each new agent. Follow the existing format exactly (bold name, description paragraph).

Entries to add:

**`repo-foundations-auditor`**
Compliance auditor and remediator for repository foundation files. Checks OpenSSF required files (SECURITY.md, CONTRIBUTING.md, CHANGELOG.md), CODEOWNERS, .gitignore entries, pyproject.toml metadata, and docs structure against the standards manifest. Returns structured findings in audit mode; creates or patches files in remediation mode.

**`python-toolchain-auditor`**
Compliance auditor and remediator for Python project toolchain configuration. Checks dev dependency presence and absence (ruff, basedpyright, pip-audit, darglint, interrogate), Ruff rule set completeness against PyStrict-aligned codes, BasedPyright config, qlty setup, and pyproject.toml settings against the standards manifest.

**`pre-commit-auditor`**
Compliance auditor and remediator for `.pre-commit-config.yaml`. Checks hook presence against the required list (ruff, basedpyright, bandit, detect-secrets, darglint, interrogate, commitizen, yamllint, markdownlint, no-em-dash) and validates all rev fields are SHA-pinned.

**`claude-docs-auditor`**
Compliance auditor and remediator for Claude configuration and project documentation. Checks CLAUDE.md section presence, `.claude/settings.json`, AGENTS.md/GEMINI.md file locations, and writing quality. Delegates em-dash and AI pattern scanning to `writing-style-editor`.

**`general-compliance-auditor`**
Freeform compliance auditor for gaps outside the standards manifest. Receives covered check IDs as a negative filter, performs a broad LLM review against global standards, and returns unclassified candidates for retrospective pattern analysis. Audit mode only.

**`compliance-retrospective`**
Post-run retrospective agent. Synthesizes findings across all repos in a session, detects patterns in unclassified candidates, and writes a lessons-learned document with ready-to-paste manifest improvement proposals and agent scope expansion candidates.

- [ ] **Step 3: Add repo-compliance skill to the skills section**

Find the skills section. Add:

**`/repo-audit`** (`repo-compliance` skill)
Repo compliance coordinator. Audits any repository against the standards manifest, presents findings grouped by severity, applies approved remediations, opens a PR, and runs the retrospective. Interactive mode for single-repo work; scheduled mode for org-wide sweeps.

- [ ] **Step 4: Run pre-commit**

```bash
cd /home/byron/dev/.claude
uv run pre-commit run --all-files
```

Expected: all hooks pass.

- [ ] **Step 5: Commit**

```bash
git add AGENTS-AND-SKILLS.md
git commit -m "docs: register compliance system agents and skill in AGENTS-AND-SKILLS.md"
```

---

### Task 14: Integration test against pp-security-master

**Files:**
- None (test only)

- [ ] **Step 1: Run /repo-audit against pp-security-master in report-only mode**

```bash
cd /home/byron/dev/pp-security-master/pp-security-master
```

Invoke `/repo-audit` and select option D (skip remediation -- report only) when the approval loop appears.

- [ ] **Step 2: Verify critical findings are detected**

The audit must report findings for at least these check IDs (known from the 2026-04-20 design spec):

```
Critical:
  FOUND-001  SECURITY.md absent
  FOUND-002  CONTRIBUTING.md absent
  TOOL-001   ruff present (should PASS -- ruff is installed)
  TOOL-003   mypy present (should FAIL -- mypy is present, should be absent)
  TOOL-004   black present (should FAIL -- black is present, should be absent)
  PC-001     .pre-commit-config.yaml absent
  CI-005     action SHA pins missing
  CLAUDE-007 em-dashes present in docs

Important:
  FOUND-003  CHANGELOG.md absent
  TOOL-005   basedpyright absent
  TOOL-006   pip-audit absent
  CI-001     CI not using org reusable workflow
  CI-006     harden-runner missing
  CLAUDE-002 CLAUDE.md missing Model Selection section
  CLAUDE-003 CLAUDE.md missing RAD section
```

If any of the above are NOT reported, investigate the owning domain agent and fix its audit logic before proceeding.

- [ ] **Step 3: Verify retrospective runs**

After the audit completes, confirm that `~/.claude/docs/compliance-reports/lessons-learned/<today>.md` was written.

- [ ] **Step 4: Verify report is gitignored**

```bash
cd /home/byron/dev/.claude
git status docs/compliance-reports/
```

Expected: no compliance-reports files appear in git status (they are gitignored).

- [ ] **Step 5: Commit any fixes surfaced by the integration test**

If the integration test required fixes to any agent or skill file:

```bash
git add .claude/agents/<fixed-files>
git commit -m "fix(compliance): correct audit logic based on integration test against pp-security-master"
```

---

## Self-Review Notes

**Spec coverage check:**
- Architecture: covered in plan header and Phase 4 coordinator skill
- Standards manifest (Section 3 of spec): covered in Task 1
- Override file schema: covered in Task 2
- All 6 new agents: covered in Tasks 3-8
- devops-deployment-agent expansion: covered in Task 9
- Coordinator skill with interactive and scheduled modes: covered in Tasks 10-12
- Repo discovery: covered in Task 12 (scheduled-mode.md)
- Report output format: covered in Task 12 (template)
- Lessons-learned format: covered in Task 8 (retrospective agent output template)
- AGENTS-AND-SKILLS.md registration: covered in Task 13
- Integration test: covered in Task 14
- Self-improvement loop: encoded in retrospective agent (Task 8) and lessons-learned doc

**No placeholders confirmed:** all code blocks contain actual content; no TBD/TODO present.

**Type consistency:** FINDING block format defined in Task 3 (repo-foundations-auditor) and referenced consistently in Tasks 4-7. ACTION line format defined in Task 3 and used consistently. Coordinator prompt template defined once in Task 10 and referenced in Tasks 11-12.
