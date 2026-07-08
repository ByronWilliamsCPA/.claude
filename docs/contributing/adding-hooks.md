---
title: "Adding a Hook"
schema_type: common
status: draft
owner: core-maintainer
purpose: "Guide for adding a new hook to hooks.json."
tags:
  - contributing
  - hooks
  - development
---

Before adding a hook, read [ADR-002](../architecture/adr/ADR-002-hook-composition.md). Key constraint: `setup.sh` union-merges `hooks.json` into `~/.claude/settings.json`'s hooks block on every run (amended 2026-07-06; it no longer overwrites the block wholesale), but only `hooks.json` entries are version-controlled and reviewed. All hook changes still go into `hooks.json` at repo root.

Hooks that do not come from this repo (a tool installer writing into `~/.claude/settings.json`, or an enabled plugin shipping its own `hooks/hooks.json`) must instead be recorded in the allowlist `hook-inventory.json` at repo root, in the same change that reviews them. `setup.sh --doctor` runs `scripts/check-hook-sources.sh` and fails on any live hook found in neither `hooks.json` nor the allowlist. The check reads the local machine's live state, so it runs at doctor time on each machine rather than in CI, and it detects drift after the fact rather than preventing it. See [ADR-010](../architecture/adr/ADR-010-hook-source-allowlist.md) and [Hook Pipeline → Hook Sources](../architecture/hook-pipeline.md#hook-sources).

## Pick a Hook Type

| Hook type | Fires when | Typical use |
| --- | --- | --- |
| `UserPromptSubmit` | User sends a message, before Claude processes it | Intent detection, context injection, reminders |
| `PreToolUse` | Before each tool call Claude attempts | Blocking gates, security checks, behavioral guards |
| `PostToolUse` | After each tool call completes | Compatibility checks, usage tracking |
| `Stop` | When Claude finishes its turn | Cleanup, session logging |
| `PreCompact` | Immediately before context compaction, automatic or manual (`/compact`) | Cheap, objective auto-handoff snapshot as an unattended-autocompact backstop |
| `SessionStart` | When a session opens, resumes, clears, or compacts (per matcher) | Context injection: stdout on exit 0 becomes session context (see `scripts/hooks/`) |

## Exit Codes

| Exit code | Meaning | Applies to |
| --- | --- | --- |
| `0` | Success: proceed | All hook types |
| `2` | Block: abort the tool call and show stderr as error | `PreToolUse` only |
| `1` | Hook error: the script itself failed | All hook types |

`PostToolUse` hooks must always exit 0. A non-zero exit from a PostToolUse hook is a hook-level error, not a tool block. Never use PostToolUse to block behavior.

## Adding an Entry to `hooks.json`

`hooks.json` is a JSON object with hook type names as keys and arrays of hook entries as values. Each entry has a `hooks` array containing the actual command definitions. An entry may optionally have a `matcher` field (a regex matched against the tool name).

**Without a matcher** (fires on all tool calls for that hook type):

```json
{
  "PostToolUse": [
    {
      "hooks": [
        {
          "type": "command",
          "command": "bash $HOME/.claude/scripts/my-new-hook.sh",
          "timeout": 10,
          "statusMessage": "Running my check..."
        }
      ]
    }
  ]
}
```

**With a matcher** (fires only for Edit or Write tool calls):

```json
{
  "PreToolUse": [
    {
      "matcher": "Edit|Write",
      "hooks": [
        {
          "type": "command",
          "command": "bash $HOME/.claude/scripts/my-gate.sh",
          "timeout": 5,
          "statusMessage": "Checking before edit..."
        }
      ]
    }
  ]
}
```

Place the new entry in the correct position within the type's array. Array order is execution order: read [ADR-002](../architecture/adr/ADR-002-hook-composition.md) for the contract around ordering.

## Write the Script

Place the script in `scripts/`. Use `$HOME/.claude/scripts/` as the path prefix in `hooks.json` (the symlink from `setup.sh` makes the repo's `scripts/` available at that path).

Script requirements:

- Must be executable (`chmod +x scripts/my-hook.sh`)
- Must exit 0 on success
- For PreToolUse gates: exit 2 to block with an error message printed to stderr
- Must complete within the `timeout` (in seconds). Hooks that time out are treated as failures.
- Should not produce unnecessary stdout: status messages appear via `statusMessage`, not stdout

## Re-run `setup.sh`

After editing `hooks.json`, merge the change into `~/.claude/settings.json`:

```bash
./setup.sh
```

The hooks take effect immediately in the next Claude Code session (or after reloading settings in the current session).

## Verify

Open a Claude Code session and trigger the relevant tool type. You should see the `statusMessage` appear during the hook execution. Check that the exit code behavior matches your intent.

## See Also

- [ADR-002 Hook Composition and Ordering](../architecture/adr/ADR-002-hook-composition.md): source-of-truth decision and execution ordering contract
- [Architecture → Hook Pipeline](../architecture/hook-pipeline.md): turn-level execution sequence
- [Hooks Reference](../reference/hooks.md): current hook scripts and their matchers
