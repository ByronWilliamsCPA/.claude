#!/usr/bin/env bash
# Applies three targeted patches to the upstream one-skill-to-rule-them-all SKILL.md
# and writes the result to ~/.claude/skills/task-observer/SKILL.md.
#
# Patch 1: Replace [your shared folder] with the local repo path (path substitution
#          for all log, archive, and staging paths referenced in the skill).
# Patch 2: Replace <available_skills> with the manifest file path (replaces
#          Cowork's system prompt injection with our SessionStart-generated file).
# Patch 3: Strip the "Without Persistent Storage" section (handoff doc mode).
#          Claude Code always has filesystem access; that section is dead weight here.
#
# The CC BY 4.0 attribution block is not touched by any patch.
# Run again after: git submodule update --remote .submodules/one-skill-to-rule-them-all
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

UPSTREAM="${REPO_ROOT}/.submodules/one-skill-to-rule-them-all/SKILL.md"
OUTPUT="${HOME}/.claude/skills/task-observer/SKILL.md"
# Security (audit M-03): derive REPO_PATH from this script's location so the
# value matches the actual install on whatever account runs it, instead of
# hardcoding /home/byron/. The string is still embedded in the installed
# SKILL.md output verbatim (so the consumer sees a concrete path) but is now
# portable across user accounts.
REPO_PATH="${REPO_ROOT}"
MANIFEST_PATH="${REPO_PATH}/skill-observations/available-skills.md"
STRIP_SECTION="### Without Persistent Storage"

if [[ ! -f "${UPSTREAM}" ]]; then
    echo "ERROR: upstream SKILL.md not found at ${UPSTREAM}" >&2
    echo "Run: git submodule update --init .submodules/one-skill-to-rule-them-all" >&2
    exit 1
fi

mkdir -p "$(dirname "${OUTPUT}")"

# Apply patches in a single pipeline:
# Patch 1 + Patch 2: sed replacements
# Patch 3: awk strips the "Without Persistent Storage" section.
#   Termination matches ## or ### headings (section is ### level;
#   #### subsections within it are also stripped).
TMP="$(mktemp)"
trap 'rm -f "${TMP}"' EXIT
sed \
    -e "s|\[your shared folder\]|${REPO_PATH}|g" \
    -e "s|<available_skills>|${MANIFEST_PATH}|g" \
    "${UPSTREAM}" | \
awk -v section="${STRIP_SECTION}" '
    { sub(/[[:space:]]+$/, "") }
    $0 == section           { skip=1; next }
    /^## |^### / && skip    { skip=0 }
    !skip                   { print }
' > "${TMP}"
[[ -s "${TMP}" ]] || { echo "ERROR: patch produced empty output" >&2; exit 1; }
mv "${TMP}" "${OUTPUT}"

echo "Installed: ${OUTPUT}"
