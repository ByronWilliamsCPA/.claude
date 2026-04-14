---
title: Platform Audit Checklist
schema_type: common
status: published
owner: core-maintainer
purpose: Accumulated drift checks from past platform audits. Grows only when a new drift type is caught.
---

Each item here was added because a specific drift type was observed in the Claude Code
platform configuration. Do not add speculative checks. Add new items only when a real
drift incident surfaces.

## Hook event validity

- [ ] All hook event keys in `~/.claude/settings.json` are in the officially documented
  set. As of 2026-04-13, the documented events are:
  ConfigChange, Elicitation, ElicitationResult, InstructionsLoaded, Notification,
  PermissionRequest, PostCompact, PostToolUse, PostToolUseFailure, PreCompact,
  PreToolUse, SessionEnd, SessionStart, Setup, Stop, SubagentStart, SubagentStop,
  TaskCompleted, TeammateIdle, UserPromptSubmit, WorktreeCreate, WorktreeRemove.
  Verify against <https://code.claude.com/docs/en/hooks> before adding any new event key.

  *Observed drift (2026-04-13):* `env-file-audit.sh` was written targeting a FileChanged
  event that does not exist in the platform. The script is retained but annotated as
  unwired.

## Hook environment variable names

- [ ] All `$CLAUDE_*` environment variable names used in hook scripts are in the
  documented env-var list. Verify against
  <https://code.claude.com/docs/en/hooks#hook-environment-variables> before relying on
  any variable in a hook script.

  *Observed drift (2026-04-13):* `stop-pre-commit-hook.sh` references
  `$CLAUDE_EDITED_FILES` with a comment noting it is unverified. Confirm or remove
  before treating it as reliable.

## settings.json key validity

- [ ] Any new top-level key added to `~/.claude/settings.json` must appear in the JSON
  schema at <https://json.schemastore.org/claude-code-settings.json> before committing.
  Unrecognized keys are silently ignored by Claude Code, giving false confidence.

## Checklist maintenance

Review this file quarterly alongside `docs/known-vulnerabilities.md`.
Remove items that are no longer relevant. Never remove the observed-drift note for an
item; it explains why the check was added and provides context for future audits.
