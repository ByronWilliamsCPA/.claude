#!/usr/bin/env bash
# install-cli-tools.sh -- SessionStart hook: install preferred CLI tools if missing.
# Best-effort and non-fatal: never fails the session if a tool cannot be
# installed (missing npm, no network, permission error). Runs as a no-op when
# all tools are already present.
set -uo pipefail

# Pin the version so SessionStart behavior is deterministic; bump deliberately.
ASTGREP_VERSION="0.43.0"

# ast-grep: structural code search and multi-file refactoring.
# Installed via npm (@ast-grep/cli). Invoke the tool as 'ast-grep', never 'sg':
# shadow-utils ships its own 'sg' command (a newgrp wrapper) that shadows it.
if ! command -v ast-grep >/dev/null 2>&1; then
    if ! command -v npm >/dev/null 2>&1; then
        echo "SESSION SETUP: npm not found -- skipping ast-grep install." >&2
    elif npm install -g "@ast-grep/cli@${ASTGREP_VERSION}" >&2; then
        echo "SESSION SETUP: ast-grep ${ASTGREP_VERSION} installed." >&2
    else
        echo "SESSION SETUP: ast-grep install failed -- continuing without it." >&2
    fi
fi

# Never fail the session over optional tooling.
exit 0
