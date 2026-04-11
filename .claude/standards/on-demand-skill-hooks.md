# On-Demand Skill Hooks

An on-demand hook activates only while a specific skill is in use and deactivates
when the skill exits. This is distinct from always-on hooks (SessionStart, Stop)
and per-tool hooks (PreToolUse, PostToolUse).

## Pattern

1. The skill SKILL.md documents the expected pre/post conditions.
2. A companion hook script is guarded by an env var set by the skill invocation.
3. The skill sets the guard on entry and unsets it on exit (or the hook script
   checks for a skill-generated lock file).

## Reference implementation: `/rad-strict`

The `rad` skill's strict mode (invoked via `/rad-strict`) blocks any Bash commit
attempt until `#VERIFY` annotations have been resolved in the session's edited files.

Hook guard: the hook script checks for `$RAD_STRICT_MODE` env var before acting.
When `/rad-strict` is not active, the hook is a no-op.

## Registration requirement

The hook script must be registered in `settings.json` or `.claude/settings.json` to
activate. Without registration, the script exists but is never called.

Add a `PreToolUse` entry pointing to the script. The guard condition makes it a no-op
when the skill is inactive, so registration cost is negligible:

```json
{
  "matcher": "Bash",
  "hooks": [
    {
      "type": "command",
      "command": "bash $HOME/.claude/scripts/<your-hook-script>.sh",
      "timeout": 10
    }
  ]
}
```

Document the registration step in the skill's SKILL.md under a `## Setup` section.

## Cautions

- On-demand hooks create a second control plane. If the guard condition is not
  reliably set/unset, the hook fires unexpectedly or silently fails.
- Always instrument the guard check with a log line so unexpected activations
  are visible.
- Maintain a `## Known Limitation` section in any skill that uses this pattern.
