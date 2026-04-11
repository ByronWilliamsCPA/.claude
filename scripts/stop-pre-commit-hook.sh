#!/usr/bin/env bash
# stop-pre-commit-hook.sh -- Stop hook: run pre-commit on session-touched files
# Trial added 2026-04-11. Decision rule: remove if median > 30s after 1 week.
set -euo pipefail

START=$(date +%s%N)

# CLAUDE_EDITED_FILES: space-separated list of files modified this session (verify var name)
if [[ -n "${CLAUDE_EDITED_FILES:-}" ]]; then
  # shellcheck disable=SC2086
  pre-commit run --files $CLAUDE_EDITED_FILES 2>&1
else
  pre-commit run --all-files 2>&1
fi

EXIT_CODE=$?
END=$(date +%s%N)
ELAPSED=$(( (END - START) / 1000000 ))
echo "[stop-pre-commit-hook] elapsed: ${ELAPSED}ms" >&2
[[ $ELAPSED -gt 30000 ]] && echo "[stop-pre-commit-hook] WARNING: >30s, consider removing" >&2
exit $EXIT_CODE
