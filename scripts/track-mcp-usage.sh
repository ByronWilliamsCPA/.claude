#!/usr/bin/env bash
# =============================================================================
# MCP Usage Tracking Hook
# =============================================================================
# Claude Code PostToolUse hook that tracks MCP tool usage for optimization.
#
# Collects metrics on:
# - Which MCP tools are used most frequently
# - Tool invocation patterns
# - Potential optimization opportunities
#
# Integration with settings.json:
# {
#   "hooks": {
#     "PostToolUse": [
#       {
#         "matcher": "mcp__*",
#         "hooks": [
#           {
#             "type": "command",
#             "command": "$HOME/.claude/scripts/track-mcp-usage.sh"
#           }
#         ]
#       }
#     ]
#   }
# }
# =============================================================================

set -euo pipefail

LOG_DIR="${HOME}/.claude/logs"
USAGE_LOG="${LOG_DIR}/mcp-usage.log"
METRICS_FILE="${LOG_DIR}/mcp-metrics.json"

# Ensure log directory exists
mkdir -p "$LOG_DIR"

# Initialize metrics file if it doesn't exist
if [[ ! -f "$METRICS_FILE" ]]; then
    echo '{"tool_counts":{},"session_start":"'"$(date -Iseconds)"'","total_calls":0}' > "$METRICS_FILE"
fi

log_usage() {
    local tool_name="$1"
    local timestamp
    timestamp=$(date -Iseconds)

    # Log to usage file
    echo "${timestamp}|${tool_name}" >> "$USAGE_LOG"

    # Update metrics (if jq is available)
    if command -v jq &> /dev/null; then
        local temp_file="${METRICS_FILE}.tmp"

        jq --arg tool "$tool_name" '
            .total_calls += 1 |
            .tool_counts[$tool] = ((.tool_counts[$tool] // 0) + 1) |
            .last_updated = now | todate
        ' "$METRICS_FILE" > "$temp_file" && mv "$temp_file" "$METRICS_FILE"
    fi
    return 0
}

# Read tool call info from stdin
read_tool_info() {
    local info=""
    if [[ ! -t 0 ]]; then
        info=$(cat)
    fi
    echo "$info"
    return 0
}

# Extract tool name from context
extract_tool_name() {
    local context="$1"

    # Try to extract from JSON
    if command -v jq &> /dev/null && [[ -n "$context" ]]; then
        local name
        name=$(echo "$context" | jq -r '.tool_name // .name // empty' 2>/dev/null)
        if [[ -n "$name" ]]; then
            echo "$name"
            return
        fi
    fi

    # Fallback: extract from environment or default
    echo "${CLAUDE_TOOL_NAME:-unknown_mcp_tool}"
}

# Generate usage report
generate_report() {
    if [[ ! -f "$METRICS_FILE" ]]; then
        echo "No metrics available yet"
        return
    fi

    if command -v jq &> /dev/null; then
        echo "=== MCP Tool Usage Report ==="
        echo ""
        jq -r '
            "Session started: \(.session_start)",
            "Total MCP calls: \(.total_calls)",
            "",
            "Tool usage counts:",
            (.tool_counts | to_entries | sort_by(-.value) | .[] | "  \(.key): \(.value)")
        ' "$METRICS_FILE"

        echo ""
        echo "=== Optimization Suggestions ==="

        # Analyze and suggest
        jq -r '
            .tool_counts | to_entries | sort_by(-.value) |
            if length > 0 then
                if .[0].value > 10 then
                    "Consider keeping \(.[0].key) in Tier 1 (used \(.[0].value) times)"
                else
                    "Tool usage is well distributed"
                end
            else
                "No usage data to analyze"
            end
        ' "$METRICS_FILE"
    else
        echo "Install jq for detailed metrics"
        echo ""
        echo "Recent usage:"
        tail -20 "$USAGE_LOG" 2>/dev/null || echo "No usage logged"
    fi
    return 0
}

# Reset metrics for new session
reset_metrics() {
    echo '{"tool_counts":{},"session_start":"'"$(date -Iseconds)"'","total_calls":0}' > "$METRICS_FILE"
    echo "Metrics reset for new session"
    return 0
}

# Main hook logic
main() {
    local context
    context=$(read_tool_info)

    local tool_name
    tool_name=$(extract_tool_name "$context")

    log_usage "$tool_name"
    return 0
}

# Handle command-line arguments
case "${1:-}" in
    --report)
        generate_report
        ;;
    --reset)
        reset_metrics
        ;;
    --raw)
        # Output raw metrics
        cat "$METRICS_FILE" 2>/dev/null || echo "{}"
        ;;
    --help|-h)
        cat << EOF
MCP Usage Tracker - Track and analyze MCP tool usage

Usage:
  $0              Run as hook (reads from stdin)
  $0 --report     Generate usage report
  $0 --reset      Reset metrics for new session
  $0 --raw        Output raw metrics JSON
  $0 --help       Show this help

Files:
  Usage log: $USAGE_LOG
  Metrics:   $METRICS_FILE
EOF
        ;;
    *)
        main
        ;;
esac
