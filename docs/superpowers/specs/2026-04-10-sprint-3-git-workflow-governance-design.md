---
schema_type: common
title: "Sprint 3: Git Workflow and Process Governance"
status: draft
owner: core-maintainer
purpose: "Design spec for adding remote verification, branch override pattern, scope tracing principle, AI review integration documentation, and cookiecutter AI review config sync to the global Claude implementation."
tags:
  - documentation
  - tooling
  - compliance
---

## Overview

This sprint adds five workflow governance patterns to the global Claude implementation,
closing gaps identified in the 2026-04-09 cross-project CLAUDE.md audit. Items 1-4
appeared in 3+ project CLAUDE.md files but were absent from the global standard. Item 5
syncs the cookiecutter template's AI review configuration with current tooling.

**Approach**: Documentation-only. All tooling (CodeRabbit, GitHub Copilot, phase-gate)
is already wired. No hook changes needed.

---

## Item 1: Git Remote Verification

**Problem**: Developers can push to the wrong GitHub organization when multiple remotes
are configured or when a cloned repo was not re-pointed after forking. Wrong-org pushes
trigger CI and create PRs that are difficult to retract.

**Solution**: Add a `## Remote Verification` section to `rules/git-workflow.md`, after
the Branch Naming Convention subsection and before `## Gate System`.

**Section content to add:**

```markdown
## Remote Verification

Before pushing to a remote you haven't used in this session, verify you are targeting
the correct organization:

    git remote -v

Check that the `origin` URL matches the expected GitHub org and repo before running
`git push`. Wrong-org pushes are difficult to retract once a PR or CI run is triggered.

If the remote URL is wrong:

    git remote set-url origin git@github.com:correct-org/repo-name.git
```

---

## Item 2: Branch Workflow Override Mechanism

**Problem**: The branch-first rule (never commit directly to `main`) is documented as
mandatory, but no pattern exists for legitimate exceptions. Developers either feel
blocked or bypass the rule silently, with no record of the trade-off.

**Solution**: Add a `## Branch Workflow Override` section to `rules/git-workflow.md`,
after `## Remote Verification` and before `## Gate System`.

**Section content to add:**

```markdown
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
```

---

## Item 3: Scope Tracing Principle

**Problem**: When working inside a formal phased project, tasks can accumulate that are
not tied to any phase acceptance criterion. These tasks produce work that either misses
the phase gate or silently expands scope. No global guidance documents this pattern.

**Solution**: Two additive changes.

### 3a: `CLAUDE.md` Development Philosophy

Add item 7 to the numbered list under `## Development Philosophy`. The current list ends
at item 6 (`6. **Collaboration**`).

**Item to add:**

```markdown
7. **Scope Tracing**: In phased projects, every task must trace to a phase acceptance
   criterion defined in the project plan. Work that cannot be traced requires a scope
   amendment before starting, not after. Use the `/phase-gate` skill to verify phase
   readiness before closing a phase.
```

### 3b: `rules/supervisor.md`

Add a `## Scope Tracing (Phased Projects)` section after `## Every Development Task
Pattern` and before `## PR Preparation Workflow`.

**Section content to add:**

```markdown
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
```

---

## Item 4: AI Review Integration Documentation

**Problem**: Two AI review tools are fully configured but undocumented in the rules
files, so developers do not know they exist or how to trigger them:

- `.coderabbit.yaml`: assertive profile, auto-reviews every PR targeting main/master/develop,
  runs ruff/gitleaks/markdownlint/yamllint as inline tools
- `.github/copilot-instructions.md`: 9 review focus areas (business logic, error
  handling, edge cases, concurrency, API design, documentation, test quality, security
  logic, maintainability); triggered manually from the Reviewers menu on GitHub

**Solution**: Two additive changes.

### 4a: `rules/git-workflow.md` Gate System section

Replace the existing Layer 2 entry with an expanded version that names all three PR
review tools: CodeRabbit (automatic), GitHub Copilot (manual, configured), and
`/code-review` (manual skill). Add a note on how they complement each other.

**Current Layer 2 text** (to be replaced):

```text
**Layer 2 - PR gates (run manually after PR creation):**
- `/code-review`: runs 5 parallel agents (CLAUDE.md compliance x2, bug scan, git-history context, comment compliance), scores each issue 0-100, and posts only issues ≥80 confidence as a PR comment.
```

**Replacement text:**

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

### 4b: `rules/pre-commit.md` PR section

Add two items to the `## PR (if creating PR)` section, after the existing `/code-review`
line: one for CodeRabbit (automatic), one for Copilot (optional manual request).

**Items to add:**

```markdown
- [ ] **CodeRabbit review**: fires automatically on PR creation; address inline comments
      before merging and use `@coderabbitai` in PR comments to ask follow-up questions
- [ ] **Copilot review** (optional): for complex logic changes, request from the
      Reviewers menu on GitHub; review instructions are in `.github/copilot-instructions.md`
```

---

## Item 5: Cookiecutter AI Review Configuration Sync

**Problem**: The cookiecutter template already contains
`{{cookiecutter.project_slug}}/.github/copilot-instructions.md` and
`{{cookiecutter.project_slug}}/.coderabbit.yaml`, but the copilot file is stale. It
references "Black" for formatting in two places, while projects generated from this
template now use `ruff format`. The instructions also list "Code formatting (Black)"
in the "What NOT to Review" section, creating a false expectation.

**Solution**: Add a `### AI Review Configuration` subsection to the `## What to Update`
section in `docs/handoff-cookiecutter-claude-removal.md`, and add two Definition of Done
checklist items.

### 5a: New subsection in `docs/handoff-cookiecutter-claude-removal.md`

Insert after `### DEVELOPMENT.md` and before `### cookiecutter.json`.

**Content to add:**

    ### AI Review Configuration

    Two AI review config files exist in `{{cookiecutter.project_slug}}/.github/` and need
    to be updated before merging the cleanup PR.

    **`.github/copilot-instructions.md`**

    The file references Black in two places that describe what automated checks handle so
    Copilot should skip them:

    - Line 4 (introductory note): `formatting (Black)` -- change to `formatting (ruff format)`
    - Line 110 ("What NOT to Review" list): `Code formatting (Black)` -- change to
      `Code formatting (ruff format)`

    No other changes are needed. The nine review focus areas are accurate and should not
    be modified.

    **`.coderabbit.yaml`**

    Compare this file with `.coderabbit.yaml` at the root of the `.claude` repo (the global
    baseline). Update the template's file if the baseline has changed. The key sections to
    compare: `language_instructions`, `path_instructions`, and `tools` block. Profile and
    auto-review settings are intentionally the same and should stay in sync.

### 5b: Two new Definition of Done items

Add to the end of the `## Definition of Done` checklist in
`docs/handoff-cookiecutter-claude-removal.md`:

    - [ ] `{{cookiecutter.project_slug}}/.github/copilot-instructions.md` updated: "Black"
          replaced with "ruff format" in both the introductory note and the "What NOT to
          Review" list
    - [ ] `{{cookiecutter.project_slug}}/.coderabbit.yaml` compared against `.claude` repo
          baseline; divergences either resolved or documented as intentional

---

## Files Modified

| File | Change Type | Description |
| --- | --- | --- |
| `.claude/rules/git-workflow.md` | Documentation | Add Remote Verification section; add Branch Workflow Override section; expand Layer 2 Gate System entry |
| `CLAUDE.md` | Documentation | Add scope tracing item 7 to Development Philosophy numbered list |
| `.claude/rules/supervisor.md` | Documentation | Add Scope Tracing section after Every Development Task Pattern |
| `.claude/rules/pre-commit.md` | Documentation | Add CodeRabbit and Copilot checklist items to PR section |
| `docs/handoff-cookiecutter-claude-removal.md` | Documentation | Add AI Review Configuration subsection and two DoD items |

---

## Verification

1. **Remote Verification present**: `grep "Remote Verification" .claude/rules/git-workflow.md`
2. **Branch Override present**: `grep "Branch Workflow Override" .claude/rules/git-workflow.md`
3. **Section ordering in git-workflow.md**: Remote Verification appears before Branch Workflow Override, which appears before Gate System
4. **Scope tracing in CLAUDE.md**: `grep "Scope Tracing" CLAUDE.md` returns one match in Development Philosophy
5. **Scope tracing in supervisor.md**: `grep "Scope Tracing" .claude/rules/supervisor.md` returns one match
6. **CodeRabbit in Gate System**: `grep "CodeRabbit" .claude/rules/git-workflow.md` returns match in Layer 2 block
7. **Copilot in Gate System**: `grep "Copilot" .claude/rules/git-workflow.md` returns match in Layer 2 block
8. **CodeRabbit in pre-commit.md**: `grep "CodeRabbit" .claude/rules/pre-commit.md` returns one match
9. **Copilot in pre-commit.md**: `grep "Copilot" .claude/rules/pre-commit.md` returns one match
10. **Handoff doc AI section present**: `grep "AI Review Configuration" docs/handoff-cookiecutter-claude-removal.md` returns one match
11. **Handoff DoD updated**: `grep "ruff format" docs/handoff-cookiecutter-claude-removal.md` returns matches
12. **All pre-commit hooks pass**: `pre-commit run --all-files`

---

## Out of Scope

- Enforcing scope tracing via a hook (documentation-only; the phase-gate skill handles verification)
- Modifying `.coderabbit.yaml` in this repo
- Executing the cookiecutter cleanup work (Item 5 updates the handoff doc only; the
  actual template changes happen in the `cookiecutter-python-template` repo)
- Documenting the `@coderabbitai` command set beyond the basic usage note
