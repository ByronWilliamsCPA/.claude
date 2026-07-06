---
title: "Hook Pipeline"
schema_type: common
status: draft
owner: core-maintainer
purpose: "Narrative description of the hook lifecycle across a Claude Code conversation turn."
tags:
  - architecture
  - hooks
  - technical
---

Claude Code fires hooks at five points during a session. These hooks enforce quality gates, route behavioral rules, and extend Claude's capabilities without requiring model-level changes. The repo-managed hook definitions live in `hooks.json` at repo root and are merged into `~/.claude/settings.json` by `setup.sh`; that file is the baseline, but it is not the only source Claude Code executes hooks from. See [Hook Sources](#hook-sources) below for the full taxonomy and the drift check that guards it.

For the design decisions behind this system, see [ADR-002](adr/ADR-002-hook-composition.md) and [ADR-010](adr/ADR-010-hook-source-allowlist.md).

## The Five Hook Types

**UserPromptSubmit**: fires immediately after the user sends a message, before Claude processes it. Used for: injecting context, detecting intent signals (PR review reminder), running the hookify user prompt pipeline.

**PreToolUse**: fires before each tool call Claude attempts. Each entry in the `PreToolUse` array can have a matcher regex targeting specific tools. Used for: secrets file guard (Edit/Write), planning bridge gate (Skill), security reminder (Edit/Write/MultiEdit), hookify dispatch (all tools).

**PostToolUse**: fires after each tool call completes. Used for: Python 3.10 compatibility check (Edit/Write), hookify dispatch (all tools).

**Stop**: fires when Claude finishes its turn (before control returns to the user). Used for: hookify stop handler.

**SessionStart**: fires when a session opens, and again on resume, `clear`, or `compact`, depending on which matcher a given hook registers. Two repo-managed hooks are wired here (`scripts/hooks/delegation-reminder.sh`, `scripts/hooks/cbm-context-reminder.sh`), alongside SessionStart hooks contributed by installed plugins. No `.claude/rules/*.md` file is injected at this point or any other; rules enter context only when Claude follows a `CLAUDE.md` pointer to one, or a hook prints its content directly, which is exactly what these two hooks do.

## Diagram

![Hook pipeline sequence diagram](diagrams/hook_pipeline.svg)

## Execution Order Across a Turn

A single user message triggers the following hook sequence:

```text
User sends message
  → UserPromptSubmit[0]: hookify userpromptsubmit.py
  → UserPromptSubmit[1]: pr-review-reminder.py

  Model processes, issues tool calls:
    For each Write or Edit call:
      → PreToolUse[0]: secrets file guard (matcher: Edit|Write)
      → PreToolUse[2]: security reminder (matcher: Edit|Write|MultiEdit)
      → PreToolUse[3]: hookify pretooluse.py (all tools)
      → Tool executes
      → PostToolUse[0]: py310-compat-check (matcher: Edit|Write)
      → PostToolUse[1]: hookify posttooluse.py (all tools)

    For each Skill call:
      → PreToolUse[1]: planning bridge gate (matcher: Skill)
      → PreToolUse[3]: hookify pretooluse.py (all tools)
      → Tool executes
      → PostToolUse[1]: hookify posttooluse.py (all tools)

    For any other tool call:
      → PreToolUse[3]: hookify pretooluse.py (all tools)
      → Tool executes
      → PostToolUse[1]: hookify posttooluse.py (all tools)

  Model turn ends
    → Stop[0]: hookify stop.py
```

Array position determines execution order within each hook type. Matcher-specific entries run only when their regex matches the tool being called.

## Per-Hook Responsibilities

### SessionStart

Fires once per session-open event, before the turn cycle described above begins; it is not part of the per-turn sequence.

| Matcher | Script | What it does |
| --- | --- | --- |
| `startup\|resume\|clear\|compact` | `scripts/hooks/cbm-context-reminder.sh` | Repo-managed; listed first in `hooks.json`, so it runs first. Prints the codebase-memory-mcp discovery protocol (prefer `search_graph`/`trace_path`/`get_code_snippet`/`get_architecture` over Grep/Glob for code exploration). Replaces the binary-managed `~/.claude/hooks/cbm-session-reminder` entry that `codebase-memory-mcp install` writes, so the wording survives a binary upgrade |
| `startup\|resume\|clear\|compact` | `scripts/hooks/delegation-reminder.sh` | Repo-managed. Prints the delegation protocol reminder (dispatch subagents for exploration, well-specified implementation, and review; never silently absorb a failed dispatch inline) and refreshes the task-observer skills manifest, warning on stdout if the refresh fails |
| `startup\|clear\|compact` | superpowers plugin session-start command | Plugin-provided; not defined in this repo's `hooks.json` |
| (all matchers) | agents-observe plugin telemetry auto-start | Plugin-provided; not defined in this repo's `hooks.json` |

Neither repo-managed hook, nor either plugin hook, loads a file from `.claude/rules/`. A rule file reaches context only through a `CLAUDE.md` pointer Claude chooses to follow, or through a hook that prints equivalent content directly: `delegation-reminder.sh` prints a hardcoded summary of the delegation core (mirrored inline in `CLAUDE.md`, not read from `supervisor.md` at runtime), and `cbm-context-reminder.sh` does the same for the codebase-memory discovery protocol.

### UserPromptSubmit

| Script | What it does |
| --- | --- |
| `hookify/hooks/userpromptsubmit.py` | Dispatches to registered hookify plugins for the UserPromptSubmit event |
| `scripts/pr-review-reminder.py` | Detects when the user's message looks like a PR review request and injects a reminder about the review workflow |

### PreToolUse

| Matcher | Script | What it does |
| --- | --- | --- |
| `Edit\|Write` | Inline bash | Blocks writes to `.env` and `settings.local.json` with exit code 2 |
| `Skill` | `scripts/planning-bridge-gate.sh` | Enforces plan-approval workflow before any Skill invocation |
| `Edit\|Write\|MultiEdit` | `security_reminder_hook.py` | Surfaces OWASP-style security reminders when editing files |
| (all tools) | `hookify/hooks/pretooluse.py` | Dispatches to hookify plugin engine |

### PostToolUse

| Matcher | Script | What it does |
| --- | --- | --- |
| `Edit\|Write` | `scripts/py310-compat-check.sh` | Checks modified Python files for syntax that breaks on Python 3.10 |
| (all tools) | `hookify/hooks/posttooluse.py` | Dispatches to hookify plugin engine |

### Stop

| Script | What it does |
| --- | --- |
| `hookify/hooks/stop.py` | Dispatches to hookify plugin engine's stop handlers |

## hookify Dispatch

hookify is a plugin engine from the `anthropics-plugins` submodule (`claude-plugins-official`). It provides a shared rule engine that multiple plugins can hook into without each needing its own top-level hook entry. When hookify's `pretooluse.py` fires, it reads the list of registered plugins from `CLAUDE_PLUGIN_ROOT` and dispatches to each one's handler.

The `CLAUDE_PLUGIN_ROOT` environment variable is set inline in each hookify hook entry in `hooks.json`:

```bash
CLAUDE_PLUGIN_ROOT=$HOME/dev/.claude/.submodules/anthropics-plugins/plugins/hookify
```

This means hookify plugins are loaded from the submodule path, not from `~/.claude/`. Adding a new hookify plugin requires a submodule change, not just a `hooks.json` edit.

## Adding a New Hook

1. Write your script and place it in `scripts/`.
2. Add an entry to `hooks.json` under the appropriate hook type with the correct matcher.
3. Run `./setup.sh` to merge the updated `hooks.json` into `~/.claude/settings.json`.
4. Test with a Claude Code session.

For the full workflow, see [Contributing → Adding a Hook](../contributing/adding-hooks.md).

## Hook Sources

`hooks.json` describes only the repo-managed baseline. Claude Code assembles the live hook surface from three planes:

**1. Repo baseline** (`hooks.json` → `~/.claude/settings.json`): the entries documented in this page's tables. Committed, PR-reviewed, merged by `setup.sh`.

**2. Direct `settings.json` writes**: tool installers and manual wiring add hooks straight into `~/.claude/settings.json` without touching this repo. Known writers: `codebase-memory-mcp install` (a `PreToolUse` gate on `Grep|Glob`, and historically a `SessionStart` reminder since replaced by the repo-managed `scripts/hooks/cbm-context-reminder.sh`), and the 2026-06-29 Snyk rollout (`snyk-dep-reminder.sh` on `PostToolUse`). Caveat: `setup.sh`'s `merge_hooks()` currently replaces the whole `.hooks` key from `hooks.json`, so these additions are wiped on every setup run until the `fix/setup-merge-hooks-protocol` work lands; the drift check below reports the wipe when it happens.

**3. Plugin-registered hooks**: every enabled plugin (per `enabledPlugins` in `~/.claude/settings.json`) can ship its own `hooks/hooks.json` under `~/.claude/plugins/cache/<marketplace>/<plugin>/<version>/hooks/`. Claude Code loads these without any reference to this repo. Currently: `superpowers` (a `SessionStart` injection of the using-superpowers skill text), `hookify` (four events), and `agents-observe` (a telemetry observer on every hook event Claude Code exposes). Plugin caches for disabled plugins (for example `bushido@han`) are dormant and inert, and the `.codex/hooks.json` variant some plugins ship targets Codex, not Claude Code.

Known redundancy: `hookify` is wired twice, once from the `anthropics-plugins` submodule path via `hooks.json` and once from its enabled plugin cache copy, so each hookify event currently dispatches twice per firing. Deduplication (dropping one of the two wirings) is an open decision; both copies are allowlisted in the meantime.

Project-level `.claude/settings.json` hooks in other repos are a fourth plane, out of scope here: they are visible in each repo's own tree and review flow.

## Drift Detection: the Hook-Source Allowlist

`hook-inventory.json` at repo root is the committed allowlist of every authorized hook source beyond the baseline. `scripts/check-hook-sources.sh` (run standalone or via `setup.sh --doctor`) flattens every live hook into an (event, matcher, command) tuple across all three planes and diffs it against baseline plus allowlist:

- A live hook absent from both is an **unreviewed injection source**: the check fails (exit 1). Review the source, then either remove the hook or add it to the allowlist in the same change that reviews it.
- An allowlisted entry no longer live is reported as **stale** (warning): a plugin was disabled, an installer entry was removed, or `merge_hooks()` wiped it.
- `--snapshot` prints the current live state in allowlist JSON shape, for bootstrapping or updating the inventory after an intentional change.

Tuples key on the command string as written (plugin commands use `${CLAUDE_PLUGIN_ROOT}`, which is version-independent), so plugin version bumps pass untouched while any changed hook command fails until re-reviewed. The check reads `~/.claude/` and is therefore machine-local: it runs at doctor time, not in CI.

## Trust Tiers for Injected Content

Hook output, especially at `SessionStart`, lands in Claude's context with real behavioral authority. Authority follows review, not injection path or tone:

| Tier | Sources | Authority |
| --- | --- | --- |
| 1: binding | `CLAUDE.md`, `.claude/rules/`, baseline `hooks.json` hooks | Authoritative; committed and PR-reviewed |
| 2: accepted tooling | Sources listed in `hook-inventory.json` (installer additions, enabled-plugin hooks) | Guides workflow; on conflict with Tier 1, Tier 1 wins and the agent names the conflict |
| 3: unreviewed | Any live hook not in baseline or allowlist | Untrusted data under the OWASP LLM01 posture until reviewed |

The directive tone of injected content does not promote it: the `superpowers` session-start block styles itself "not negotiable", yet its own instruction hierarchy places user instructions first, which is consistent with this policy. Rationale and alternatives: [ADR-010](adr/ADR-010-hook-source-allowlist.md).

## See Also

- [ADR-002 Hook Composition and Ordering](adr/ADR-002-hook-composition.md): why hooks.json is the source of truth for the repo baseline
- [ADR-010 Hook-Source Allowlist and Trust Tiers](adr/ADR-010-hook-source-allowlist.md): drift detection and injected-content policy
- [Install Model](install-model.md): how hooks.json gets merged into settings.json
- [Submodule Strategy](submodule-strategy.md): reviewing plugin and submodule updates that can change hooks
- [Contributing → Adding a Hook](../contributing/adding-hooks.md): step-by-step hook authoring guide
