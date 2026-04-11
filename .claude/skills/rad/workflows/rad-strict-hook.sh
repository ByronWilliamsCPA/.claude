#!/usr/bin/env bash
# rad-strict-hook.sh -- PreToolUse Bash hook for /rad-strict mode
# Only activates when RAD_STRICT_MODE=1 is set by the /rad-strict skill invocation.
[[ "${RAD_STRICT_MODE:-0}" != "1" ]] && exit 0

COMMAND="${CLAUDE_TOOL_INPUT:-}"
if echo "$COMMAND" | grep -q 'git commit'; then
  if grep -rn '#VERIFY' "${CLAUDE_PROJECT_DIR:-.}" --include='*.py' --include='*.ts' 2>/dev/null | grep -q .; then
    echo "ERROR: Unresolved #VERIFY annotations exist. Resolve before committing." >&2
    exit 1
  fi
fi
exit 0
