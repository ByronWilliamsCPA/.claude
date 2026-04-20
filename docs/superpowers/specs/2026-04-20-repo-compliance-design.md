---
schema_type: common
title: Repo Compliance System Design
status: published
owner: engineering
tags: [compliance, agents, skills, standards]
purpose: Design for a self-improving, multi-agent system that audits any repository against current global standards and remediates identified gaps.
---

**Date**: 2026-04-20
**Status**: Approved
**Author**: Byron Williams

---

## Background

Projects initialized before global standards solidified in `~/.claude/CLAUDE.md` and
`~/.claude/.claude/rules/` accumulate drift. Past approaches (cookiecutter for
initial setup, cruft for propagation) did not solve the ongoing alignment problem:
cookiecutter starts projects correctly but does not keep them updated, and cruft
caused conflicts with local work.

The org-level GitHub at `https://github.com/ByronWilliamsCPA/.github` and the
`~/.claude/` configuration have raised the baseline for new work, but there is no
consistent way to evaluate existing repos or capture lessons from each review cycle.

This design specifies a self-improving, multi-agent system that:
- Audits any repo against current standards on demand (interactive mode)
- Runs scheduled org-wide sweeps and produces local reports (scheduled mode)
- Captures lessons from each run and proposes manifest improvements (retrospective)

---

## Scope of Standards

The system evaluates six domains:

| Domain | What It Covers |
|--------|----------------|
| Foundations | OpenSSF required files, .gitignore entries, pyproject.toml metadata |
| Toolchain | Ruff config, BasedPyright, pip-audit, qlty, dep presence/absence |
| Pre-commit | Hook inventory vs. required list, SHA pinning in hooks |
| CI | GitHub Actions structure, SHA-pinned actions, reusable workflows, harden-runner |
| Claude and Docs | CLAUDE.md sections, settings.json, AGENTS.md/GEMINI.md location, em-dash/AI patterns |
| General | Freeform review for gaps outside the five defined domains |

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│  Entry Points                                            │
│  /repo-audit (interactive)  |  cron trigger (scheduled) │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│  Coordinator Skill: repo-compliance                      │
│  - Reads standards-manifest.yaml                         │
│  - Discovers repo list (~/dev/ + GitHub orgs)            │
│  - Dispatches domain agents in phase order               │
│  - Merges reports, filters overrides, ranks findings     │
│  - Interactive: approval loop then remediation           │
│  - Scheduled: report-only, one file per repo             │
│  - Both: triggers compliance-retrospective at end        │
└──┬──────────┬──────────┬───────────┬────────────────────┘
   │          │          │           │           │
   ▼          ▼          ▼           ▼           ▼
Found.    Toolchain  Pre-commit   DevOps*   Claude+Docs
agent      agent      agent      (expanded)   agent
(new)      (new)      (new)                (new, delegates
                                        to writing-style-editor)
                                               +
                                          General
                                          Auditor
                                           (new)
                                               +
                                          Retrospective
                                           (post-run)
```

---

## Component Inventory

### New Agents

| Agent file | Purpose |
|-----------|---------|
| `repo-foundations-auditor.md` | OpenSSF files, .gitignore, pyproject metadata, CODEOWNERS |
| `python-toolchain-auditor.md` | Ruff, BasedPyright, pip-audit, qlty, dep config |
| `pre-commit-auditor.md` | Hook inventory vs. required list, hook SHA pinning |
| `claude-docs-auditor.md` | CLAUDE.md sections, settings.json, file locations, writing checks |
| `general-compliance-auditor.md` | Freeform gaps outside the manifest |
| `compliance-retrospective.md` | Lessons learned, pattern detection, manifest proposals |

### Expanded Agent

| Agent file | Addition |
|-----------|---------|
| `devops-deployment-agent.md` | Compliance audit mode for CI workflows (new alongside existing capabilities) |

### New Skill

| Skill | Purpose |
|-------|---------|
| `repo-compliance/SKILL.md` | Coordinator for both interactive and scheduled modes |

### New Files in `~/dev/.claude/`

| File | Purpose |
|------|---------|
| `docs/standards-manifest.yaml` | Authoritative check registry |
| `docs/compliance-exclusions.yaml` | Repos excluded from scheduled sweeps |
| `docs/compliance-reports/.gitignore` | Keeps all reports local, never pushed |
| `docs/compliance-reports/lessons-learned/` | Directory for retrospective outputs |
| `.claude/compliance-overrides.md` | Per-repo override template (copied into target repos) |

---

## Standards Manifest

`docs/standards-manifest.yaml` is the authoritative source for what "compliant"
means. Domain agents read it to know what to check. Adding a new standard is a
manifest edit, not an agent code change.

### Schema

```yaml
version: "1.0"
last_updated: "2026-04-20"

checks:
  - id: FOUND-001
    domain: foundations
    severity: critical          # critical | important | suggested
    description: "SECURITY.md present at project root"
    verify: "file_exists: SECURITY.md"
    source_template: "/home/byron/dev/.github/SECURITY.md"
    override_eligible: false    # false = cannot be suppressed by overrides file

  - id: FOUND-005
    domain: foundations
    severity: important
    description: ".worktrees/ in .gitignore"
    verify: "content_present: .gitignore, .worktrees/"
    override_eligible: true

  - id: TOOL-003
    domain: toolchain
    severity: critical
    description: "mypy absent from dependencies (replaced by basedpyright)"
    verify: "dep_absent: mypy"
    override_eligible: false

  - id: CI-004
    domain: ci
    severity: critical
    description: "All GitHub Action uses: pins are 40-char SHAs"
    verify: "sha_pinned: .github/workflows/**"
    override_eligible: false

  - id: CLAUDE-002
    domain: claude_docs
    severity: important
    description: "CLAUDE.md contains Model Selection table"
    verify: "section_present: CLAUDE.md, Model Selection"
    override_eligible: true
```

### Field Definitions

| Field | Required | Purpose |
|-------|----------|---------|
| `id` | yes | Stable identifier referenced by overrides file; format `DOMAIN-NNN` |
| `domain` | yes | Routes to the correct agent: `foundations`, `toolchain`, `pre_commit`, `ci`, `claude_docs` |
| `severity` | yes | `critical` (always shown, remediate by default), `important` (shown, confirm), `suggested` (batched) |
| `description` | yes | Human-readable description of the expected state |
| `verify` | yes | Hint to the domain agent on how to check; not executable, agents interpret it |
| `source_template` | no | Path to copy from when the fix is "use this file" |
| `override_eligible` | yes | `false` reserves the check for security-critical items that cannot be suppressed |

---

## Per-Repo Override File

Each target repo may contain `.claude/compliance-overrides.md`. The coordinator
reads this file before presenting findings and silently skips any `override_eligible`
check listed in it. Non-eligible checks are flagged regardless.

```markdown
## Compliance Overrides

| Check ID | Reason | Approved By | Date |
|----------|--------|-------------|------|
| TOOL-001 | Poetry grandfathered -- predates uv standard | Byron | 2026-04-20 |
| CLAUDE-002 | Minimal repo, no AI tooling in scope | Byron | 2026-04-20 |
```

The override template lives at `~/.claude/.claude/compliance-overrides.md` and is
copied into a new repo during initial setup.

---

## Agent Designs

### `repo-foundations-auditor`

**Audit mode:** Checks for presence of SECURITY.md, CONTRIBUTING.md, CHANGELOG.md,
CODEOWNERS, and known-vulnerabilities.md. Validates .gitignore contains required
entries (.worktrees/, compliance-reports/). Reads pyproject.toml for metadata
correctness (author email, python version bounds). Checks docs/ structure.

**Remediation mode:** Creates missing files from source_template paths in the
manifest. Patches pyproject.toml metadata fields. Appends missing .gitignore lines.

---

### `python-toolchain-auditor`

**Audit mode:** Diffs the repo dependency list against required and forbidden dep
lists from the manifest. Checks that Ruff rule set contains all PyStrict-aligned
codes. Validates that basedpyright, qlty, darglint, and interrogate config blocks
exist with correct keys. Checks target-version setting.

**Remediation mode:** Edits pyproject.toml to add or remove deps and config blocks.
Does NOT resolve resulting type errors or lint violations; flags those as a follow-on
task for the user.

---

### `pre-commit-auditor`

**Audit mode:** If `.pre-commit-config.yaml` is absent, flags as critical. If
present, inventories hooks against the required hook list from the manifest. Checks
that all `rev` fields are 40-character SHAs, not mutable tags.

**Remediation mode:** Creates `.pre-commit-config.yaml` if absent. Patches missing
hooks into an existing config. Resolves SHAs at run time by reading each hook's
GitHub releases page.

---

### `devops-deployment-agent` (expanded)

**New compliance audit mode (added alongside existing capabilities):**

Audit: Inspects GitHub Actions workflows for use of org reusable workflows, SHA-pinned
action references, harden-runner presence as first step in each job, blocking security
scan configuration (no `continue-on-error: true`), and presence of
`.github/copilot-instructions.md`.

Remediation: Rewrites workflow files to reference org reusable workflows, replaces
mutable tags with resolved SHAs, adds harden-runner steps, removes
`continue-on-error` from security jobs, creates copilot-instructions.md.

Existing deployment and pipeline operation capabilities are unchanged.

---

### `claude-docs-auditor`

**Audit mode:** Checks CLAUDE.md for required sections (RAD marker guidance, Model
Selection table, global rule cross-reference pointers). Verifies `.claude/settings.json`
exists with expected permission structure. Confirms AGENTS.md and GEMINI.md are at
the project root, not in docs/. Delegates em-dash and AI pattern scanning to
`writing-style-editor` and includes results in its report.

**Remediation mode:** Appends missing CLAUDE.md sections from templates. Creates
`.claude/settings.json` with the project's tool allowlist. Relocates misplaced
AGENTS.md and GEMINI.md to the project root.

---

### `general-compliance-auditor`

**Audit only (no remediation mode).**

Reads the manifest to know what is already covered, then performs a freeform LLM
review of the repo against global standards. Outputs candidate findings tagged as
`unclassified` with a proposed domain and severity. These become inputs to the
retrospective agent and are presented to the user separately from the domain
findings, with a note that they are candidates rather than confirmed violations.

---

### `compliance-retrospective`

**Post-run only.**

Reads all findings from the current session across all repos reviewed. Groups
unclassified findings from the general auditor by pattern. Identifies any check
appearing in three or more repos as a manifest candidate. Writes
`docs/compliance-reports/lessons-learned/YYYY-MM-DD.md` with:

- Patterns observed this session
- Proposed manifest entries as ready-to-paste YAML snippets
- Domain agents flagged for potential scope expansion
- Count of findings by domain and severity across all repos reviewed

In interactive mode, presents the lessons-learned file path at session close and
asks the user to review it before the next scheduled run.

---

## Coordinator Skill: `repo-compliance`

### Interactive Mode (`/repo-audit`)

```
1. Detect target repo (current working directory)
2. Load standards-manifest.yaml from ~/.claude/docs/
3. Load .claude/compliance-overrides.md from target repo (if present)
4. Dispatch 5 domain agents in parallel:
     repo-foundations-auditor
     python-toolchain-auditor
     pre-commit-auditor
     devops-deployment-agent (compliance audit mode)
     claude-docs-auditor
5. Dispatch general-compliance-auditor (receives domain findings to avoid overlap)
6. Merge all findings, filter overrides, sort by severity
7. Present findings grouped: Critical | Important | Suggested | Unclassified
8. Approval loop:
     a. User selects which findings to fix (all critical auto-highlighted)
     b. Coordinator dispatches relevant domain agents in remediation mode
     c. Reports what changed
9. Open PR with all remediations
10. Run compliance-retrospective
11. Present path to lessons-learned doc
```

### Scheduled Mode (cron trigger)

```
1. Discover repos:
     Local: find ~/dev -maxdepth 2 -name ".git" -type d (excludes .worktrees/)
     Remote: gh repo list williaby --limit 100
             gh repo list ByronWilliamsCPA --limit 100
     Merge and deduplicate; apply compliance-exclusions.yaml
2. For each repo:
     a. Pull latest if local; clone to temp dir if remote-only
     b. Run steps 2-7 from interactive mode (no approval, no remediation)
     c. Write docs/compliance-reports/YYYY-MM-DD-<repo-slug>.md
3. Run compliance-retrospective across all repos in the session
4. Write docs/compliance-reports/lessons-learned/YYYY-MM-DD.md
```

### Repo Exclusion File

`docs/compliance-exclusions.yaml`:

```yaml
exclusions:
  - repo: cookiecutter-python-template
    reason: "template source, not a generated project"
  - repo: some-archived-repo
    reason: "archived, no active development"
```

---

## Output Formats

### Per-Repo Compliance Report

Path: `docs/compliance-reports/YYYY-MM-DD-<repo-slug>.md`
Gitignored: yes

```markdown
# Compliance Report: <repo-name>
**Date**: YYYY-MM-DD
**Standards version**: 1.0 (manifest last updated YYYY-MM-DD)
**Overrides applied**: N

## Summary
| Severity | Found | Overridden | Net |
|----------|-------|------------|-----|
| Critical | 3 | 0 | 3 |
| Important | 8 | 2 | 6 |
| Suggested | 4 | 1 | 3 |
| Unclassified | 2 | 0 | 2 |

## Critical Findings
- [FOUND-001] SECURITY.md absent from project root
- [CI-004] 6 GitHub Actions use mutable tags instead of SHA pins

## Important Findings
...

## Unclassified Candidates (for retrospective review)
...
```

### Lessons-Learned Doc

Path: `docs/compliance-reports/lessons-learned/YYYY-MM-DD.md`
Gitignored: yes

```markdown
# Compliance Retrospective: YYYY-MM-DD

## Session Summary
Repos reviewed: N | Total findings: N | Overrides applied: N

## Patterns Observed
- <pattern appearing in 3+ repos>

## Proposed Manifest Additions
```yaml
- id: FOUND-XXX
  domain: foundations
  severity: important
  description: "..."
  verify: "..."
  override_eligible: true
```

## Agent Scope Expansion Candidates
- <agent>: consider adding <check> based on pattern seen in <repos>
```

---

## Self-Improvement Loop

```
Review run
    -> lessons-learned doc written
         -> user reviews and approves proposals
              -> standards-manifest.yaml updated
                   -> agent definitions updated where needed
                        -> next review run catches more
```

The manifest is the artifact that accumulates organizational learning. Each cycle
makes the next one more thorough without requiring manual tracking of what was
discovered.

---

## File Structure Summary

```
~/.claude/
  docs/
    standards-manifest.yaml          # authoritative check registry
    compliance-exclusions.yaml       # repos excluded from scheduled sweeps
    compliance-reports/
      .gitignore                     # ignores everything in this dir
      lessons-learned/               # retrospective outputs
  .claude/
    agents/
      repo-foundations-auditor.md    # new
      python-toolchain-auditor.md    # new
      pre-commit-auditor.md          # new
      claude-docs-auditor.md         # new
      general-compliance-auditor.md  # new
      compliance-retrospective.md    # new
      devops-deployment-agent.md     # expanded
    skills/
      repo-compliance/
        SKILL.md                     # coordinator
    compliance-overrides.md          # template copied into target repos
```

---

## Testing Strategy

- **Unit**: Each domain agent tested against a synthetic repo with known violations
- **Integration**: Full coordinator run against pp-security-master (known 34-gap baseline)
- **Scheduled**: Dry run against ~/dev/ with report-only mode before enabling cron
- **Retrospective**: Verify lessons-learned doc is written and gitignored after each run
