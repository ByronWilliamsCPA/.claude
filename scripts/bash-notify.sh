#!/usr/bin/env bash
# =============================================================================
# Bash Notify — PostToolUse Hook
# =============================================================================
# Reads the timing start timestamp written by bash-pre-hook.sh, computes the
# duration of the completed Bash command, and fires a Windows balloon
# notification via powershell.exe if the duration exceeds the threshold.
#
# Always exits 0 (advisory — never blocks Claude Code).
#
# Expected stdin: JSON payload from Claude Code PostToolUse hook:
#   {"tool_name":"Bash","tool_input":{"command":"..."},"tool_response":{...}}
#
# Timing file: /tmp/claude-bash-start (written by bash-pre-hook.sh)
# =============================================================================

set -uo pipefail

NOTIFY_THRESHOLD_SECONDS=30
LOG_FILE="${HOME}/.claude/logs/bash-notify.log"
mkdir -p "$(dirname "$LOG_FILE")"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" >> "$LOG_FILE"
}

# ---------------------------------------------------------------------------
# Read and validate the timing start file
# ---------------------------------------------------------------------------
START_FILE="/tmp/claude-bash-start"

if [[ ! -f "$START_FILE" ]]; then
    exit 0
fi

START=$(cat "$START_FILE" 2>/dev/null || true)
rm -f "$START_FILE"

# Validate that START is a non-empty integer
if [[ -z "$START" ]] || ! [[ "$START" =~ ^[0-9]+$ ]]; then
    exit 0
fi

# ---------------------------------------------------------------------------
# Compute duration
# ---------------------------------------------------------------------------
NOW=$(date +%s)
DURATION=$(( NOW - START ))

if [[ $DURATION -le $NOTIFY_THRESHOLD_SECONDS ]]; then
    exit 0
fi

# ---------------------------------------------------------------------------
# Duration exceeded threshold — build notification message
# ---------------------------------------------------------------------------

# Try to extract command from stdin JSON (optional)
CMD=""
if command -v jq &>/dev/null; then
    STDIN_JSON=$(cat 2>/dev/null || true)
    if [[ -n "$STDIN_JSON" ]]; then
        CMD=$(jq -r '.tool_input.command // empty' 2>/dev/null <<< "$STDIN_JSON" || true)
    fi
fi

# Truncate command to 80 chars
if [[ -n "$CMD" ]]; then
    CMD="${CMD:0:80}"
    MSG="Task complete (${DURATION}s): ${CMD}"
else
    MSG="Task complete (${DURATION}s)"
fi

# ---------------------------------------------------------------------------
# Fire non-blocking Windows toast notification via powershell.exe
# ---------------------------------------------------------------------------

# Escape single quotes in MSG for safe embedding in PowerShell single-quoted strings
PS_MSG="${MSG//\'/\'\'}"

PS_CMD="Add-Type -AssemblyName System.Windows.Forms; \$n = New-Object System.Windows.Forms.NotifyIcon; \$n.Icon = [System.Drawing.SystemIcons]::Application; \$n.BalloonTipTitle = 'Claude Code'; \$n.BalloonTipText = '${PS_MSG}'; \$n.Visible = \$true; \$n.ShowBalloonTip(5000); Start-Sleep -Milliseconds 5500; \$n.Dispose()"

powershell.exe -NonInteractive -command "$PS_CMD" &>/dev/null & disown 2>/dev/null || true

# ---------------------------------------------------------------------------
# Emit NOTIFY line (visible to Claude and captured by tests)
# ---------------------------------------------------------------------------
echo "NOTIFY: ${MSG}"
log "NOTIFY: ${MSG}"

exit 0
