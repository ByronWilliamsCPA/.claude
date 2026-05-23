#!/usr/bin/env bash
# =============================================================================
# Session Length Warning -- Stop Hook
# =============================================================================
# After each response, counts the number of API calls in the current session
# JSONL and prints a warning banner when the session is getting expensive.
#
# Thresholds (API calls = unique requestIds in the session JSONL):
#   >= 150: caution -- approaching the expensive zone
#   >= 250: strong warning -- session is very long, break recommended
#
# Wiring: settings.json Stop hook, no matcher (fires after every response).
# =============================================================================

set -euo pipefail

CAUTION_THRESHOLD=150
WARNING_THRESHOLD=250

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-}"
if [[ -z "$PROJECT_DIR" ]]; then
  exit 0
fi

# Derive the project slug used by Claude Code for the .claude/projects/ directory.
# Claude Code converts the absolute path by replacing each '/' with '-'.
PROJECT_SLUG=$(echo "$PROJECT_DIR" | sed 's|/|-|g')
PROJECTS_ROOT="$HOME/.claude/projects"
PROJECT_PATH="$PROJECTS_ROOT/$PROJECT_SLUG"

if [[ ! -d "$PROJECT_PATH" ]]; then
  exit 0
fi

# Find the most recently modified top-level JSONL (current session file).
# -maxdepth 1 excludes subagent files which live under <session-id>/subagents/.
CURRENT_JSONL=$(find "$PROJECT_PATH" -maxdepth 1 -name "*.jsonl" -type f \
  2>/dev/null | xargs ls -t 2>/dev/null | head -1)

if [[ -z "$CURRENT_JSONL" ]]; then
  exit 0
fi

# Count unique requestIds -- each unique ID corresponds to one API call.
# Gracefully handle missing/malformed files.
CALL_COUNT=$(grep -o '"requestId":"[^"]*"' "$CURRENT_JSONL" 2>/dev/null \
  | sort -u | wc -l | tr -d ' ')

if [[ "$CALL_COUNT" -ge "$WARNING_THRESHOLD" ]]; then
  echo ""
  echo "SESSION LENGTH WARNING: ~${CALL_COUNT} API calls in this session."
  echo "This session is very long. Cache-write costs compound with each exchange."
  echo "Finish the current task, then type /clear to start a fresh session."
  echo ""
elif [[ "$CALL_COUNT" -ge "$CAUTION_THRESHOLD" ]]; then
  echo ""
  echo "Session length notice: ~${CALL_COUNT} API calls. Consider a /clear"
  echo "break after finishing the current task to keep costs down."
  echo ""
fi
