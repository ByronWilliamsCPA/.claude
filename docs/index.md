---
title: "Claude Code Configuration"
schema_type: common
status: published
owner: core-maintainer
purpose: "Role-based landing page for Claude Code Configuration documentation."
tags:
  - documentation
  - home
  - overview
  - new_dev
  - technical
---

A repository of agents, skills, hooks, and standards that customize Claude Code for professional development workflows.

## Pick Your Path

| I am a... | I want to... | Start here |
| --- | --- | --- |
| **New developer** | Clone the repo and run my first agent | [Getting Started → Install](getting-started/install.md) |
| **New developer** | Trigger my first skill | [Getting Started → First Skill](getting-started/first-skill.md) |
| **New developer** | Understand when to use what | [Picking Agents vs Skills](getting-started/picking.md) |
| **Maintainer** | Understand the two-layer install model | [Architecture → Install Model](architecture/install-model.md) |
| **Maintainer** | See why a decision was made | [Architecture → Decisions (ADRs)](architecture/adr/index.md) |
| **Maintainer** | See how hooks fire during a turn | [Architecture → Hook Pipeline](architecture/hook-pipeline.md) |
| **Maintainer** | Understand the MCP context budget | [Architecture → MCP Tiered Loading](architecture/mcp-tiered-loading.md) |
| **Maintainer** | Add a new agent, skill, or hook | [Contributing](contributing/index.md) |
| **Auditor** | Review the security and install surface | [Architecture Overview](architecture/index.md) + [ADR-001](architecture/adr/ADR-001-two-layer-symlink-install.md) |
| **Looking for something specific** | Find a file by name | Use the search box in the top right. |

## New to This Project?

**New developer path** (15 minutes):

1. [Install](getting-started/install.md) — clone, submodules, `setup.sh`
2. [Your First Agent](getting-started/first-agent.md) — invoke an agent via the `Agent` tool
3. [Your First Skill](getting-started/first-skill.md) — trigger a skill by keyword
4. [Troubleshooting](getting-started/troubleshooting.md) — common symlink and hook issues

**Architecture path** (60 minutes, in order):

1. [Architecture Overview](architecture/index.md) — the mental model
2. [Install Model](architecture/install-model.md) — two-layer symlink diagram + [ADR-001](architecture/adr/ADR-001-two-layer-symlink-install.md)
3. [Hook Pipeline](architecture/hook-pipeline.md) — lifecycle diagram + [ADR-002](architecture/adr/ADR-002-hook-composition.md)
4. [Agent Dispatch](architecture/agent-dispatch.md) — runtime flow + [ADR-004](architecture/adr/ADR-004-skill-vs-agent-boundary.md)
5. [MCP Tiered Loading](architecture/mcp-tiered-loading.md) — context budget + [ADR-003](architecture/adr/ADR-003-tiered-mcp-loading.md)
6. [ADR Index](architecture/adr/index.md) — full decision log

## System at a Glance

- **43 agents** — one-shot specialized prompts. See [Agents Catalog](reference/agents.md).
- **40+ skills** — trigger-based automations. See [Skills Catalog](reference/skills.md).
- **5 hook types** — PreToolUse, PostToolUse, UserPromptSubmit, SessionStart, Stop. See [Hooks Reference](reference/hooks.md).
- **5 submodules** — reference-library, anthropics-plugins, anthropics-skills, image-generation, superpowers. See [Submodule Strategy](architecture/submodule-strategy.md).
- **11+ rules and standards** — in `.claude/rules/` and `.claude/standards/`. See [Rules vs Standards](architecture/rules-vs-standards.md).

## See Also

- [Architecture Decision Records](architecture/adr/index.md) — load-bearing design decisions with rationale.
- [Contributing](contributing/index.md) — how to add an agent, skill, hook, ADR, or diagram.
- `CLAUDE.md` at the repo root — global development standards.
- `AGENTS-AND-SKILLS.md` at the repo root — canonical agent and skill catalog.
