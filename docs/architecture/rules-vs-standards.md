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

**`.claude/rules/`**: pointer-referenced, read on demand.

Rule files are referenced from `CLAUDE.md` using explicit "see `.claude/rules/X.md`" pointers. No mechanism in Claude Code auto-loads a rule file into the system prompt at session start. A rule file only enters context when Claude reads it, either by following one of these CLAUDE.md pointers while the surrounding instruction is relevant to the current turn, or because a hook explicitly injects its content (the `delegation-reminder` SessionStart hook, for example, prints the `supervisor.md` delegation core directly rather than relying on Claude to go read the file).

Current rules:

| File | Scope | Purpose |
| --- | --- | --- |
| `python.md` | Python files | Linting standards, function quality gates, coverage thresholds |
| `git-workflow.md` | Git operations | Branch naming, commit signing, conventional commits |
| `testing.md` | Test files | Test scope, root-cause order, golden file protection |
| `writing.md` | All files | No em-dashes, AI pattern blacklist, grammar authority |
| `mcp-strategy.md` | All sessions | Tier 1/2/3 MCP loading definitions |
| `supervisor.md` | All sessions | Reference material for agent assignment patterns and reviewer model pins; its delegation core is now inlined directly in CLAUDE.md and reinforced every session by the `delegation-reminder` SessionStart hook, rather than depended on as a stand-alone auto-load |
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

> **Does this content need a `CLAUDE.md` pointer so Claude reads it whenever the surrounding instruction is relevant?**

If yes: place it in `.claude/rules/` and add a `see .claude/rules/X.md` reference from `CLAUDE.md` next to the instruction it supports. If no: place it in `.claude/standards/`, where it is discovered only through an agent's own prompt or an ad hoc lookup, never through a `CLAUDE.md` pointer.

The question is intentionally conservative. If the content is needed in *most* sessions but not *all*, it still belongs in `standards/`. A `CLAUDE.md` pointer raises the odds Claude reads a file on a relevant turn, but it is never a guarantee either way, so a pointer to content that is only occasionally useful buys little and adds a permanent line to `CLAUDE.md`. Reserve `rules/` for content tied to a recurring, nameable trigger (a file type, an operation) that CLAUDE.md's prose can name next to the pointer.

When adding a rule, also consider whether it should be path-scoped. Rules that apply only to Python files can include a `paths:` frontmatter header (see `python.md`, `testing.md`) or a `> path-scoped to Python files` note near the top. This is a documentation convention for reviewers and for CLAUDE.md's pointer text, not a technical filter: nothing in Claude Code restricts a rule file's visibility by path, and nothing loads it automatically regardless of path.

## Why Mixing Them Is a Bug

**Standard mis-filed as a rule**: `CLAUDE.md` gains a pointer implying the content is broadly relevant. `writing-quality.md` contains detailed quality thresholds relevant only when editing prose. If it were pointed to from `rules/` the way `python.md` or `writing.md` are, Claude becomes more likely to read it on turns that do not need it (coding, debugging, git operations), burning context on a lookup the turn did not require. Multiply by several mis-filed standards and the wasted-read pattern matches the pre-tiered-MCP problem described in [MCP Tiered Loading](mcp-tiered-loading.md).

**Rule mis-filed as a standard**: There is no `CLAUDE.md` pointer prompting a read at all. If `git-workflow.md` were in `standards/`, nothing would cue Claude to consult it before a commit; the behavior it enforces (commit signing, conventional commit format, branch naming) would depend entirely on Claude discovering the file unprompted. This failure mode is invisible: the file passes all syntax checks, builds without warnings, and looks correct in the docs site.

Both failure modes are silent. There is no runtime error when a file is in the wrong directory, only reduced odds that the right content gets read at the right time. Human review of any new addition to either directory is the only gate.

## See Also

- [ADR-006 Rules vs Standards Boundary](adr/ADR-006-rules-vs-standards.md): why this split exists
- [ADR-004 Skill vs Agent Boundary](adr/ADR-004-skill-vs-agent-boundary.md): the full four-way taxonomy: skills, agents, rules, standards
- `CLAUDE.md`: the session entry point that references rule files
- [Contributing → Adding a Hook](../contributing/adding-hooks.md): hooks enforce behavior differently from rules; understand the distinction
