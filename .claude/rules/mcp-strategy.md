# MCP Tool Loading Strategy

> Reference: `/mcp/mcp_config.yaml` for full configuration
> Based on: [Anthropic's Advanced Tool Use Guide](https://www.anthropic.com/engineering/advanced-tool-use)

## Overview

MCP tools use a tiered strategy to reduce context consumption by 85-95%:
- **Before**: ~55K tokens consumed by 80+ tools at session start
- **After**: ~3K tokens (Tier 1) + context-specific loading

## The zen server: fork identity and cost lanes

`zen` in the tables below is our maintained fork, `williaby/zen-mcp-server`, kept
in sync with upstream `BeehiveInnovations/pal-mcp-server` (the rebrand of the
original zen-mcp-server) so we can pull their updates. We keep the `zen` name
because our config and tool identifiers point at the fork; do not rename these
references to `pal`. The fork's local addition over upstream is the
`tiered_consensus` tool (upstream ships a single-tier `consensus`). When syncing
from upstream, preserve `tiered_consensus`.

### Three cost lanes

Multi-agent and multi-model work draws on three separate quotas. Route each task
to the cheapest lane that can do the job.

| Lane | Marginal cost | What runs here |
|------|---------------|----------------|
| Interactive subscription | None (flat Max plan) | Interactive `claude` sessions and Claude Code Task/Agent subagents (they run inside the interactive session) |
| `claude -p` headless bucket | Rationed, separate quota | `claude -p` / `--print` scripts, and zen/pal `clink` (its Claude agent runs `claude --print --output-format json`, verified in `clink/constants.py`) |
| Provider API | Metered, real money | zen/pal `chat`, `consensus`, `tiered_consensus`, `thinkdeep`, and similar calling Gemini/GPT/Grok/etc., plus any Claude-over-API usage |

Selection heuristic:

- For parallel *Claude* work, prefer in-session subagents (Task/Agent tool):
  they ride the flat subscription at no marginal cost.
- Reserve zen/pal API tools (`tiered_consensus`, `chat`) for what only they
  provide, a different model's judgment on a high-value decision. You pay per
  call, so use them deliberately, not for volume.
- `clink` lands in the `-p` bucket, not the interactive subscription. Use it for
  bridging to other CLIs (gemini, codex) or occasional structured headless
  calls, not high-volume Claude fan-out. When `clink` drives a non-Claude CLI it
  uses that provider's own auth and billing.
- Spawning many interactive `claude` processes directly (the munder-difflin
  technique) is the only spawn path that rides the full interactive
  subscription; our subagents reach the same cost profile inside one session.

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
