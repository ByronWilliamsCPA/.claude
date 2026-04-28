---
schema_type: planning
title: "Sprint 3: Git Workflow and Process Governance Implementation Plan"
status: draft
owner: core-maintainer
purpose: "Implementation plan for adding remote verification, branch override pattern, scope tracing, AI review integration documentation, and cookiecutter AI review config sync to the global Claude implementation."
component: Development-Tools
source: "docs/superpowers/specs/2026-04-10-sprint-3-git-workflow-governance-design.md"
tags:
  - planning
  - documentation
  - tooling
---

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add five workflow governance patterns (remote verification, branch override, scope tracing, AI review integration, cookiecutter sync) to the global Claude rules files.

**Architecture:** Documentation-only sprint. All five items are additive edits to existing Markdown files - no tooling changes, no new hooks. Three items land in `.claude/rules/git-workflow.md` (two new sections plus Layer 2 expansion), two land in `CLAUDE.md` and `rules/supervisor.md`, one in `rules/pre-commit.md`, and one in `docs/handoff-cookiecutter-claude-removal.md`. Four commits, one per file or logical group.

**Tech Stack:** Markdown, git, pre-commit hooks.

---

## File Map

| File | Action | What Changes |
| --- | --- | --- |
| `.claude/rules/git-workflow.md` | Modify | Insert `## Remote Verification` and `## Branch Workflow Override` before `## Gate System`; replace Layer 2 entry with three-tool block |
| `CLAUDE.md` | Modify | Append item 7 (`Scope Tracing`) to `## Development Philosophy` list |
| `.claude/rules/supervisor.md` | Modify | Insert `## Scope Tracing (Phased Projects)` between `## Every Development Task Pattern` and `## PR Preparation Workflow` |
| `.claude/rules/pre-commit.md` | Modify | Add two checklist items after `**Automated Review**` in `## PR (if creating PR)` |
| `docs/handoff-cookiecutter-claude-removal.md` | Modify | Insert `### AI Review Configuration` after `### DEVELOPMENT.md`; append two items to `## Definition of Done` |

---

## Task 1: Update git-workflow.md (Remote Verification, Branch Override, Layer 2)

**Files:**

- Modify: `.claude/rules/git-workflow.md`

This task makes three edits to the same file and ships them in one commit.

- [ ] **Step 1: Confirm the insertion point for Remote Verification and Branch Override**

```bash
grep -n "Descriptive but concise\|## Gate System" .claude/rules/git-workflow.md
```

Expected output:

```text
38:- Descriptive but concise: `feat/oauth-google` not `feat/add-oauth-integration-with-google-identity-provider`
40:## Gate System
```

- [ ] **Step 2: Confirm the Layer 2 text that will be replaced**

```bash
grep -n "Layer 2\|/code-review.*5 parallel" .claude/rules/git-workflow.md
```

Expected output:

```text
49:**Layer 2 - PR gates (run manually after PR creation):**
50:- `/code-review`: runs 5 parallel agents (CLAUDE.md compliance x2, bug scan, git-history context, comment compliance), scores each issue 0-100, and posts only issues ≥80 confidence as a PR comment.
```

- [ ] **Step 3: Insert Remote Verification and Branch Workflow Override sections**

In `.claude/rules/git-workflow.md`, use the Edit tool with:

`old_string`:

```text
- Descriptive but concise: `feat/oauth-google` not `feat/add-oauth-integration-with-google-identity-provider`

## Gate System
```

`new_string`:

```text
- Descriptive but concise: `feat/oauth-google` not `feat/add-oauth-integration-with-google-identity-provider`

## Remote Verification

Before pushing to a remote you have not used in this session, verify you are targeting
the correct organization:

    git remote -v

Check that the `origin` URL matches the expected GitHub org and repo before running
`git push`. Wrong-org pushes are difficult to retract once a PR or CI run is triggered.

If the remote URL is wrong:

    git remote set-url origin git@github.com:correct-org/repo-name.git

## Branch Workflow Override

The branch-first rule (never commit directly to `main`) applies in all standard cases.
When a legitimate exception exists (hotfix to an unprotected repo, solo maintenance
commit, CI config tweak), document the override with three elements before proceeding:

1. **Rule overridden**: which rule is being bypassed (e.g., "branch-first commit rule")
2. **Reason**: why the exception applies in this specific context
3. **Compensating control**: what replaces the protection the rule normally provides
   (e.g., "PR is not required; commit is reviewed via pair programming before push")

Record this as a comment in the commit message footer:

    Override: branch-first commit rule
    Reason: hotfix to unprotected solo repo, no CI gating
    Compensating control: manual review of diff before push

## Gate System
```

- [ ] **Step 4: Verify the two new sections are present**

```bash
grep -n "^## Remote Verification\|^## Branch Workflow Override\|^## Gate System" .claude/rules/git-workflow.md
```

Expected: three matches in order - Remote Verification, Branch Workflow Override, Gate System.

- [ ] **Step 5: Replace the Layer 2 block**

In `.claude/rules/git-workflow.md`, use the Edit tool with:

`old_string`:

```text
**Layer 2 - PR gates (run manually after PR creation):**
- `/code-review`: runs 5 parallel agents (CLAUDE.md compliance x2, bug scan, git-history context, comment compliance), scores each issue 0-100, and posts only issues ≥80 confidence as a PR comment.
```

`new_string`:

```text
**Layer 2 - PR gates (automatic and manual, after PR creation):**
- `CodeRabbit`: fires automatically on every PR targeting `main`, `master`, or `develop`.
  Profile: assertive. Provides high-level summary, file-by-file walkthrough, inline
  comments, and suggested labels. Runs ruff, gitleaks, markdownlint, and yamllint as
  inline tools. No action required to trigger it.
- `GitHub Copilot`: request manually from the Reviewers menu on GitHub. Configured via
  `.github/copilot-instructions.md` to focus on business logic, error handling, edge
  cases, concurrency, and security logic flaws that automated linters cannot catch.
  Leaves advisory comments only; does not block merge.
- `/code-review`: runs 5 parallel agents (CLAUDE.md compliance x2, bug scan,
  git-history context, comment compliance), scores each issue 0-100, and posts only
  issues ≥80 confidence as a PR comment. Run manually after PR creation.

Use CodeRabbit for holistic structural review, GitHub Copilot for deep logic review on
complex PRs, and `/code-review` for project-standards enforcement.
```

- [ ] **Step 6: Verify CodeRabbit and Copilot are in the Gate System section**

```bash
grep -n "CodeRabbit\|GitHub Copilot" .claude/rules/git-workflow.md
```

Expected: two or more matches, all within the Gate System section.

- [ ] **Step 7: Commit Task 1**

```bash
git add .claude/rules/git-workflow.md
git commit -m "docs: add remote verification, branch override, and AI review gate documentation"
```

Expected: commit succeeds, all pre-commit hooks pass.

---

## Task 2: Add Scope Tracing to CLAUDE.md and supervisor.md

**Files:**

- Modify: `CLAUDE.md` (line 245 area)
- Modify: `.claude/rules/supervisor.md` (line 51 area)

Both changes are logically coupled (scope tracing principle) and ship in one commit.

- [ ] **Step 1: Confirm the CLAUDE.md insertion point**

```bash
grep -n "Collaboration\|Development Philosophy" CLAUDE.md
```

Expected output:

```text
238:**Security First** → **Quality Standards** → **Documentation** → **Testing** → **Collaboration**
240:1. **Security First**: Always validate keys, encrypt secrets, scan dependencies
...
245:6. **Collaboration**: Use consistent Git workflows and clear commit messages
```

- [ ] **Step 2: Add scope tracing item to CLAUDE.md**

In `CLAUDE.md`, use the Edit tool with:

`old_string`:

```text
6. **Collaboration**: Use consistent Git workflows and clear commit messages
```

`new_string`:

```text
6. **Collaboration**: Use consistent Git workflows and clear commit messages
7. **Scope Tracing**: In phased projects, every task must trace to a phase acceptance
   criterion defined in the project plan. Work that cannot be traced requires a scope
   amendment before starting, not after. Use the `/phase-gate` skill to verify phase
   readiness before closing a phase.
```

- [ ] **Step 3: Verify item 7 is present**

```bash
grep -n "Scope Tracing" CLAUDE.md
```

Expected: one match in the Development Philosophy section.

- [ ] **Step 4: Confirm the supervisor.md insertion point**

```bash
grep -n "Validate.*agent output\|## PR Preparation" .claude/rules/supervisor.md
```

Expected output:

```text
51:5. **Validate** all agent output before marking complete
53:## PR Preparation Workflow
```

- [ ] **Step 5: Add Scope Tracing section to supervisor.md**

In `.claude/rules/supervisor.md`, use the Edit tool with:

`old_string`:

```text
5. **Validate** all agent output before marking complete

## PR Preparation Workflow
```

`new_string`:

```text
5. **Validate** all agent output before marking complete

## Scope Tracing (Phased Projects)

When working inside a phase of a formal project (one with a `PROJECT-PLAN.md` and
phase acceptance criteria), every task in the TodoWrite list must map to a specific
acceptance criterion in the current phase.

Before adding a task to the list, ask: which acceptance criterion does this serve?

- If it traces clearly: add the task normally
- If it does not trace: it is out-of-scope work; either defer it or initiate a scope
  amendment before starting
- If the phase has no acceptance criteria: the project plan is incomplete; surface this
  before proceeding

Use `/phase-gate` at the end of each phase to confirm all criteria are met before
closing.

## PR Preparation Workflow
```

- [ ] **Step 6: Verify the section is present and in the right place**

```bash
grep -n "^## Every Development Task\|^## Scope Tracing\|^## PR Preparation" .claude/rules/supervisor.md
```

Expected order: Every Development Task Pattern, then Scope Tracing (Phased Projects), then PR Preparation Workflow.

- [ ] **Step 7: Commit Task 2**

```bash
git add CLAUDE.md .claude/rules/supervisor.md
git commit -m "docs: add scope tracing principle to CLAUDE.md and supervisor rules"
```

Expected: commit succeeds, all pre-commit hooks pass.

---

## Task 3: Add AI Review Checklist Items to pre-commit.md

**Files:**

- Modify: `.claude/rules/pre-commit.md`

- [ ] **Step 1: Confirm the insertion point**

```bash
grep -n "Automated Review\|CodeRabbit" .claude/rules/pre-commit.md
```

Expected: one match for `Automated Review`, no match for `CodeRabbit` (not yet present).

- [ ] **Step 2: Add CodeRabbit and Copilot checklist items**

In `.claude/rules/pre-commit.md`, use the Edit tool with:

`old_string`:

```text
- [ ] **Automated Review**: Run `/code-review` after PR is created to get AI review feedback (CLAUDE.md compliance + bug detection + git history analysis)
```

`new_string`:

```text
- [ ] **Automated Review**: Run `/code-review` after PR is created to get AI review feedback (CLAUDE.md compliance + bug detection + git history analysis)
- [ ] **CodeRabbit review**: fires automatically on PR creation; address inline comments
      before merging and use `@coderabbitai` in PR comments to ask follow-up questions
- [ ] **Copilot review** (optional): for complex logic changes, request from the
      Reviewers menu on GitHub; review instructions are in `.github/copilot-instructions.md`
```

- [ ] **Step 3: Verify both items are present**

```bash
grep -n "CodeRabbit\|Copilot" .claude/rules/pre-commit.md
```

Expected: two matches - one for CodeRabbit, one for Copilot.

- [ ] **Step 4: Commit Task 3**

```bash
git add .claude/rules/pre-commit.md
git commit -m "docs: add CodeRabbit and Copilot review checklist items to pre-commit rules"
```

Expected: commit succeeds, all pre-commit hooks pass.

---

## Task 4: Update Handoff Document with AI Review Configuration

**Files:**

- Modify: `docs/handoff-cookiecutter-claude-removal.md`

Two edits to the same file: one inserts a new `### AI Review Configuration` subsection,
one appends two items to the `## Definition of Done` checklist.

- [ ] **Step 1: Confirm the insertion point for the new subsection**

```bash
grep -n "### DEVELOPMENT.md\|### cookiecutter.json" docs/handoff-cookiecutter-claude-removal.md
```

Expected output:

```text
135:### DEVELOPMENT.md
140:### cookiecutter.json
```

(Exact line numbers may differ - the order is what matters.)

- [ ] **Step 2: Insert the AI Review Configuration subsection**

In `docs/handoff-cookiecutter-claude-removal.md`, use the Edit tool with:

`old_string`:

```text
### DEVELOPMENT.md

Remove any instructions referencing `.claude/standard/` subtree updates or per-project
Claude config management.

### cookiecutter.json
```

`new_string`:

```text
### DEVELOPMENT.md

Remove any instructions referencing `.claude/standard/` subtree updates or per-project
Claude config management.

### AI Review Configuration

Two AI review config files exist in `{{cookiecutter.project_slug}}/.github/` and need
to be updated before merging the cleanup PR.

**`.github/copilot-instructions.md`**

The file references Black in two places that describe what automated checks handle so
Copilot should skip them:

- Line 4 (introductory note): `formatting (Black)` → change to `formatting (ruff format)`
- Line 110 ("What NOT to Review" list): `Code formatting (Black)` → change to
  `Code formatting (ruff format)`

No other changes are needed. The nine review focus areas are accurate and should not
be modified.

**`.coderabbit.yaml`**

Compare this file with `.coderabbit.yaml` at the root of the `.claude` repo (the global
baseline). Update the template's file if the baseline has changed. The key sections to
compare: `language_instructions`, `path_instructions`, and `tools` block. Profile and
auto-review settings are intentionally the same and should stay in sync.

### cookiecutter.json
```

- [ ] **Step 3: Verify the new subsection is present**

```bash
grep -n "AI Review Configuration\|ruff format" docs/handoff-cookiecutter-claude-removal.md
```

Expected: at least two matches - one for the heading, one or more for `ruff format`.

- [ ] **Step 4: Confirm the DoD insertion point**

```bash
grep -n "PR reviewed and merged" docs/handoff-cookiecutter-claude-removal.md
```

Expected: one match showing the last existing DoD item.

- [ ] **Step 5: Append two items to the Definition of Done checklist**

In `docs/handoff-cookiecutter-claude-removal.md`, use the Edit tool with:

`old_string`:

```text
- [ ] PR reviewed and merged to main
```

`new_string`:

```text
- [ ] PR reviewed and merged to main
- [ ] `{{cookiecutter.project_slug}}/.github/copilot-instructions.md` updated: "Black"
      replaced with "ruff format" in both the introductory note and the "What NOT to
      Review" list
- [ ] `{{cookiecutter.project_slug}}/.coderabbit.yaml` compared against `.claude` repo
      baseline; divergences either resolved or documented as intentional
```

- [ ] **Step 6: Verify both DoD items are present**

```bash
grep -n "ruff format\|coderabbit.yaml.*compared" docs/handoff-cookiecutter-claude-removal.md
```

Expected: at least two matches - one in the subsection body, one in the DoD checklist.

- [ ] **Step 7: Commit Task 4**

```bash
git add docs/handoff-cookiecutter-claude-removal.md
git commit -m "docs: add AI review configuration sync guidance to cookiecutter handoff doc"
```

Expected: commit succeeds, all pre-commit hooks pass.

---

## Task 5: End-to-End Verification

**Files:** none (read-only verification)

- [ ] **Step 1: Run full pre-commit suite**

```bash
pre-commit run --all-files
```

Expected: all hooks pass. Fix any failures before proceeding.

- [ ] **Step 2: Verify all spec content is present**

```bash
grep -n "^## Remote Verification" .claude/rules/git-workflow.md && \
grep -n "^## Branch Workflow Override" .claude/rules/git-workflow.md && \
grep -n "CodeRabbit" .claude/rules/git-workflow.md && \
grep -n "Copilot" .claude/rules/git-workflow.md && \
grep -n "Scope Tracing" CLAUDE.md && \
grep -n "^## Scope Tracing" .claude/rules/supervisor.md && \
grep -n "CodeRabbit" .claude/rules/pre-commit.md && \
grep -n "Copilot" .claude/rules/pre-commit.md && \
grep -n "AI Review Configuration" docs/handoff-cookiecutter-claude-removal.md && \
grep -n "ruff format" docs/handoff-cookiecutter-claude-removal.md
```

Expected: all ten commands return at least one matching line.

- [ ] **Step 3: Verify section order in git-workflow.md**

```bash
grep -n "^## " .claude/rules/git-workflow.md
```

Expected order:

```text
## Branch Strategy (MANDATORY)
## Remote Verification
## Branch Workflow Override
## Gate System
## Security Practices
## Git Worktrees
```

- [ ] **Step 4: Verify section order in supervisor.md**

```bash
grep -n "^## " .claude/rules/supervisor.md
```

Expected order:

```text
## Core Requirements
## Agent Assignment Patterns
## Temporary Reference Files
## Every Development Task Pattern
## Scope Tracing (Phased Projects)
## PR Preparation Workflow
```

- [ ] **Step 5: Confirm CLAUDE.md has item 7**

```bash
grep -n "^[0-9]\." CLAUDE.md | tail -5
```

Expected: item 6 is Collaboration, item 7 is Scope Tracing.

- [ ] **Step 6: Final fixup commit if any corrections were needed**

If Steps 1–5 required corrections, stage and commit them:

```bash
git add -p
git commit -m "docs: fixup sprint-3 governance changes"
```

If no corrections were needed, skip this step.

---

## Completion Checklist

- [ ] `## Remote Verification` present in `rules/git-workflow.md` after Branch Naming Convention
- [ ] `## Branch Workflow Override` present in `rules/git-workflow.md` after Remote Verification
- [ ] Layer 2 Gate System expanded with CodeRabbit, GitHub Copilot, and `/code-review` entries
- [ ] Item 7 (Scope Tracing) appended to Development Philosophy in `CLAUDE.md`
- [ ] `## Scope Tracing (Phased Projects)` section present in `rules/supervisor.md`
- [ ] Two AI review checklist items (CodeRabbit, Copilot) in `rules/pre-commit.md` PR section
- [ ] `### AI Review Configuration` subsection in `docs/handoff-cookiecutter-claude-removal.md`
- [ ] Two new DoD items appended to `docs/handoff-cookiecutter-claude-removal.md`
- [ ] All pre-commit hooks pass on `--all-files`
- [ ] Branch is `docs/sprint-3-git-workflow-governance` with clean, conventional commits
