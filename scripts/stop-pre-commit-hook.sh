#!/usr/bin/env bash
# stop-pre-commit-hook.sh -- Stop hook: run pre-commit on session-touched files
# Trial added 2026-04-11. Decision rule: remove if median > 30s after 1 week.
# NOTE: CLAUDE_EDITED_FILES is not yet confirmed as a valid Claude Code hook env var.
# If unset, the hook always runs --all-files. Verify against hook env-vars docs.
set -uo pipefail

START=$(date +%s%N)

PRE_COMMIT_RC=0
# CLAUDE_EDITED_FILES: space-separated list of files modified this session (verify var name)
# Security (audit M-02): split into an array with `read -ra` and pass quoted so
# paths containing spaces or shell metacharacters cannot inject extra arguments
# into the pre-commit invocation.
if [[ -n "${CLAUDE_EDITED_FILES:-}" ]]; then
  read -ra _EDITED_FILES <<< "$CLAUDE_EDITED_FILES"
  pre-commit run --files "${_EDITED_FILES[@]}" 2>&1 || PRE_COMMIT_RC=$?
else
  pre-commit run --all-files 2>&1 || PRE_COMMIT_RC=$?
fi

END=$(date +%s%N)
ELAPSED=$(( (END - START) / 1000000 ))
echo "[stop-pre-commit-hook] elapsed: ${ELAPSED}ms" >&2
[[ $ELAPSED -gt 30000 ]] && echo "[stop-pre-commit-hook] WARNING: >30s, consider removing" >&2
# Security (audit M-06): Stop hooks must not propagate non-zero exits because
# Claude Code blocks session cleanup on a non-zero Stop. Surface the pre-commit
# result as advisory text and always exit 0.
if [[ $PRE_COMMIT_RC -ne 0 ]]; then
    echo "[stop-pre-commit-hook] pre-commit returned ${PRE_COMMIT_RC} (advisory; not blocking session)" >&2
fi
exit 0
