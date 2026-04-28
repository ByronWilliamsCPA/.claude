#!/bin/bash

# TDD Enforcement Hook Script
# Enforces Test-Driven Development for agent-generated code.
# Registered as a PreToolUse hook in Claude Code settings.
# Exit 0 = allow; exit 2 = block (stdout is shown to Claude as the block reason).

# Do NOT use set -e here: PreToolUse hooks with a non-zero exit block the matched
# tool calls. Any unhandled error under set -e would silently block Write/Edit/MultiEdit.
set -uo pipefail

# Configuration
TDD_LOG="$HOME/.claude/logs/tdd-enforcement.log"
HOOK_DEBUG_LOG="$HOME/.claude/logs/hook-debug.log"
PROJECT_ROOT="${CLAUDE_PROJECT_DIR:-$(pwd)}"

# Log directory creation must not block tool calls on failure
mkdir -p "$(dirname "$TDD_LOG")" || true

log_tdd() {
    local timestamp
    timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "$timestamp,$1,$2,$3" >> "$TDD_LOG" || true
}

debug_log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') TDD-HOOK: $1" >> "$HOOK_DEBUG_LOG" 2>/dev/null || true
}

# Read hook input from stdin
HOOK_INPUT=$(cat)
debug_log "Hook triggered with input: $HOOK_INPUT"

# Parse tool information.
# Claude Code hook payload schema: {"tool_name": "...", "tool_input": {...}}
if command -v jq >/dev/null 2>&1; then
    TOOL_NAME=$(echo "$HOOK_INPUT" | jq -r '.tool_name // "unknown"' 2>/dev/null || echo "unknown")
    FILE_PATH=$(echo "$HOOK_INPUT" | jq -r '.tool_input.file_path // .tool_input.path // ""' 2>/dev/null || echo "")
else
    TOOL_NAME=$(echo "$HOOK_INPUT" | grep -o '"tool_name":"[^"]*"' | cut -d'"' -f4 2>/dev/null || echo "unknown")
    FILE_PATH=$(echo "$HOOK_INPUT" | grep -o '"file_path":"[^"]*"' | cut -d'"' -f4 2>/dev/null || echo "")
fi

debug_log "Parsed tool: $TOOL_NAME, file: $FILE_PATH"

case "$TOOL_NAME" in
    "Write"|"Edit"|"MultiEdit")
        debug_log "Code modification tool detected: $TOOL_NAME"

        if [[ -n "$FILE_PATH" ]]; then
            case "$FILE_PATH" in
                *test*.py|*/tests/*|*/test_*|*spec*.js|*test*.js|*.test.ts|*.spec.ts)
                    log_tdd "ALLOW" "TEST_FILE" "$FILE_PATH"
                    exit 0
                    ;;
                *.md|*.txt|*.json|*.yaml|*.yml|*.toml|*.cfg|*.ini)
                    log_tdd "ALLOW" "CONFIG_FILE" "$FILE_PATH"
                    exit 0
                    ;;
                *.py|*.js|*.ts|*.go|*.rs|*.php)
                    debug_log "Implementation file detected: $FILE_PATH"

                    TEST_EXISTS=false
                    TEST_FILES=()

                    BASE_NAME=$(basename "$FILE_PATH" | cut -d'.' -f1)
                    DIR_NAME=$(dirname "$FILE_PATH")
                    EXT="${FILE_PATH##*.}"

                    case "$EXT" in
                        "py")
                            TEST_FILES=(
                                "${DIR_NAME}/test_${BASE_NAME}.py"
                                "${DIR_NAME}/tests/test_${BASE_NAME}.py"
                                "${DIR_NAME}/../tests/test_${BASE_NAME}.py"
                                "${PROJECT_ROOT}/tests/test_${BASE_NAME}.py"
                            )
                            ;;
                        "js"|"ts")
                            TEST_FILES=(
                                "${DIR_NAME}/${BASE_NAME}.test.${EXT}"
                                "${DIR_NAME}/${BASE_NAME}.spec.${EXT}"
                                "${DIR_NAME}/tests/${BASE_NAME}.test.${EXT}"
                                "${DIR_NAME}/../tests/${BASE_NAME}.test.${EXT}"
                            )
                            ;;
                    esac

                    # ${TEST_FILES[@]+"${TEST_FILES[@]}"} safely iterates an empty array under set -u
                    for test_file in "${TEST_FILES[@]+"${TEST_FILES[@]}"}"; do
                        if [[ -f "$test_file" && -s "$test_file" ]]; then
                            TEST_EXISTS=true
                            debug_log "Found test file: $test_file"
                            break
                        fi
                    done

                    if [[ "$TEST_EXISTS" == true ]]; then
                        log_tdd "ALLOW" "HAS_TESTS" "$FILE_PATH"
                        exit 0
                    else
                        log_tdd "BLOCK" "NO_TESTS" "$FILE_PATH"
                        debug_log "BLOCKING - no tests found for: $FILE_PATH"

                        # Exit 2 is the PreToolUse block signal; stdout is surfaced to Claude
                        echo "TDD Enforcement: Cannot modify implementation file without corresponding tests."
                        echo "Please create tests first for: $FILE_PATH"
                        echo "Expected test files: ${TEST_FILES[0]:-none} (or similar)"
                        exit 2
                    fi
                    ;;
                *)
                    log_tdd "ALLOW" "OTHER_FILE" "$FILE_PATH"
                    exit 0
                    ;;
            esac
        fi
        ;;
    *)
        exit 0
        ;;
esac

log_tdd "ALLOW" "DEFAULT" "unknown"
exit 0
