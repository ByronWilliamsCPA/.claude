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
# Linked worktrees do not get submodule checkouts, so `submodule status` there
# always reports uninitialized. Reporting that as degraded would be a standing
# false alarm in every worktree, and advisory output that cries wolf gets
# ignored, which defeats the point of this probe. Only check in the main
# worktree, where an uninitialized submodule is a real finding.
GIT_DIR_PATH=$(git -C "$REPO_ROOT" rev-parse --git-dir 2> /dev/null)
GIT_COMMON_DIR=$(git -C "$REPO_ROOT" rev-parse --git-common-dir 2> /dev/null)
if [[ -n "$GIT_DIR_PATH" && "$GIT_DIR_PATH" == "$GIT_COMMON_DIR" ]]; then
    if git -C "$REPO_ROOT" submodule status 2> /dev/null | grep -q '^-'; then
        DEGRADED+=("submodules uninitialized (vendored agents/skills unresolvable)")
    fi
fi

BROKEN=$(find "${HOME}/.claude/agents" "${HOME}/.claude/skills" \
    -maxdepth 2 -xtype l 2> /dev/null | wc -l | tr -d ' ')
if [[ "${BROKEN}" != "0" ]]; then
    DEGRADED+=("${BROKEN} broken agent/skill symlinks")
fi

# hooks.json is canonical; setup.sh merge_hooks() regenerates the live
# settings.json block from it. Nothing runs setup.sh automatically, so a hook
# can be committed, reviewed and merged yet never become live. That is not
# hypothetical: commit 88356c6 added task-observer-flush-check.py,
# task-observer-reminder.sh and this script to hooks.json on 2026-08-04, and
# all three sat inert in the live settings for 32 days. This script's own
# purpose is guarding against trusting protections that are not live, so it
# must detect the case where it is itself the thing that is not live.
# Reports drift only; it never repairs. A detector that silently self-healed
# would hide the fact that the propagation step was skipped, recreating the
# failure mode above. The fix is to run setup.sh.
# Event names sit at the top level in hooks.json but under .hooks in
# settings.json, hence the `(.hooks // .)` normalisation on both sides. The
# comparison is a generic set difference, so hooks added later need no change
# here.
HOOKS_JSON="${REPO_ROOT}/hooks.json"
SETTINGS_JSON="${HOME}/.claude/settings.json"
if command -v jq > /dev/null 2>&1 &&
    [[ -f "$HOOKS_JSON" && -f "$SETTINGS_JSON" ]]; then
    jq_cmds='[(.hooks // .) | to_entries[] | .value[]? | .hooks[]? | .command]
             | unique[]'
    DECLARED=$(jq -r "$jq_cmds" "$HOOKS_JSON" 2> /dev/null | sort)
    INSTALLED=$(jq -r "$jq_cmds" "$SETTINGS_JSON" 2> /dev/null | sort)
    # Only the declared-but-not-live direction is a finding. Live-only entries
    # are foreign hooks from plugins and other installers, which merge_hooks()
    # deliberately preserves; flagging those would be a standing false alarm.
    DRIFT=$(comm -23 <(printf '%s\n' "$DECLARED") <(printf '%s\n' "$INSTALLED"))
    DRIFT_N=$(printf '%s' "$DRIFT" | grep -c . || true)
    if [[ "$DRIFT_N" != "0" ]]; then
        DRIFT_NAMES=$(printf '%s\n' "$DRIFT" | sed 's#.*/##' | paste -sd, -)
        DEGRADED+=("${DRIFT_N} hook(s) declared in hooks.json but not live in settings.json (${DRIFT_NAMES}); run setup.sh")
    fi
fi

echo "[harness-doctor] live: ${LIVE[*]:-none}" >&2
if [[ ${#DEGRADED[@]} -gt 0 ]]; then
    joined=$(printf '%s; ' "${DEGRADED[@]}")
    echo "[harness-doctor] degraded: ${joined%; }" >&2
fi
exit 0
