#!/usr/bin/env bash
set -e
REPO_ROOT="$(git rev-parse --show-toplevel)"
GIT_COMMON_DIR="$(git rev-parse --git-common-dir)"
SOURCE="$REPO_ROOT/.github/hooks/pre-push"
DEST="$GIT_COMMON_DIR/hooks/pre-push"

if [ ! -f "$SOURCE" ]; then
  echo "ERROR: Hook source not found at $SOURCE" >&2
  exit 1
fi

cp "$SOURCE" "$DEST"
chmod +x "$DEST"
echo "Pre-push hook installed at $DEST"
echo "Bypass with: git push --no-verify"
