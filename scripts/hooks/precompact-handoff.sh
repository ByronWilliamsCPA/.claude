#!/usr/bin/env bash
# =============================================================================
# PreCompact Auto-Handoff -- PreCompact Hook
# =============================================================================
# Fires immediately before Claude Code compacts the conversation. Captures a
# handful of cheap, objective facts about repo state (current branch,
# dirty-file count, the first ~8 changed paths, a UTC timestamp, and the
# compaction trigger when available) into a SINGLE per-project file that is
# overwritten on every firing:
# ~/.claude/logs/handoffs/auto-precompact-latest-<project-hash>.md, where
# <project-hash> is a 12-character sha256 of the project directory path. The
# hash namespacing keeps concurrent sessions in different projects from
# racing on, or reading, each other's snapshot (see #ASSUME/#EDGE markers
# below).
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
#        degrades to a placeholder value on failure instead of aborting. A
#        directory-creation or write failure still exits 0, but now emits a
#        one-line stderr warning and removes any incomplete target file
#        instead of leaving a stale snapshot in place.
#
# Smoke test (trigger / happy path, run inside a git repo with uncommitted
# changes):
#   echo '{"hook_event_name":"PreCompact","trigger":"auto"}' | \
#     bash precompact-handoff.sh; echo "exit=$?"
#   ls ~/.claude/logs/handoffs/auto-precompact-latest-*.md
#   (expect exit=0 and a populated, namespaced file with mode 600 containing
#   Branch/Dirty files/Captured lines)
#
# Smoke test (pass-through outside a repo, still succeeds and writes a
# placeholder file rather than erroring):
#   cd /tmp && echo '{}' | bash precompact-handoff.sh; echo "exit=$?"
#   (expect exit=0; Branch line reads the not-a-repo placeholder)
# =============================================================================

set -uo pipefail

HANDOFF_DIR="${HOME}/.claude/logs/handoffs"
PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$PWD}"

# ---- Namespace the snapshot filename by project so concurrent sessions in --
# ---- different projects never collide on, or resume into, each other's file
# #ASSUME: sha256sum (GNU coreutils) is present; shasum (macOS/BSD) is the
# fallback. When neither exists, every project on the host collapses onto one
# "nohash" snapshot file, reintroducing the cross-project collision this
# namespacing exists to prevent.
# #VERIFY: `command -v sha256sum shasum` on any host running this hook; add a
# real fallback (or a loud warning) if a target OS ships neither.
if command -v sha256sum &>/dev/null; then
    PROJECT_HASH=$(printf '%s' "$PROJECT_DIR" | sha256sum | cut -c1-12)
elif command -v shasum &>/dev/null; then
    PROJECT_HASH=$(printf '%s' "$PROJECT_DIR" | shasum -a 256 | cut -c1-12)
else
    PROJECT_HASH="nohash"
fi
HANDOFF_FILE="${HANDOFF_DIR}/auto-precompact-latest-${PROJECT_HASH}.md"

# #CRITICAL: this hook must never block compaction (see header). Both failure
# points below (mkdir, write) degrade to a stderr warning plus exit 0, never a
# nonzero exit or a hang.
# #VERIFY: if compaction ever stalls or a session bricks, rule this script out
# first via `bash -x precompact-handoff.sh` with the same stdin/env, before
# assuming a harness bug.
if ! mkdir -p "$HANDOFF_DIR" 2>/dev/null; then
    echo "WARNING: precompact-handoff.sh: failed to create ${HANDOFF_DIR}; skipping snapshot" >&2
    exit 0
fi

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

# ---- Write to a temp file first, then rename into place ----------------------
# Temp-file-then-mv keeps the write atomic within the same directory: a
# concurrent reader (handoff-resume-reminder.sh) never observes a
# partially-written file, and mv within one filesystem is a single rename
# syscall rather than a truncate-then-write race.
# #EDGE: two sessions compacting the SAME project concurrently can still race
# on the final mv (last writer wins); this only protects against a
# torn/partial read, not against one session's snapshot overwriting a
# sibling's. Acceptable for a best-effort backstop; do not rely on this file
# for anything that needs cross-session consistency.
TMP_FILE=$(mktemp "${HANDOFF_DIR}/.auto-precompact-tmp.XXXXXX" 2>/dev/null || true)
if [[ -z "$TMP_FILE" ]]; then
    echo "WARNING: precompact-handoff.sh: failed to create temp file in ${HANDOFF_DIR}; skipping snapshot" >&2
    exit 0
fi

WRITE_OK=1
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
} > "$TMP_FILE" 2>/dev/null || WRITE_OK=0

if [[ "$WRITE_OK" -ne 1 || ! -s "$TMP_FILE" ]]; then
    echo "WARNING: precompact-handoff.sh: snapshot write failed; removing incomplete file so a stale snapshot cannot masquerade as fresh" >&2
    rm -f "$TMP_FILE" "$HANDOFF_FILE"
    exit 0
fi

chmod 600 "$TMP_FILE" 2>/dev/null

if ! mv -f "$TMP_FILE" "$HANDOFF_FILE" 2>/dev/null; then
    echo "WARNING: precompact-handoff.sh: failed to finalize snapshot; removing stale target" >&2
    rm -f "$TMP_FILE" "$HANDOFF_FILE"
    exit 0
fi

exit 0
