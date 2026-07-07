#!/usr/bin/env bash
# =============================================================================
# Handoff-Resume Reminder -- SessionStart Hook
# =============================================================================
# Companion to precompact-handoff.sh. On session start (startup, resume,
# clear, or compact), checks for the single overwritten backstop file at
# ~/.claude/logs/handoffs/auto-precompact-latest.md and, if present, prints its
# key content (branch, dirty count, captured timestamp) as session-start
# context, clearly labeled as an automatic backstop capture rather than a
# manual /handoff. A capture older than 48 hours is still printed but labeled
# STALE, so a resuming session does not mistake ancient state for current
# state.
#
# Registered alongside cbm-context-reminder.sh and delegation-reminder.sh under
# hooks.SessionStart with matchers startup|resume|clear|compact.
#
# Exit codes:
#   0 -- always. If the file is missing, prints nothing and exits silently.
#
# Fail-safe: any internal error (unreadable file, unparsable timestamp) exits
# 0 with no noise beyond what could already be printed; the staleness check
# degrades to "unknown age" rather than aborting.
#
# Smoke test (trigger / file-present path):
#   mkdir -p ~/.claude/logs/handoffs
#   cat > ~/.claude/logs/handoffs/auto-precompact-latest.md <<'EOF'
#   # Auto-Precompact Handoff (backstop snapshot, overwritten every compaction)
#   Captured: 2026-07-07T12:00:00Z
#   Trigger: auto
#   Branch: feat/example
#   Dirty files: 2
#   EOF
#   bash handoff-resume-reminder.sh < /dev/null; echo "exit=$?"
#   (expect exit=0 and the file's content printed with a backstop-capture note)
#
# Smoke test (pass-through, no file):
#   rm -f ~/.claude/logs/handoffs/auto-precompact-latest.md
#   bash handoff-resume-reminder.sh < /dev/null; echo "exit=$?"
#   (expect exit=0, no output)
# =============================================================================

set -uo pipefail

HANDOFF_FILE="${HOME}/.claude/logs/handoffs/auto-precompact-latest.md"

[[ -f "$HANDOFF_FILE" ]] || exit 0

CONTENT=$(cat "$HANDOFF_FILE" 2>/dev/null || true)
[[ -z "$CONTENT" ]] && exit 0

# ---- Staleness check: parse the "Captured:" line, degrade quietly on failure -
CAPTURED_LINE=$(printf '%s\n' "$CONTENT" | grep -m1 '^Captured:' || true)
CAPTURED_TS="${CAPTURED_LINE#Captured: }"

STALE=0
if [[ -n "$CAPTURED_TS" ]] && command -v date &>/dev/null; then
    CAPTURED_EPOCH=$(date -u -d "$CAPTURED_TS" +%s 2>/dev/null || true)
    if [[ -n "$CAPTURED_EPOCH" ]]; then
        NOW_EPOCH=$(date -u +%s 2>/dev/null || true)
        if [[ -n "$NOW_EPOCH" ]]; then
            AGE=$(( NOW_EPOCH - CAPTURED_EPOCH ))
            if (( AGE > 48 * 3600 )); then
                STALE=1
            fi
        fi
    fi
fi

echo "AUTOMATIC PRECOMPACT BACKSTOP FOUND:"
if [[ "$STALE" -eq 1 ]]; then
    echo "STALE: this capture is more than 48 hours old. Treat it as historical, not current, state."
fi
echo ""
printf '%s\n' "$CONTENT"
echo ""
echo "This is an automatic backstop capture, not a substitute for /handoff. Its presence means compaction happened without a manual handoff written first; re-verify current state before acting on anything above."

exit 0
