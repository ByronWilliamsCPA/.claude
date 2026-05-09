#!/usr/bin/env bash
# =============================================================================
# Bash Pre-Hook -- PreToolUse Hook
# =============================================================================
# Intercepts Bash tool calls to:
#   1. Block force-pushes to main or master (exit 2 with BLOCKED message)
#   2. Write a timing start timestamp to /tmp/claude-bash-start for the
#      post-hook notification script to compute command duration.
#
# The timestamp is written ONLY when the command is allowed through.
#
# Exit codes:
#   0 -- allow tool call to proceed
#   2 -- block tool call; stdout message fed back to Claude
# =============================================================================

set -uo pipefail
# Note: -e is intentionally omitted. This is a PreToolUse hook that must never
# exit non-zero unexpectedly (exit 2 is reserved for the block signal). Any
# unhandled error must fall through to the allow path.

# Security (audit H-01): timing state lives under the user's home directory,
# not world-writable /tmp. This eliminates the TOCTOU symlink-attack window
# that existed when the previous fixed path /tmp/claude-bash-start.tmp could
# be pre-created by any local user.
TMP_DIR="${HOME}/.claude/tmp_cleanup"
START_FILE="${TMP_DIR}/bash-start"
mkdir -p "${TMP_DIR}"
chmod 700 "${TMP_DIR}" 2>/dev/null || true

LOG_FILE="${HOME}/.claude/logs/bash-pre-hook.log"
mkdir -p "$(dirname "$LOG_FILE")"
# Security (audit M-07): bash logs may capture commands that contain inline
# tokens or connection strings; restrict permissions on first creation.
[[ -f "$LOG_FILE" ]] || { : > "$LOG_FILE"; chmod 600 "$LOG_FILE" 2>/dev/null || true; }

# Redact common credential-pattern strings from log lines.
redact() {
    printf '%s' "$1" | sed -E \
        -e 's/(Authorization:[[:space:]]*Bearer[[:space:]]+)[^[:space:]]+/\1[REDACTED]/gi' \
        -e 's/(password[[:space:]]*[:=][[:space:]]*)[^[:space:]&]+/\1[REDACTED]/gi' \
        -e 's/((api[_-]?key|token|secret)[[:space:]]*[:=][[:space:]]*)[^[:space:]&]+/\1[REDACTED]/gi' \
        -e 's|://([^:/@[:space:]]+):[^@[:space:]]+@|://\1:[REDACTED]@|g'
}

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $(redact "$*")" >> "$LOG_FILE"
}

# Atomically write the timing start timestamp to START_FILE.
# Uses mktemp inside the same directory so the rename stays on one filesystem.
write_start_marker() {
    local tmp
    tmp=$(mktemp "${START_FILE}.XXXXXX") || return 0
    printf '%s' "$(date +%s)" > "$tmp" && mv "$tmp" "$START_FILE"
}

# Require jq for JSON parsing
if ! command -v jq &>/dev/null; then
    log "ERROR: jq not found; cannot parse hook context -- passing through"
    write_start_marker
    exit 0
fi

# Read JSON context from stdin
CONTEXT=$(cat)

if [[ -z "$CONTEXT" ]]; then
    write_start_marker
    exit 0
fi

# Extract command from tool input
CMD=$(jq -r '.tool_input.command // empty' 2>/dev/null <<< "$CONTEXT")

if [[ -z "$CMD" ]]; then
    write_start_marker
    exit 0
fi

# ---------------------------------------------------------------------------
# Force-push guard
# Block: git push with --force, -f, or --force-with-lease when:
#   (a) the explicit branch target is main or master, OR
#   (b) no branch token is present at all (bare force push), OR
#   (c) parsing is ambiguous (safe fallback: block)
#
# Three bypass vectors are handled:
#
#   Bypass 1 -- URL-format remote names:
#     git push git@github.com:org/repo main --force
#     A URL remote defeats simple alphanumeric sed stripping. Detected by
#     checking for "://" or "@" in the remote position and blocked (ambiguous
#     parse is treated as the safe fallback).
#
#   Bypass 2 -- Interleaved flags:
#     git push -f -u origin main  OR  git push origin -f main
#     Fixed by stripping ALL flag tokens first, then reading remote and branch
#     positionally from the remaining non-flag arguments.
#
#   Bypass 3 -- Compound commands:
#     ls; git push --force origin main  OR  git status && git push --force
#     Fixed by extracting only the "git push ..." segment before any analysis.
# ---------------------------------------------------------------------------

# Only check force-push for git push commands
if ! echo "$CMD" | grep -qE 'git\s+push'; then
    write_start_marker
    exit 0
fi

# ---------------------------------------------------------------------------
# Bypass 3: Extract only the git push segment from compound commands.
# Strip everything before the last "git push" occurrence so that prefix
# commands (ls; git push, git status && git push, etc.) do not pollute the
# argument list used for branch extraction below.
# ---------------------------------------------------------------------------
PUSH_SEGMENT=$(echo "$CMD" | grep -oE 'git\s+push.*' | tail -1)

if [[ -z "$PUSH_SEGMENT" ]]; then
    # grep -oE found nothing; fall through to allow
    write_start_marker
    exit 0
fi

# Now check for force flags within the extracted push segment
if echo "$PUSH_SEGMENT" | grep -qE '(--force|--force-with-lease(=[^\s]+)?|-f)(\s|$)'; then

    # -----------------------------------------------------------------------
    # Bypass 2: Strip all flags first, then read positional args in order.
    #
    # 1. Remove "git push" prefix.
    # 2. Strip every token that starts with "-" (flags, including -f, -u,
    #    --force, --force-with-lease=..., etc.).
    # 3. The first remaining token is the remote; the second is the branch.
    #    If there is no remote or no branch, treat as bare/ambiguous and block.
    # -----------------------------------------------------------------------
    ARGS_ONLY=$(echo "$PUSH_SEGMENT" | sed -E 's/^git\s+push\s*//')

    # Build an array of positional (non-flag) tokens
    declare -a POS_ARGS=()
    for token in $ARGS_ONLY; do
        if [[ "$token" != -* ]]; then
            POS_ARGS+=("$token")
        fi
    done

    REMOTE_TOKEN="${POS_ARGS[0]:-}"
    BRANCH_TOKEN="${POS_ARGS[1]:-}"

    # -----------------------------------------------------------------------
    # Bypass 1: Detect URL-format remote names.
    # If the remote looks like a URL (contains "://" or starts with git@),
    # parsing the branch is ambiguous; block as the safe fallback.
    # -----------------------------------------------------------------------
    if [[ -n "$REMOTE_TOKEN" ]] && \
       (echo "$REMOTE_TOKEN" | grep -qE '://|^git@'); then
        log "BLOCKED force-push (URL remote, ambiguous parse): CMD=${CMD}"
        echo "BLOCKED: force-push with a URL remote cannot be safely validated. Use a named remote and a PR instead."
        exit 2
    fi

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
# Command is allowed -- write timing start timestamp (atomic write)
# ---------------------------------------------------------------------------
printf '%s' "$(date +%s)" > /tmp/claude-bash-start.tmp && mv /tmp/claude-bash-start.tmp /tmp/claude-bash-start
log "Allowed: ${CMD}"
exit 0
