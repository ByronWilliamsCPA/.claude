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
# Note: -e is intentionally omitted. This is a PreToolUse hook that must never
# exit non-zero unexpectedly (exit 2 is reserved for the block signal). Any
# unhandled error must fall through to the allow path.

LOG_FILE="${HOME}/.claude/logs/bash-pre-hook.log"
mkdir -p "$(dirname "$LOG_FILE")"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" >> "$LOG_FILE"
}

# Require jq for JSON parsing
if ! command -v jq &>/dev/null; then
    log "ERROR: jq not found; cannot parse hook context — passing through"
    printf '%s' "$(date +%s)" > /tmp/claude-bash-start.tmp && mv /tmp/claude-bash-start.tmp /tmp/claude-bash-start
    exit 0
fi

# Read JSON context from stdin
CONTEXT=$(cat)

if [[ -z "$CONTEXT" ]]; then
    printf '%s' "$(date +%s)" > /tmp/claude-bash-start.tmp && mv /tmp/claude-bash-start.tmp /tmp/claude-bash-start
    exit 0
fi

# Extract command from tool input
CMD=$(jq -r '.tool_input.command // empty' 2>/dev/null <<< "$CONTEXT")

if [[ -z "$CMD" ]]; then
    printf '%s' "$(date +%s)" > /tmp/claude-bash-start.tmp && mv /tmp/claude-bash-start.tmp /tmp/claude-bash-start
    exit 0
fi

# ---------------------------------------------------------------------------
# Force-push guard
# Block: git push with --force, -f, or --force-with-lease when:
#   (a) the explicit branch target is main or master, OR
#   (b) no branch target is present at all (bare force push)
#
# Logic: detect force flag first, then extract the branch token by stripping
# "git push", the force flag(s), and the remote name from the command string.
# If no branch token remains, the push is bare (could target any tracking
# branch including main) and must be blocked.
# ---------------------------------------------------------------------------

# Only check force-push for git push commands
if ! echo "$CMD" | grep -qE 'git\s+push'; then
    printf '%s' "$(date +%s)" > /tmp/claude-bash-start.tmp && mv /tmp/claude-bash-start.tmp /tmp/claude-bash-start
    exit 0
fi

# Now check for force flags (we know it's a git push command)
if echo "$CMD" | grep -qE '(--force|--force-with-lease(=[^\s]+)?|-f)(\s|$)'; then
    # Extract the branch portion: strip git push, force flags, remote name
    BRANCH_TOKEN=$(echo "$CMD" | \
        sed -E 's/git\s+push\s+//' | \
        sed -E 's/(--force|--force-with-lease(=[^\s]+)?|-f)\s*//' | \
        sed -E 's/[a-zA-Z0-9_-]+\s+//' | \
        awk '{print $1}')

    # Extract destination ref from refspec forms (HEAD:main, :main, src:dest).
    # ${BRANCH_TOKEN##*:} strips the source ref; if no colon, returns BRANCH_TOKEN.
    DEST_TOKEN="${BRANCH_TOKEN##*:}"

    # Normalize common Git ref prefixes so fully-qualified refs such as
    # refs/heads/main and refs/main are treated the same as main.
    NORMALIZED_BRANCH_TOKEN="${BRANCH_TOKEN#refs/heads/}"
    NORMALIZED_BRANCH_TOKEN="${NORMALIZED_BRANCH_TOKEN#refs/}"
    NORMALIZED_DEST_TOKEN="${DEST_TOKEN#refs/heads/}"
    NORMALIZED_DEST_TOKEN="${NORMALIZED_DEST_TOKEN#refs/}"

    # Block if: no branch token (bare force push), explicit branch is main/master,
    # or destination ref extracted from a refspec is main/master.
    if [[ -z "$BRANCH_TOKEN" ]] || \
       echo "$NORMALIZED_BRANCH_TOKEN" | grep -qE '^(main|master)$' || \
       echo "$NORMALIZED_DEST_TOKEN" | grep -qE '^(main|master)$'; then
        log "BLOCKED force-push: CMD=${CMD}"
        echo "BLOCKED: force-push to main/master (or bare force-push) is prohibited. Use a PR instead."
        exit 2
    fi
fi

# ---------------------------------------------------------------------------
# Command is allowed — write timing start timestamp (atomic write)
# ---------------------------------------------------------------------------
printf '%s' "$(date +%s)" > /tmp/claude-bash-start.tmp && mv /tmp/claude-bash-start.tmp /tmp/claude-bash-start
log "Allowed: ${CMD}"
exit 0
