---
title: "Contributing"
schema_type: common
status: draft
owner: core-maintainer
purpose: "Overview of the contribution workflow for Claude Code Configuration."
tags:
  - contributing
  - development
  - overview
---

This section is for adding new agents, skills, hooks, ADRs, or diagrams to the repo. If you are just getting started, see [Getting Started](../getting-started/index.md) first.

## Workflow

1. Read the relevant ADR for the area you are changing.
2. Follow the corresponding "Adding a..." guide below.
3. Run local validation: `uv run python tools/validate_front_matter.py docs` and `uv run mkdocs build --strict`.
4. Follow the git workflow in `.claude/rules/git-workflow.md`.

## Guides

- [Adding an Agent](adding-agents.md)
- [Adding a Skill](adding-skills.md)
- [Adding a Hook](adding-hooks.md)
- [Writing ADRs](writing-adrs.md)
- [Writing Diagrams](writing-diagrams.md)
- [Frontmatter Standard](../frontmatter-standard.md)

## Existing References

- `CONTRIBUTING.md`: top-level contribution guide.
- `.claude/rules/git-workflow.md`: branch, commit, and PR conventions.
- `.claude/rules/pre-commit.md`: pre-commit checklist.
