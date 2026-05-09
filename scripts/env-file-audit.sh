#!/usr/bin/env bash
# env-file-audit.sh -- FileChanged hook: advisory on .env* file writes
set -euo pipefail

FILE="${CLAUDE_FILE_PATH:-}"
[[ -z "$FILE" ]] && exit 0

# Security (audit M-08): canonicalize the path with realpath, then verify it
# is a regular file genuinely under $HOME. The previous version compared
# string prefixes, which let /home/byron-evil/... slip through when
# HOME=/home/byron, and used a dead null-byte check (bash strings cannot
# contain NUL). All rejection branches log to stderr so an operator can
# trace why a particular invocation was a no-op.
REAL_FILE=$(realpath -e -- "$FILE" 2>/dev/null) || {
    echo "SECURITY: env-file-audit could not resolve $FILE; skipping" >&2
    exit 0
}
if [[ ! -f "$REAL_FILE" ]]; then
    echo "SECURITY: env-file-audit: $REAL_FILE is not a regular file; skipping" >&2
    exit 0
fi
case "$REAL_FILE" in
    "$HOME"/*) ;;  # genuinely inside $HOME, fall through
    *)
        echo "SECURITY: env-file-audit refused path outside \$HOME: $REAL_FILE" >&2
        exit 0
        ;;
esac
FILE="$REAL_FILE"

echo "SECURITY: .env file modified: $FILE" >&2
echo "Verify no secrets are being written. If intentional, acknowledge." >&2

if grep -qE '(SECRET|PASSWORD|API_KEY|TOKEN|PRIVATE_KEY)=' "$FILE" 2>/dev/null; then
  echo "WARNING: secret-pattern strings detected in $FILE" >&2
fi
exit 0
