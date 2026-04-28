#!/bin/bash

# TDD Enforcement Hook Script
# Based on TDD Guard principles, adapted for our hybrid MCP architecture
# Enforces Test-Driven Development for agent-generated code

set -euo pipefail

# Configuration
TDD_LOG="/home/byron/.claude/logs/tdd-enforcement.log"
HOOK_DEBUG_LOG="/home/byron/.claude/logs/hook-debug.log"
PROJECT_ROOT="${CLAUDE_PROJECT_DIR:-$(pwd)}"

# Create log directories
mkdir -p "$(dirname "$TDD_LOG")"

# Function to log TDD enforcement actions
log_tdd() {
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "$timestamp,$1,$2,$3" >> "$TDD_LOG"
}

# Function to debug log
debug_log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') TDD-HOOK: $1" >> "$HOOK_DEBUG_LOG" 2>/dev/null || true
}

# Read hook input from stdin
HOOK_INPUT=$(cat)
debug_log "Hook triggered with input: $HOOK_INPUT"

# Parse tool information
if command -v jq >/dev/null 2>&1; then
    TOOL_NAME=$(echo "$HOOK_INPUT" | jq -r '.tool // "unknown"' 2>/dev/null || echo "unknown")
    TOOL_ARGS=$(echo "$HOOK_INPUT" | jq -r '.args // {}' 2>/dev/null || echo "{}")
else
    # Fallback parsing
    TOOL_NAME=$(echo "$HOOK_INPUT" | grep -o '"tool":"[^"]*"' | cut -d'"' -f4 2>/dev/null || echo "unknown")
    TOOL_ARGS="{}"
fi

debug_log "Parsed tool: $TOOL_NAME"

# Only enforce TDD for code-writing tools used by specific agents
case "$TOOL_NAME" in
    "Write"|"Edit"|"MultiEdit")
        debug_log "Code modification tool detected: $TOOL_NAME"

        # Extract file path from tool arguments
        FILE_PATH=""
        if [[ "$TOOL_ARGS" =~ \"file_path\":\"([^\"]+)\" ]]; then
            FILE_PATH="${BASH_REMATCH[1]}"
        elif [[ "$TOOL_ARGS" =~ \"path\":\"([^\"]+)\" ]]; then
            FILE_PATH="${BASH_REMATCH[1]}"
        fi

        debug_log "File path: $FILE_PATH"

        # Only enforce TDD for implementation files (not tests, docs, configs)
        if [[ -n "$FILE_PATH" ]]; then
            case "$FILE_PATH" in
                *test*.py|*_test.py|*/tests/*|*/test_*|*spec*.js|*test*.js|*.test.ts|*.spec.ts)
                    log_tdd "ALLOW" "TEST_FILE" "$FILE_PATH"
                    debug_log "Test file - allowing: $FILE_PATH"
                    exit 0
                    ;;
                *.md|*.txt|*.json|*.yaml|*.yml|*.toml|*.cfg|*.ini)
                    log_tdd "ALLOW" "CONFIG_FILE" "$FILE_PATH"
                    debug_log "Config/doc file - allowing: $FILE_PATH"
                    exit 0
                    ;;
                *.py|*.js|*.ts|*.go|*.rs|*.php)
                    debug_log "Implementation file detected: $FILE_PATH"

                    # Check if corresponding test files exist and have content
                    TEST_EXISTS=false
                    TEST_FILES=()

                    # Generate possible test file paths
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

                    # Check if any test files exist and have content
                    for test_file in "${TEST_FILES[@]}"; do
                        if [[ -f "$test_file" && -s "$test_file" ]]; then
                            TEST_EXISTS=true
                            debug_log "Found test file: $test_file"
                            break
                        fi
                    done

                    if [[ "$TEST_EXISTS" == true ]]; then
                        log_tdd "ALLOW" "HAS_TESTS" "$FILE_PATH"
                        debug_log "Implementation allowed - tests exist: $FILE_PATH"
                        exit 0
                    else
                        log_tdd "BLOCK" "NO_TESTS" "$FILE_PATH"
                        debug_log "BLOCKING - no tests found for: $FILE_PATH"

                        # Return error to block the tool execution
                        echo "TDD Enforcement: Cannot modify implementation file without corresponding tests."
                        echo "Please create tests first for: $FILE_PATH"
                        echo "Expected test files: ${TEST_FILES[0]} (or similar)"
                        exit 1
                    fi
                    ;;
                *)
                    log_tdd "ALLOW" "OTHER_FILE" "$FILE_PATH"
                    debug_log "Non-implementation file - allowing: $FILE_PATH"
                    exit 0
                    ;;
            esac
        fi
        ;;
    *)
        debug_log "Non-code-writing tool - allowing: $TOOL_NAME"
        exit 0
        ;;
esac

# Default allow (should not reach here)
log_tdd "ALLOW" "DEFAULT" "unknown"
exit 0
