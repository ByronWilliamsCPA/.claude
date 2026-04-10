#!/usr/bin/env bash
# =============================================================================
# Planning Bridge Gate — PreToolUse Hook
# =============================================================================
# Intercepts Skill tool calls targeting "writing-plans". When brainstorming
# has produced a spec but bridge mode has not yet run (no ADR, no Roadmap),
# blocks the call with exit 2 and directs Claude to run project-planning
# in bridge mode first.
#
# Exit codes:
#   0 — allow tool call to proceed
#   2 — block tool call; stdout message fed back to Claude
# =============================================================================

set -euo pipefail

LOG_FILE="${HOME}/.claude/logs/planning-bridge-gate.log"
mkdir -p "$(dirname "$LOG_FILE")"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" >> "$LOG_FILE"
}

# Read JSON context from stdin
CONTEXT=$(cat)

if [[ -z "$CONTEXT" ]]; then
    exit 0
fi

# Extract skill name from tool input
SKILL=$(echo "$CONTEXT" | jq -r '.tool_input.skill // empty' 2>/dev/null)

# Only act on writing-plans invocations
if [[ "$SKILL" != "writing-plans" ]]; then
    exit 0
fi

# Resolve project working directory
# Claude Code sets PWD to the project root when running hooks
PROJECT_DIR="${PWD}"

# Condition 1: a brainstorming spec exists
SPEC_FILE=$(find "${PROJECT_DIR}/docs/superpowers/specs" -name "*.md" 2>/dev/null | sort | tail -1 || true)

if [[ -z "$SPEC_FILE" ]]; then
    # No spec — brainstorming hasn't run; let writing-plans proceed normally
    log "No spec found, passing through writing-plans"
    exit 0
fi

# Condition 2: no ADR has been generated yet
ADR_FILE=$(find "${PROJECT_DIR}/docs/planning/adr" -name "*.md" 2>/dev/null | head -1 || true)

# Condition 3: roadmap does not exist yet
ROADMAP="${PROJECT_DIR}/docs/planning/roadmap.md"

if [[ -z "$ADR_FILE" ]] && [[ ! -f "$ROADMAP" ]]; then
    log "Bridge mode required: spec=${SPEC_FILE}, no ADR, no roadmap"
    echo "Bridge mode required: a brainstorming spec exists at '${SPEC_FILE}' but no ADR or Roadmap have been generated yet. Invoke the project-planning skill in bridge mode first (run: /project-planning bridge), then retry writing-plans."
    exit 2
fi

# ADR or Roadmap already exists — bridge has run, allow writing-plans
log "Bridge already complete, passing through writing-plans"
exit 0
