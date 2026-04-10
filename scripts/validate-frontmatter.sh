#!/usr/bin/env bash
# =============================================================================
# Frontmatter Validator — PostToolUse Hook
# =============================================================================
# Fires after Edit or Write tool calls. Checks SKILL.md and agents/*.md files
# for required YAML frontmatter fields: name and description.
#
# Prints WARN lines to stdout (Claude reads them). Silent on valid files.
# Exit codes: always 0 — PostToolUse hooks must never fail
# =============================================================================

set -euo pipefail

# ---- jq guard ----------------------------------------------------------------
if ! command -v jq &>/dev/null; then
    exit 0
fi

# ---- Read hook context from stdin --------------------------------------------
CONTEXT=$(cat)
[[ -z "$CONTEXT" ]] && exit 0

FILE_PATH=$(jq -r '.tool_input.file_path // empty' 2>/dev/null <<< "$CONTEXT")
[[ -z "$FILE_PATH" ]] && exit 0

# ---- Guards: only check SKILL.md and agents/*.md files ----------------------
# Match */SKILL.md or any path containing "agents" ending in .md
is_target=0
if [[ "$FILE_PATH" == */SKILL.md ]]; then
    is_target=1
elif [[ "$FILE_PATH" == *agents*.md ]]; then
    is_target=1
fi

[[ $is_target -eq 0 ]] && exit 0

# File must exist
[[ ! -f "$FILE_PATH" ]] && exit 0

# ---- Extract frontmatter (content between first two --- delimiters) ----------
# Read the file and check for frontmatter block
CONTENT=$(<"$FILE_PATH")

# Check if file starts with ---
if ! echo "$CONTENT" | head -1 | grep -q '^---'; then
    echo "WARN: no frontmatter found in $FILE_PATH"
    exit 0
fi

# Extract lines between first and second --- delimiter
FRONTMATTER=$(awk '
    /^---/ { count++; if (count == 1) { next } if (count == 2) { exit } }
    count == 1 { print }
' "$FILE_PATH")

# If we only found one --- (no closing ---), no valid frontmatter block
DASH_COUNT=$(grep -c '^---' "$FILE_PATH" 2>/dev/null || true)
if [[ "$DASH_COUNT" -lt 2 ]]; then
    echo "WARN: no frontmatter found in $FILE_PATH"
    exit 0
fi

# ---- Check required fields --------------------------------------------------
if ! echo "$FRONTMATTER" | grep -q '^name:'; then
    echo "WARN: missing 'name:' in frontmatter of $FILE_PATH"
fi

if ! echo "$FRONTMATTER" | grep -q '^description:'; then
    echo "WARN: missing 'description:' in frontmatter of $FILE_PATH"
fi

exit 0
