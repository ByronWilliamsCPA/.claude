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

## Tier 3: Keyword-Triggered

| Keywords | Tools Loaded |
|----------|--------------|
| dockerfile, container, docker, k8s | `docker.*` |
| e2e, browser test, playwright, ui test | `playwright.*` |
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

```yaml
---
name: security-auditor
mcp_tools:
  load:
    zen: [secaudit, challenge]
    sentry: [search_errors, get_issue, analyze_issue]
  defer:
    sentry: [list_projects, create_dsn]
---
```
