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
   breaker exists." No such tooling existed in the repo at the time of
   this survey; Layer 2 below closes the gap.
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
times. ccstatusline 2.2.19 is now configured as the consumer (Layer 1 below).

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

### Subscription compatibility (verified 2026-06-10)

Both candidates work on a Max subscription; neither depends on API-key
billing. Verified empirically against a live transcript set:

- ccusage 20.0.9 produced per-model daily breakdowns and an active five-hour
  block report (burn rate, projected tokens and cost) from local JSONL files
  alone. It never contacts Anthropic; auth method is irrelevant to it.
- ccstatusline 2.2.19 rendered a status line from a sample statusLine JSON
  payload on stdin with no credentials. Its optional usage-limit widgets
  (weekly usage, extra usage) call Anthropic's usage endpoint as the signed-in
  account read from `~/.claude.json`, which is the subscription OAuth
  identity, the same data `/usage` shows; no API key is involved.

The one caveat stands for both: dollar figures are estimates against API list
pricing, a relative spend signal for a subscriber, not a bill.

## 4. Recommendation: layered adoption

The recommendation is to build nothing custom for token accounting; the
ecosystem already parses the transcript format well. Adopt in layers, each
independent of the next.

**Layer 1 (implemented): statusLine.** `settings.json` now sets:

```json
{
  "statusLine": {
    "type": "command",
    "command": "npx -y ccstatusline@2.2.19"
  }
}
```

The version is pinned in line with this repo's pinning posture; `npx` matches
the existing MCP server entries. To avoid the per-message npx registry
lookup, optionally install once with `npm install -g ccstatusline@2.2.19`
so the command resolves locally. This closes Gap 16 with live model, cost,
context, and rate-limit visibility in every session, and directly supports
the CLAUDE.md "Session length" self-assessment with data instead of
guesswork.

**Layer 2 (implemented): ccusage as the reporting CLI.** The
`/usage-report` skill (`.claude/skills/usage-report/SKILL.md`) wraps
ccusage 20.0.9: `daily --instances` for per-project review, `monthly` for
trends, `blocks --active` for the five-hour window. Three integrations make
it repo-native:

- `loop-recipes.md` now names `/usage-report blocks` as the required cost
  circuit breaker for unattended `/loop` runs.
- `/close` Step 1 captures the active block's tokens, estimated cost, and
  per-model split at session wind-down and appends a summary line to
  `~/.claude/logs/session-usage.log`, building a per-session longitudinal
  record with no daemon.
- The skill flags per-model spend that contradicts the CLAUDE.md Model
  Selection policy, a lightweight stand-in for the Layer 4 policy audit.

**Layer 3 (implemented 2026-06-11): agents-observe plugin.** The only
surveyed tool showing the full agent delegation hierarchy with token data
in real time. Installs as a plugin onto the hooks system this repo already
manages. Relevant given the 45-agent catalog and supervisor pattern.

*Pin and install.* The submodule `.submodules/agents-observe` is pinned at
tag v0.9.11 (SHA e15b7f6) and registered as a directory-source marketplace
plugin named `agents-observe` in `settings.json`. The local Claude Code
plugins registry (`~/.claude/plugins/installed_plugins.json`, a machine-local
file, not a repo artifact) records version 0.9.11 with a matching
`gitCommitSha`. Do not run `claude plugin update` for this plugin without
re-running the security review: the directory-source marketplace loads
whatever is checked out in the submodule working tree, not the pinned
gitlink SHA, so a plugin update or a manual checkout inside the submodule
silently floats the reviewed version.
`#ASSUME` the submodule working tree matches the pinned SHA.
`#VERIFY` after any submodule operation:
`git -C .submodules/agents-observe rev-parse HEAD` must print
`e15b7f6d06fecda44eb903f9de503ee04973bcaa`.

The marketplace path in `settings.json` is absolute
(`/home/byron/dev/.claude/.submodules/agents-observe`); this is the first
marketplace entry committed to that file, so there is no prior pattern, and
env-var expansion support for this field is unverified.
`#ASSUME` the repo lives at `/home/byron/dev/.claude`; the plugin silently
fails to load from any other clone location.
`#VERIFY` when porting this config to another machine: update the path to
the new clone location, or confirm `$HOME` expansion works for
`extraKnownMarketplaces.source.path` before relying on it.

The committed `settings.json` also enables the plugin
(`enabledPlugins."agents-observe@agents-observe": true`), an opt-out
posture for every clone of this public repo. This default is deliberate
for this repo: it is a single-user personal config whose maintainer has
accepted the exposure documented below, and it is not a recommendation
for any other environment.
`#ASSUME` single-user personal config repo; this machine is the only
consumer of the committed settings.
`#VERIFY` when adopting this repo as your own Claude config on another
machine: before your first session, edit your copy to set the
`enabledPlugins` entry to `false`, re-grade the security caveats below
for your network, and only then opt back in deliberately.

*Data storage.* The SQLite database lives at
`~/.claude/plugins/data/agents-observe-agents-observe/data/observe.db`,
outside the repo tree. `*.db`, `*.db-wal`, and `*.db-shm` are gitignored as
defense in depth. The database is root-owned (written by the plugin's Docker
container); host queries go through the local REST API, not `sqlite3` directly.

*Hook composition.* The plugin contributes 28 hook registrations including
SubagentStart, SubagentStop, PreToolUse, and PostToolUse via fire-and-forget
wrappers; see [docs/reference/hooks.md](hooks.md) for the composition details.

*Security caveats (review result: PASS with required guardrails).*

- Full tool inputs are persisted unredacted: every Bash command string and
  every Write/Edit file body lands in `observe.db` (only large base64 image
  blobs are stripped). Any secret that appears in a shell command or written
  config file is stored in plaintext. Treat `observe.db` as secret-bearing;
  use `/observe stop` and `db-reset` when handling sensitive credentials.
- The Docker container publishes port 4981 on `0.0.0.0` (not `127.0.0.1`)
  with no authentication on any route and fully open CORS. The bind
  interface is hard-coded with no env var override in v0.9.11
  (`docker.mjs:214` bare `port:port` mapping); `AGENTS_OBSERVE_SERVER_PORT`
  changes only the host port number, not the interface. On an untrusted
  LAN, any host on the network can read all captured prompts, commands,
  and file bodies. In this install, WSL2 NAT keeps the port off the
  physical LAN; the 30-second idle shutdown also limits the exposure
  window.
  `#ASSUME` WSL2 NAT isolation holds: no portproxy rule forwards 4981 and
  the WSL adapter is not bridged.
  `#VERIFY` before trusting this boundary, and again after any Windows
  networking change: `netsh interface portproxy show all` on the Windows
  host must not list 4981.
  Operational rule: enable only on a single-user trusted machine on a
  trusted network. v0.9.11 has no loopback bind option, so the only
  mitigations on an untrusted network are stopping the container
  (`/observe stop`), a host firewall rule blocking 4981, or leaving the
  plugin disabled. An upstream feature request for a `127.0.0.1:` publish
  prefix is recommended (not yet filed as of 2026-06-11).
- Do not raise the log level to `trace`; that writes a second plaintext copy
  of all payloads to `cli.log`/`mcp.log` and the server console. The
  enabling config sets `warn`.
- One outbound GET to `https://models.dev/api.json` (model pricing table, no
  captured data sent); fails closed in air-gapped environments.
- The SessionStart hook runs `node` in the foreground; a hung node process
  delays session start until the hook timeout (default 30s). The plugin's
  `hooks/hooks.json` sets no `timeout` field and plugin hooks cannot be
  overridden from this repo's settings, so the repo convention of
  `timeout: 10` on repo-managed SessionStart hooks does not reach it. An
  upstream request for a configurable SessionStart hook timeout is
  recommended (not yet filed as of 2026-06-11).
- Fire-and-forget design drops events silently when the spool is unwritable;
  this is a completeness concern, not a safety concern.

*Validation (session 6238e84c-acf1-4ebe-9ba0-e136bf751311, 2026-06-11 test
run).* A
supervisor-pattern session with a Fable 5 root agent delegating to three
parallel Explore subagents (Haiku) confirmed the full delegation tree is
visible via `GET /api/sessions/:id/transcript-stats`: all three Explore
subagents showed nonzero per-subagent `inputTokens`, `outputTokens`,
`cacheReadTokens`, `model`, and `costCents`. Hook regression probes
confirmed the force-push guard still blocks (exit 2) and the
fire-and-forget path passes through cleanly (exit 0).

*`/usage-report` agents mode (implemented, commit 78dd523).* The
`/usage-report` skill gained an `agents` mode that queries the local API
(health check, sessions/recent, transcript-stats) for per-subagent token
attribution. One caveat: `transcript-stats` requires the session JSONL to
still be on disk; queries after JSONL cleanup return `{"error":
"file_not_found"}`. The agents mode is therefore most reliable when run
during or immediately after a session.

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
