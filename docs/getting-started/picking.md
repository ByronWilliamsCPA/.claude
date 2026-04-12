---
title: "Picking Agents vs Skills"
schema_type: common
status: draft
owner: core-maintainer
purpose: "Decision guide for when to use an agent, a skill, a rule, or a standard."
tags:
  - new_dev
  - agents
  - skills
  - rules
  - standards
  - guide
---

Four capability forms extend Claude Code's behavior in this repo. They look similar but work very differently. This page helps you choose the right one.

For the load-bearing version of this decision with full rationale, see [ADR-004](../architecture/adr/ADR-004-skill-vs-agent-boundary.md).

## Quick Decision Table

| If you need... | Use a... | How it invokes |
| --- | --- | --- |
| A one-shot delegated investigation or specialized task | Agent | `Agent` tool, explicit `subagent_type` |
| A repeated workflow that should auto-trigger from a keyword | Skill | `Skill` tool, keyword or slash command |
| Behavior that must shape every single session turn | Rule | Referenced from `CLAUDE.md`, auto-loaded at session start |
| Reference material consulted only for specific tasks | Standard | Read on demand when a task requires it |

## Examples

### Agent — code-reviewer

You have just written a feature and want an independent code review before creating a PR. The `code-reviewer` agent runs in isolation, reads the diff, applies the project standards, and returns a structured review. You invoke it explicitly:

> "Use the code-reviewer agent to review my staged changes."

### Skill — /quality

You want to run Ruff format, lint, and BasedPyright on your Python files before committing. This is a routine, one-step workflow that should fire the same way every time. You trigger it with:

> `/quality`

### Rule — python.md

Linting standards, function complexity limits, and coverage thresholds must apply to every Python file edit, not just when you remember to ask. The `python.md` rule is referenced from `CLAUDE.md` and loads at session start so it is always active.

### Standard — packages.md

When you are choosing between `httpx` and `requests` for a new project, you look up `packages.md` for the canonical choice. You only need it for that specific decision — it should not load into every session.

## When Not to Add Anything

Before adding a new agent, skill, rule, or standard, ask:

- **Does a similar capability already exist?** Check [Agents Catalog](../reference/agents.md) and [Skills Catalog](../reference/skills.md). 40+ skills and 43 agents cover most common tasks. Composing existing capabilities is almost always better than adding new ones.
- **Is this a one-time task?** If you only need the behavior once, describe it inline to Claude rather than codifying it. Capabilities in the repo should be reused repeatedly.
- **Is this better as a `CLAUDE.md` instruction?** Short, direct project-specific instructions (not session-wide behavioral rules) belong in a project-local `CLAUDE.md`, not in `.claude/rules/`.

## See Also

- [Architecture → Agent Dispatch](../architecture/agent-dispatch.md) — how dispatch works at runtime
- [ADR-004 Skill vs Agent Boundary](../architecture/adr/ADR-004-skill-vs-agent-boundary.md) — full rubric with all four capability forms
- [Contributing → Adding an Agent](../contributing/adding-agents.md) — when you decide you do need a new agent
- [Contributing → Adding a Skill](../contributing/adding-skills.md) — when you decide you do need a new skill
