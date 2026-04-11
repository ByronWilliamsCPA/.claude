#!/usr/bin/env bash
# session-start-rules.sh -- SessionStart hook: inject context-relevant rules
# v1: branch detection only. Expand incrementally after proving stable.
set -euo pipefail

BRANCH=$(git -C "${CLAUDE_PROJECT_DIR:-.}" rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")

# Phase-gate projects: if we're on a phase/ branch, note it
if [[ "$BRANCH" =~ ^phase/ ]]; then
  echo "SESSION CONTEXT: Phase branch $BRANCH -- /phase-gate skill is relevant" >&2
fi

# Python projects: if pyproject.toml exists, remind about python rules
if [[ -f "${CLAUDE_PROJECT_DIR:-.}/pyproject.toml" ]]; then
  echo "SESSION CONTEXT: Python project detected -- rules/python.md applies" >&2
fi

exit 0
