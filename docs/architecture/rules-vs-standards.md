---
title: "Rules vs Standards"
schema_type: common
status: draft
owner: core-maintainer
purpose: "Narrative description of the loading-semantics difference between .claude/rules/ and .claude/standards/."
tags:
  - architecture
  - rules
  - standards
  - technical
---

Two directories under `.claude/` look identical from the filesystem but behave completely differently at runtime. Knowing the difference is required before adding any new behavioral file to the repo.

For the design decisions behind this split, see [ADR-006](adr/ADR-006-rules-vs-standards.md).

## Two Directories, Two Loading Semantics

**`.claude/rules/`**: session-injected behavior.

Rule files are referenced from `CLAUDE.md` using explicit paths. When Claude Code starts a session, it reads `CLAUDE.md` and loads the referenced rule files into the system prompt. Every rule file in `rules/` that is referenced from `CLAUDE.md` is active from the very first turn of every session.

Current rules:

| File | Scope | Purpose |
| --- | --- | --- |
| `python.md` | Python files | Linting standards, function quality gates, coverage thresholds |
| `git-workflow.md` | Git operations | Branch naming, commit signing, conventional commits |
| `testing.md` | Test files | Test scope, root-cause order, golden file protection |
| `writing.md` | All files | No em-dashes, AI pattern blacklist, grammar authority |
| `mcp-strategy.md` | All sessions | Tier 1/2/3 MCP loading definitions |
| `supervisor.md` | All sessions | Agent assignment patterns for common task types |
| `pre-commit.md` | Git operations | Pre-commit checklist before committing |

**`.claude/standards/`**: on-demand reference material.

Standards are never referenced from `CLAUDE.md`. Nothing loads them automatically. They are read when a specific task requires the information they contain: either because the model decides to look them up, or because an agent's prompt instructs it to consult a specific standard.

Current standards:

| File | Purpose |
| --- | --- |
| `packages.md` | Canonical package choices for common task types |
| `writing-quality.md` | Prose quality thresholds for the writing pipeline |

## How to Decide Where a New File Belongs

Ask this single question:

> **Must this content influence behavior in every session, from the very first turn?**

If yes: place it in `.claude/rules/` and add a reference to it from `CLAUDE.md`. If no: place it in `.claude/standards/`.

The question is intentionally conservative. If the content is needed in *most* sessions but not *all*, it still belongs in `standards/`. Load it on demand in the sessions where it applies rather than paying its context cost in sessions where it does not. The cost of an occasional missed lookup is lower than the cost of constant context bloat.

When adding a rule, also consider whether it should be path-scoped. Rules that apply only to Python files can include a note like `> path-scoped to Python files` near the top. This is a social convention for reviewers, not a technical filter: Claude Code loads all referenced rules at session start regardless of what files the session touches.

## Why Mixing Them Is a Bug

**Standard mis-filed as a rule**: The content loads into every session's system prompt. `writing-quality.md` contains detailed quality thresholds relevant only when editing prose. If it were in `rules/`, it would consume context tokens on every coding session, every debugging session, every git operation. Multiply by several mis-filed standards and the context budget impact matches the pre-tiered-MCP problem described in [MCP Tiered Loading](mcp-tiered-loading.md).

**Rule mis-filed as a standards**: The behavior silently stops firing. If `git-workflow.md` were in `standards/`, there would be nothing in the session context to enforce commit signing, conventional commit format, or branch naming. The rule simply does not exist from the session's perspective. This failure mode is invisible: the file passes all syntax checks, builds without warnings, and looks correct in the docs site.

Both failure modes are silent. There is no runtime error when a file is in the wrong directory. Human review of any new addition to either directory is the only gate.

## See Also

- [ADR-006 Rules vs Standards Boundary](adr/ADR-006-rules-vs-standards.md): why this split exists
- [ADR-004 Skill vs Agent Boundary](adr/ADR-004-skill-vs-agent-boundary.md): the full four-way taxonomy: skills, agents, rules, standards
- `CLAUDE.md`: the session entry point that references rule files
- [Contributing → Adding a Hook](../contributing/adding-hooks.md): hooks enforce behavior differently from rules; understand the distinction
