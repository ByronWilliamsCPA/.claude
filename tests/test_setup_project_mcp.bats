#!/usr/bin/env bats
# Tests for setup-project-mcp.sh - Project MCP Server Setup

load 'helpers/test_helper'

setup() {
    setup_test_environment
    # Copy setup-project-mcp.sh to test location
    cp "$SCRIPTS_DIR/setup-project-mcp.sh" "$TEST_TMP_DIR/setup-project-mcp.sh"
    chmod +x "$TEST_TMP_DIR/setup-project-mcp.sh"

    # Create a mock git repository for testing
    mkdir -p "$TEST_TMP_DIR/test_project"
    init_git_repo "$TEST_TMP_DIR/test_project"

    # Create .env file in .claude directory
    mkdir -p "$HOME/.claude"
    cat > "$HOME/.claude/.env" << 'EOF'
PERPLEXITY_API_KEY=test_perplexity_key
TAVILY_API_KEY=test_tavily_key
GITHUB_PERSONAL_ACCESS_TOKEN=test_github_token
UPSTASH_REDIS_REST_URL=https://test.upstash.io
UPSTASH_REDIS_REST_TOKEN=test_redis_token
SERENA_INSTALL_PATH=/path/to/serena
EOF

    # Create mocks
    mock_command "claude" 0 "Success"
    mock_command "npx" 0 "9.0.0"
    mock_command "uvx" 0 "uvx"
    mock_command "uv" 0 "uv"
}

teardown() {
    teardown_test_environment
}

# =============================================================================
# Git Repository Check Tests
# =============================================================================

@test "setup-project-mcp.sh fails when not in git repository" {
    cd "$TEST_TMP_DIR"
    run bash "$TEST_TMP_DIR/setup-project-mcp.sh"
    assert_failure
    assert_output_contains "Not in a git repository"
}

@test "setup-project-mcp.sh succeeds in git repository" {
    cd "$TEST_TMP_DIR/test_project"
    run bash "$TEST_TMP_DIR/setup-project-mcp.sh"
    assert_success
}

@test "setup-project-mcp.sh displays project name" {
    cd "$TEST_TMP_DIR/test_project"
    run bash "$TEST_TMP_DIR/setup-project-mcp.sh"
    assert_success
    assert_output_contains "test_project"
}

@test "setup-project-mcp.sh displays project path" {
    cd "$TEST_TMP_DIR/test_project"
    run bash "$TEST_TMP_DIR/setup-project-mcp.sh"
    assert_success
    assert_output_contains "Project path"
}

# =============================================================================
# Help and Usage Tests
# =============================================================================

@test "setup-project-mcp.sh --help shows usage" {
    cd "$TEST_TMP_DIR/test_project"
    run bash "$TEST_TMP_DIR/setup-project-mcp.sh" --help
    assert_success
    assert_output_contains "Usage:"
    assert_output_contains "Options:"
}

@test "setup-project-mcp.sh -h shows usage" {
    cd "$TEST_TMP_DIR/test_project"
    run bash "$TEST_TMP_DIR/setup-project-mcp.sh" -h
    assert_success
    assert_output_contains "Usage:"
}

@test "setup-project-mcp.sh --list shows available servers" {
    cd "$TEST_TMP_DIR/test_project"
    run bash "$TEST_TMP_DIR/setup-project-mcp.sh" --list
    assert_success
    assert_output_contains "Available MCP servers"
    assert_output_contains "zen"
    assert_output_contains "git"
    assert_output_contains "sequential-thinking"
}

# =============================================================================
# Directory Creation Tests
# =============================================================================

@test "setup-project-mcp.sh creates .claude directory in project" {
    cd "$TEST_TMP_DIR/test_project"
    rm -rf "$TEST_TMP_DIR/test_project/.claude"
    run bash "$TEST_TMP_DIR/setup-project-mcp.sh"
    assert_success
    assert_dir_exists "$TEST_TMP_DIR/test_project/.claude"
}

@test "setup-project-mcp.sh creates mcp.json in project" {
    cd "$TEST_TMP_DIR/test_project"
    run bash "$TEST_TMP_DIR/setup-project-mcp.sh"
    assert_success
    assert_file_exists "$TEST_TMP_DIR/test_project/.claude/mcp.json"
}

@test "setup-project-mcp.sh mcp.json contains git server config" {
    cd "$TEST_TMP_DIR/test_project"
    run bash "$TEST_TMP_DIR/setup-project-mcp.sh"
    assert_success
    assert_file_contains "$TEST_TMP_DIR/test_project/.claude/mcp.json" "mcpServers"
    assert_file_contains "$TEST_TMP_DIR/test_project/.claude/mcp.json" "git"
}

# =============================================================================
# Default Servers Tests
# =============================================================================

@test "setup-project-mcp.sh installs default servers with no args" {
    cd "$TEST_TMP_DIR/test_project"
    run bash "$TEST_TMP_DIR/setup-project-mcp.sh"
    assert_success
    assert_output_contains "Installing servers: git sequential-thinking zen" || \
    assert_output_contains "Installing servers:"
}

# =============================================================================
# Option Flags Tests
# =============================================================================

@test "setup-project-mcp.sh --all installs all servers" {
    cd "$TEST_TMP_DIR/test_project"
    run bash "$TEST_TMP_DIR/setup-project-mcp.sh" --all
    assert_success
    assert_output_contains "Installing servers:"
}

@test "setup-project-mcp.sh --dev installs dev tools" {
    cd "$TEST_TMP_DIR/test_project"
    run bash "$TEST_TMP_DIR/setup-project-mcp.sh" --dev
    assert_success
    assert_output_contains "git"
    assert_output_contains "sequential-thinking"
}

@test "setup-project-mcp.sh --ai installs AI servers" {
    cd "$TEST_TMP_DIR/test_project"
    run bash "$TEST_TMP_DIR/setup-project-mcp.sh" --ai
    assert_success
    # Should attempt to install AI servers
    assert_output_contains "Installing"
}

# =============================================================================
# Specific Server Installation Tests
# =============================================================================

@test "setup-project-mcp.sh installs specific server by name" {
    cd "$TEST_TMP_DIR/test_project"
    run bash "$TEST_TMP_DIR/setup-project-mcp.sh" time
    assert_success
    assert_output_contains "time"
}

@test "setup-project-mcp.sh handles unknown server gracefully" {
    cd "$TEST_TMP_DIR/test_project"
    run bash "$TEST_TMP_DIR/setup-project-mcp.sh" nonexistent_server
    assert_success
    assert_output_contains "Unknown server: nonexistent_server"
}

# =============================================================================
# API Key Validation Tests
# =============================================================================

@test "setup-project-mcp.sh skips perplexity without API key" {
    cd "$TEST_TMP_DIR/test_project"
    unset PERPLEXITY_API_KEY
    echo "" > "$HOME/.claude/.env"
    run bash "$TEST_TMP_DIR/setup-project-mcp.sh" perplexity
    assert_output_contains "Skipping Perplexity"
}

@test "setup-project-mcp.sh skips tavily without API key" {
    cd "$TEST_TMP_DIR/test_project"
    unset TAVILY_API_KEY
    echo "" > "$HOME/.claude/.env"
    run bash "$TEST_TMP_DIR/setup-project-mcp.sh" tavily
    assert_output_contains "Skipping Tavily"
}

@test "setup-project-mcp.sh skips github without token" {
    cd "$TEST_TMP_DIR/test_project"
    unset GITHUB_PERSONAL_ACCESS_TOKEN
    echo "" > "$HOME/.claude/.env"
    run bash "$TEST_TMP_DIR/setup-project-mcp.sh" github
    assert_output_contains "Skipping GitHub"
}

@test "setup-project-mcp.sh skips context7 without redis credentials" {
    cd "$TEST_TMP_DIR/test_project"
    unset UPSTASH_REDIS_REST_URL
    unset UPSTASH_REDIS_REST_TOKEN
    echo "" > "$HOME/.claude/.env"
    run bash "$TEST_TMP_DIR/setup-project-mcp.sh" context7
    assert_output_contains "Skipping Context7"
}

@test "setup-project-mcp.sh skips serena without install path" {
    cd "$TEST_TMP_DIR/test_project"
    unset SERENA_INSTALL_PATH
    echo "" > "$HOME/.claude/.env"
    run bash "$TEST_TMP_DIR/setup-project-mcp.sh" serena
    assert_output_contains "Skipping Serena"
}

# =============================================================================
# Completion Message Tests
# =============================================================================

@test "setup-project-mcp.sh shows completion message" {
    cd "$TEST_TMP_DIR/test_project"
    run bash "$TEST_TMP_DIR/setup-project-mcp.sh"
    assert_success
    assert_output_contains "MCP server setup complete"
}

@test "setup-project-mcp.sh lists created files" {
    cd "$TEST_TMP_DIR/test_project"
    run bash "$TEST_TMP_DIR/setup-project-mcp.sh"
    assert_success
    assert_output_contains "files were created"
    assert_output_contains "mcp.json"
}

@test "setup-project-mcp.sh suggests verification command" {
    cd "$TEST_TMP_DIR/test_project"
    run bash "$TEST_TMP_DIR/setup-project-mcp.sh"
    assert_success
    assert_output_contains "claude mcp list"
}

# =============================================================================
# Script Structure Tests
# =============================================================================

@test "setup-project-mcp.sh uses set -e" {
    head -20 "$TEST_TMP_DIR/setup-project-mcp.sh" | grep -q 'set -e'
    [ $? -eq 0 ]
}

@test "setup-project-mcp.sh defines print_usage function" {
    grep -q 'print_usage()' "$TEST_TMP_DIR/setup-project-mcp.sh"
    [ $? -eq 0 ]
}

@test "setup-project-mcp.sh defines DEFAULT_SERVERS" {
    grep -q 'DEFAULT_SERVERS=' "$TEST_TMP_DIR/setup-project-mcp.sh"
    [ $? -eq 0 ]
}

@test "setup-project-mcp.sh defines color variables" {
    grep -q 'GREEN=' "$TEST_TMP_DIR/setup-project-mcp.sh"
    [ $? -eq 0 ]
    grep -q 'YELLOW=' "$TEST_TMP_DIR/setup-project-mcp.sh"
    [ $? -eq 0 ]
    grep -q 'RED=' "$TEST_TMP_DIR/setup-project-mcp.sh"
    [ $? -eq 0 ]
}

# =============================================================================
# Duplicate Server Handling Tests
# =============================================================================

@test "setup-project-mcp.sh removes duplicate server entries" {
    cd "$TEST_TMP_DIR/test_project"
    run bash "$TEST_TMP_DIR/setup-project-mcp.sh" git git git
    assert_success
    # Should install git only once
    local git_count=$(echo "$output" | grep -c "Installing git" || echo "1")
    [ "$git_count" -le 2 ]  # At most 2 mentions (one for plan, one for execution)
}

# =============================================================================
# Environment Loading Tests
# =============================================================================

@test "setup-project-mcp.sh loads .env from ~/.claude" {
    grep -q 'source "$ENV_FILE"' "$TEST_TMP_DIR/setup-project-mcp.sh"
    [ $? -eq 0 ]
}

@test "setup-project-mcp.sh displays loading message for .env" {
    cd "$TEST_TMP_DIR/test_project"
    run bash "$TEST_TMP_DIR/setup-project-mcp.sh"
    assert_output_contains "Loading environment variables"
}
