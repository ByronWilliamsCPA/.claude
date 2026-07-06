#!/usr/bin/env bash
# SessionStart hook: inject the delegation protocol reminder and silently
# refresh the task-observer skills manifest.
#
# Registered under hooks.SessionStart with matchers startup|resume|clear|compact.
# Canonical source: hooks.json in this repo; setup.sh merge_hooks() regenerates
# the live ~/.claude/settings.json hooks block from it, so edit hooks.json, not
# the live file. Stdout becomes session context; keep it short.
# Companion inline text lives in CLAUDE.md ("Delegation and subagent usage");
# full patterns live in .claude/rules/supervisor.md (not auto-loaded).
set -uo pipefail

# Refresh ~/.claude/skill-observations/available-skills.md for task-observer.
# Success output is suppressed (the manifest is a file artifact, not session
# context); failure emits a one-line warning so a stale manifest stays visible.
# #ASSUME: the generator lives one directory above this script; hooks invoke it
# via the ~/.claude/scripts symlink, so $0 resolves inside that tree.
# #EDGE: a hung generator would starve the reminder payload below, which shares
# this hook's timeout budget; the inner timeout bounds it at 3 seconds.
# #VERIFY: if task-observer reports missing skills, compare the manifest mtime
# against the session start time.
MANIFEST_GEN="$(dirname "$0")/../generate-skills-manifest.sh"
if [ -x "$MANIFEST_GEN" ]; then
  timeout 3 "$MANIFEST_GEN" >/dev/null 2>&1 \
    || echo "WARNING: skills-manifest refresh failed; available-skills.md may be stale."
else
  echo "WARNING: skills-manifest generator not found at $MANIFEST_GEN; available-skills.md may be stale."
fi

cat <<'EOF'
DELEGATION PROTOCOL (main session = orchestrator):
- Dispatch subagents for exploration (Explore, haiku), well-specified
  implementation units (sonnet), and all reviews. Keep the main thread for
  decisions, synthesis, validation, and user interaction.
- Any exploration beyond 1-2 known files belongs in an Explore subagent.
  Subagents apply the codebase-memory-mcp tool preference the same as the
  main session; the "MCP tools first" rule governs how, not where.
- If a dispatch fails on usage limits: narrow scope, retry on a cheaper
  model, or surface the blocker. Never silently absorb the task inline.
Full patterns: ~/.claude/rules/supervisor.md
EOF
