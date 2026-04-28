#!/usr/bin/env bash
# =============================================================================
# Frontmatter Validator: PostToolUse Hook
# =============================================================================
# Fires after Edit or Write tool calls. Checks SKILL.md and agents/*.md files
# for required YAML frontmatter fields: name and description.
# Also validates status: field; rejects 'template' and unknown values.
#
# Prints WARN/ERROR lines to stdout (Claude reads them). Silent on valid files.
# Exit codes: always 0 (PostToolUse hooks must not block writes)
# =============================================================================

set -uo pipefail

LOG_FILE="${HOME}/.claude/logs/validate-frontmatter.log"

log() {
    mkdir -p "$(dirname "$LOG_FILE")"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" >> "$LOG_FILE"
}

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
# Match */SKILL.md or a literal agents/ directory ending in .md
# Exclude CLAUDE.md meta-docs that live inside agents/ or skills/ as folder
# convention guides; they are not agent/skill definitions and have no frontmatter.
is_target=0
if [[ "$FILE_PATH" == */SKILL.md ]]; then
    is_target=1
elif [[ "$FILE_PATH" == */agents/*.md ]]; then
    is_target=1
elif [[ "$FILE_PATH" == */skills/*.md ]]; then
    is_target=1
fi

# Skip folder-level convention guides named CLAUDE.md
if [[ $is_target -eq 1 ]] && [[ "$(basename "$FILE_PATH")" == "CLAUDE.md" ]]; then
    exit 0
fi

[[ $is_target -eq 0 ]] && exit 0

# File must exist
[[ ! -f "$FILE_PATH" ]] && exit 0

# ---- Extract frontmatter (content between first two --- delimiters) ----------
# Check file starts with ---
FIRST_LINE=$(head -1 "$FILE_PATH" | tr -d '\r')
if [[ "$FIRST_LINE" != "---" ]]; then
    log "WARN no frontmatter found in ${FILE_PATH}"
    echo "WARN: no frontmatter found in $FILE_PATH"
    exit 0
fi

# Extract content between first and second --- delimiters
FRONTMATTER=$(awk 'NR==1{next} /^---/{exit} {print}' "$FILE_PATH" | tr -d '\r')

if [[ -z "$FRONTMATTER" ]]; then
    log "WARN no frontmatter found in ${FILE_PATH}"
    echo "WARN: no frontmatter found in $FILE_PATH"
    exit 0
fi

# ---- Check required fields --------------------------------------------------
if ! echo "$FRONTMATTER" | grep -q '^name:'; then
    log "WARN missing name: ${FILE_PATH}"
    echo "WARN: missing 'name:' in frontmatter of $FILE_PATH; add: name: <slug>"
fi

if ! echo "$FRONTMATTER" | grep -q '^description:'; then
    log "WARN missing description: ${FILE_PATH}"
    echo "WARN: missing 'description:' in frontmatter of $FILE_PATH; add: description: <one-line summary>"
fi

# ---- Validate status: field if present --------------------------------------
# Valid values: draft, in-review, published, active, deprecated
# 'template' is reserved for actual template files; using it on a real
# skill or agent definition causes the validate-front-matter pre-commit hook to fail.
if echo "$FRONTMATTER" | grep -q '^status:'; then
    STATUS_VALUE=$(echo "$FRONTMATTER" | grep '^status:' | sed 's/^status:[[:space:]]*//' | tr -d '\r')
    case "$STATUS_VALUE" in
        draft|in-review|published|active|deprecated)
            ;;
        template)
            log "ERROR invalid status 'template' in ${FILE_PATH}"
            echo "ERROR: status: template is reserved for template files only. Use draft, in-review, published, active, or deprecated in $FILE_PATH; fix before committing."
            ;;
        *)
            log "WARN unknown status '${STATUS_VALUE}' in ${FILE_PATH}"
            echo "WARN: unknown status '${STATUS_VALUE}' in $FILE_PATH; valid values: draft, in-review, published, active, deprecated"
            ;;
    esac
fi

exit 0
