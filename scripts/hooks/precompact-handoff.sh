#!/usr/bin/env bash
# =============================================================================
# PreCompact Auto-Handoff -- PreCompact Hook
# =============================================================================
# Fires immediately before Claude Code compacts the conversation. Captures a
# handful of cheap, objective facts about repo state (current branch,
# dirty-file count, the first ~8 changed paths, a UTC timestamp, and the
# compaction trigger when available) into a SINGLE file that is overwritten on
# every firing: ~/.claude/logs/handoffs/auto-precompact-latest.md.
#
# This is deliberately a different convention from the manual /handoff skill,
# which archives a curated, timestamped doc per invocation at
# ~/.claude/logs/handoffs/handoff-<ts>.md. This hook is the lighter backstop
# for the case CLAUDE.md's "Session length" section names directly: autocompact
# is "lossy... the backstop, not the plan," and this pair (paired with
# handoff-resume-reminder.sh) is a cheap safety net for compaction firing with
# no manual handoff written first. It never replaces a real /handoff.
#
# Exit codes:
#   0 -- always. A PreCompact hook must never block compaction, and a bug in
#        this capture step must never brick a session; every step below
#        degrades to a placeholder value on failure instead of aborting.
#
# Smoke test (trigger / happy path, run inside a git repo with uncommitted
# changes):
#   echo '{"hook_event_name":"PreCompact","trigger":"auto"}' | \
#     bash precompact-handoff.sh; echo "exit=$?"
#   cat ~/.claude/logs/handoffs/auto-precompact-latest.md
#   (expect exit=0 and a populated file with Branch/Dirty files/Captured lines)
#
# Smoke test (pass-through outside a repo, still succeeds and writes a
# placeholder file rather than erroring):
#   cd /tmp && echo '{}' | bash precompact-handoff.sh; echo "exit=$?"
#   (expect exit=0; Branch line reads the not-a-repo placeholder)
# =============================================================================

set -uo pipefail

HANDOFF_DIR="${HOME}/.claude/logs/handoffs"
HANDOFF_FILE="${HANDOFF_DIR}/auto-precompact-latest.md"
PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$PWD}"

mkdir -p "$HANDOFF_DIR" 2>/dev/null || exit 0

# ---- Optional: read the compaction trigger (manual|auto) from stdin ----------
# Best-effort only; a missing jq or unparsable payload just leaves it unknown.
INPUT=$(cat 2>/dev/null || true)
TRIGGER="unknown"
if [[ -n "$INPUT" ]] && command -v jq &>/dev/null; then
    PARSED_TRIGGER=$(jq -r '.trigger // empty' 2>/dev/null <<< "$INPUT" || true)
    [[ -n "$PARSED_TRIGGER" ]] && TRIGGER="$PARSED_TRIGGER"
fi

# ---- Cheap, objective git state; every lookup degrades to a placeholder ------
BRANCH=$(git -C "$PROJECT_DIR" branch --show-current 2>/dev/null || true)
[[ -z "$BRANCH" ]] && BRANCH="(unknown: not a git repo, or detached HEAD)"

DIRTY_COUNT=$(git -C "$PROJECT_DIR" status --porcelain 2>/dev/null | wc -l | tr -d '[:space:]' || true)
[[ -z "$DIRTY_COUNT" ]] && DIRTY_COUNT="0"

# Strip the two-character status code plus its trailing space to get bare
# paths (rename entries keep their "old -> new" form, which is fine here).
CHANGED_FILES=$(git -C "$PROJECT_DIR" status --porcelain 2>/dev/null | sed -E 's/^.{3}//' | head -8 || true)

TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null || echo "unknown")

# ---- Write the single, overwritten snapshot file -----------------------------
{
    echo "# Auto-Precompact Handoff (backstop snapshot, overwritten every compaction)"
    echo ""
    echo "Captured: ${TIMESTAMP}"
    echo "Trigger: ${TRIGGER}"
    echo "Branch: ${BRANCH}"
    echo "Dirty files: ${DIRTY_COUNT}"
    echo ""
    echo "Changed files (first 8):"
    if [[ -n "$CHANGED_FILES" ]]; then
        printf '%s\n' "$CHANGED_FILES" | sed 's/^/- /'
    else
        echo "- none"
    fi
    echo ""
    echo "This snapshot was written automatically by precompact-handoff.sh. It is"
    echo "not a substitute for the manual /handoff skill; its existence means"
    echo "compaction happened without a manual handoff written first. Treat it as a"
    echo "coarse, best-effort snapshot, not a curated summary."
} > "$HANDOFF_FILE" 2>/dev/null

exit 0
