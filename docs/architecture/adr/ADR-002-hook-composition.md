---
title: "ADR-002: Hook Composition and Ordering"
schema_type: common
status: draft
owner: core-maintainer
purpose: "Records how hooks compose across hookify dispatch and project-specific gates."
tags:
  - adr
  - decisions
  - hooks
  - architecture
---

> **Status**: Accepted
>
> **Decision date**: 2026-04-11
>
> **Deciders**: Byron Williams

## Context

Claude Code supports five hook types: `PreToolUse`, `PostToolUse`, `Stop`, `UserPromptSubmit`, and `SessionStart`. Hook configuration lives in `~/.claude/settings.json` under the `hooks` key. The immediate problem: `settings.json` is machine-local state. If a developer edits the hooks block directly in `settings.json`, those changes are lost the next time `setup.sh` runs, because `setup.sh` overwrites the hooks block from `hooks.json`.

A second problem: this repo needs both generic hooks (the hookify plugin dispatch engine from `anthropics-plugins`) and project-specific behavioral gates (secrets file guard, planning bridge gate, Python compatibility check, PR review reminder). These need to compose cleanly without one overwriting the other.

A third problem: within a single tool invocation, several hooks fire in a defined order. That order is a behavioral contract. A `PreToolUse` that runs before the secrets check would silently allow edits that the secrets check is supposed to block.

This ADR documents the source-of-truth decision, the composition pattern, and the execution ordering contract.

## Decision

`hooks.json` at repo root is the authoritative definition of all hooks. `setup.sh` merges it into `~/.claude/settings.json` using:

```bash
jq --slurpfile h "$hooks_source" '.hooks = $h[0]' "$settings"
```

This wholesale replaces the `.hooks` key in `settings.json` with the contents of `hooks.json` on every `setup.sh` run. Consequences: direct edits to `settings.json`'s hooks block are always clobbered; all hook changes go into `hooks.json` and are committed.

### Composition of hook arrays

Each hook type in `hooks.json` is an array of hook entries. Entries within an array execute in order. An entry may have a `matcher` (a regex matching the tool name) or no matcher (applies to all tool invocations within that hook type). Matcher-specific entries fire only when the matched tool is called; no-matcher entries fire on every call.

Current hook definitions by type:

**PreToolUse** (fires before each tool call, in this order):

1. **Secrets file guard**: matcher `Edit|Write`. Blocks writes to `.env` and `settings.local.json` with exit code 2.
2. **Planning bridge gate**: matcher `Skill`. Calls `scripts/planning-bridge-gate.sh` before any Skill invocation to enforce plan-approval workflow.
3. **Security guidance reminder**: matcher `Edit|Write|MultiEdit`. Runs `security_reminder_hook.py` from `anthropics-plugins/security-guidance` to surface security patterns.
4. **hookify PreToolUse**: no matcher (all tools). Dispatches to the hookify plugin engine, which runs any plugins registered for PreToolUse events.

**PostToolUse** (fires after each tool call, in this order):

1. **py310-compat-check**: matcher `Edit|Write`. Checks modified Python files for syntax incompatible with Python 3.10.
2. **hookify PostToolUse**: no matcher (all tools). Dispatches to hookify plugin engine for PostToolUse plugins.

**Stop** (fires at end of model turn):

1. **hookify Stop**: dispatches to hookify plugin engine's stop handler.

**UserPromptSubmit** (fires on each user message, in this order):

1. **hookify UserPromptSubmit**: dispatches to hookify plugin engine. Runs first, before any project-specific logic.
2. **PR review reminder**: runs `scripts/pr-review-reminder.py` to detect PR review intent and inject reminders.

### Execution ordering across a conversation turn

```text
User sends message
  → UserPromptSubmit[0]: hookify userpromptsubmit.py
  → UserPromptSubmit[1]: pr-review-reminder.py
  → Model processes prompt, issues tool calls
    → For each tool call:
        → PreToolUse[matcher]: secrets guard (if Edit|Write)
        → PreToolUse[matcher]: planning gate (if Skill)
        → PreToolUse[matcher]: security reminder (if Edit|Write|MultiEdit)
        → PreToolUse[no-matcher]: hookify pretooluse.py
        → Tool executes
        → PostToolUse[matcher]: py310-compat-check (if Edit|Write)
        → PostToolUse[no-matcher]: hookify posttooluse.py
  → Model finishes turn
    → Stop[no-matcher]: hookify stop.py
```

Exit codes from hook scripts determine whether the tool call proceeds: exit 0 allows, exit 2 blocks with an error message, exit 1 is a hook-level failure.

## Alternatives Considered

**Edit `settings.json` directly and commit it**: `settings.json` contains machine-local state (API keys, model preferences) that must not be committed. Committing it would either expose secrets or require heavy `.gitignore` surgery that makes the hooks block uneditable via git.

**Separate per-hook scripts invoked from `settings.json` without hookify**: Each hook type would call one script, which would then `source` or call others. This is exactly what hookify provides, but reimplemented without the plugin registry, conditional enabling, or shared rule engine hookify supplies.

**Collapse project-specific gates into hookify plugins**: hookify plugins live in the `anthropics-plugins` submodule, which is an upstream repo we do not control. Project-specific gates (planning-bridge-gate, py310-compat-check, PR review reminder) belong in this repo's `scripts/` and `hooks.json`, not as upstream plugin contributions.

**One hook entry per hook type**: If each type had a single dispatcher script, that script would need to hardcode all the sub-hooks. Composition via array entries in `hooks.json` makes the order explicit and readable without a secondary dispatch layer.

## Consequences

### Positive

- Hook definitions are version-controlled, diffable, and reproducible on any machine.
- Execution order within each hook type is explicit in `hooks.json`: no hidden dispatch logic.
- Adding a new gate is a two-step change: add the script to `scripts/`, add an entry to `hooks.json`, re-run `setup.sh`.
- hookify plugins (from upstream `anthropics-plugins`) compose cleanly alongside project-specific gates because each is a separate array entry.

### Negative

- Contributors who do not know about `hooks.json` will edit `settings.json` directly and lose their changes on the next `setup.sh` run. The `--doctor` flag surfaces broken symlinks but not settings.json drift.
- `setup.sh` must be re-run after every change to `hooks.json`. The hooks do not take effect until the jq merge runs.

### Neutral

- hookify's plugin registry is in `.submodules/anthropics-plugins/plugins/hookify/`. Adding a hookify plugin still requires a submodule commit, not just a `hooks.json` change.

## References

- `hooks.json`: the authoritative hook definitions
- `setup.sh`: the jq merge command (`merge_hooks` function)
- `scripts/planning-bridge-gate.sh`: Skill PreToolUse gate
- `scripts/py310-compat-check.sh`: Edit/Write PostToolUse compatibility check
- `scripts/pr-review-reminder.py`: UserPromptSubmit PR review detector
- `.submodules/anthropics-plugins/plugins/hookify/`: the hookify plugin engine
- `.submodules/anthropics-plugins/plugins/security-guidance/`: security reminder hook
- `docs/architecture/hook-pipeline.md`: narrative explanation with embedded diagram
- `docs/architecture/diagrams/hook_pipeline.svg`: sequence diagram of a full turn
- [ADR-001](ADR-001-two-layer-symlink-install.md): explains why `hooks.json` is separate from `settings.json`
