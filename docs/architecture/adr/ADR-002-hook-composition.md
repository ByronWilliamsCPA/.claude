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

Claude Code supports six hook types: `PreToolUse`, `PostToolUse`, `Stop`, `UserPromptSubmit`, `SessionStart`, and `PreCompact`. Hook configuration lives in `~/.claude/settings.json` under the `hooks` key. The immediate problem: `settings.json` is machine-local state. If a developer edits the hooks block directly in `settings.json`, those changes are lost the next time `setup.sh` runs, because `setup.sh` overwrites the hooks block from `hooks.json`.

A second problem: this repo needs both generic hooks (the hookify plugin dispatch engine from `anthropics-plugins`) and project-specific behavioral gates (secrets file guard, planning bridge gate, Python compatibility check, PR review reminder). These need to compose cleanly without one overwriting the other.

A third problem: within a single tool invocation, several hooks fire in a defined order. That order is a behavioral contract. A `PreToolUse` that runs before the secrets check would silently allow edits that the secrets check is supposed to block.

This ADR documents the source-of-truth decision, the composition pattern, and the execution ordering contract.

## Decision

`hooks.json` at repo root is the authoritative definition of all repo-owned hooks. `setup.sh` merges it into `~/.claude/settings.json`.

> **Amended 2026-07-06.** The original decision used a replace-assignment
> (`.hooks = $h[0]`), which wholesale-replaced the `.hooks` key on every
> `setup.sh` run. That held only while `setup.sh` was the sole writer. By
> 2026-07 at least three writers targeted `settings.json .hooks` (setup.sh,
> the codebase-memory-mcp installer, direct edits), and the replace semantics
> silently deleted the other writers' entries (senior review 2026-07-01,
> Critical finding). `merge_hooks()` now performs a union merge: hook identity
> is the (event, matcher, command) triple, deduplicated per event type over
> (matcher, command) pairs; `hooks.json` entries are authoritative for their
> own identities, and unrecognized `settings.json` entries are preserved. Removals from `hooks.json` no longer propagate
> automatically; `setup.sh --doctor` reports live-only drift for manual
> action. The rule "all repo-owned hook changes go into `hooks.json` and are
> committed" still stands; direct edits registering repo scripts are flagged
> by `--doctor` as unbackported.

### Composition of hook arrays

Each hook type in `hooks.json` is an array of hook entries. Entries within an array execute in order. An entry may have a `matcher` (a regex matching the tool name) or no matcher (applies to all tool invocations within that hook type). Matcher-specific entries fire only when the matched tool is called; no-matcher entries fire on every call.

Current hook definitions by type:

**PreToolUse** (fires before each tool call, in this order):

1. **Bash command guard**: matcher `Bash`. Runs `scripts/bash-pre-hook.sh` to block bypass flags (`--no-verify`, `--no-gpg-sign`, admin merges, force-push to protected branches).
2. **Sensitive file guard**: matcher `Edit|Write|MultiEdit`. Runs `scripts/sensitive-file-guard.sh`; blocks writes to `.env` and `settings.local.json` with exit code 2.
3. **Planning bridge gate**: matcher `Skill`. Calls `scripts/planning-bridge-gate.sh` before any Skill invocation to enforce plan-approval workflow.
4. **Security guidance reminder**: matcher `Edit|Write|MultiEdit`. Runs `security_reminder_hook.py` from `anthropics-plugins/security-guidance` to surface security patterns.
5. **hookify PreToolUse**: no matcher (all tools). Dispatches to the hookify plugin engine, which runs any plugins registered for PreToolUse events.
6. **Destructive-command guard**: matcher `Bash`. Runs `scripts/destructive-command-guard.sh`, a sibling to `bash-pre-hook.sh` that blocks recursive chmod/chown on a root/home/cwd/glob target, SQL DROP/TRUNCATE, curl/wget piped into a shell interpreter, and recursive force-delete targeting a root/home/cwd/glob path or any path outside the project workspace.

**PostToolUse** (fires after each tool call, in this order):

1. **py310-compat-check**: matcher `(Edit|Write)`. Checks modified Python files for syntax incompatible with Python 3.10.
2. **snyk-dep-reminder**: matcher `Edit|Write|MultiEdit`. Runs `scripts/snyk-dep-reminder.sh` to surface a Snyk scan reminder when dependency manifests change.
3. **test-skip-guard**: matcher `Edit|Write|MultiEdit`. Runs `scripts/test-skip-guard.sh`, which mechanically enforces CLAUDE.md's "never propose `pytest.mark.skip` to silence a failing test" rule by grepping post-edit test-file contents for a skip/ignore marker and blocking (exit 2) if found.
4. **hookify PostToolUse**: no matcher (all tools). Dispatches to hookify plugin engine for PostToolUse plugins.

**Stop** (fires at end of model turn):

1. **hookify Stop**: dispatches to hookify plugin engine's stop handler.

**PreCompact** (fires immediately before context compaction, automatic or manual):

1. **precompact-handoff**: no matcher. Runs `scripts/hooks/precompact-handoff.sh`, which writes a cheap, objective auto-handoff snapshot (git branch, dirty-file count, first ~8 changed paths, UTC timestamp) to a single overwritten file as a backstop for the unattended-autocompact case; always exits 0 and never blocks compaction.

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
        → PreToolUse[matcher]: bash command guard (if Bash)
        → PreToolUse[matcher]: sensitive file guard (if Edit|Write|MultiEdit)
        → PreToolUse[matcher]: planning gate (if Skill)
        → PreToolUse[matcher]: security reminder (if Edit|Write|MultiEdit)
        → PreToolUse[no-matcher]: hookify pretooluse.py
        → PreToolUse[matcher]: destructive-command guard (if Bash)
        → Tool executes
        → PostToolUse[matcher]: py310-compat-check (if Edit|Write)
        → PostToolUse[matcher]: snyk-dep-reminder (if Edit|Write|MultiEdit)
        → PostToolUse[matcher]: test-skip-guard (if Edit|Write|MultiEdit)
        → PostToolUse[no-matcher]: hookify posttooluse.py
  → Model finishes turn
    → Stop[no-matcher]: hookify stop.py
  → If context is compacted (auto or manual), separately from the turn cycle:
    → PreCompact[no-matcher]: precompact-handoff.sh
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

- Contributors who do not know about `hooks.json` may still edit `settings.json` directly. Since the 2026-07-06 amendment those edits survive the merge, but they are unversioned; `setup.sh --doctor` flags live-only entries that reference repo-owned paths as unbackported.
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
