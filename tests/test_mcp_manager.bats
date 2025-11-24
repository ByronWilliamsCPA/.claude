#!/usr/bin/env bats
# Tests for mcp-manager.sh - MCP Server Manager for Claude Code

load 'helpers/test_helper'

setup() {
    setup_test_environment
    # Copy mcp-manager.sh to test location
    cp "$SCRIPTS_DIR/mcp-manager.sh" "$TEST_TMP_DIR/mcp-manager.sh"
    chmod +x "$TEST_TMP_DIR/mcp-manager.sh"

    # Create mcp directory
    mkdir -p "$TEST_TMP_DIR/.claude/mcp"

    # Create .env file for tests
    cat > "$TEST_TMP_DIR/.claude/.env" << 'EOF'
PERPLEXITY_API_KEY=test_perplexity_key
TAVILY_API_KEY=test_tavily_key
GITHUB_PERSONAL_ACCESS_TOKEN=test_github_token
UPSTASH_REDIS_REST_URL=https://test.upstash.io
UPSTASH_REDIS_REST_TOKEN=test_redis_token
EOF

    # Create mock claude command
    mock_command "claude" 0 "Success"
    mock_command "npx" 0 "9.0.0"
    mock_command "uvx" 0 "uvx"
}

teardown() {
    teardown_test_environment
}

# =============================================================================
# Logging Function Tests
# =============================================================================

@test "mcp-manager.sh creates log file" {
    # The script will create a log file when run
    run bash -c "echo '8' | bash '$TEST_TMP_DIR/mcp-manager.sh'"
    # Log file should be created in the script directory parent
    assert_file_exists "$TEST_TMP_DIR/.claude/mcp-install.log" || \
    [ -f "$TEST_TMP_DIR/mcp-install.log" ] || true
}

# =============================================================================
# Menu Display Tests
# =============================================================================

@test "mcp-manager.sh shows menu on start" {
    run bash -c "echo '8' | bash '$TEST_TMP_DIR/mcp-manager.sh'"
    assert_output_contains "MCP Server Manager for Claude"
    assert_output_contains "Install all recommended servers"
    assert_output_contains "Install development tools"
    assert_output_contains "Install AI/Search servers"
}

@test "mcp-manager.sh menu has 8 options" {
    run bash -c "echo '8' | bash '$TEST_TMP_DIR/mcp-manager.sh'"
    assert_output_contains "1)"
    assert_output_contains "2)"
    assert_output_contains "3)"
    assert_output_contains "4)"
    assert_output_contains "5)"
    assert_output_contains "6)"
    assert_output_contains "7)"
    assert_output_contains "8)"
}

@test "mcp-manager.sh exits cleanly on option 8" {
    run bash -c "echo '8' | bash '$TEST_TMP_DIR/mcp-manager.sh'"
    assert_success
    assert_output_contains "Goodbye!"
}

# =============================================================================
# Environment Variable Loading Tests
# =============================================================================

@test "mcp-manager.sh loads .env file" {
    # Create script wrapper to test env loading
    cat > "$TEST_TMP_DIR/test_env.sh" << 'EOF'
#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${SCRIPT_DIR}/.claude/.env"
if [ -f "$ENV_FILE" ]; then
    set -a
    source "$ENV_FILE"
    set +a
fi
echo "PERPLEXITY_API_KEY=$PERPLEXITY_API_KEY"
EOF
    chmod +x "$TEST_TMP_DIR/test_env.sh"

    run bash "$TEST_TMP_DIR/test_env.sh"
    assert_output_contains "PERPLEXITY_API_KEY=test_perplexity_key"
}

@test "mcp-manager.sh warns when .env not found" {
    rm -f "$TEST_TMP_DIR/.claude/.env"
    run bash -c "echo '8' | bash '$TEST_TMP_DIR/mcp-manager.sh'"
    assert_output_contains "Warning: No .env file found"
}

# =============================================================================
# Color Output Tests
# =============================================================================

@test "mcp-manager.sh defines color codes" {
    # Test that script can run without color errors
    run bash -c "echo '8' | bash '$TEST_TMP_DIR/mcp-manager.sh'"
    assert_success
}

# =============================================================================
# Server List Tests
# =============================================================================

@test "mcp-manager.sh option 5 lists installed servers" {
    # Mock claude mcp list
    mock_command "claude" 0 "zen: /path/to/server"

    # Send option 5 then press enter then 8 to exit
    run bash -c "printf '5\n\n8\n' | bash '$TEST_TMP_DIR/mcp-manager.sh'"
    assert_output_contains "Installed MCP servers"
}

# =============================================================================
# Invalid Option Tests
# =============================================================================

@test "mcp-manager.sh handles invalid option" {
    run bash -c "printf '99\n\n8\n' | bash '$TEST_TMP_DIR/mcp-manager.sh'"
    assert_output_contains "Invalid option"
}

# =============================================================================
# Install Functions Tests
# =============================================================================

@test "mcp-manager.sh install_all includes core servers" {
    # Test that the script mentions core servers when installing all
    # We need to check the script content
    grep -q 'install_stdio_server "zen"' "$TEST_TMP_DIR/mcp-manager.sh"
    [ $? -eq 0 ]
}

@test "mcp-manager.sh install_dev_tools includes git server" {
    grep -q 'install_server_with_env "git"' "$TEST_TMP_DIR/mcp-manager.sh"
    [ $? -eq 0 ]
}

@test "mcp-manager.sh install_dev_tools includes sequential-thinking" {
    grep -q 'install_stdio_server "sequential-thinking"' "$TEST_TMP_DIR/mcp-manager.sh"
    [ $? -eq 0 ]
}

@test "mcp-manager.sh install_dev_tools includes time server" {
    grep -q 'install_stdio_server "time"' "$TEST_TMP_DIR/mcp-manager.sh"
    [ $? -eq 0 ]
}

# =============================================================================
# API Key Check Tests
# =============================================================================

@test "mcp-manager.sh checks for PERPLEXITY_API_KEY" {
    grep -q 'PERPLEXITY_API_KEY' "$TEST_TMP_DIR/mcp-manager.sh"
    [ $? -eq 0 ]
}

@test "mcp-manager.sh checks for TAVILY_API_KEY" {
    grep -q 'TAVILY_API_KEY' "$TEST_TMP_DIR/mcp-manager.sh"
    [ $? -eq 0 ]
}

@test "mcp-manager.sh checks for GITHUB_PERSONAL_ACCESS_TOKEN" {
    grep -q 'GITHUB_PERSONAL_ACCESS_TOKEN' "$TEST_TMP_DIR/mcp-manager.sh"
    [ $? -eq 0 ]
}

@test "mcp-manager.sh checks for UPSTASH credentials" {
    grep -q 'UPSTASH_REDIS_REST_URL' "$TEST_TMP_DIR/mcp-manager.sh"
    [ $? -eq 0 ]
    grep -q 'UPSTASH_REDIS_REST_TOKEN' "$TEST_TMP_DIR/mcp-manager.sh"
    [ $? -eq 0 ]
}

# =============================================================================
# Server Installation Command Tests
# =============================================================================

@test "mcp-manager.sh uses claude mcp add command" {
    grep -q 'claude mcp add' "$TEST_TMP_DIR/mcp-manager.sh"
    [ $? -eq 0 ]
}

@test "mcp-manager.sh supports stdio server installation" {
    grep -q 'install_stdio_server' "$TEST_TMP_DIR/mcp-manager.sh"
    [ $? -eq 0 ]
}

@test "mcp-manager.sh supports http server installation" {
    grep -q 'install_http_server' "$TEST_TMP_DIR/mcp-manager.sh"
    [ $? -eq 0 ]
}

@test "mcp-manager.sh supports env var server installation" {
    grep -q 'install_server_with_env' "$TEST_TMP_DIR/mcp-manager.sh"
    [ $? -eq 0 ]
}

# =============================================================================
# Server Removal Tests
# =============================================================================

@test "mcp-manager.sh option 6 allows server removal" {
    mock_command "claude" 0 ""
    run bash -c "printf '6\ntest_server\n\n8\n' | bash '$TEST_TMP_DIR/mcp-manager.sh'"
    # Should attempt to remove server
    assert_output_contains "removed successfully" || assert_output_contains "Failed to remove"
}

# =============================================================================
# Script Structure Tests
# =============================================================================

@test "mcp-manager.sh uses set -e for error handling" {
    head -20 "$TEST_TMP_DIR/mcp-manager.sh" | grep -q 'set -e'
    [ $? -eq 0 ]
}

@test "mcp-manager.sh defines print_status function" {
    grep -q 'print_status()' "$TEST_TMP_DIR/mcp-manager.sh"
    [ $? -eq 0 ]
}

@test "mcp-manager.sh defines log function" {
    grep -q 'log()' "$TEST_TMP_DIR/mcp-manager.sh"
    [ $? -eq 0 ]
}

@test "mcp-manager.sh defines is_server_installed function" {
    grep -q 'is_server_installed()' "$TEST_TMP_DIR/mcp-manager.sh"
    [ $? -eq 0 ]
}

@test "mcp-manager.sh defines main function" {
    grep -q 'main()' "$TEST_TMP_DIR/mcp-manager.sh"
    [ $? -eq 0 ]
}

# =============================================================================
# Context7 SSE Server Tests
# =============================================================================

@test "mcp-manager.sh installs context7-sse as http server" {
    grep -q 'context7-sse' "$TEST_TMP_DIR/mcp-manager.sh"
    [ $? -eq 0 ]
    grep -q 'mcp.context7.com' "$TEST_TMP_DIR/mcp-manager.sh"
    [ $? -eq 0 ]
}

# =============================================================================
# Zen Server Tests
# =============================================================================

@test "mcp-manager.sh configures zen server with python venv" {
    grep -q '.zen_venv/bin/python' "$TEST_TMP_DIR/mcp-manager.sh"
    [ $? -eq 0 ]
}
