---
schema_type: common
title: "Handoff: Remove Claude Configuration from Cookiecutter Template"
status: published
owner: core-maintainer
tags: [documentation]
purpose: "Decision and task handoff for removing Claude config from cookiecutter-python-template."
---

> **For**: cookiecutter-python-template maintainers
> **From**: ByronWilliamsCPA/.claude session: 2026-04-08
> **Branch to use**: `chore/remove-claude-config`
> **Repo**: `ByronWilliamsCPA/cookiecutter-python-template`

---

## Decision Context

Claude Code configuration (agents, skills, CLAUDE.md) is moving to the **user level only**
(`~/.claude`). It will no longer be embedded in generated projects or managed as a git subtree
inside individual repos.

**Why**: Project-level `.claude/` directories drift from the central standards repo over time.
User-level config is shared across all projects automatically, gets updated in one place, and
aligns with how the superpowers community plugin works.

**New install story for developers**:
1. Install superpowers from the Claude marketplace (or `npm install -g @obra/superpowers`)
2. Clone `https://github.com/ByronWilliamsCPA/.claude` to `~/.claude`
3. Done: all projects on the machine inherit the full agent/skill suite automatically

---

## What to Remove

### 1. `.claude/` directory at the template repo root

The template repo itself has a `.claude/` folder used during template development. Remove it:

```text
.claude/
  commands/pr.md          ← delete
  skills/                 ← delete entire directory
```

### 2. `.claude/` directory inside `{{cookiecutter.project_slug}}/`

This is what gets generated into new projects. Delete entirely:

```text
{{cookiecutter.project_slug}}/.claude/
  README.md
  settings.local.json.example
  agents/
    code-reviewer.md
    merge-standards.md
    security-auditor.md
    test-engineer.md
  context/
    python-standards.md
    testing-patterns.md
  skills/
    commit-prepare/
    git/
    pr-prepare/
    project-planning/
    quality/
    security/
    testing/
```

> **Note on `merge-standards.md`**: This agent handles merging `cruft update` changes without
> clobbering project customizations. Its logic should be **preserved**: either document it
> in the cruft update runbook or move the merge guidance into a `docs/cruft-update-guide.md`
> in the template before deleting the agent file.

### 3. `hooks/post_gen_project.py`: Claude setup functions

Remove or stub out these two functions:

- `setup_claude_subtree()`: cloned `.claude` as a git subtree into `.claude/standard/`
- `setup_claude_user_settings()`: optionally cloned to `~/.claude`

Also remove any calls to these functions in the `main()` entrypoint. The rest of the hook
(virtualenv setup, git init, dependency install, etc.) is unaffected.

### 4. `scripts/update-claude-standards.sh` (if present)

Delete: this script updated the `.claude/standard` subtree. No longer needed.

### 5. `CLAUDE.md` at the template repo root

Remove or replace. If the template repo itself uses Claude Code for its own development,
replace with a minimal project-level `CLAUDE.md` that reads:

```markdown
# cookiecutter-python-template

Extends global CLAUDE.md standards at ~/.claude/CLAUDE.md.

## Project-Specific Notes

- Template variables use `{{cookiecutter.x}}` syntax: treat these as literals when editing
- Test template generation with: `cookiecutter . --no-input`
- Post-gen hook is at `hooks/post_gen_project.py`
```

---

## What to Update

### `README.md`

Replace the Claude Code setup section with:

```markdown
## Claude Code Setup (User-Level)

This template no longer manages Claude Code configuration at the project level.
Configure once at the user level and all projects inherit it automatically.

1. Install superpowers (community plugin maintained at github.com/obra/superpowers):
   Follow install instructions at that repo for your platform.

1. Clone the ByronWilliamsCPA custom agents and skills:
   ```bash
   git clone https://github.com/ByronWilliamsCPA/.claude.git ~/.claude
   ```

3. That's it. All projects on your machine now have the full agent/skill suite.
```

### `DEVELOPMENT.md`

Remove any instructions referencing `.claude/standard/` subtree updates or per-project
Claude config management.

### AI Review Configuration

Two AI review config files exist in `{{cookiecutter.project_slug}}/.github/` and need
to be updated before merging the cleanup PR.

**`.github/copilot-instructions.md`**

The file references Black in two places that describe what automated checks handle so
Copilot should skip them:

- Line 4 (introductory note): `formatting (Black)` - change to `formatting (ruff format)`
- Line 110 ("What NOT to Review" list): `Code formatting (Black)` - change to
  `Code formatting (ruff format)`

No other changes are needed. The nine review focus areas are accurate and should not
be modified.

**`.coderabbit.yaml`**

Compare this file with `.coderabbit.yaml` at the root of the `.claude` repo (the global
baseline). Update the template's file if the baseline has changed. The key sections to
compare: `language_instructions`, `path_instructions`, and `tools` block. Profile and
auto-review settings are intentionally the same and should stay in sync.

### `cookiecutter.json`

Check for any variables related to Claude config options (e.g., `include_claude_config`,
`claude_settings_repo`). Remove if present.

### `CENTRALIZATION_ANALYSIS.md` / `SYNC-WITH-COOKIECUTTER.md` (if referenced)

Review for any references to the `.claude/standard/` subtree pattern and update to reflect
the user-level model.

---

## Cruft Update Guidance Preservation

Before deleting `merge-standards.md`, extract its logic into a runbook. The core of what
it does:

- After `cruft update`, seven files need careful merging: `CLAUDE.md`, `REUSE.toml`,
  `README.md`, `docs/template_feedback.md`, `.env.example`, `pyproject.toml`, `mkdocs.yml`
- Rule: never overwrite project-specific sections; only apply baseline changes marked with
  HTML comment blocks
- Workflow: read both files → diff → categorize each change as new/updated/project-specific
  → present to user for approval before applying

Suggest adding this as `docs/cruft-update-guide.md` in the template.

---

## Definition of Done

- [ ] No `.claude/` directory in the template repo root
- [ ] No `.claude/` directory generated in `{{cookiecutter.project_slug}}/`
- [ ] `post_gen_project.py` has no Claude setup functions
- [ ] README updated with user-level install instructions
- [ ] `cruft update` merge logic preserved in `docs/cruft-update-guide.md`
- [ ] `cookiecutter . --no-input` runs clean with no errors
- [ ] Generated project has no `.claude/` directory
- [ ] PR reviewed and merged to main
- [ ] `{{cookiecutter.project_slug}}/.github/copilot-instructions.md` updated: "Black"
      replaced with "ruff format" in both the introductory note and the "What NOT to
      Review" list
- [ ] `{{cookiecutter.project_slug}}/.coderabbit.yaml` compared against `.claude` repo
      baseline; divergences either resolved or documented as intentional

---

## Questions / Decisions Not Made Here

1. **The template repo's own development**: Does the cookiecutter team want to keep using
   Claude Code for template maintenance? If yes, they just need `~/.claude` set up at the
   user level like everyone else: no special per-repo config needed.

2. **`settings.local.json.example`**: This was in `{{cookiecutter.project_slug}}/.claude/`.
   If it contained useful local settings guidance (editor paths, model overrides), that
   content should move to a developer onboarding doc rather than disappear.
