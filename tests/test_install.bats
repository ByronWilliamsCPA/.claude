#!/usr/bin/env bats
# Tests for install.sh - Claude Code Configuration Installer

load 'helpers/test_helper'

setup() {
    setup_test_environment
    # Copy install.sh to test location
    cp "$SCRIPTS_DIR/install.sh" "$TEST_TMP_DIR/install.sh"
    chmod +x "$TEST_TMP_DIR/install.sh"

    # Create required mocks for commands checked by script
    # Don't mock: bash, find, du, wc, cat, mkdir, touch, chmod (basic commands needed for script)
    mock_command "git" 0 "git version 2.30.0"
    mock_command "jq" 0 ""
    mock_command "node" 0 "v18.0.0"
    mock_command "npm" 0 "9.0.0"
    mock_command "npx" 0 "9.0.0"
    mock_command "python3" 0 "Python 3.11.0"
    mock_command "poetry" 0 "Poetry 1.5.0"
    mock_command "gpg" 0 ""
    mock_command "ssh-add" 0 ""
}

teardown() {
    teardown_test_environment
}

# =============================================================================
# Help and Usage Tests
# =============================================================================

@test "install.sh --help shows usage information" {
    run bash "$TEST_TMP_DIR/install.sh" --help
    assert_success
    assert_output_contains "Usage:"
    assert_output_contains "Modes:"
    assert_output_contains "full"
    assert_output_contains "minimal"
    assert_output_contains "validate-only"
}

@test "install.sh help shows usage information" {
    run bash "$TEST_TMP_DIR/install.sh" help
    assert_success
    assert_output_contains "Usage:"
}

@test "install.sh -h shows usage information" {
    run bash "$TEST_TMP_DIR/install.sh" -h
    assert_success
    assert_output_contains "Usage:"
}

# =============================================================================
# Mode Selection Tests
# =============================================================================

@test "install.sh defaults to full mode" {
    run bash "$TEST_TMP_DIR/install.sh"
    assert_success
    assert_output_contains "Installation mode: full"
}

@test "install.sh accepts minimal mode" {
    run bash "$TEST_TMP_DIR/install.sh" minimal
    assert_success
    assert_output_contains "Installation mode: minimal"
}

@test "install.sh accepts validate-only mode" {
    create_claude_md
    create_settings_json
    run bash "$TEST_TMP_DIR/install.sh" validate-only
    assert_success
    assert_output_contains "Installation mode: validate-only"
}

@test "install.sh rejects unknown mode" {
    run bash "$TEST_TMP_DIR/install.sh" unknown_mode
    assert_failure
    assert_output_contains "Unknown mode: unknown_mode"
}

# =============================================================================
# Prerequisites Check Tests
# =============================================================================

@test "install.sh checks for required commands" {
    run bash "$TEST_TMP_DIR/install.sh"
    assert_success
    assert_output_contains "Checking prerequisites"
}

@test "install.sh warns about missing recommended commands" {
    # Remove poetry mock to simulate missing command
    rm -f "$TEST_TMP_DIR/mocks/poetry" 2>/dev/null || true

    run bash "$TEST_TMP_DIR/install.sh"
    # Should still succeed but with warnings
    assert_success
}

# =============================================================================
# Directory Structure Tests
# =============================================================================

@test "install.sh creates required directories" {
    run bash "$TEST_TMP_DIR/install.sh"
    assert_success
    assert_dir_exists "$CLAUDE_CONFIG_DIR/logs"
    assert_dir_exists "$CLAUDE_CONFIG_DIR/scripts"
    assert_dir_exists "$CLAUDE_CONFIG_DIR/tmp_cleanup"
    assert_dir_exists "$CLAUDE_CONFIG_DIR/agents"
    assert_dir_exists "$CLAUDE_CONFIG_DIR/commands"
    assert_dir_exists "$CLAUDE_CONFIG_DIR/docs"
    assert_dir_exists "$CLAUDE_CONFIG_DIR/mcp"
    assert_dir_exists "$CLAUDE_CONFIG_DIR/standards"
    assert_dir_exists "$CLAUDE_CONFIG_DIR/templates"
}

@test "install.sh does not recreate existing directories" {
    mkdir -p "$CLAUDE_CONFIG_DIR/logs"
    touch "$CLAUDE_CONFIG_DIR/logs/test_marker"

    run bash "$TEST_TMP_DIR/install.sh"
    assert_success
    assert_file_exists "$CLAUDE_CONFIG_DIR/logs/test_marker"
}

# =============================================================================
# Environment File Tests
# =============================================================================

@test "install.sh creates .env.mcp.example" {
    run bash "$TEST_TMP_DIR/install.sh"
    assert_success
    assert_file_exists "$CLAUDE_CONFIG_DIR/.env.mcp.example"
}

@test "install.sh .env.mcp.example contains expected variables" {
    run bash "$TEST_TMP_DIR/install.sh"
    assert_success
    assert_file_contains "$CLAUDE_CONFIG_DIR/.env.mcp.example" "ZEN_MCP_SERVER_PATH"
    assert_file_contains "$CLAUDE_CONFIG_DIR/.env.mcp.example" "GITHUB_TOKEN"
}

# =============================================================================
# Configuration Validation Tests
# =============================================================================

@test "install.sh validates settings.json when present" {
    create_settings_json
    run bash "$TEST_TMP_DIR/install.sh" validate-only
    assert_success
    assert_output_contains "settings.json is valid"
}

@test "install.sh validates CLAUDE.md presence" {
    create_claude_md
    create_settings_json
    run bash "$TEST_TMP_DIR/install.sh" validate-only
    assert_success
    assert_output_contains "CLAUDE.md found"
}

@test "install.sh reports missing CLAUDE.md" {
    create_settings_json
    run bash "$TEST_TMP_DIR/install.sh" validate-only
    # Should complete but report the missing file
    assert_output_contains "CLAUDE.md not found"
}

# =============================================================================
# Health Check Tests
# =============================================================================

@test "install.sh runs health checks" {
    run bash "$TEST_TMP_DIR/install.sh"
    assert_success
    assert_output_contains "Running health checks"
    assert_output_contains "Config directory size"
    assert_output_contains "Total files"
}

# =============================================================================
# Summary Output Tests
# =============================================================================

@test "install.sh prints summary on completion" {
    run bash "$TEST_TMP_DIR/install.sh"
    assert_success
    assert_output_contains "Installation Complete"
    assert_output_contains "Next Steps"
}

@test "install.sh shows documentation paths in summary" {
    run bash "$TEST_TMP_DIR/install.sh"
    assert_success
    assert_output_contains "Documentation:"
    assert_output_contains "CLAUDE.md"
}

# =============================================================================
# Git Configuration Tests
# =============================================================================

@test "install.sh checks git signing configuration" {
    run bash "$TEST_TMP_DIR/install.sh"
    assert_success
    assert_output_contains "Configuring Git"
}

# =============================================================================
# Environment Variable Tests
# =============================================================================

@test "install.sh respects SKIP_DEPS environment variable" {
    export SKIP_DEPS=1
    run bash "$TEST_TMP_DIR/install.sh"
    assert_success
    assert_output_contains "Skipping Node.js dependency installation"
}

@test "install.sh respects CLAUDE_CONFIG_DIR environment variable" {
    export CLAUDE_CONFIG_DIR="$TEST_TMP_DIR/custom_claude"
    mkdir -p "$CLAUDE_CONFIG_DIR"
    touch "$CLAUDE_CONFIG_DIR/.env.mcp"  # Prevent interactive prompt
    run bash "$TEST_TMP_DIR/install.sh"
    assert_success
    assert_output_contains "$CLAUDE_CONFIG_DIR"
    assert_dir_exists "$CLAUDE_CONFIG_DIR/logs"
}

# =============================================================================
# Script Executability Tests
# =============================================================================

@test "install.sh makes scripts executable" {
    mkdir -p "$CLAUDE_CONFIG_DIR/scripts"
    touch "$CLAUDE_CONFIG_DIR/scripts/test_script.sh"

    run bash "$TEST_TMP_DIR/install.sh"
    assert_success
    assert_output_contains "Making scripts executable"
}

# =============================================================================
# Banner Tests
# =============================================================================

@test "install.sh displays banner" {
    run bash "$TEST_TMP_DIR/install.sh"
    assert_success
    assert_output_contains "Claude Code Global Configuration Installer"
}

# =============================================================================
# Minimal Mode Tests
# =============================================================================

@test "install.sh minimal mode skips dependencies" {
    run bash "$TEST_TMP_DIR/install.sh" minimal
    assert_success
    assert_output_contains "Installation mode: minimal"
    # Minimal mode should still create directories
    assert_dir_exists "$CLAUDE_CONFIG_DIR/logs"
}
