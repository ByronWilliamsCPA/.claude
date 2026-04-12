---
title: "Adding a Skill"
schema_type: common
status: draft
owner: core-maintainer
purpose: "Guide for adding a new skill to .claude/skills/."
tags:
  - contributing
  - skills
  - development
---

Before adding a skill, confirm it should be a skill and not an agent. Use [ADR-004](../architecture/adr/ADR-004-skill-vs-agent-boundary.md) as your guide. The short version: if the capability is a repeatable one-step automation that should trigger from a keyword or slash command and run in the main conversation, it is a skill.

If you are unsure, read [Getting Started → Picking Agents vs Skills](../getting-started/picking.md) first.

## Directory Structure

Each skill is a directory under `.claude/skills/<skill-name>/` containing at minimum a `SKILL.md` file:

```text
.claude/skills/my-skill/
└── SKILL.md
```

Additional files (helper scripts, templates) can live in the same directory if needed by the skill's workflow.

## Anatomy of `SKILL.md`

`SKILL.md` defines the skill's trigger and workflow instructions. The format is flexible, but the following sections are expected:

```markdown
# My Skill

## Overview

One paragraph describing what this skill does and when to use it.

## Trigger

This skill is invoked with `/my-skill` or when the user asks to [description of trigger intent].

## Workflow

1. Step one — what Claude does first
2. Step two — what Claude does next
3. Step three — what the skill produces

## Output

Describe what the user should expect when the skill completes.
```

## Triggers

Skills can be triggered two ways:

**Slash commands** — the user types `/my-skill` explicitly. This is the most reliable trigger and should be used for workflows that the user intentionally invokes. The `git` skill is triggered this way (`/commit`, `/git pr`).

**Keyword patterns** — the `Skill` tool fires when matching words appear in the user's prompt. These are registered in the skill system's matcher configuration. Keyword triggers are appropriate for skills that should fire contextually (e.g., `frontend-design` fires on "build UI", "create component", "design page").

For most new skills, start with an explicit slash command trigger. Keyword triggers require more care — they can fire unexpectedly if the trigger words are too common.

## The Planning Bridge Gate

The `Skill` PreToolUse hook includes a planning bridge gate (`scripts/planning-bridge-gate.sh`). For skills that involve significant code changes or architecture decisions, the gate may require a plan to be approved first. If your skill should bypass this gate, document the reason in `SKILL.md`.

## Testing

After creating the directory and `SKILL.md`, test the trigger:

1. Start a Claude Code session in the relevant working directory.
2. Type the slash command or trigger phrase.
3. Verify the skill loads (Claude should describe the steps it is about to take).
4. Verify the output matches what `SKILL.md` specifies.

Check the `PreToolUse` and `PostToolUse` hooks fire as expected (visible in the hook status messages).

## Registering in the Catalog

After testing, add the skill to `AGENTS-AND-SKILLS.md` at the repo root and to the [Skills Catalog](../reference/skills.md) under the appropriate section.

## See Also

- [ADR-004 Skill vs Agent Boundary](../architecture/adr/ADR-004-skill-vs-agent-boundary.md) — the classification rubric
- [Architecture → Agent Dispatch](../architecture/agent-dispatch.md) — how skills are dispatched at runtime
- [Skills Catalog](../reference/skills.md) — the current full catalog
- [Adding a Hook](adding-hooks.md) — if your skill needs a dedicated hook entry
