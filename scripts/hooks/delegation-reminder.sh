#!/usr/bin/env bash
# SessionStart hook: inject the delegation protocol reminder and silently
# refresh the task-observer skills manifest.
#
# Registered in ~/.claude/settings.json under hooks.SessionStart with matchers
# startup|resume|clear|compact. Stdout becomes session context; keep it short.
# Companion inline text lives in CLAUDE.md ("Delegation and subagent usage");
# full patterns live in .claude/rules/supervisor.md (not auto-loaded).
set -uo pipefail

# Refresh ~/.claude/skill-observations/available-skills.md for task-observer.
# Output is suppressed: the manifest is a file artifact, not session context.
MANIFEST_GEN="$(dirname "$0")/../generate-skills-manifest.sh"
if [ -x "$MANIFEST_GEN" ]; then
  "$MANIFEST_GEN" >/dev/null 2>&1 || true
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
