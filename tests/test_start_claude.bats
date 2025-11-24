#!/usr/bin/env bats
# Tests for start-claude.sh - Claude Code Startup Script

load 'helpers/test_helper'

setup() {
    setup_test_environment
    # Copy start-claude.sh to test location
    cp "$SCRIPTS_DIR/start-claude.sh" "$TEST_TMP_DIR/start-claude.sh"
    chmod +x "$TEST_TMP_DIR/start-claude.sh"

    # Create mock claude command
    cat > "$TEST_TMP_DIR/mocks/claude" << 'EOF'
#!/bin/bash
echo "CLAUDE_CONFIG_DIR=$CLAUDE_CONFIG_DIR"
echo "Arguments: $@"
exit 0
EOF
    chmod +x "$TEST_TMP_DIR/mocks/claude"
}

teardown() {
    teardown_test_environment
}

# =============================================================================
# Environment Variable Tests
# =============================================================================

@test "start-claude.sh sets CLAUDE_CONFIG_DIR" {
    run bash "$TEST_TMP_DIR/start-claude.sh"
    assert_success
    assert_output_contains "CLAUDE_CONFIG_DIR=$HOME/.claude"
}

@test "start-claude.sh exports CLAUDE_CONFIG_DIR to child processes" {
    run bash "$TEST_TMP_DIR/start-claude.sh"
    assert_success
    # The mock claude command echoes CLAUDE_CONFIG_DIR, proving it was exported
    assert_output_contains "CLAUDE_CONFIG_DIR="
}

# =============================================================================
# Argument Passing Tests
# =============================================================================

@test "start-claude.sh passes no arguments" {
    run bash "$TEST_TMP_DIR/start-claude.sh"
    assert_success
    assert_output_contains "Arguments:"
}

@test "start-claude.sh passes single argument to claude" {
    run bash "$TEST_TMP_DIR/start-claude.sh" --help
    assert_success
    assert_output_contains "Arguments: --help"
}

@test "start-claude.sh passes multiple arguments to claude" {
    run bash "$TEST_TMP_DIR/start-claude.sh" --model gpt-4 --verbose
    assert_success
    assert_output_contains "Arguments: --model gpt-4 --verbose"
}

@test "start-claude.sh passes arguments with spaces" {
    run bash "$TEST_TMP_DIR/start-claude.sh" --prompt "Hello World"
    assert_success
    assert_output_contains "Arguments: --prompt Hello World"
}

@test "start-claude.sh passes complex arguments" {
    run bash "$TEST_TMP_DIR/start-claude.sh" mcp add zen --config ./config.json
    assert_success
    assert_output_contains "Arguments: mcp add zen --config ./config.json"
}

# =============================================================================
# Script Structure Tests
# =============================================================================

@test "start-claude.sh has correct shebang" {
    head -1 "$TEST_TMP_DIR/start-claude.sh" | grep -q '#!/bin/bash'
    [ $? -eq 0 ]
}

@test "start-claude.sh uses exec for claude" {
    grep -q 'exec claude' "$TEST_TMP_DIR/start-claude.sh"
    [ $? -eq 0 ]
}

@test "start-claude.sh passes all arguments with \$@" {
    grep -q '\$@' "$TEST_TMP_DIR/start-claude.sh"
    [ $? -eq 0 ]
}

@test "start-claude.sh defines CLAUDE_CONFIG_DIR" {
    grep -q 'CLAUDE_CONFIG_DIR=' "$TEST_TMP_DIR/start-claude.sh"
    [ $? -eq 0 ]
}

@test "start-claude.sh exports CLAUDE_CONFIG_DIR" {
    grep -q 'export CLAUDE_CONFIG_DIR' "$TEST_TMP_DIR/start-claude.sh"
    [ $? -eq 0 ]
}

# =============================================================================
# Exit Code Tests
# =============================================================================

@test "start-claude.sh propagates claude exit code 0" {
    cat > "$TEST_TMP_DIR/mocks/claude" << 'EOF'
#!/bin/bash
exit 0
EOF
    chmod +x "$TEST_TMP_DIR/mocks/claude"

    run bash "$TEST_TMP_DIR/start-claude.sh"
    assert_success
}

@test "start-claude.sh propagates claude exit code 1" {
    cat > "$TEST_TMP_DIR/mocks/claude" << 'EOF'
#!/bin/bash
exit 1
EOF
    chmod +x "$TEST_TMP_DIR/mocks/claude"

    run bash "$TEST_TMP_DIR/start-claude.sh"
    assert_failure
    [ "$status" -eq 1 ]
}

@test "start-claude.sh propagates claude exit code 2" {
    cat > "$TEST_TMP_DIR/mocks/claude" << 'EOF'
#!/bin/bash
exit 2
EOF
    chmod +x "$TEST_TMP_DIR/mocks/claude"

    run bash "$TEST_TMP_DIR/start-claude.sh"
    assert_failure
    [ "$status" -eq 2 ]
}

# =============================================================================
# Config Directory Tests
# =============================================================================

@test "start-claude.sh uses ~/.claude as config directory" {
    run bash "$TEST_TMP_DIR/start-claude.sh"
    assert_success
    assert_output_contains ".claude"
}

@test "start-claude.sh config directory is under HOME" {
    grep -q '\$HOME/.claude' "$TEST_TMP_DIR/start-claude.sh"
    [ $? -eq 0 ]
}

# =============================================================================
# Script Comments Tests
# =============================================================================

@test "start-claude.sh has description comment" {
    grep -q 'startup script' "$TEST_TMP_DIR/start-claude.sh" || \
    grep -q 'Claude Code' "$TEST_TMP_DIR/start-claude.sh"
    [ $? -eq 0 ]
}

@test "start-claude.sh has usage comment" {
    grep -q 'Usage:' "$TEST_TMP_DIR/start-claude.sh"
    [ $? -eq 0 ]
}

# =============================================================================
# Line Count Tests (Script should be minimal)
# =============================================================================

@test "start-claude.sh is concise (under 20 lines)" {
    local line_count=$(wc -l < "$TEST_TMP_DIR/start-claude.sh")
    [ "$line_count" -lt 20 ]
}

# =============================================================================
# Edge Case Tests
# =============================================================================

@test "start-claude.sh handles special characters in arguments" {
    run bash "$TEST_TMP_DIR/start-claude.sh" --msg "Test & special < > chars"
    assert_success
}

@test "start-claude.sh handles empty string argument" {
    run bash "$TEST_TMP_DIR/start-claude.sh" ""
    assert_success
}
