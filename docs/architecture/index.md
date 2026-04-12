---
title: "Architecture"
schema_type: common
status: draft
owner: core-maintainer
purpose: "Overview of Claude Code Configuration architecture and load-bearing decisions."
tags:
  - architecture
  - technical
  - overview
---

This section is for technical maintainers and anyone who needs to understand not just what the system does, but why it was built this way. Everything here is meant to answer one question: "Why can't I just change this?"

The system has six load-bearing decisions. Each one has an ADR that records the context, the decision, the alternatives that were rejected, and the consequences that follow from the choice. If you are about to modify the install model, add a hook, change the MCP configuration, or add a new capability type, read the relevant ADR first. Silently reversing a load-bearing decision causes breakage that is hard to trace back to the original cause.

## Load-Bearing Decisions

Each decision has its own ADR. Read these first if you plan to modify the install layer, the hook pipeline, or the agent dispatch model.

- [ADR-001 Two-Layer Symlink Install](adr/ADR-001-two-layer-symlink-install.md)
- [ADR-002 Hook Composition and Ordering](adr/ADR-002-hook-composition.md)
- [ADR-003 Tiered MCP Loading](adr/ADR-003-tiered-mcp-loading.md)
- [ADR-004 Skill vs Agent Boundary](adr/ADR-004-skill-vs-agent-boundary.md)
- [ADR-005 Submodule Extension Model](adr/ADR-005-submodule-extension-model.md)
- [ADR-006 Rules vs Standards Boundary](adr/ADR-006-rules-vs-standards.md)
- [ADR-007 Dual-Audience Documentation Structure](adr/ADR-007-dual-audience-docs.md)

## Diagrams

Four PlantUML diagrams visualize the system. Sources live under [diagrams/](diagrams/index.md); rendered SVGs are committed next to their sources.

- `install_layer` — the two-layer symlink install flow.
- `hook_pipeline` — hook execution order across a conversation turn.
- `agent_skill_dispatch` — how Skills and Agents get invoked at runtime.
- `mcp_tier_loading` — context-budget tiering for MCP tools.

## Narrative Pages

Each narrative page pairs prose with a specific diagram and its backing ADR(s):

- [Install Model](install-model.md)
- [Hook Pipeline](hook-pipeline.md)
- [Agent Dispatch](agent-dispatch.md)
- [MCP Tiered Loading](mcp-tiered-loading.md)
- [Submodule Strategy](submodule-strategy.md)
- [Rules vs Standards](rules-vs-standards.md)

## How to Read This Section

**If you are modifying the install topology** (new symlink, new submodule, changing where `~/.claude/` points): start with [Install Model](install-model.md) and [ADR-001](adr/ADR-001-two-layer-symlink-install.md).

**If you are adding or changing a hook**: start with [Hook Pipeline](hook-pipeline.md) and [ADR-002](adr/ADR-002-hook-composition.md). Remember that `hooks.json` is the source of truth — changes to `~/.claude/settings.json` directly will be lost.

**If you are adding a new agent, skill, rule, or standard**: start with [Agent Dispatch](agent-dispatch.md) and [ADR-004](adr/ADR-004-skill-vs-agent-boundary.md). The classification rubric determines which form is appropriate.

**If you are changing MCP configuration**: start with [MCP Tiered Loading](mcp-tiered-loading.md) and [ADR-003](adr/ADR-003-tiered-mcp-loading.md). New tools default to Tier 3.

**If you are adding documentation**: start with [ADR-007](adr/ADR-007-dual-audience-docs.md) for the nav structure and frontmatter schema decisions. Use the slim ADR template at `docs/architecture/adr/_template.md` for new ADRs.

**If you are reviewing a past decision**: go directly to the [ADR Index](adr/index.md) and read the specific ADR. Each one records what was decided, what was rejected, and why.
