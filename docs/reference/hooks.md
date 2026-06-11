---
title: "Hooks Reference"
schema_type: common
status: draft
owner: core-maintainer
purpose: "Reference page for the hook pipeline: types, scripts, and configuration location."
tags:
  - reference
  - hooks
  - technical
---

Hooks are shell commands or Python scripts that fire at defined points in a Claude Code conversation turn. They enforce quality gates, extend behavior, and integrate project-specific logic without requiring model-level changes.

The authoritative hook definition is `hooks.json` at repo root. It is merged into `~/.claude/settings.json` by `setup.sh`. For the design decisions behind this approach, see [ADR-002](../architecture/adr/ADR-002-hook-composition.md). For the full turn-level execution sequence, see [Architecture → Hook Pipeline](../architecture/hook-pipeline.md).

## Hook Types

| Type | Fires when | Use for |
| --- | --- | --- |
| `UserPromptSubmit` | User sends a message, before Claude processes it | Context injection, intent detection |
| `PreToolUse` | Before each tool call Claude attempts | Quality gates, security checks, behavioral guards |
| `PostToolUse` | After each tool call completes | Compatibility checks, usage tracking |
| `Stop` | When Claude finishes its turn | Cleanup, logging |
| `SessionStart` | When a new Claude Code session opens | Session initialization (reserved for future use) |

## Current Hook Scripts

### UserPromptSubmit

| Script | Matcher | Purpose |
| --- | --- | --- |
| `anthropics-plugins/.../userpromptsubmit.py` | (all) | hookify plugin engine dispatch |
| `scripts/pr-review-reminder.py` | (all) | Detects PR review intent and injects reminders |

### PreToolUse

| Script | Matcher | Purpose |
| --- | --- | --- |
| Inline bash | `Edit\|Write` | Blocks writes to `.env` and `settings.local.json` |
| `scripts/planning-bridge-gate.sh` | `Skill` | Enforces plan-approval before Skill invocations |
| `anthropics-plugins/.../security_reminder_hook.py` | `Edit\|Write\|MultiEdit` | OWASP security pattern reminders on file edits |
| `anthropics-plugins/.../pretooluse.py` | (all) | hookify plugin engine dispatch |

### PostToolUse

| Script | Matcher | Purpose |
| --- | --- | --- |
| `scripts/py310-compat-check.sh` | `Edit\|Write` | Checks modified Python files for Python 3.10 incompatibilities |
| `anthropics-plugins/.../posttooluse.py` | (all) | hookify plugin engine dispatch |

### Stop

| Script | Matcher | Purpose |
| --- | --- | --- |
| `anthropics-plugins/.../stop.py` | (all) | hookify plugin engine stop handler |

## Hook Exit Codes

| Exit code | Meaning |
| --- | --- |
| `0` | Allow: the tool call proceeds |
| `2` | Block: the tool call is aborted; stderr is shown as an error message |
| `1` | Hook failure: treated as an error in the hook script itself |

## Adding a Hook

1. Write the script and place it in `scripts/`.
2. Add an entry to `hooks.json` under the appropriate hook type.
3. Run `./setup.sh` to merge `hooks.json` into `~/.claude/settings.json`.
4. Test in a Claude Code session.

For the full step-by-step workflow, see [Contributing → Adding a Hook](../contributing/adding-hooks.md).

## Plugin Hooks vs Repo-Managed Hooks

Plugins enabled through `enabledPlugins` contribute hooks from their own `hooks/hooks.json`. Claude Code loads them alongside the repo-managed hooks defined in `hooks.json` and the `hooks` block of `settings.json`. The two sources compose additively:

- A plugin cannot modify, remove, or reorder repo-managed hooks. Disabling the plugin removes its hooks without touching repo-managed ones.
- When both sources register on the same event, every matching hook from both sources runs. Ordering between the sources is unspecified; do not write hooks that depend on cross-source ordering.
- Blocking semantics apply per hook regardless of source: any PreToolUse hook that exits 2 or returns a deny decision blocks the tool call. Observability hooks must therefore be fire-and-forget (exit 0 on every code path, nothing written to stdout).
- Latency is cumulative: each matching registration is one process spawn per event, so a plugin adds its own spawns on top of the repo-managed ones.

As of 2026-06, `hooks.json` defines 10 repo-managed commands across PreToolUse (5), PostToolUse (2), Stop (1), and UserPromptSubmit (2), and `settings.json` carries additional entries including four SessionStart commands. The hookify and security-guidance plugins ship under `.submodules/anthropics-plugins` but are wired as command entries in `hooks.json` (legacy wiring), so they count as repo-managed hooks, not plugin-system hooks.

### agents-observe (pinned v0.9.11)

The agents-observe plugin (`.submodules/agents-observe`, pinned at tag v0.9.11) is the first true plugin-system hook contributor. Its `hooks/hooks.json` registers exactly one command on each of 28 events, including SubagentStart and SubagentStop (the events that drive per-subagent token attribution) plus PreToolUse and PostToolUse on every tool call; the 28 also include the install-time `Setup` lifecycle event, which runs once at plugin install rather than per session. It overlaps with repo-managed hooks on five events: PreToolUse, PostToolUse, Stop, UserPromptSubmit, and SessionStart. On each overlapping event both sources fire independently, and the plugin adds one process spawn per event. With the plugin enabled, each tool call therefore carries six PreToolUse spawns (five repo-managed plus the plugin wrapper) and three PostToolUse spawns; the wrapper backgrounds its node process, so the added synchronous cost is one fork-and-exec per event, typically single-digit milliseconds. For latency-sensitive sessions (tight subagent loops with hundreds of tool calls), disable the plugin by setting the `enabledPlugins` entry for `agents-observe@agents-observe` to `false`.

27 of the 28 registrations run `hooks/scripts/hook.sh`, a 9-line wrapper that reads stdin, backgrounds the node CLI with stdout and stderr discarded to `/dev/null`, and ends in an unconditional `exit 0`. It never writes to stdout, so no code path can block a tool call or emit a permission decision (verified at v0.9.11; re-verify after any submodule bump). Two caveats:

- The SessionStart registration bypasses the wrapper and runs `observe_cli.mjs hook-autostart` as a foreground node process. A missing or hung `node` binary delays session start until the hook timeout; SessionStart is not a tool-gating event, so it still cannot block tool calls.
- Failures inside the backgrounded process are discarded along with its output. If the event spool or database is unwritable, events drop silently instead of surfacing an error; this is the intended trade-off of fire-and-forget observability.

## See Also

- `hooks.json` at repo root: the authoritative hook definition
- `.submodules/agents-observe/hooks/hooks.json`: agents-observe plugin hook registrations
- [Architecture → Hook Pipeline](../architecture/hook-pipeline.md): turn-level execution diagram and narrative
- [ADR-002 Hook Composition and Ordering](../architecture/adr/ADR-002-hook-composition.md): design rationale
- [Contributing → Adding a Hook](../contributing/adding-hooks.md): step-by-step authoring guide
