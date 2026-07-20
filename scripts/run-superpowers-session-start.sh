#!/usr/bin/env bash
# Wrapper for superpowers session-start hook.
# Resolves the real repo root from this script's location (following symlinks),
# so it works whether ~/.claude/scripts/ is a symlink or a direct path.
SCRIPT_DIR="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
HOOK="${REPO_ROOT}/.submodules/superpowers/hooks/session-start"
if [[ -x "${HOOK}" ]]; then
    exec "${HOOK}" "$@"
fi
echo "[superpowers] session-start hook missing (submodule uninitialized?)" >&2
