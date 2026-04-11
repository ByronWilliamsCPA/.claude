---
title: "Adding an Agent"
schema_type: common
status: draft
owner: core-maintainer
purpose: "Guide for adding a new agent to .claude/agents/."
tags:
  - contributing
  - agents
  - development
---

Before adding an agent, confirm it should be an agent and not a skill. Use [ADR-004](../architecture/adr/ADR-004-skill-vs-agent-boundary.md) as your guide. The short version: if the capability needs explicit invocation, an isolated context, and scoped tool restrictions, it is an agent. If it auto-triggers on keywords and runs in the main conversation, it is a skill.

If you are unsure, read [Getting Started → Picking Agents vs Skills](../getting-started/picking.md) first.

## Anatomy of an Agent File

Agent files are markdown documents with YAML frontmatter followed by the agent's system prompt. They live in `.claude/agents/` as a single `.md` file (no subdirectory).

```markdown
---
name: my-agent
description: One-sentence description used by the Agent tool picker and catalog.
model: sonnet
tools: ["Read", "Grep", "Glob"]
---

You are a specialist in [domain]. Your task is [specific purpose].

## Your responsibilities

- [Responsibility 1]
- [Responsibility 2]

## What to return

Return [output format] at the end of your analysis.
```

## Frontmatter Fields

| Field | Required | Notes |
| --- | --- | --- |
| `name` | Yes | Lowercase kebab-case. This is the `subagent_type` value used to invoke the agent. Must be unique across all agent files. |
| `description` | Yes | One sentence. Used by the `Agent` tool picker and in `AGENTS-AND-SKILLS.md`. |
| `model` | Yes | `sonnet` for most agents. Use `opus` only for tasks requiring maximum reasoning depth. `haiku` for lightweight utilities. |
| `tools` | Yes | Array of permitted built-in Claude Code tools. Keep this minimal. |

## Naming Convention

Filename: `{domain-prefix}-{purpose}.md` or `{purpose}.md` for single-domain agents.

Domain prefixes in use: `owasp-`, `test-`, `diagram-`, `database-`, `devops-`, `git-`, `github-`, `frontend-`, `document-`, `writing-`.

The `name:` field in frontmatter does not need to match the filename, but they should be consistent for discoverability. Example: file `owasp-web.md`, name `owasp-web`.

## Choosing Tool Restrictions

Start with the minimum needed:

- **Read-only analysis** (security audits, code review): `["Read", "Grep", "Glob"]`
- **Analysis with bash**: `["Read", "Bash", "Grep", "Glob"]`
- **Write access** (code generation, documentation): `["Read", "Write", "Edit", "Grep", "Glob"]`
- **Agent delegation** (orchestrators): add `"Agent"` to the above

Avoid giving agents `Write` or `Bash` unless the task genuinely requires it. Agents with only `Read`, `Grep`, and `Glob` cannot make accidental changes.

## Writing the System Prompt

The prompt body after the frontmatter is the agent's complete system prompt. Structure it with:

1. **Role statement** — who the agent is and its domain
2. **Responsibilities** — what tasks it performs
3. **Output format** — how results should be structured (what to include, length constraints, headers)
4. **References** — any files, standards, or ADRs the agent should consult

Keep the prompt focused. Agents with well-scoped prompts produce more reliable results than generalists.

## Testing

After creating the file, test by invoking the agent from a Claude Code session:

```text
Use the [my-agent] agent to [specific task].
```

Verify:

- The agent is found (no "unknown agent type" error)
- The tool set is correct — the agent should not attempt tools you did not list
- The output shape matches what the prompt specifies
- The agent completes without requesting more permissions

## Registering in the Catalog

After testing, add the agent to `AGENTS-AND-SKILLS.md` at the repo root. This is the canonical human-readable catalog referenced from the docs site.

## See Also

- [ADR-004 Skill vs Agent Boundary](../architecture/adr/ADR-004-skill-vs-agent-boundary.md) — the classification rubric
- [Architecture → Agent Dispatch](../architecture/agent-dispatch.md) — how agents are invoked at runtime
- [Agents Catalog](../reference/agents.md) — the current full catalog
