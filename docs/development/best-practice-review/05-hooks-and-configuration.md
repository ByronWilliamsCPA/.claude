---
title: "Analysis: Hooks and Configuration"
schema_type: common
status: draft
owner: core-maintainer
purpose: "Subagent 5 analysis: external settings.json, hooks, and codex vs local settings and hook scripts."
tags:
  - analysis
  - hooks
  - configuration
---

Subagent 5 of 6 slice comparing `shanraisshan/claude-code-best-practice`
against `/home/byron/dev/.claude`. Focus: `.claude/settings.json`, hook
scripts, hook event coverage, and the parallel `.codex/` configuration.

## Files reviewed

| External file | Size | Summary |
| --- | --- | --- |
| `.claude/settings.json` | 443 lines | Permissions, spinnerVerbs (replace mode), spinnerTipsOverride, plansDirectory, outputStyle=Explanatory, statusLine command, attribution, env.CLAUDE_AUTOCOMPACT_PCT_OVERRIDE=80, and all 27 Claude Code hook events wired to one Python script |
| `.claude/hooks/scripts/hooks.py` | 480 lines | Monolithic Python hook handler, event-to-sound folder map for 27 events plus 6 agent events, audio-player auto-detection (afplay / paplay / aplay / ffplay / winsound), git-commit pattern detection, JSONL logging, disable-flag fallback chain |
| `.claude/hooks/config/hooks-config.json` | 28 keys | Granular `disable<Event>Hook` boolean for every event, plus `disableLogging` toggle |
| `.claude/hooks/HOOKS-README.md` | 579 lines | Documentation of the soundboard architecture (not fetched in detail) |
| `.claude/hooks/sounds/` | 33 folders | One folder per hook event with `.mp3` and `.wav` pairs, plus 6 `agent_*` folders and `pretooluse-git-committing` special sound |
| `.codex/config.toml` | 1 line | `notify = ["python3", ".codex/hooks/scripts/hooks.py"]` |
| `.codex/hooks.json` | 62 lines | Codex-parallel wiring for 5 events (SessionStart, PreToolUse, PostToolUse, Stop, UserPromptSubmit) calling the same `hooks.py` with `--hook <name>` |

## Our local files reviewed

- `/home/byron/dev/.claude/settings.json` (top-level, 103 lines)
- `/home/byron/dev/.claude/.claude/settings.json` (inner, 70 lines: the
  real hook wiring lives here)
- `/home/byron/dev/.claude/.claude/settings.local.json.example`
- `/home/byron/dev/.claude/scripts/bash-pre-hook.sh`
- `/home/byron/dev/.claude/scripts/bash-notify.sh`
- `/home/byron/dev/.claude/scripts/keyword-tool-trigger.sh`
- `/home/byron/dev/.claude/scripts/track-mcp-usage.sh`
- `/home/byron/dev/.claude/scripts/pr-review-reminder.py`
- `/home/byron/dev/.claude/scripts/run-superpowers-session-start.sh`
- `/home/byron/dev/.claude/.claude/rules/mcp-strategy.md`

## Settings.json comparison

| Config section | External | Ours | Gap? |
| --- | --- | --- | --- |
| `permissions.allow` | Broad wildcards: `Edit(*)`, `Write(*)`, `Bash(*)`, `WebFetch(domain:*)`, `mcp__*` | Top-level: narrow (`Bash(poetry run ruff:*)`, `Read`, `Task`). Inner local example: per-command allows (`Bash(git:*)`, `Bash(uv:*)`) | we-do-differently |
| `permissions.ask` | 22 dangerous-command patterns: `rm`, `rmdir`, `shred`, `dd`, `mkfs`, `chmod`, `chown`, `npm`, `pip`, `docker`, `kubectl`, `firebase`, `gcloud`, `kill*` | `settings.local.json.example` has 4: `rm`, `mv`, `git push`, `gh pr create` | gap (incomplete coverage) |
| `permissions.deny` | Empty | Empty | overlap |
| `spinnerVerbs` | `mode: "replace"` with 8 custom verbs | Not set | no-equivalent (novelty) |
| `spinnerTipsOverride` | 2 custom tips, `excludeDefault: true` | Not set | no-equivalent |
| `spinnerTipsEnabled` | `true` | Not set | no-equivalent |
| `plansDirectory` | `./reports` | Not set | gap |
| `outputStyle` | `"Explanatory"` | Not set | gap |
| `statusLine` | Custom echo command | Not set | no-equivalent |
| `attribution.commit` | `Co-Authored-By: Claude <noreply@anthropic.com>` | Not set | gap |
| `attribution.pr` | `Generated with [Claude Code](https://claude.ai/code)` | Not set | gap |
| `respectGitignore` | `true` | Not set (default presumably) | overlap |
| `env.CLAUDE_AUTOCOMPACT_PCT_OVERRIDE` | `80` | Not set | gap |
| `enableAllProjectMcpServers` | `true` | `true` (both files) | overlap |
| `disableAllHooks` | `false` (explicit) | Not set | overlap |
| `$schema` | None | `json.schemastore.org/claude-code-settings.json` | we-do-differently (we are stricter) |
| `hooks` (event count) | 27 events wired | 4 events wired (PreToolUse, PostToolUse, UserPromptSubmit, SessionStart) | gap (coverage) |
| `mcpServers` | Not in settings.json (in .mcp.json) | `zen`, `context7`, `github` in top-level; extended in inner | we-do-differently |

## Hook event coverage matrix

| Event | External | Our inner settings | Notes |
| --- | --- | --- | --- |
| `PreToolUse` | yes (all matchers) | yes (Bash matcher only: `pre-commit`, `bash-pre-hook.sh`) | we target Bash specifically |
| `PostToolUse` | yes | yes (Bash: `bash-notify.sh`; Edit/Write: ruff, shellcheck, frontmatter; mcp__*: `track-mcp-usage.sh`) | we have richer per-matcher coverage |
| `UserPromptSubmit` | yes | yes (`keyword-tool-trigger.sh`, `pr-review-reminder.py`) | overlap |
| `SessionStart` | yes | yes (`keyword-tool-trigger.sh --reset`, superpowers wrapper) | overlap |
| `PermissionRequest` | yes | no | external-only |
| `PostToolUseFailure` | yes | no | external-only |
| `Notification` | yes | no | external-only |
| `Stop` | yes | no | external-only |
| `SubagentStart` | yes | no | external-only |
| `SubagentStop` | yes | no | external-only |
| `PreCompact` | yes (`once: true`) | no | external-only |
| `PostCompact` | yes | no | external-only |
| `SessionEnd` | yes (`once: true`) | no | external-only |
| `Setup` | yes (30s timeout) | no | external-only |
| `TeammateIdle` | yes | no | external-only |
| `TaskCreated` | yes | no | external-only |
| `TaskCompleted` | yes | no | external-only |
| `ConfigChange` | yes | no | external-only |
| `WorktreeCreate` | yes | no | external-only |
| `WorktreeRemove` | yes | no | external-only |
| `InstructionsLoaded` | yes | no | external-only |
| `Elicitation` | yes | no | external-only |
| `ElicitationResult` | yes | no | external-only |
| `StopFailure` | yes | no | external-only |
| `CwdChanged` | yes | no | external-only |
| `FileChanged` | yes (matcher: `.envrc`, `.env`, `.env.local`) | no | external-only |
| `PermissionDenied` | yes | no | external-only |

27 external vs 4 ours. Quantitative gap is stark, but coverage alone is
not a proxy for value: see the lifecycle-events recommendation below for
which are worth wiring.

## Hook architecture comparison

### Shape

- **External**: one monolithic `hooks.py` handles all 27 events, dispatches
  by `hook_event_name` from stdin JSON, plays an MP3/WAV for the matching
  event folder. Config toggles live in `hooks-config.json` with local
  override via `hooks-config.local.json`. Disabling is runtime-side: the
  script still boots and reads config on every event.
- **Ours**: multiple targeted scripts. Each script has one job:
  - `bash-pre-hook.sh` enforces the force-push-to-main guard and records a
    start timestamp for the postHook duration calculation
  - `bash-notify.sh` reads that timestamp and fires a Windows balloon via
    `powershell.exe` if duration exceeds 30 seconds
  - `keyword-tool-trigger.sh` detects MCP tool keywords and logs state
  - `track-mcp-usage.sh` aggregates metrics via `jq` into a JSON file
  - `pr-review-reminder.py` detects PR review intent and emits a
    `systemMessage` payload

### Tradeoffs

| Dimension | Monolithic Python (external) | Targeted shell scripts (ours) |
| --- | --- | --- |
| Startup latency per event | Python interpreter boot + json + argparse + config read, on every invocation | Bash startup is effectively free for most scripts; Python only for `pr-review-reminder.py` |
| Disable UX | Config file toggles via `disable<Event>Hook` keys | Edit `settings.json` to remove the entry (or disable via env var like `PR_REVIEW_REMINDER_DISABLED=1`) |
| Blast radius of bugs | One syntax error breaks every event | Broken script breaks only the one event that calls it |
| Shared state | In-process (but not persistent since script exits immediately each run) | File-based via `/tmp/claude-bash-start`, `~/.claude/tmp_cleanup/.mcp-loaded-tools` |
| Cross-script logic | Easy: single file | Harder but we solved the only real case (pre/post Bash timing) with atomic file write |
| Cross-platform audio | Detects `afplay`, `paplay`, `aplay`, `ffplay`, `winsound`, falls back silently | `powershell.exe` for Windows toast; no macOS/Linux equivalent wired |
| Event payload interpretation | `hooks.py` mostly ignores payload except for Bash command regex: it is a router, not a validator | Each script parses its own payload via `jq` and reacts meaningfully |

### Sound and notification patterns

- **External**: 33 sound folders, roughly 60+ audio files total. Every
  hook event fires a sound. Special handling only for `git commit` in the
  `PreToolUse + Bash` combination. Agent contexts get separate sound
  folders (`agent_*`) for a narrower subset of 6 events.
- **Ours**: one threshold-based Windows toast via `bash-notify.sh` only
  when a Bash command runs longer than 30 seconds. Silent for everything
  else. The approach is fundamentally different: sound as reward signal
  (external) vs sound as exception signal (ours).

### The .codex parallel

The external repo demonstrates that the **same Python hook handler can
service an OpenAI Codex CLI** via `.codex/hooks.json`. Codex uses a
simpler 5-event model (SessionStart, PreToolUse, PostToolUse, Stop,
UserPromptSubmit) and passes the hook name as `--hook <Name>`. The single
`hooks.py` file is portable because it dispatches purely on
`hook_event_name`. We do not have a Codex or other CLI parallel and
therefore this is not a direct gap, but it is a portability pattern worth
noting.

## Key patterns observed in external repo

- **Pattern A: Single-binary hook dispatcher.** One script for all 27
  events. Dispatch key is `hook_event_name` from stdin. File:
  `.claude/hooks/scripts/hooks.py` lines 31-59.
- **Pattern B: File-based disable flags with local override.** Two-tier
  fallback: `hooks-config.local.json` then `hooks-config.json`. File:
  `.claude/hooks/scripts/hooks.py` lines 203-261.
- **Pattern C: JSONL audit log with toggle.** Every hook invocation gets
  a full payload appended to `hooks-log.jsonl` unless `disableLogging:
  true` overrides. File: `.claude/hooks/scripts/hooks.py` lines 312-350.
- **Pattern D: Granular permission `ask` list.** 22 dangerous commands
  explicitly require confirmation. Combined with broad `allow` it yields
  low-friction but safety-gated bash. File: `.claude/settings.json` lines
  31-54.
- **Pattern E: `$CLAUDE_PROJECT_DIR` variable in hook commands.** Hook
  commands in `settings.json` use `${CLAUDE_PROJECT_DIR}` instead of
  `$HOME`, so the same settings work across project moves. File:
  `.claude/settings.json` lines 92, 105, 118, etc.
- **Pattern F: `once: true` flag on lifecycle events.** `PreCompact`,
  `SessionStart`, `SessionEnd`, `Setup` use `once: true` to prevent
  repeated firings in a single context transition. File:
  `.claude/settings.json` lines 212, 239, 253.
- **Pattern G: `async: true` flag on every hook.** All external hooks are
  marked `async: true`, which prevents the hook from blocking the Claude
  turn. File: `.claude/settings.json` pervasive.
- **Pattern H: `FileChanged` hook with a sensitive-file matcher.** Scoped
  to `.envrc|.env|.env.local` so the hook only fires when secret files
  are modified. File: `.claude/settings.json` line 417.
- **Pattern I: Attribution string in settings.** Declarative commit and
  PR footer strings: `"Co-Authored-By: Claude"` and `"Generated with
  [Claude Code](https://claude.ai/code)"`. File: `.claude/settings.json`
  lines 75-78.
- **Pattern J: `plansDirectory` setting.** Forces Claude to save plan
  artifacts to a fixed location. File: `.claude/settings.json` line 68.
- **Pattern K: `outputStyle: "Explanatory"`.** Global model-behavior knob
  that biases toward narrated reasoning. File: `.claude/settings.json`
  line 69.
- **Pattern L: `env.CLAUDE_AUTOCOMPACT_PCT_OVERRIDE=80`.** Deterministic
  override of the default compaction threshold. File:
  `.claude/settings.json` lines 81-83.
- **Pattern M: Parallel `.codex/` directory.** Same `hooks.py` reused for
  a second CLI host. File: `.codex/hooks.json` and `.codex/config.toml`.

## Comparison to our practices

| External pattern | Our equivalent | Verdict |
| --- | --- | --- |
| A. Single-binary dispatcher | Multiple targeted scripts | we-do-differently (ours is better for this workload: see tradeoffs) |
| B. File-based disable flags | Remove entry from settings.json, or env var (`PR_REVIEW_REMINDER_DISABLED`) | we-do-differently (our approach skips the python boot cost but lacks a central toggle doc) |
| C. JSONL audit log | `bash-pre-hook.log`, `bash-notify.log`, `mcp-usage.log`, `keyword-triggers.log` (per-script logs) | overlap (different structure) |
| D. `ask` list for dangerous commands | Partial in `settings.local.json.example` (4 entries) | gap |
| E. `${CLAUDE_PROJECT_DIR}` in commands | `$HOME/.claude/scripts/...` | we-do-differently (home-scoped is fine for our user-wide scripts) |
| F. `once: true` on lifecycle events | Not applicable: we do not wire those events | no-equivalent |
| G. `async: true` on every hook | Not set on any of our hooks | gap (worth investigating) |
| H. `FileChanged` with `.env*` matcher | No FileChanged hook | gap (sensitive-file audit is a real use case) |
| I. Attribution strings | Not set | gap |
| J. `plansDirectory` | Not set | gap |
| K. `outputStyle: "Explanatory"` | Not set | gap |
| L. `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE` | Not set | gap |
| M. Parallel `.codex/` | Not applicable | no-equivalent |

## Recommendations

### Recommendation 1: Adopt the `ask` list for dangerous bash commands

- **What:** Copy external's 22-entry `permissions.ask` list into our
  top-level `settings.json` (and the local example). Covers `rm`,
  `rmdir`, `shred`, `unlink`, `dd`, `mkfs`, `fdisk`, `chmod`, `chown`,
  `npm`, `pip`, `pip3`, `yarn`, `pnpm`, `docker`, `kubectl`, `firebase`,
  `gcloud`, `wget`, `kill`, `killall`, `pkill`.
- **Why:** Our current ask list has 4 entries. A wider ask list forces
  confirmation for destructive commands without sacrificing the
  broad-allow ergonomic for everything else. This is the single highest
  safety win from the external repo.
- **Target files:** `/home/byron/dev/.claude/settings.json`,
  `/home/byron/dev/.claude/.claude/settings.local.json.example`
- **Effort:** S
- **Priority:** high
- **Source citation:** `.claude/settings.json` lines 31-54 in
  shanraisshan/claude-code-best-practice.

### Recommendation 2: Add attribution, plansDirectory, outputStyle, and CLAUDE_AUTOCOMPACT_PCT_OVERRIDE to settings.json

- **What:** Add these four keys to our top-level `settings.json`:
  - `attribution.commit = "Co-Authored-By: Claude <noreply@anthropic.com>"`
  - `attribution.pr = "Generated with [Claude Code](https://claude.ai/code)"`
  - `plansDirectory = "./reports"` (or `.claude/plans`)
  - `outputStyle = "Explanatory"` (bias toward narrated reasoning)
  - `env.CLAUDE_AUTOCOMPACT_PCT_OVERRIDE = "80"` (or tune to taste)
- **Why:** Each of these is a one-line declarative gain. Attribution
  standardizes our PR and commit footers without manual effort.
  `plansDirectory` gives us a consistent artifact location for plan-mode
  output. `outputStyle` is a model-behavior nudge that may reduce "jumps
  straight to edit" behavior. `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE` gives us
  deterministic control over compaction.
- **Target files:** `/home/byron/dev/.claude/settings.json`
- **Effort:** S
- **Priority:** medium
- **Source citation:** `.claude/settings.json` lines 68-83 in
  shanraisshan/claude-code-best-practice.

### Recommendation 3: Wire a FileChanged hook with an `.env*` matcher

- **What:** Add a `FileChanged` hook entry with matcher
  `.envrc|.env|.env.local|secrets.yaml` that logs the event to an audit
  log. Optionally, have it emit a warning `systemMessage` if the file
  being edited is not the user's own `.env` (e.g., a tracked file).
- **Why:** Secret files are the highest-risk edit target in most repos.
  We have no current hook for this category. Implementation effort is low
  because it can reuse the existing shell-script pattern.
- **Target files:** `/home/byron/dev/.claude/.claude/settings.json` and a
  new `/home/byron/dev/.claude/scripts/env-file-guard.sh`
- **Effort:** M
- **Priority:** medium
- **Source citation:** `.claude/settings.json` lines 415-428 in
  shanraisshan/claude-code-best-practice.

### Recommendation 4: Wire a SessionEnd cleanup hook

- **What:** Add a `SessionEnd` hook entry (with `once: true`) that
  removes stale temp state files: `/tmp/claude-bash-start`,
  `~/.claude/tmp_cleanup/.mcp-loaded-tools`, plus any per-session logs
  we want rotated.
- **Why:** Our scripts currently leak state between sessions. The
  `.mcp-loaded-tools` state file specifically persists across sessions,
  so the keyword-trigger logic can get stuck. A two-line cleanup script
  solves this cleanly.
- **Target files:** `/home/byron/dev/.claude/.claude/settings.json`,
  new `/home/byron/dev/.claude/scripts/session-end-cleanup.sh`
- **Effort:** S
- **Priority:** medium
- **Priority rationale:** This is the one lifecycle event from the 27
  external events that is clearly worth wiring for our workload; the
  others are speculative or novelty.
- **Source citation:** `.claude/settings.json` lines 245-258 in
  shanraisshan/claude-code-best-practice.

### Recommendation 5: Wire a PermissionDenied advisory hook

- **What:** Add a `PermissionDenied` hook that logs the denied tool call
  and optionally emits a `systemMessage` reminding Claude that the user
  denied the previous action and to re-evaluate rather than retry.
- **Why:** Claude can get stuck in retry loops when a user denies a
  permission request. A short advisory message reduces the friction and
  moves Claude into a thinking step rather than a reflex retry.
- **Target files:** `/home/byron/dev/.claude/.claude/settings.json`,
  new `/home/byron/dev/.claude/scripts/permission-denied-advisor.sh`
- **Effort:** S
- **Priority:** low
- **Source citation:** `.claude/settings.json` lines 429-441 in
  shanraisshan/claude-code-best-practice.

### Recommendation 6: Do NOT adopt the monolithic hooks.py architecture

- **What:** Reject the pattern of wiring every event to a single Python
  dispatcher.
- **Why:** For our workload (quality gates, force-push guards, MCP
  metrics, PR review nudges), the shell-script-per-event architecture is
  architecturally superior. Monolithic dispatch pays a Python interpreter
  startup tax on every tool call, and our scripts already satisfy the
  Unix philosophy of one-tool-one-purpose. The external monolith is
  essentially a big switch statement wrapping an MP3 player, which is
  not a template we should emulate.
- **Target files:** none (no change)
- **Effort:** N/A
- **Priority:** high (decision record, not an implementation task)
- **Source citation:** `.claude/hooks/scripts/hooks.py` lines 423-476 in
  shanraisshan/claude-code-best-practice.

### Recommendation 7: Do NOT adopt the soundboard pattern

- **What:** Reject the per-event MP3/WAV sound effect pattern.
- **Why:** Our `bash-notify.sh` threshold-based (>30s) Windows toast is
  fundamentally better UX. It fires on exception (long task) rather than
  on every event (cognitive fatigue). A 27-sound soundboard that chirps
  on every Read, Edit, Grep, Bash, Stop, SubagentStop, etc. is novelty,
  not ergonomics.
- **Target files:** none (no change)
- **Effort:** N/A
- **Priority:** high (decision record)
- **Source citation:** `.claude/hooks/scripts/hooks.py` lines 124-201 in
  shanraisshan/claude-code-best-practice.

### Recommendation 8: Do NOT adopt the disable-flag config pattern

- **What:** Reject the `hooks-config.json` approach of toggling hooks
  via disable flags.
- **Why:** Even when `disable<Event>Hook: true`, Claude Code still
  triggers the hook, pays the process-fork cost, boots the Python
  interpreter, and only then exits after reading the config. Toggling at
  the `settings.json` level (remove/add the entry, or use a
  `settings.local.json` override) is strictly more performant because
  the disabled hook never runs at all. Our env-var approach for
  `pr-review-reminder.py` is fine for one script but does not need a
  central config file.
- **Target files:** none (no change)
- **Effort:** N/A
- **Priority:** medium (decision record)
- **Source citation:** `.claude/hooks/config/hooks-config.json` lines
  1-28 in shanraisshan/claude-code-best-practice.

## Gemini review pass (summary)

- External repo is fundamentally a "soundboard and UI customization
  layer". Our setup is a "functional CI/CD-style quality and safety
  pipeline". They are solving different problems.
- Concrete gaps worth closing: the `ask` list (destructive commands),
  `plansDirectory`, `outputStyle`, `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE`,
  attribution strings, and a `PermissionDenied` or `SessionEnd` hook.
- Monolithic Python hooks.py is an anti-pattern for high-frequency
  events: Python interpreter boot time compounds across every tool
  invocation. Our targeted shell scripts (with a narrow Python script
  only where JSON parsing is non-trivial) are the right architecture.
- Per-event sound effects are pure novelty. Threshold-based exception
  alerts (our bash-notify.sh) are strictly better UX.
- The `disable<Event>Hook` flag pattern is an anti-pattern for
  performance: you pay the fork cost even for disabled hooks. Toggling at
  the settings.json layer is correct.
- Lifecycle hooks (PreCompact, PostCompact, Setup, TeammateIdle,
  InstructionsLoaded) are bloat for most users. `SessionEnd` is the one
  exception worth wiring because we leak temp state across sessions.

## Authoritative citations found

- External repo tree:
  `https://github.com/shanraisshan/claude-code-best-practice`
- External settings.json:
  `https://github.com/shanraisshan/claude-code-best-practice/blob/main/.claude/settings.json`
- External hooks.py:
  `https://github.com/shanraisshan/claude-code-best-practice/blob/main/.claude/hooks/scripts/hooks.py`
- External hooks-config.json:
  `https://github.com/shanraisshan/claude-code-best-practice/blob/main/.claude/hooks/config/hooks-config.json`
- External HOOKS-README.md:
  `https://github.com/shanraisshan/claude-code-best-practice/blob/main/.claude/hooks/HOOKS-README.md`
- External .codex/hooks.json:
  `https://github.com/shanraisshan/claude-code-best-practice/blob/main/.codex/hooks.json`
- Claude Code hooks documentation (referenced by external hooks.py):
  `https://code.claude.com/docs/en/hooks`
