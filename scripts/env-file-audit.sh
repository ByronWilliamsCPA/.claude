#!/usr/bin/env bash
# env-file-audit.sh -- FileChanged hook: advisory on .env* file writes
set -euo pipefail

FILE="${CLAUDE_FILE_PATH:-}"
[[ -z "$FILE" ]] && exit 0

# Security (audit M-08): validate FILE before passing it to grep. Reject paths
# that are not regular files, are outside $HOME, or contain null bytes. This
# prevents pseudo-files like /dev/stdin or /proc/self/mem from being read.
if [[ "$FILE" == *$'\0'* ]] || [[ ! -f "$FILE" ]] || [[ "$FILE" != "$HOME"* ]]; then
    exit 0
fi

echo "SECURITY: .env file modified: $FILE" >&2
echo "Verify no secrets are being written. If intentional, acknowledge." >&2

if grep -qE '(SECRET|PASSWORD|API_KEY|TOKEN|PRIVATE_KEY)=' "$FILE" 2>/dev/null; then
  echo "WARNING: secret-pattern strings detected in $FILE" >&2
fi
exit 0
