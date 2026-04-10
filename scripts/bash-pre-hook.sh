#!/usr/bin/env bash
# =============================================================================
# Bash Pre-Hook — PreToolUse Hook
# =============================================================================
# Intercepts Bash tool calls to:
#   1. Block force-pushes to main or master (exit 2 with BLOCKED message)
#   2. Write a timing start timestamp to /tmp/claude-bash-start for the
#      post-hook notification script to compute command duration.
#
# The timestamp is written ONLY when the command is allowed through.
#
# Exit codes:
#   0 — allow tool call to proceed
#   2 — block tool call; stdout message fed back to Claude
# =============================================================================

set -uo pipefail

LOG_FILE="${HOME}/.claude/logs/bash-pre-hook.log"
mkdir -p "$(dirname "$LOG_FILE")"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" >> "$LOG_FILE"
}

# Require jq for JSON parsing
if ! command -v jq &>/dev/null; then
    log "ERROR: jq not found; cannot parse hook context — passing through"
    date +%s > /tmp/claude-bash-start
    exit 0
fi

# Read JSON context from stdin
CONTEXT=$(cat)

if [[ -z "$CONTEXT" ]]; then
    date +%s > /tmp/claude-bash-start
    exit 0
fi

# Extract command from tool input
CMD=$(jq -r '.tool_input.command // empty' 2>/dev/null <<< "$CONTEXT")

if [[ -z "$CMD" ]]; then
    date +%s > /tmp/claude-bash-start
    exit 0
fi

# ---------------------------------------------------------------------------
# Force-push guard
# Block: git push with --force, -f, or --force-with-lease targeting main/master
#
# Two patterns cover argument ordering variations:
#   Pattern A: force flag appears before branch name
#     e.g. git push --force origin main
#   Pattern B: branch name appears before force flag (uncommon but possible)
#     e.g. git push origin main --force
# ---------------------------------------------------------------------------

is_force_push=false
if echo "$CMD" | grep -qE 'git\s+push\s+(.*\s)?(--force|-f|--force-with-lease)'; then
    is_force_push=true
fi

if $is_force_push; then
    targets_protected=false
    # Check for main or master as a standalone word (branch name)
    if echo "$CMD" | grep -qE '\b(main|master)\b'; then
        targets_protected=true
    fi

    if $targets_protected; then
        log "BLOCKED force-push to protected branch: ${CMD}"
        echo "BLOCKED: Force-pushing to main or master is not allowed. Use a feature branch or open a PR. Command was: ${CMD}"
        exit 2
    fi
fi

# ---------------------------------------------------------------------------
# Command is allowed — write timing start timestamp
# ---------------------------------------------------------------------------
date +%s > /tmp/claude-bash-start
log "Allowed: ${CMD}"
exit 0
