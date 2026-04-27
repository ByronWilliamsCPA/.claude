#!/usr/bin/env bash
set -e
REPO_ROOT="$(git rev-parse --show-toplevel)"
SOURCE="$REPO_ROOT/.github/hooks/pre-push"
DEST="$REPO_ROOT/.git/hooks/pre-push"
cp "$SOURCE" "$DEST"
chmod +x "$DEST"
echo "Pre-push hook installed at $DEST"
echo "Bypass with: git push --no-verify"
