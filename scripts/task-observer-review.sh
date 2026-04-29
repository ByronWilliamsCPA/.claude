#!/usr/bin/env bash
# Task Observer scheduled review: invoke Claude non-interactively with the review prompt.
#
# Install in user crontab (crontab -e):
#   0 8 * * 1,3,5 /home/byron/dev/.claude/scripts/task-observer-review.sh
#
# Cron environment note: PATH is stripped in cron sessions. The CLAUDE_BIN path
# is hardcoded below to avoid relying on PATH. Update it if claude is reinstalled
# to a different location (check with: which claude).

set -euo pipefail

# Restore the minimal PATH cron needs to find standard tools.
# Must appear before any external command (including date, grep, printf).
export PATH="/home/byron/.local/bin:/usr/local/bin:/usr/bin:/bin"
export HOME="/home/byron"

# #ASSUME: hardcoded deploy path; #VERIFY: confirm REPO_ROOT matches actual install location
REPO_ROOT="/home/byron/dev/.claude"
OBS_LOG="${REPO_ROOT}/skill-observations/log.md"
RUN_LOG="${REPO_ROOT}/skill-observations/review-run.log"
# #ASSUME: claude installed at this path; #VERIFY: run `which claude` after upgrades
CLAUDE_BIN="/home/byron/.local/bin/claude"

# Ensure the runtime directory exists (gitignored, absent on fresh install).
mkdir -p "$(dirname "${RUN_LOG}")"

# Preflight: confirm claude binary is executable before any work.
if [[ ! -x "${CLAUDE_BIN}" ]]; then
    printf '%s: claude binary not found or not executable at %s\n' "$(date -Is)" "${CLAUDE_BIN}" >> "${RUN_LOG}"
    exit 1
fi

# Bail early if there are no OPEN observations: avoids an unnecessary claude invocation.
if [[ ! -f "${OBS_LOG}" ]] || ! grep -q "Status: OPEN" "${OBS_LOG}"; then
    printf '%s: no OPEN observations, skipping review\n' "$(date -Is)" >> "${RUN_LOG}"
    exit 0
fi

TODAY="$(date +%Y-%m-%d)"

REVIEW_PROMPT="You are the Task Observer scheduled review agent for ${REPO_ROOT}.

Working directory: ${REPO_ROOT}

Your job this run:

1. Read skill-observations/log.md. Extract all observations with Status: OPEN.
2. Read skill-observations/cross-cutting-principles.md.
3. For each OPEN observation that is NOT escalated (see escalation policy below),
   find the affected skill at ~/.claude/skills/<skill-name>/SKILL.md and prepare
   an updated version that integrates the observation.
4. Write each updated skill to skill-updates/${TODAY}/<skill-name>/SKILL.md
5. In skill-observations/log.md, change Status: OPEN to Status: ACTIONED for each
   applied observation, adding the note: Applied ${TODAY}.
6. Write ${TODAY} to skill-observations/last-review-date.txt.
7. Delete all date directories in skill-updates/ EXCEPT the two most recent.
8. Write a brief summary: what was applied, what was escalated and why.

ESCALATION POLICY -- flag in the log but do NOT apply autonomously:
- New skill candidates (naming and scope require user input)
- Observations that remove or restructure existing skill content
- Observations with uncertainty phrases: not sure if, might be, possibly, unclear whether
- Two or more observations on the same skill pointing in opposite directions

Model: claude-sonnet-4-6
Repo root: ${REPO_ROOT}"

cd "${REPO_ROOT}"
printf '%s: starting review run\n' "$(date -Is)" >> "${RUN_LOG}"
# --dangerously-skip-permissions is required for unattended execution.
# WARNING: this flag removes ALL Claude Code permission guardrails; the blast radius
# is not bounded to REPO_ROOT. Review the prompt carefully before modifying this script.
CLAUDE_EXIT=0
"${CLAUDE_BIN}" -p "${REVIEW_PROMPT}" --dangerously-skip-permissions >> "${RUN_LOG}" 2>&1 || CLAUDE_EXIT=$?
printf '%s: review run complete (exit %d)\n' "$(date -Is)" "${CLAUDE_EXIT}" >> "${RUN_LOG}"
exit "${CLAUDE_EXIT}"
