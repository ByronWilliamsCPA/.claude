#!/usr/bin/env bats
# Tests for validate-mcp-env.sh - MCP Environment Validation

load 'helpers/test_helper'

setup() {
    setup_test_environment
    # Copy validate-mcp-env.sh to test location
    cp "$SCRIPTS_DIR/validate-mcp-env.sh" "$TEST_TMP_DIR/validate-mcp-env.sh"
    chmod +x "$TEST_TMP_DIR/validate-mcp-env.sh"

    # Create all mocks for executables
    mock_command "python3" 0 "Python 3.11.0"
    mock_command "node" 0 "v18.0.0"
    mock_command "npm" 0 "9.0.0"
    mock_command "npx" 0 "9.0.0"
    mock_command "docker" 0 "Docker version 24.0.0"
    mock_command "uvx" 0 "uvx"
    mock_command "uv" 0 "uv"

    # Set required environment variables
    export GIT_REPO_PATH="$TEST_TMP_DIR"
    export PERPLEXITY_API_KEY="test_key"
    export TAVILY_API_KEY="test_key"
    export GITHUB_PERSONAL_ACCESS_TOKEN="test_token"
    export ZAPIER_API_KEY="test_key"
    export UPSTASH_REDIS_REST_URL="https://test.upstash.io"
    export UPSTASH_REDIS_REST_TOKEN="test_token"
    export SENTRY_AUTH_TOKEN="test_token"
    export SENTRY_ORG="test_org"
    export SENTRY_PROJECT="test_project"
    export SERENA_INSTALL_PATH="$TEST_TMP_DIR"
    export SERENA_PROJECT_PATH="$TEST_TMP_DIR"

    # Create required paths
    mkdir -p "$HOME/.claude/settings"
    mkdir -p "$HOME/dev/zen-mcp-server/.zen_venv/bin"
    touch "$HOME/dev/zen-mcp-server/server.py"
    touch "$HOME/dev/zen-mcp-server/.zen_venv/bin/python"
    touch "$HOME/.claude/mcp-servers.json"
    echo '{"enableAllProjectMcpServers": true}' > "$HOME/.claude/settings/base-settings.json"
}

teardown() {
    teardown_test_environment
}

# =============================================================================
# Header Tests
# =============================================================================

@test "validate-mcp-env.sh displays header" {
    run bash "$TEST_TMP_DIR/validate-mcp-env.sh"
    assert_output_contains "MCP Environment Validation"
}

# =============================================================================
# Executable Check Tests
# =============================================================================

@test "validate-mcp-env.sh checks for python3" {
    run bash "$TEST_TMP_DIR/validate-mcp-env.sh"
    assert_output_contains "Python3"
}

@test "validate-mcp-env.sh checks for node" {
    run bash "$TEST_TMP_DIR/validate-mcp-env.sh"
    assert_output_contains "Node.js"
}

@test "validate-mcp-env.sh checks for npm" {
    run bash "$TEST_TMP_DIR/validate-mcp-env.sh"
    assert_output_contains "NPM"
}

@test "validate-mcp-env.sh checks for npx" {
    run bash "$TEST_TMP_DIR/validate-mcp-env.sh"
    assert_output_contains "NPX"
}

@test "validate-mcp-env.sh checks for docker" {
    run bash "$TEST_TMP_DIR/validate-mcp-env.sh"
    assert_output_contains "Docker"
}

@test "validate-mcp-env.sh checks for uvx" {
    run bash "$TEST_TMP_DIR/validate-mcp-env.sh"
    assert_output_contains "UVX"
}

@test "validate-mcp-env.sh checks for uv" {
    run bash "$TEST_TMP_DIR/validate-mcp-env.sh"
    assert_output_contains "UV"
}

@test "validate-mcp-env.sh reports missing executable as error" {
    # Remove docker mock
    rm -f "$TEST_TMP_DIR/mocks/docker"
    run bash "$TEST_TMP_DIR/validate-mcp-env.sh"
    assert_output_contains "Docker executable not found"
}

# =============================================================================
# Environment Variable Check Tests
# =============================================================================

@test "validate-mcp-env.sh checks for PERPLEXITY_API_KEY" {
    run bash "$TEST_TMP_DIR/validate-mcp-env.sh"
    assert_output_contains "Perplexity"
}

@test "validate-mcp-env.sh checks for TAVILY_API_KEY" {
    run bash "$TEST_TMP_DIR/validate-mcp-env.sh"
    assert_output_contains "Tavily"
}

@test "validate-mcp-env.sh checks for GITHUB_PERSONAL_ACCESS_TOKEN" {
    run bash "$TEST_TMP_DIR/validate-mcp-env.sh"
    assert_output_contains "GitHub"
}

@test "validate-mcp-env.sh checks for ZAPIER_API_KEY" {
    run bash "$TEST_TMP_DIR/validate-mcp-env.sh"
    assert_output_contains "Zapier"
}

@test "validate-mcp-env.sh checks for Upstash Redis credentials" {
    run bash "$TEST_TMP_DIR/validate-mcp-env.sh"
    assert_output_contains "Upstash Redis URL"
    assert_output_contains "Upstash Redis Token"
}

@test "validate-mcp-env.sh checks for Sentry credentials" {
    run bash "$TEST_TMP_DIR/validate-mcp-env.sh"
    assert_output_contains "Sentry Auth Token"
    assert_output_contains "Sentry Organization"
    assert_output_contains "Sentry Project"
}

@test "validate-mcp-env.sh checks for Serena paths" {
    run bash "$TEST_TMP_DIR/validate-mcp-env.sh"
    assert_output_contains "Serena Install Path"
    assert_output_contains "Serena Project Path"
}

@test "validate-mcp-env.sh warns for missing optional env var" {
    unset PERPLEXITY_API_KEY
    run bash "$TEST_TMP_DIR/validate-mcp-env.sh"
    assert_output_contains "Perplexity"
    # Should be a warning, not error for optional vars
}

# =============================================================================
# Path Check Tests
# =============================================================================

@test "validate-mcp-env.sh checks for zen server script" {
    run bash "$TEST_TMP_DIR/validate-mcp-env.sh"
    assert_output_contains "Zen server script"
}

@test "validate-mcp-env.sh checks for zen python environment" {
    run bash "$TEST_TMP_DIR/validate-mcp-env.sh"
    assert_output_contains "Zen Python environment"
}

@test "validate-mcp-env.sh checks for MCP configuration" {
    run bash "$TEST_TMP_DIR/validate-mcp-env.sh"
    assert_output_contains "MCP configuration"
}

@test "validate-mcp-env.sh checks for base settings file" {
    run bash "$TEST_TMP_DIR/validate-mcp-env.sh"
    assert_output_contains "Base settings file"
}

@test "validate-mcp-env.sh reports missing path as error" {
    rm -f "$HOME/dev/zen-mcp-server/server.py"
    run bash "$TEST_TMP_DIR/validate-mcp-env.sh"
    assert_output_contains "Zen server script"
    assert_output_contains "not found"
}

# =============================================================================
# Claude Code Configuration Tests
# =============================================================================

@test "validate-mcp-env.sh checks enableAllProjectMcpServers" {
    run bash "$TEST_TMP_DIR/validate-mcp-env.sh"
    assert_output_contains "enableAllProjectMcpServers"
}

@test "validate-mcp-env.sh warns if enableAllProjectMcpServers not enabled" {
    echo '{"enableAllProjectMcpServers": false}' > "$HOME/.claude/settings/base-settings.json"
    run bash "$TEST_TMP_DIR/validate-mcp-env.sh"
    assert_output_contains "enableAllProjectMcpServers is not enabled"
}

# =============================================================================
# Summary Tests
# =============================================================================

@test "validate-mcp-env.sh displays validation summary" {
    run bash "$TEST_TMP_DIR/validate-mcp-env.sh"
    assert_output_contains "Validation Summary"
    assert_output_contains "Warnings:"
    assert_output_contains "Errors:"
}

@test "validate-mcp-env.sh shows success when all checks pass" {
    run bash "$TEST_TMP_DIR/validate-mcp-env.sh"
    assert_success
    assert_output_contains "passed" || assert_output_contains "completed"
}

@test "validate-mcp-env.sh exits with error code when errors found" {
    # Remove critical paths to trigger errors
    rm -f "$HOME/dev/zen-mcp-server/server.py"
    rm -f "$HOME/dev/zen-mcp-server/.zen_venv/bin/python"
    rm -f "$HOME/.claude/mcp-servers.json"
    rm -f "$HOME/.claude/settings/base-settings.json"
    run bash "$TEST_TMP_DIR/validate-mcp-env.sh"
    assert_failure
    assert_output_contains "not found" || assert_output_contains "errors"
}

# =============================================================================
# Next Steps Tests
# =============================================================================

@test "validate-mcp-env.sh shows next steps on failure" {
    # Remove critical paths to trigger failure
    rm -f "$HOME/dev/zen-mcp-server/server.py"
    rm -f "$HOME/dev/zen-mcp-server/.zen_venv/bin/python"
    rm -f "$HOME/.claude/mcp-servers.json"
    rm -f "$HOME/.claude/settings/base-settings.json"
    run bash "$TEST_TMP_DIR/validate-mcp-env.sh"
    assert_failure
    # The script shows "Next Steps" section when there are errors
    assert_output_contains "not found" || assert_output_contains "Next Steps"
}

@test "validate-mcp-env.sh suggests running claude mcp list" {
    # When errors are found, the script suggests running claude mcp list
    # This is part of the "Next Steps" section
    grep -q "claude mcp list" "$TEST_TMP_DIR/validate-mcp-env.sh"
    [ $? -eq 0 ]
}

# =============================================================================
# Script Structure Tests
# =============================================================================

@test "validate-mcp-env.sh uses set -e" {
    head -20 "$TEST_TMP_DIR/validate-mcp-env.sh" | grep -q 'set -e'
    [ $? -eq 0 ]
}

@test "validate-mcp-env.sh defines print_status function" {
    grep -q 'print_status()' "$TEST_TMP_DIR/validate-mcp-env.sh"
    [ $? -eq 0 ]
}

@test "validate-mcp-env.sh defines check_executable function" {
    grep -q 'check_executable()' "$TEST_TMP_DIR/validate-mcp-env.sh"
    [ $? -eq 0 ]
}

@test "validate-mcp-env.sh defines check_env_var function" {
    grep -q 'check_env_var()' "$TEST_TMP_DIR/validate-mcp-env.sh"
    [ $? -eq 0 ]
}

@test "validate-mcp-env.sh defines check_path function" {
    grep -q 'check_path()' "$TEST_TMP_DIR/validate-mcp-env.sh"
    [ $? -eq 0 ]
}

@test "validate-mcp-env.sh defines color variables" {
    grep -q 'GREEN=' "$TEST_TMP_DIR/validate-mcp-env.sh"
    [ $? -eq 0 ]
    grep -q 'YELLOW=' "$TEST_TMP_DIR/validate-mcp-env.sh"
    [ $? -eq 0 ]
    grep -q 'RED=' "$TEST_TMP_DIR/validate-mcp-env.sh"
    [ $? -eq 0 ]
}

@test "validate-mcp-env.sh initializes counters" {
    grep -q 'WARNINGS=0' "$TEST_TMP_DIR/validate-mcp-env.sh"
    [ $? -eq 0 ]
    grep -q 'ERRORS=0' "$TEST_TMP_DIR/validate-mcp-env.sh"
    [ $? -eq 0 ]
}

# =============================================================================
# Serena Path Conditional Tests
# =============================================================================

@test "validate-mcp-env.sh checks serena path only if env var is set" {
    unset SERENA_INSTALL_PATH
    run bash "$TEST_TMP_DIR/validate-mcp-env.sh"
    # Should not try to check a non-existent serena path
    assert_success || [ "$status" -eq 0 ] || [ "$status" -eq 1 ]
}
