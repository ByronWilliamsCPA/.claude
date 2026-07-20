#!/usr/bin/env bash
# stop-pre-commit-hook.sh -- Stop hook: run pre-commit on session-touched files
# Trial added 2026-04-11. Decision rule: remove if median > 30s after 1 week.
set -uo pipefail

START=$(date +%s%N)

PRE_COMMIT_RC=0
# Scope to files changed in the working tree; never --all-files on Stop.
git rev-parse --is-inside-work-tree >/dev/null 2>&1 || exit 0
mapfile -t _CHANGED < <(git diff --name-only HEAD 2>/dev/null; git ls-files --others --exclude-standard 2>/dev/null)
[[ ${#_CHANGED[@]} -eq 0 ]] && exit 0
pre-commit run --files "${_CHANGED[@]}" 2>&1 || PRE_COMMIT_RC=$?

END=$(date +%s%N)
ELAPSED=$(( (END - START) / 1000000 ))
echo "[stop-pre-commit-hook] elapsed: ${ELAPSED}ms" >&2
[[ $ELAPSED -gt 30000 ]] && echo "[stop-pre-commit-hook] WARNING: >30s, consider removing" >&2
# Security (audit M-06): Stop hooks must not propagate non-zero exits because
# Claude Code blocks session cleanup on a non-zero Stop. Surface the pre-commit
# result as advisory text AND persist it to a log so the user can review what
# actually failed (a single stderr line at session end is easy to miss).
if [[ $PRE_COMMIT_RC -ne 0 ]]; then
    case $PRE_COMMIT_RC in
        1) MSG="pre-commit found issues (rc=1). Run 'pre-commit run --all-files' to see details." ;;
        127) MSG="pre-commit not installed (rc=127). Install with: pipx install pre-commit" ;;
        *) MSG="pre-commit exited with unexpected code ${PRE_COMMIT_RC}; investigate." ;;
    esac
    echo "[stop-pre-commit-hook] ${MSG}" >&2
    FINDINGS_LOG="${HOME}/.claude/logs/stop-pre-commit-findings.log"
    mkdir -p "$(dirname "$FINDINGS_LOG")" 2>/dev/null \
        && printf '%s\t%s\n' "$(date -Is)" "$MSG" >> "$FINDINGS_LOG" 2>/dev/null \
        || true
fi
exit 0
