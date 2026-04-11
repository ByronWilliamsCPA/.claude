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
| `0` | Allow — the tool call proceeds |
| `2` | Block — the tool call is aborted; stderr is shown as an error message |
| `1` | Hook failure — treated as an error in the hook script itself |

## Adding a Hook

1. Write the script and place it in `scripts/`.
2. Add an entry to `hooks.json` under the appropriate hook type.
3. Run `./setup.sh` to merge `hooks.json` into `~/.claude/settings.json`.
4. Test in a Claude Code session.

For the full step-by-step workflow, see [Contributing → Adding a Hook](../contributing/adding-hooks.md).

## See Also

- `hooks.json` at repo root — the authoritative hook definition
- [Architecture → Hook Pipeline](../architecture/hook-pipeline.md) — turn-level execution diagram and narrative
- [ADR-002 Hook Composition and Ordering](../architecture/adr/ADR-002-hook-composition.md) — design rationale
- [Contributing → Adding a Hook](../contributing/adding-hooks.md) — step-by-step authoring guide
