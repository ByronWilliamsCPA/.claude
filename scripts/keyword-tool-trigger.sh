#!/usr/bin/env bash
# =============================================================================
# Keyword Tool Trigger Hook
# =============================================================================
# Claude Code PreToolUse hook that detects keywords in user prompts and
# suggests loading relevant MCP tools.
#
# This hook is triggered before tool use and can:
# 1. Detect keywords in the current context
# 2. Suggest additional MCP tools to load
# 3. Log tool loading recommendations
#
# Integration with settings.json:
# {
#   "hooks": {
#     "PreToolUse": [
#       {
#         "matcher": "*",
#         "hooks": [
#           {
#             "type": "command",
#             "command": "$HOME/.claude/scripts/keyword-tool-trigger.sh"
#           }
#         ]
#       }
#     ]
#   }
# }
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="${HOME}/.claude/logs/keyword-triggers.log"
STATE_FILE="${HOME}/.claude/tmp_cleanup/.mcp-loaded-tools"

# Ensure directories exist
mkdir -p "$(dirname "$LOG_FILE")"
mkdir -p "$(dirname "$STATE_FILE")"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" >> "$LOG_FILE"
}

# Read tool call context from stdin (Claude Code passes context as JSON)
read_context() {
    local context=""
    if [ -t 0 ]; then
        # No stdin, likely manual invocation
        echo ""
    else
        context=$(cat)
    fi
    echo "$context"
}

# Check if a tool/server has already been loaded this session
is_already_loaded() {
    local server="$1"
    if [ -f "$STATE_FILE" ]; then
        grep -q "^${server}$" "$STATE_FILE" 2>/dev/null
        return $?
    fi
    return 1
}

# Mark a server as loaded
mark_loaded() {
    local server="$1"
    echo "$server" >> "$STATE_FILE"
}

# Keyword detection patterns
# Returns: server names that should be loaded
detect_keywords() {
    local text="$1"
    local text_lower
    text_lower=$(echo "$text" | tr '[:upper:]' '[:lower:]')

    local suggestions=""

    # Docker/Container patterns
    if echo "$text_lower" | grep -qE "\b(dockerfile|docker-compose|container|kubernetes|k8s|helm|pod|deployment)\b"; then
        if ! is_already_loaded "docker"; then
            suggestions="$suggestions docker"
            log "Suggesting docker tools based on keywords"
        fi
    fi

    # Browser/E2E testing patterns
    if echo "$text_lower" | grep -qE "\b(playwright|selenium|puppeteer|e2e|end.to.end|browser.test|ui.test|cypress)\b"; then
        if ! is_already_loaded "playwright"; then
            suggestions="$suggestions playwright"
            log "Suggesting playwright tools based on keywords"
        fi
    fi

    # Database patterns
    if echo "$text_lower" | grep -qE "\b(postgres|postgresql|mysql|database|sql|query|index|migration|schema|orm)\b"; then
        if ! is_already_loaded "postgres"; then
            suggestions="$suggestions postgres"
            log "Suggesting postgres tools based on keywords"
        fi
    fi

    # Error monitoring patterns
    if echo "$text_lower" | grep -qE "\b(sentry|error.monitor|exception|stack.trace|crash|bug.report|production.error)\b"; then
        if ! is_already_loaded "sentry"; then
            suggestions="$suggestions sentry"
            log "Suggesting sentry tools based on keywords"
        fi
    fi

    # Diagram patterns
    if echo "$text_lower" | grep -qE "\b(diagram|flowchart|sequence.diagram|class.diagram|uml|mermaid|plantuml|architecture.diagram|er.diagram)\b"; then
        if ! is_already_loaded "mermaid"; then
            suggestions="$suggestions mermaid"
            log "Suggesting mermaid tools based on keywords"
        fi
    fi

    echo "$suggestions" | xargs
}

# Generate recommendation message for Claude
generate_recommendation() {
    local servers="$1"

    if [ -z "$servers" ]; then
        return 0
    fi

    local message="Based on keywords detected, consider loading these MCP tools: $servers"
    echo "$message"

    # Mark as loaded to avoid repeated suggestions
    for server in $servers; do
        mark_loaded "$server"
    done
}

# Main hook logic
main() {
    local context
    context=$(read_context)

    if [ -z "$context" ]; then
        # No context provided, exit silently
        exit 0
    fi

    # Extract relevant text from context (tool name, parameters, etc.)
    # Claude Code passes JSON context, extract what we need
    local text_to_analyze=""

    # Try to extract from JSON if jq is available
    if command -v jq &> /dev/null; then
        text_to_analyze=$(echo "$context" | jq -r '.tool_input // .prompt // .content // empty' 2>/dev/null || echo "$context")
    else
        text_to_analyze="$context"
    fi

    # Detect keywords
    local suggestions
    suggestions=$(detect_keywords "$text_to_analyze")

    # Generate and output recommendation
    if [ -n "$suggestions" ]; then
        generate_recommendation "$suggestions"
    fi
}

# Handle command-line arguments for testing
case "${1:-}" in
    --test)
        # Test mode: pass text directly
        shift
        detect_keywords "$*"
        ;;
    --reset)
        # Reset loaded tools state
        rm -f "$STATE_FILE"
        echo "Reset MCP tool loading state"
        ;;
    --status)
        # Show currently loaded tools
        if [ -f "$STATE_FILE" ]; then
            echo "Loaded tools this session:"
            cat "$STATE_FILE"
        else
            echo "No tools loaded yet"
        fi
        ;;
    *)
        main
        ;;
esac
