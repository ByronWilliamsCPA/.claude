# MCP Tool Loading Strategy

> Reference: `/mcp/mcp_config.yaml` for full configuration
> Based on: [Anthropic's Advanced Tool Use Guide](https://www.anthropic.com/engineering/advanced-tool-use)

## Overview

MCP tools use a tiered strategy to reduce context consumption by 85-95%:
- **Before**: ~55K tokens consumed by 80+ tools at session start
- **After**: ~3K tokens (Tier 1) + context-specific loading

## Binary-managed MCP servers (outside the tiered strategy)

Some MCP servers manage their own Claude Code wiring via an install command and
are not part of the tiered loading strategy. They load at session start
unconditionally, like Tier 1, but are configured outside `settings.json`'s
`mcpServers` block.

| Server | Config file | Managed by | Setup guide |
|--------|-------------|------------|-------------|
| `codebase-memory-mcp` | `~/.claude/.mcp.json` (gitignored) | `codebase-memory-mcp install` | `docs/getting-started/codebase-memory-mcp.md` |

**What codebase-memory-mcp provides:** 14 MCP tools for structural code queries
(`search_graph`, `trace_path`, `get_architecture`, `detect_changes`, Cypher queries,
dead code detection, ADR management). Indexes each repo into a SQLite knowledge
graph; answers structural queries in <1ms. Prefer these tools over `Grep`/`Glob`
for any code-discovery task. Its `PreToolUse` hook (matcher: `Grep|Glob`, script:
`~/.claude/hooks/cbm-code-discovery-gate`) augments Grep/Glob calls with graph
context automatically and never blocks.

Do not add this server to `mcp_config.yaml` or the tiered tables below; its binary
manages upgrades and config changes independently.

**Recognizing a binary-managed server:** any MCP server distributed as a standalone binary
with its own `install`/`uninstall` command that writes to `~/.claude` is binary-managed. Its
config file (typically `~/.claude/.mcp.json`) is the source of truth for that server's
presence, not the tiered strategy YAML. Before adding any new server to the tiered tables,
check whether it ships such a command; if it does, document it in the table above with a
pointer to its setup guide rather than wiring it into the tiers. Adding a binary-managed
server to the tiers creates a parallel config with no enforcement: an upgrade to either side
will not propagate to the other.

## The zen server: fork identity and cost lanes

`zen` in the tables below is our maintained fork, `williaby/zen-mcp-server`, kept
in sync with upstream `BeehiveInnovations/pal-mcp-server` (the rebrand of the
original zen-mcp-server) so we can pull their updates. We keep the `zen` name
because our config and tool identifiers point at the fork; do not rename these
references to `pal`. Multi-model panel reviews have moved to the `/panel` skill
(OpenRouter-based; `.claude/skills/panel/`), which supersedes the zen/pal
`consensus` and `tiered_consensus` tools. Those tools remain available from the
now-frozen server; the `project-planning` skill still calls `consensus` pending
migration, while `pr-review` has already moved to the `/panel` skill. New
work should use the `/panel` skill. Apart from that one legacy `consensus`
call, the server's active tools are `chat`, `thinkdeep`, and `codereview`.

### Three cost lanes

Multi-agent and multi-model work draws on three separate quotas. Route each task
to the cheapest lane that can do the job.

| Lane | Marginal cost | What runs here |
|------|---------------|----------------|
| Interactive subscription | None (flat Max plan) | Interactive `claude` sessions, Claude Code Task/Agent subagents, and Claude Code agent teams (all run inside the interactive session); web/mobile conversations and Cowork |
| Agent SDK credit | Separate monthly credit from 2026-06-15 (Pro $20, Max 5x $100, Max 20x $200); overage at API rates only if usage credits enabled | `claude -p` / `--print` scripts, the Python/TypeScript Agent SDK, and zen/pal `clink` (its Claude agent runs `claude --print --output-format json`, verified in `clink/constants.py`) |
| Provider API | Metered, real money | zen/pal `chat`, `thinkdeep`, `codereview`, and similar calling Gemini/GPT/Grok/etc.; the `/panel` skill (OpenRouter); plus any direct Claude-over-API usage |

Selection heuristic:

- For parallel *Claude* work, prefer in-session subagents (Task/Agent tool):
  they ride the flat subscription at no marginal cost.
- Reserve metered cross-model tools for what only they provide, a different
  model's judgment on a high-value decision: zen `chat` or `thinkdeep` for one
  outside opinion, the `/panel` skill for a multi-model panel. You pay per
  call, so use them deliberately, not for volume.
- `clink` lands in the `-p` bucket, not the interactive subscription. Use it for
  bridging to other CLIs (gemini, codex) or occasional structured headless
  calls, not high-volume Claude fan-out. When `clink` drives a non-Claude CLI it
  uses that provider's own auth and billing.
- Spawning many interactive `claude` processes directly (the munder-difflin
  technique) is the only spawn path that rides the full interactive
  subscription; our subagents reach the same cost profile inside one session.

### Staying on the subscription lane

Two policy facts make the lane boundary sharper than a cost preference:

- **2026-04 third-party-framework block.** Anthropic blocks Pro/Max
  subscriptions from authenticating third-party agent frameworks (CrewAI,
  AutoGen, LangGraph, claude-flow/Ruflo, claude-swarm, and similar). Those
  tools are forced onto an `ANTHROPIC_API_KEY`, which is the metered Provider
  API lane. A tool keeps the subscription lane only when it drives interactive
  `claude` sessions (PTY/tmux-spawned or manually launched), not the SDK.
- **2026-06-15 dual-bucket split.** Agent SDK and `claude -p` usage move off
  the flat subscription into the separate Agent SDK credit (see the table).
  Interactive Claude Code, including subagents and agent teams, stays on the
  subscription. Source: Anthropic support, "Use the Claude Agent SDK with your
  Claude plan."

**Guardrail: unset `ANTHROPIC_API_KEY` for subscription work.** If the key is
present in the environment when subagents or child `claude` processes spawn,
they can silently route through the metered Provider API even though the parent
session is on Max (anthropics/claude-code#39903, #37686). Keep the key out of
the environment for interactive and subagent workflows.

**Collaborative analysis on the subscription = agent teams.** For peer
collaboration (agents messaging each other and sharing a task list) rather than
hub-and-spoke dispatch, use Claude Code agent teams
(`CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`), which run on the interactive
subscription. See `docs/development/agent-teams-pilot.md`.

## Tier 1: Always Loaded

| Server | Tools | Purpose |
|--------|-------|---------|
| zen | thinkdeep, codereview, chat | Deep analysis, reviews, second opinions |
| context7 | resolve_library_id, get_library_docs | Library documentation |
| github | get_file_contents | Basic file access |

## Tier 2: Agent/Skill-Bundled

Loaded automatically when specific agents are invoked:

| Agent | MCP Tools Loaded |
|-------|------------------|
| security-auditor | `zen.secaudit`, `sentry.*`, `github.code_security`, `postgres.analyze_db_health`, `snyk-mcp.snyk_sca_scan`, `snyk-mcp.snyk_code_scan` |
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
| `/project-planning` | `zen.planner`, `zen.consensus`, `mermaid.*` (consensus tool retained pending the skill's migration to the `/panel` skill) |

### Snyk MCP Server (always-on authoring)

Snyk MCP Server is an **always-on authoring server**, registered at user scope in
`~/.claude.json` so `snyk_code_scan` and `snyk_package_health_check` are callable
inline in every session. This is a deliberate shift-left choice: security
feedback woven into authoring, not deferred to CI. The always-on rule
`rules/snyk-secure-at-inception.md` governs when the agent calls these tools,
using a significant-change trigger (not every edit) to bound Snyk hosted-test
quota.

The `security-auditor` agent bundle still surfaces `snyk_sca_scan` and
`snyk_code_scan` for deep on-demand scans (the bundle path complements, rather
than replaces, the always-on authoring path).

The server is registered with the installed global Snyk binary, not via npx:

```bash
snyk mcp configure --tool=claude-cli
```

It registers at user scope in `~/.claude.json` (runtime-managed, not committed),
for the same machine-specific-path reason the localhost-bound sonarqube entry is
not committed. Full setup instructions, including removing the auto-injected
CLAUDE.md rule block, and tool invocation guidance: `standards/snyk-mcp-setup.md`.

`snyk monitor` (a CLI-only command, not an MCP tool) must not be called from any
agent bundle or hook. See `standards/snyk-mcp-setup.md` for the reason.

### Claude Design MCP Server (per-UI-repo, local scope)

Claude Design is a runtime-config server like Snyk, but scoped the opposite way:
registered at `--scope local` in UI repos only (cyo-adventure, fragrance-rater,
future UI repos), never at user scope and never in the config repo. It is an
OAuth HTTP connector (claude.ai login, scopes `user:design:read`/`write`), so it
is present by scope rather than gated by the loader tables below. It exposes one
tool, `DesignSync`, driven by the `/design` and `/design-sync` skills. Local
scope deliberately keeps it isolated per project path, which also sidesteps the
`--scope user` registration defects
(anthropics/claude-code#16728, `#32939`, `#54803`). Full setup, the OAuth-grant
step, and the `frontend-designer` / `ui-testing-agent` bundle intent:
`standards/claude-design-setup.md`.

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
