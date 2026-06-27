---
title: "MCP Strategy"
schema_type: common
status: draft
owner: core-maintainer
purpose: "Reference wrapper for the MCP tiered loading strategy and tool tier assignments."
tags:
  - reference
  - mcp_strategy
  - technical
---

This page summarizes the MCP tool loading strategy. The authoritative definition is in `.claude/rules/mcp-strategy.md`. For the architecture narrative and design decisions, see [Architecture → MCP Tiered Loading](../architecture/mcp-tiered-loading.md) and [ADR-003](../architecture/adr/ADR-003-tiered-mcp-loading.md).

## The Three Tiers at a Glance

![MCP tier loading state diagram](../architecture/diagrams/mcp_tier_loading.svg)

| Tier | Load trigger | Token cost | Use for |
| --- | --- | --- | --- |
| Tier 1 | Session start, always | ~3K tokens | Tools needed in majority of sessions |
| Tier 2 | Agent or skill invocation | Per-bundle | Tools needed only with specific agents |
| Tier 3 | Keyword in user prompt | Per-trigger | Tools needed for specific task domains |

## Tier 1: Always Loaded

| Server | Tools |
| --- | --- |
| `zen` | `thinkdeep`, `codereview`, `tiered_consensus`, `chat` |
| `context7` | `resolve_library_id`, `get_library_docs` |
| `github` | `get_file_contents` |

## Tier 2: Agent Bundles (Selected)

| Agent or Skill | MCP tools loaded |
| --- | --- |
| `security-auditor` | `zen.secaudit`, `sentry.*`, `github.code_security`, `postgres.analyze_db_health` |
| `code-reviewer` | `zen.precommit`, `zen.challenge`, `github.pull_requests` |
| `test-engineer` | `zen.testgen`, `playwright.*` |
| `database-operations-agent` | `postgres.*` |
| `devops-deployment-agent` | `docker.*`, `github.actions`, `sentry.*` |
| `/git pr` skill | `zen.codereview`, `github.pull_requests`, `github.issues`, `sentry.list_releases` |
| `/project-planning` skill | `zen.planner`, `zen.tiered_consensus`, `mermaid.*` |

Full bundle list: `.claude/rules/mcp-strategy.md`.

## Tier 3: Keyword Triggers

| Keywords | Tools loaded |
| --- | --- |
| `dockerfile`, `container`, `deploy`, `kubernetes`, `k8s` | `docker.*` |
| `e2e`, `playwright`, `browser test`, `ui test` | `playwright.*` |
| `database`, `sql`, `postgres`, `migration` | `postgres.*` |
| `sentry`, `error monitoring`, `exception` | `sentry.*` |
| `diagram`, `mermaid`, `uml`, `flowchart` | `mermaid.*`, `uml-mcp-server.*` |

## Binary-Managed Servers (Outside the Tiers)

Some MCP servers manage their own Claude Code wiring and are not part of the
tiered strategy. They load unconditionally via `~/.claude/.mcp.json` (gitignored),
which Claude Code merges with `settings.json`'s `mcpServers` block.

| Server | Tools | Config |
| --- | --- | --- |
| `codebase-memory-mcp` | 14 tools: `search_graph`, `trace_path`, `get_architecture`, `detect_changes`, Cypher queries, dead code detection, ADR management, and more | `~/.claude/.mcp.json`, managed by `codebase-memory-mcp install` |

Do not add binary-managed servers to the tier tables. Their config changes with
binary upgrades, not with edits to `mcp-strategy.md`.

Setup: [docs/getting-started/codebase-memory-mcp.md](../getting-started/codebase-memory-mcp.md)

## Placement and Promotion

All new MCP tools default to Tier 3. To request promotion:

1. Collect usage data: `./scripts/track-mcp-usage.sh --report`
2. Tier 3 → Tier 2: tool appears in >50% of a specific agent's sessions
3. Tier 2 → Tier 1: tool appears in >80% of all sessions across agent types
4. Edit `.claude/rules/mcp-strategy.md` with the new tier assignment

## See Also

- `.claude/rules/mcp-strategy.md`: operative tier definitions and full tool list
- [Architecture → MCP Tiered Loading](../architecture/mcp-tiered-loading.md): narrative with context budget analysis
- [ADR-003 Tiered MCP Loading](../architecture/adr/ADR-003-tiered-mcp-loading.md): design decisions and alternatives
- `scripts/track-mcp-usage.sh`: usage tracking for evidence-based promotion decisions
