---
title: "MCP Tiered Loading"
schema_type: common
status: draft
owner: core-maintainer
purpose: "Narrative description of the Tier 1/2/3 MCP loading strategy and its context budget rationale."
tags:
  - architecture
  - mcp_strategy
  - technical
---

The repo connects Claude to dozens of external tools via the Model Context Protocol (MCP): database clients, browser automation, observability platforms, diagram renderers, and more. Every connected tool consumes context tokens to describe its schema to the model.

Before tiered loading, all tools loaded at session start: roughly 55,000 tokens on tool descriptions alone, before a single line of user input. Tiered loading reduces that to approximately 3,000 tokens at session start, with additional tools loaded only when the current task actually needs them.

For the design decisions behind this approach, see [ADR-003](adr/ADR-003-tiered-mcp-loading.md).

## The Context Budget Problem

A Claude Code session with a 128K-token context window has roughly 127K tokens of usable space after the system prompt. Loading 80+ MCP tool schemas at session start consumes ~55K of those tokens: 43% of the context window, before any work begins. Multi-file coding sessions, long code reviews, and document-intensive tasks routinely exceed the remaining budget.

The solution is not to use fewer MCP tools. It is to load tools only when the current task needs them.

## Diagram

![MCP tier loading state diagram](diagrams/mcp_tier_loading.svg)

## The Three Tiers

### Tier 1: Always Loaded

Tier 1 contains tools used in the large majority of sessions regardless of task type. Loading them unconditionally is correct because the cost of not having them (re-injecting on demand, breaking mid-task) exceeds the ~3K token overhead.

Current Tier 1 servers:

| Server | Tools | Why Tier 1 |
| --- | --- | --- |
| `zen` | thinkdeep, codereview, tiered_consensus, chat | Decision support and deep analysis used across almost all non-trivial tasks |
| `context7` | resolve_library_id, get_library_docs | Library documentation lookups needed in most coding sessions |
| `github` | get_file_contents | Basic file access used whenever working with GitHub-hosted content |

### Tier 2: Agent-Bundled

Tier 2 tools are loaded when a specific agent or skill is invoked. The agent invocation is the loading trigger; no other signal is needed.

Example agent bundles:

| Agent / Skill | MCP Tools Loaded |
| --- | --- |
| `security-auditor` | `zen.secaudit`, `sentry.*`, `github.code_security`, `postgres.analyze_db_health` |
| `code-reviewer` | `zen.precommit`, `zen.challenge`, `github.pull_requests` |
| `test-engineer` | `zen.testgen`, `playwright.*` |
| `database-operations-agent` | `postgres.*` |
| `/git pr` skill | `zen.codereview`, `github.pull_requests`, `github.issues`, `sentry.list_releases` |
| `/project-planning` skill | `zen.planner`, `zen.tiered_consensus`, `mermaid.*` |

The full bundle list is in `.claude/rules/mcp-strategy.md`.

### Tier 3: Keyword-Triggered

Tier 3 tools load dynamically when specific words appear in the user's prompt. The `keyword-tool-trigger.sh` PreToolUse hook scans each message for registered keywords and loads the associated tools on match.

Current keyword-to-tool mappings:

| Trigger keywords | Tools loaded |
| --- | --- |
| `dockerfile`, `container`, `deploy`, `kubernetes`, `k8s` | `docker.*` |
| `e2e`, `playwright`, `browser test`, `ui test` | `playwright.*` |
| `database`, `sql`, `postgres`, `migration` | `postgres.*` |
| `sentry`, `error monitoring`, `exception` | `sentry.*` |
| `diagram`, `mermaid`, `uml`, `flowchart` | `mermaid.*`, `uml-mcp-server.*` |

Keyword triggers are fuzzy: they fire on substring match, not exact phrase. A false positive (loading Docker tools when "deploy" appears in a non-Docker context) costs a few hundred tokens, not a session failure.

## Promotion Rules

All new MCP tools default to Tier 3. Tier changes require usage evidence from `scripts/track-mcp-usage.sh`.

| Promotion path | Evidence required |
| --- | --- |
| Tier 3 → Tier 2 | Tool activates in >50% of sessions for a specific agent or skill |
| Tier 2 → Tier 1 | Tool activates in >80% of all sessions across agent types |

Demotion works in reverse: a Tier 1 tool that drops below 60% session frequency is a candidate for Tier 2. Run `./scripts/track-mcp-usage.sh --report` to see current usage counts.

## See Also

- [ADR-003 Tiered MCP Loading](adr/ADR-003-tiered-mcp-loading.md): why this structure was chosen
- `.claude/rules/mcp-strategy.md`: the operative tier definitions and full tool assignments
- `scripts/track-mcp-usage.sh`: usage tracking for promotion/demotion decisions
- `scripts/mcp-tool-loader.sh`: the loader script invoked for Tier 2 agent/skill bundles
