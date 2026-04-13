#!/usr/bin/env bash
# =============================================================================
# MCP Tool Loader Hook
# =============================================================================
# This script is called by Claude Code hooks to dynamically load MCP tools
# based on agent invocation or keyword detection.
#
# Usage:
#   mcp-tool-loader.sh --agent <agent-name>
#   mcp-tool-loader.sh --keywords "<user-prompt>"
#   mcp-tool-loader.sh --list-tier1
#
# Based on Anthropic's Advanced Tool Use Guide:
# https://www.anthropic.com/engineering/advanced-tool-use
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE="${SCRIPT_DIR}/../mcp/mcp_config.yaml"
LOG_FILE="${HOME}/.claude/logs/mcp-tool-loader.log"

# Ensure log directory exists
mkdir -p "$(dirname "$LOG_FILE")"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" >> "$LOG_FILE"
    return 0
}

# Parse YAML configuration (simplified parser)
parse_agent_tools() {
    local agent_name="$1"

    # Use yq if available, otherwise fallback to grep/sed
    if command -v yq &> /dev/null; then
        yq eval ".tier_2_agent_bundles.${agent_name}.tools" "$CONFIG_FILE" 2>/dev/null
    else
        # Simplified grep-based extraction
        grep -A 20 "^  ${agent_name}:" "$CONFIG_FILE" | grep -E "^\s+\w+:" | head -10
    fi
    return 0
}

# Get Tier 1 tools (always loaded)
get_tier1_tools() {
    if command -v yq &> /dev/null; then
        yq eval '.tier_1.tools' "$CONFIG_FILE" 2>/dev/null
    else
        grep -A 15 "^tier_1:" "$CONFIG_FILE" | grep -E "^\s+-\s+" | sed 's/^\s*-\s*//'
    fi
    return 0
}

# Check for keyword triggers in user prompt
check_keyword_triggers() {
    local prompt="$1"
    local prompt_lower
    prompt_lower=$(echo "$prompt" | tr '[:upper:]' '[:lower:]')

    local triggered_servers=""

    # Docker keywords
    if echo "$prompt_lower" | grep -qE "(dockerfile|container|image|deploy|docker|kubernetes|k8s)"; then
        triggered_servers="$triggered_servers docker"
        log "Keyword trigger: docker"
    fi

    # Playwright keywords
    if echo "$prompt_lower" | grep -qE "(e2e|end-to-end|browser test|ui test|playwright|selenium|automation)"; then
        triggered_servers="$triggered_servers playwright"
        log "Keyword trigger: playwright"
    fi

    # Postgres keywords
    if echo "$prompt_lower" | grep -qE "(database|sql|query performance|slow query|index|postgres|postgresql|migration|schema)"; then
        triggered_servers="$triggered_servers postgres"
        log "Keyword trigger: postgres"
    fi

    # Sentry keywords
    if echo "$prompt_lower" | grep -qE "(error monitoring|sentry|exception|crash|stack trace|production error)"; then
        triggered_servers="$triggered_servers sentry"
        log "Keyword trigger: sentry"
    fi

    # Diagram keywords
    if echo "$prompt_lower" | grep -qE "(diagram|flowchart|architecture diagram|sequence diagram|uml|mermaid|visualize|er diagram|class diagram)"; then
        triggered_servers="$triggered_servers mermaid uml-mcp-server"
        log "Keyword trigger: diagrams"
    fi

    echo "$triggered_servers"
    return 0
}

# Output tools in JSON format for Claude Code
output_tools_json() {
    local tools=("$@")
    local json="["
    local first=true

    for tool in "${tools[@]}"; do
        if [[ "$first" = true ]]; then
            first=false
        else
            json="$json,"
        fi
        json="$json\"$tool\""
    done

    json="$json]"
    echo "$json"
    return 0
}

# Main command processing
main() {
    case "${1:-}" in
        --agent)
            local agent_name="${2:-}"
            if [[ -z "$agent_name" ]]; then
                echo "Error: Agent name required" >&2
                exit 1
            fi
            log "Loading tools for agent: $agent_name"
            parse_agent_tools "$agent_name"
            ;;

        --keywords)
            local prompt="${2:-}"
            if [[ -z "$prompt" ]]; then
                echo "Error: Prompt required" >&2
                exit 1
            fi
            log "Checking keywords in prompt"
            check_keyword_triggers "$prompt"
            ;;

        --list-tier1)
            log "Listing Tier 1 tools"
            get_tier1_tools
            ;;

        --help|-h)
            cat << EOF
MCP Tool Loader - Dynamic tool loading for Claude Code

Usage:
  $0 --agent <agent-name>     Load tools for specific agent
  $0 --keywords "<prompt>"    Check keyword triggers in prompt
  $0 --list-tier1             List always-loaded Tier 1 tools
  $0 --help                   Show this help message

Examples:
  $0 --agent security-auditor
  $0 --keywords "fix the database query performance issue"
  $0 --list-tier1

Configuration: $CONFIG_FILE
Log file: $LOG_FILE
EOF
            ;;

        *)
            echo "Unknown command: ${1:-}" >&2
            echo "Use --help for usage information" >&2
            exit 1
            ;;
    esac
    return 0
}

main "$@"
