# MCP Tool Loading Strategy

> Reference: `/mcp/mcp_config.yaml` for full configuration
> Based on: [Anthropic's Advanced Tool Use Guide](https://www.anthropic.com/engineering/advanced-tool-use)

## Overview

MCP tools use a tiered strategy to reduce context consumption by 85-95%:
- **Before**: ~55K tokens consumed by 80+ tools at session start
- **After**: ~3K tokens (Tier 1) + context-specific loading

## Tier 1: Always Loaded

| Server | Tools | Purpose |
|--------|-------|---------|
| zen | thinkdeep, codereview, tiered_consensus, chat | Deep analysis, reviews, decisions |
| context7 | resolve_library_id, get_library_docs | Library documentation |
| github | get_file_contents | Basic file access |

## Tier 2: Agent/Skill-Bundled

Loaded automatically when specific agents are invoked:

| Agent | MCP Tools Loaded |
|-------|------------------|
| security-auditor | `zen.secaudit`, `sentry.*`, `github.code_security`, `postgres.analyze_db_health` |
| code-reviewer | `zen.precommit`, `zen.challenge`, `github.pull_requests` |
| test-engineer | `zen.testgen`, `playwright.*` |
| test-writer | `zen.testgen` |
| owasp-dispatch | `zen.secaudit`, `zen.challenge` |
| documentation-writer | `zen.docgen`, `mermaid.*`, `uml-mcp-server.*` |
| database-operations-agent | `postgres.*` |
| devops-deployment-agent | `docker.*`, `github.actions`, `sentry.*` |
| debug-agent | `zen.debug`, `sentry.*`, `postgres.explain_query` |

### Skill Bundles

Loaded automatically when specific skills are invoked:

| Skill | MCP Tools Loaded |
|-------|-----------------|
| `/git` (commit prep) | `zen.precommit`, `github.repos` |
| `/git` (PR prep) | `zen.codereview`, `github.pull_requests`, `github.issues`, `sentry.list_releases` |
| `/project-planning` | `zen.planner`, `zen.tiered_consensus`, `mermaid.*` |

## Tier 3: Keyword-Triggered

| Keywords | Tools Loaded |
|----------|--------------|
| dockerfile, container, image, deploy, docker, kubernetes, k8s | `docker.*` |
| e2e, end-to-end, browser test, playwright, ui test, selenium, automation | `playwright.*` |
| database, sql, postgres, migration | `postgres.*` |
| sentry, error monitoring, exception | `sentry.*` |
| diagram, flowchart, mermaid, uml | `mermaid.*`, `uml-mcp-server.*` |

## Hook Scripts (`/scripts/`)

- **mcp-tool-loader.sh**: Load tools for agents or check keyword triggers
- **keyword-tool-trigger.sh**: PreToolUse hook for keyword detection
- **track-mcp-usage.sh**: PostToolUse hook for usage analytics

```bash
./scripts/mcp-tool-loader.sh --agent security-auditor
./scripts/mcp-tool-loader.sh --keywords "fix the database query"
./scripts/track-mcp-usage.sh --report
```

## Agent Frontmatter Format

Agent files use standard Claude Code frontmatter. The `tools` field controls which **built-in Claude Code tools** the agent can access (not MCP servers):

```yaml
---
name: security-auditor
description: Security audit specialist for vulnerability detection and hardening.
model: sonnet
tools: ["Read", "Write", "Edit", "Bash", "Grep", "Glob"]
---
```

MCP tool bundles for agents are configured in `mcp_config.yaml` under `tier_2_agent_bundles`, not in agent frontmatter. The loading infrastructure reads that config to determine which MCP tools to activate when a given agent is invoked.

## Sources

- Model Context Protocol specification: <https://modelcontextprotocol.io/>
- Claude Code MCP documentation: <https://code.claude.com/docs/en/mcp>
- Claude Code settings schema: <https://json.schemastore.org/claude-code-settings.json>
