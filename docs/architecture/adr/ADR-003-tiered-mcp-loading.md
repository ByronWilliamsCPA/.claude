---
title: "ADR-003: Tiered MCP Loading Strategy"
schema_type: common
status: draft
owner: core-maintainer
purpose: "Records the Tier 1/2/3 MCP loading split and the rules for promoting tools between tiers."
tags:
  - adr
  - decisions
  - mcp_strategy
  - architecture
---

> **Status**: Accepted
>
> **Decision date**: 2026-04-11
>
> **Deciders**: Byron Williams

## Context

The Model Context Protocol (MCP) allows Claude Code to call external tools: database clients, browser automation, observability platforms, diagram renderers, and more. This repo's MCP configuration exposes roughly 80 tools across multiple servers.

The problem: every tool loaded into a session consumes context tokens to describe its schema. Before tiered loading, all 80+ tools were present in every session. Measured token cost: approximately 55,000 tokens at session start, before a single line of user input. That left under half the context window for actual work in a 128K-token session, and made long coding sessions hit context limits before completing multi-file tasks.

Most of those tools are irrelevant to most sessions. A session writing Python unit tests does not need Docker, Playwright, or Postgres tools. A session reviewing a database migration does not need image-generation tools. Loading everything always is wasteful and actively harmful.

`.claude/rules/mcp-strategy.md` defines the solution: a three-tier partition. This ADR records why that partition exists, how tools are assigned to tiers, and what it takes to move a tool between tiers.

## Decision

MCP tools are partitioned into three tiers. Each tier has a distinct loading trigger:

**Tier 1: Always loaded** (session start, every session)

Tier 1 contains tools used in the majority of sessions, regardless of task type. The cost of loading them is paid once at session start; the cost of not loading them is re-injecting them on demand for nearly every session.

Current Tier 1 servers: `zen` (thinkdeep, codereview, tiered_consensus, chat), `context7` (resolve_library_id, get_library_docs), `github` (get_file_contents).

Token budget for Tier 1: ~3,000 tokens (vs. ~55,000 before tiering: an 85–95% reduction).

**Tier 2: Agent-bundled** (loaded when a specific agent is invoked)

Tier 2 tools are specialized enough that they are only needed when a particular agent is active. The agent's invocation is the loading trigger; when the agent finishes, the tools are no longer active in the session.

Example bundles: `security-auditor` loads `zen.secaudit`, `sentry.*`, `github.code_security`; `code-reviewer` loads `zen.precommit`, `zen.challenge`, `github.pull_requests`; `database-operations-agent` loads `postgres.*`.

Skill bundles follow the same pattern: `/git pr` loads `zen.codereview`, `github.pull_requests`, `github.issues`, `sentry.list_releases`.

**Tier 3: Keyword-triggered** (loaded when matching terms appear in the user's prompt)

Tier 3 tools are loaded dynamically by the `keyword-tool-trigger.sh` PreToolUse hook when specific words appear in the conversation. This handles tools that are neither universal enough for Tier 1 nor cleanly associated with a single agent.

Example trigger: any prompt containing "dockerfile", "container", "deploy", or "kubernetes" loads `docker.*`.

### Promotion rules

New MCP tools default to Tier 3. Promotion requires evidence:

- Tier 3 → Tier 2: the tool is consistently needed with a specific agent or skill. Evidence: usage data from `track-mcp-usage.sh` showing the tool activates in >50% of that agent's sessions.
- Tier 2 → Tier 1: the tool is needed across many different agent types in the majority of sessions. Evidence: usage data showing the tool activates in >80% of all sessions.

Demotion follows the same logic in reverse: a Tier 1 tool that stops appearing in usage data should drop to Tier 2 or Tier 3.

## Alternatives Considered

**Load all tools always**: The status quo before this decision. Consumed ~55K tokens per session on tool schemas alone. Unacceptable context budget.

**Per-session manual tool selection**: The user declares which MCP servers they need at the start of each session. High friction, easy to forget, and requires users to know the full tool taxonomy before they need any specific tool.

**Only Tier 1 with no on-demand loading**: Fixes the context budget problem but loses the specialized capability surface. A session that needs Playwright testing or Postgres query analysis must work without those tools.

**Dynamic loading without keyword triggers (Tier 2 only)**: Works when tasks clearly map to a single agent. Fails for cross-cutting concerns (e.g., a code review that also needs Docker context) and for ad-hoc tool needs that do not justify a dedicated agent.

## Consequences

### Positive

- Context budget reduced from ~55K to ~3K tokens at session start, leaving the bulk of the context window for actual work.
- Tool load is proportional to task complexity: simple tasks never pay the cost of specialized tooling.
- `track-mcp-usage.sh` provides data-driven evidence for tier assignment changes, avoiding both over-loading and under-loading.

### Negative

- Tier 3 keyword triggers can fire incorrectly if trigger words appear incidentally (e.g., mentioning "database" in a non-database context loads Postgres tools). False positives are low-cost (a few extra tokens) but not zero.
- Adding a new MCP tool requires a conscious placement decision. Defaulting to Tier 3 is safe, but teams unfamiliar with the strategy may add tools to Tier 1 inappropriately.
- Tool availability is session-state-dependent. An agent invoked after another agent may have different tools available than the same agent invoked fresh, if the first agent's bundle was not cleared.

### Neutral

- Tier boundaries are configuration, not code. Changing a tool's tier requires editing `.claude/rules/mcp-strategy.md` and the relevant `mcp_config.yaml` entries, not code changes.

## References

- `.claude/rules/mcp-strategy.md`: the operative tier definitions and tool assignments
- `scripts/track-mcp-usage.sh`: usage data collection for tier promotion decisions
- `scripts/mcp-tool-loader.sh`: agent/skill bundle loading script
- `scripts/keyword-tool-trigger.sh`: Tier 3 keyword detection PreToolUse hook
- `docs/architecture/mcp-tiered-loading.md`: narrative explanation with embedded diagram
- `docs/architecture/diagrams/mcp_tier_loading.svg`: state diagram of tier transitions
