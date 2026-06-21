#!/usr/bin/env bash
# install-cli-tools.sh -- SessionStart hook: install preferred CLI tools if missing.
# Runs as a no-op when all tools are already present.
set -euo pipefail

# ast-grep: structural code search and multi-file refactoring.
# Install via npm (@ast-grep/cli package); the short alias 'sg' is intentionally
# not used here because it collides with shadow-utils 'newgrp'.
if ! command -v ast-grep >/dev/null 2>&1; then
  echo "SESSION SETUP: ast-grep not found -- installing via npm..." >&2
  npm install -g @ast-grep/cli >&2
  echo "SESSION SETUP: ast-grep installed." >&2
fi
