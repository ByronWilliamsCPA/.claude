---
schema_type: common
title: "Model and Token Usage Monitoring: Current State, Ecosystem Survey, and Adoption Plan"
status: published
owner: core-maintainer
purpose: "Survey of what this global settings repo currently tracks about model and token usage, the local and built-in data sources available, the 2026 open-source monitoring ecosystem, and a layered adoption recommendation for a solo Max subscriber working across many project repos."
tags:
  - reference
  - evaluation
  - automation
---

This report answers three questions: what does this repo track about model and
token usage today, what is trackable with data sources that already exist on
disk or ship with Claude Code, and which open-source projects are worth
adopting or learning from. It follows the same evaluation pattern as
[dependency-tooling-comparison.md](dependency-tooling-comparison.md) and
[fossa-ci-evaluation.md](fossa-ci-evaluation.md).

## 1. What this repo tracks today

The current tracking surface is one hook and one log directory:

- `scripts/track-mcp-usage.sh`, wired as a PostToolUse hook on `mcp__*`
  matchers in `settings.json`, appends `timestamp|tool_name` lines to
  `~/.claude/logs/mcp-usage.log` and maintains per-tool counts in
  `~/.claude/logs/mcp-metrics.json`. It records call counts only: no tokens,
  no model ids, no cost, and nothing for built-in tools, skills, or agents.
- `~/.claude/logs/` is gitignored, so all runtime metrics stay local.

Three documented intentions depend on usage data that nothing currently
collects:

1. `.claude/rules/loop-recipes.md` requires a cost circuit breaker before any
   unattended `/loop` run and notes Claude Code has no built-in cost cap. The
   synthesis report deferred `/loop` recipes "until a token/cost circuit
   breaker exists." No such tooling exists in the repo.
2. `docs/development/best-practice-review/04-tips-harvest.md` Recommendation 7
   proposed skill-usage telemetry via a PreToolUse log to find dead-weight
   skills. Never implemented.
3. `CLAUDE.md` Model Selection sets a policy (Opus for deep reasoning, Sonnet
   default, Haiku for read-only exploration) and agent frontmatter encodes it
   (44 agents on `sonnet`, 1 on `opus`), but nothing measures whether actual
   token spend follows the policy.

The tips harvest also classified `/statusline` as a cosmetic gap (Gap 16).
That classification undersold it: the statusLine JSON payload carries session
cost, context-window fill, and five-hour and seven-day rate-limit percentages,
which makes it the cheapest live-visibility surface available.

## 2. What is trackable without new collection

Four data sources already exist or require only configuration:

**Session transcripts** (`~/.claude/projects/<encoded-path>/<session-id>.jsonl`).
Every assistant turn carries a `message.usage` object with `input_tokens`,
`output_tokens`, `cache_read_input_tokens`, cache-creation splits
(`ephemeral_5m_input_tokens`, `ephemeral_1h_input_tokens`), server tool use
counts, service tier, and the `model` id. Records also carry `sessionId`,
`cwd`, `gitBranch`, and timestamps, and multi-agent sessions add `agentId`,
`agentType`, and `parentToolUseId`. This is the richest source: per-model,
per-project, per-session accounting is derivable from files already on disk.

**statusLine JSON.** When a `statusLine` command is set in `settings.json`,
Claude Code pipes a JSON blob to it on every assistant message containing
`model.id`, `cost.total_cost_usd`, `context_window.used_percentage`, and
`rate_limits.five_hour` / `rate_limits.seven_day` percentages with reset
times. Nothing is configured today.

**Built-in OpenTelemetry.** `CLAUDE_CODE_ENABLE_TELEMETRY=1` plus
`OTEL_METRICS_EXPORTER` / `OTEL_LOGS_EXPORTER` emits `claude_code.token.usage`
and `claude_code.cost.usage` metrics with `model`, `query_source`
(main/subagent/auxiliary), `agent.name`, and `skill.name` attributes, plus
session, lines-of-code, commit, and tool-decision metrics. This is the only
source that attributes tokens to a named agent or skill, which is exactly what
Recommendation 7 and the model-policy verification need. Requires a local
collector to receive it.

**Built-in commands.** `/usage` (plan usage bars, token breakdown attributed
to skills, subagents, and MCP servers, 24h/7d views), `/context` (context
window breakdown), and `/cost` (session API token usage). Zero setup, but
interactive-only and not aggregatable.

The Anthropic Admin API usage and cost endpoints cover API-key billing only;
they are not applicable to Max subscription usage and can be ignored here.

## 3. Ecosystem survey (June 2026)

| Tool | Stars (approx) | Active 2026 | Data source | Per-model | Per-project | Per-subagent | Real-time | Composes with this repo |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| [ccusage](https://github.com/ryoppippi/ccusage) | 15.9k | Yes, frequent releases | JSONL transcripts | Yes | Yes (`--instances`) | No | No | Excellent: statusLine mode, MCP server mode, no daemon |
| [ccstatusline](https://github.com/sirmalloc/ccstatusline) | 10.5k | Yes (v2.2.x, May 2026) | statusLine JSON | Yes | n/a | No | Yes (live bar) | Excellent: is a statusLine command |
| [claudia / opcode](https://github.com/getAsterisk/claudia) | 22k | Yes | JSONL transcripts | Yes | Yes | No | Partial | Low: desktop GUI, no hooks |
| [Claude-Code-Usage-Monitor](https://github.com/Maciek-roboblog/Claude-Code-Usage-Monitor) | 8.2k | Stale (July 2025) | JSONL transcripts | Partial | No | No | Yes (terminal) | Low: separate process; best Max plan-limit awareness of the JSONL tools |
| [sniffly](https://github.com/chiphuyen/sniffly) | 1.2k | Moderate | JSONL transcripts | No | Yes | No | No | Low: local web app; error-pattern analysis, not cost |
| [agents-observe](https://github.com/simple10/agents-observe) | 589 | Yes (weekly releases) | Hooks to SQLite | No | No | Yes (full hierarchy) | Yes | Good: installs as a Claude Code plugin onto the existing hooks system |
| [claude-code-otel](https://github.com/ColeMurray/claude-code-otel) | 435 | Low activity | OTEL | Yes | Via session id | In data, not in shipped dashboards | Yes (Prometheus) | Moderate: env block in settings.json plus a Docker stack |
| [claude-code-dashboard](https://github.com/Stargx/claude-code-dashboard) | 9 | Yes | JSONL file watcher | No | No | While live | Yes | Low: small project, current sessions only |
| [claude_telemetry](https://github.com/TechNickAI/claude_telemetry) | small | Moderate | CLI wrapper to OTEL | Yes | No | No | Via backend | Poor: requires a shell alias, bypasses hooks |
| [logfire plugin](https://github.com/pydantic/claude-code-logfire-plugin) | 11 | Yes | Plugin hooks | Yes | No | No | Via backend | Poor without a Logfire subscription |

Notes on the two strongest candidates:

- **ccusage** parses the same JSONL transcripts described in section 2 and
  produces `daily`, `weekly`, `monthly`, `session`, and `blocks` reports (the
  blocks report tracks the five-hour billing window relevant to Max
  throttling). `--instances` groups by project. Cost is an estimate against
  API pricing via LiteLLM data, which is the correct framing for a Max
  subscriber: a relative spend signal, not a bill. It also runs as an MCP
  server, so an agent can query usage data mid-session, which is the missing
  primitive for the `/loop` cost circuit breaker.
- **ccstatusline** renders model name, session cost, per-model tokens,
  context-window percentage with a progress bar, five-hour block timer, and
  git status in the status bar. Configured once globally, it applies to every
  project repo with zero ongoing maintenance.

## 4. Recommendation: layered adoption

The recommendation is to build nothing custom for token accounting; the
ecosystem already parses the transcript format well. Adopt in layers, each
independent of the next.

**Layer 1 (do now, zero maintenance): statusline.** Add to `settings.json`:

```json
{
  "statusLine": {
    "type": "command",
    "command": "bunx -y ccstatusline@latest"
  }
}
```

Pin the version in line with this repo's SHA-pinning posture, or vendor a
small wrapper script under `scripts/`. ccusage's `statusline` subcommand is
the alternative if its formatting is preferred; choose one. This closes Gap
16 with live model, cost, context, and rate-limit visibility in every
session, and directly supports the CLAUDE.md "Session length" self-assessment
with data instead of guesswork.

**Layer 2 (do now, zero install): ccusage as the reporting CLI.**
`bunx ccusage daily --instances` for per-project daily review,
`ccusage monthly` for trends, `ccusage blocks` for the five-hour window. Two
follow-ups make it repo-native:

- A thin `/usage-report` skill that shells out to ccusage and summarizes,
  so reporting is invocable from any session.
- Wire `ccusage blocks` (or its MCP server mode) into the `/loop` safeguards
  as the cost circuit breaker that `loop-recipes.md` requires and currently
  lacks.

**Layer 3 (when subagent attribution matters): agents-observe plugin.** The
only surveyed tool showing the full agent delegation hierarchy with token
data in real time. Installs as a plugin onto the hooks system this repo
already manages. Relevant given the 46-agent catalog and supervisor pattern.

**Layer 4 (optional, when trends matter): OTEL to a local Grafana stack.**
Add the telemetry env block to `settings.json` and run the ColeMurray
collector + Prometheus + Loki + Grafana stack, extending its dashboards to
surface the `agent.name`, `skill.name`, and `query_source` attributes the raw
metrics already carry. This is the only path to verifying the Model Selection
policy empirically (tokens by model by agent over weeks) and would also
deliver Recommendation 7's skill telemetry without the custom PreToolUse
logging pipeline the synthesis report flagged as a storage and rotation
burden. Defer until Layers 1 and 2 prove insufficient; it is the only layer
with a standing infrastructure cost.

**What to skip:** the Anthropic Admin API (API billing only), Maciek's
Claude-Code-Usage-Monitor (stale; superseded by ccstatusline plus ccusage),
claude_telemetry and the Logfire plugin (external backends or alias changes),
claudia/opcode (GUI without hooks integration; revisit at GA), and sniffly
(useful later for error-pattern analysis, not for usage visibility).

**Retire or extend `track-mcp-usage.sh`:** once Layer 4 exists, OTEL's
per-tool metrics supersede it. Until then it remains the only MCP frequency
signal feeding the Tier 1/2/3 loading strategy, so keep it.

## Sources

- Claude Code monitoring docs: <https://code.claude.com/docs/en/monitoring-usage>
- Claude Code statusline docs: <https://code.claude.com/docs/en/statusline>
- Claude Code cost docs: <https://code.claude.com/docs/en/costs>
- Anthropic Admin API usage and cost: <https://platform.claude.com/docs/en/manage-claude/usage-cost-api>
- ccusage: <https://github.com/ryoppippi/ccusage> and <https://ccusage.com/>
- ccstatusline: <https://github.com/sirmalloc/ccstatusline>
- agents-observe: <https://github.com/simple10/agents-observe>
- claude-code-otel: <https://github.com/ColeMurray/claude-code-otel>
- Claude-Code-Usage-Monitor: <https://github.com/Maciek-roboblog/Claude-Code-Usage-Monitor>
- sniffly: <https://github.com/chiphuyen/sniffly>
- claudia / opcode: <https://github.com/getAsterisk/claudia>
- claude-code-dashboard: <https://github.com/Stargx/claude-code-dashboard>
- claude_telemetry: <https://github.com/TechNickAI/claude_telemetry>
- Logfire plugin: <https://github.com/pydantic/claude-code-logfire-plugin>
- SigNoz Claude Code OpenTelemetry guide: <https://signoz.io/blog/claude-code-monitoring-with-opentelemetry/>
