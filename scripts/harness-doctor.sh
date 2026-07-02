#!/usr/bin/env bash
# harness-doctor.sh -- SessionStart hook
# GUARDS AGAINST: the model trusting gates and tools that are not live
# (review R-12). Prints a one-line inventory of live vs degraded protections
# to stderr so the session can reason about which checks exist.
# CLASS: advisory (always exit 0). FAIL MODE: fail-open; this is telemetry.
# DEPENDENCIES: none hard; each probe degrades independently.
# TESTED BY: tests/scripts/test_harness_doctor.bats
# REGISTERED IN: hooks.json only
set -uo pipefail

LIVE=()
DEGRADED=()

for bin in jq python3 pre-commit; do
    if command -v "$bin" > /dev/null 2>&1; then
        LIVE+=("$bin")
    else
        DEGRADED+=("$bin missing (hooks that need it fail open)")
    fi
done

for s in bash-pre-hook.sh sensitive-file-guard.sh; do
    if [[ -f "${HOME}/.claude/scripts/${s}" ]]; then
        LIVE+=("${s%.sh}")
    else
        DEGRADED+=("${s} not installed")
    fi
done

if [[ -f "${HOME}/.claude/plugin-hooks/hookify/hooks/pretooluse.py" ]]; then
    LIVE+=("hookify")
else
    DEGRADED+=("hookify (plugin hooks not installed)")
fi

SELF_DIR=$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")" && pwd)
REPO_ROOT=$(cd "${SELF_DIR}/.." && pwd)
if git -C "$REPO_ROOT" submodule status 2> /dev/null | grep -q '^-'; then
    DEGRADED+=("submodules uninitialized (vendored agents/skills unresolvable)")
fi

BROKEN=$(find "${HOME}/.claude/agents" "${HOME}/.claude/skills" \
    -maxdepth 2 -xtype l 2> /dev/null | wc -l | tr -d ' ')
if [[ "${BROKEN}" != "0" ]]; then
    DEGRADED+=("${BROKEN} broken agent/skill symlinks")
fi

echo "[harness-doctor] live: ${LIVE[*]:-none}" >&2
if [[ ${#DEGRADED[@]} -gt 0 ]]; then
    joined=$(printf '%s; ' "${DEGRADED[@]}")
    echo "[harness-doctor] degraded: ${joined%; }" >&2
fi
exit 0
