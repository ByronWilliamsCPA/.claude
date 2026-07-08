#!/usr/bin/env bash
# =============================================================================
# Handoff-Resume Reminder -- SessionStart Hook
# =============================================================================
# Companion to precompact-handoff.sh. On session start (startup, resume,
# clear, or compact), checks for the single overwritten backstop file for the
# CURRENT project at
# ~/.claude/logs/handoffs/auto-precompact-latest-<project-hash>.md (the same
# 12-character sha256-of-project-dir namespacing precompact-handoff.sh writes)
# and, if present, prints its key content (branch, dirty count, captured
# timestamp) as session-start context, clearly labeled as an automatic
# backstop capture rather than a manual /handoff. A capture older than 48
# hours is still printed but labeled STALE, so a resuming session does not
# mistake ancient state for current state. A capture whose timestamp cannot be
# parsed is labeled AGE UNKNOWN, never silently treated as fresh.
#
# Registered alongside cbm-context-reminder.sh and delegation-reminder.sh under
# hooks.SessionStart with matchers startup|resume|clear|compact.
#
# Exit codes:
#   0 -- always. If the file is missing, prints nothing and exits silently.
#
# Fail-safe: any internal error (unreadable file, unparsable timestamp) exits
# 0 with no noise beyond what could already be printed; the staleness check
# degrades to an explicit "unknown age" label (never to "fresh") rather than
# aborting.
#
# Smoke test (trigger / file-present path):
#   mkdir -p ~/.claude/logs/handoffs
#   HASH=$(printf '%s' "${CLAUDE_PROJECT_DIR:-$PWD}" | sha256sum | cut -c1-12)
#   cat > ~/.claude/logs/handoffs/auto-precompact-latest-${HASH}.md <<'EOF'
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
#   rm -f ~/.claude/logs/handoffs/auto-precompact-latest-*.md
#   bash handoff-resume-reminder.sh < /dev/null; echo "exit=$?"
#   (expect exit=0, no output)
# =============================================================================

set -uo pipefail

HANDOFF_DIR="${HOME}/.claude/logs/handoffs"
PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$PWD}"

# ---- Namespace by project, matching precompact-handoff.sh exactly ------------
# #ASSUME: this hash computation must stay byte-for-byte identical to
# precompact-handoff.sh's (same tool-preference order, same input string, same
# cut width); any drift makes this script look at the wrong filename and
# silently print nothing, even though a snapshot exists.
# #VERIFY: diff the hash-computation block against precompact-handoff.sh
# whenever either file changes.
if command -v sha256sum &>/dev/null; then
    PROJECT_HASH=$(printf '%s' "$PROJECT_DIR" | sha256sum | cut -c1-12)
elif command -v shasum &>/dev/null; then
    PROJECT_HASH=$(printf '%s' "$PROJECT_DIR" | shasum -a 256 | cut -c1-12)
else
    PROJECT_HASH="nohash"
fi
HANDOFF_FILE="${HANDOFF_DIR}/auto-precompact-latest-${PROJECT_HASH}.md"

[[ -f "$HANDOFF_FILE" ]] || exit 0

CONTENT=$(cat "$HANDOFF_FILE" 2>/dev/null || true)
[[ -z "$CONTENT" ]] && exit 0

# ---- Staleness check: parse the "Captured:" line ------------------------------
# #CRITICAL: an unparseable (or missing) timestamp must never be presented as
# fresh. STALE has three states: 0=fresh (age computed and under 48h),
# 1=stale (age computed and over 48h), 2=unknown (age could not be computed
# for any reason). It starts at 2 and is only set to 0 or 1 once every parse
# step below succeeds; no code path leaves it at 0 by default.
# #VERIFY: if a new date variant is ever targeted (neither GNU -d nor BSD -j
# -f), confirm it lands in STALE=2 rather than silently parsing wrong.
CAPTURED_LINE=$(printf '%s\n' "$CONTENT" | grep -m1 '^Captured:' || true)
CAPTURED_TS="${CAPTURED_LINE#Captured: }"

STALE=2
if [[ -n "$CAPTURED_TS" ]] && command -v date &>/dev/null; then
    # GNU date (-d) first; BSD/macOS date has no -d, so fall back to its -j -f
    # form parsing the known ISO-8601 UTC format precompact-handoff.sh writes.
    CAPTURED_EPOCH=$(date -u -d "$CAPTURED_TS" +%s 2>/dev/null || true)
    if [[ -z "$CAPTURED_EPOCH" ]]; then
        CAPTURED_EPOCH=$(date -u -j -f "%Y-%m-%dT%H:%M:%SZ" "$CAPTURED_TS" +%s 2>/dev/null || true)
    fi
    if [[ -n "$CAPTURED_EPOCH" ]]; then
        NOW_EPOCH=$(date -u +%s 2>/dev/null || true)
        if [[ -n "$NOW_EPOCH" ]]; then
            AGE=$(( NOW_EPOCH - CAPTURED_EPOCH ))
            if (( AGE > 48 * 3600 )); then
                STALE=1
            else
                STALE=0
            fi
        fi
    fi
fi

echo "AUTOMATIC PRECOMPACT BACKSTOP FOUND:"
if [[ "$STALE" -eq 1 ]]; then
    echo "STALE: this capture is more than 48 hours old. Treat it as historical, not current, state."
elif [[ "$STALE" -eq 2 ]]; then
    echo "AGE UNKNOWN: the capture timestamp could not be parsed. Treat this snapshot with caution; it may be stale."
fi
echo ""
printf '%s\n' "$CONTENT"
echo ""
echo "This is an automatic backstop capture, not a substitute for /handoff. Its presence means compaction happened without a manual handoff written first; re-verify current state before acting on anything above."

exit 0
