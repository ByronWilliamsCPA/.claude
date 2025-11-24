#!/usr/bin/env bats
# Tests for setup-env.sh - Environment Variables Setup

load 'helpers/test_helper'

setup() {
    setup_test_environment
    # Copy setup-env.sh to test location
    cp "$SCRIPTS_DIR/setup-env.sh" "$TEST_TMP_DIR/setup-env.sh"
    chmod +x "$TEST_TMP_DIR/setup-env.sh"

    # Create .env.example template
    mkdir -p "$HOME/.claude"
    cat > "$HOME/.claude/.env.example" << 'EOF'
# Test environment configuration
PERPLEXITY_API_KEY=your_key_here
TAVILY_API_KEY=your_key_here
GITHUB_PERSONAL_ACCESS_TOKEN=your_token_here
UPSTASH_REDIS_REST_URL=your_url_here
UPSTASH_REDIS_REST_TOKEN=your_token_here
EOF
}

teardown() {
    teardown_test_environment
}

# =============================================================================
# Script Header Tests
# =============================================================================

@test "setup-env.sh displays header" {
    # When no .env exists, script runs without prompts
    run bash "$TEST_TMP_DIR/setup-env.sh"
    assert_success
    assert_output_contains "Claude Global Configuration"
    assert_output_contains "Environment Setup"
}

# =============================================================================
# .env.example Check Tests
# =============================================================================

@test "setup-env.sh fails when .env.example is missing" {
    rm -f "$HOME/.claude/.env.example"
    run bash "$TEST_TMP_DIR/setup-env.sh"
    assert_failure
    assert_output_contains "Error"
    assert_output_contains ".env.example not found"
}

# =============================================================================
# New .env Creation Tests
# =============================================================================

@test "setup-env.sh creates .env from template when none exists" {
    run bash "$TEST_TMP_DIR/setup-env.sh"
    assert_success
    assert_file_exists "$HOME/.claude/.env"
    assert_output_contains "Created"
}

@test "setup-env.sh copies template content to .env" {
    run bash "$TEST_TMP_DIR/setup-env.sh"
    assert_success
    assert_file_contains "$HOME/.claude/.env" "PERPLEXITY_API_KEY"
    assert_file_contains "$HOME/.claude/.env" "TAVILY_API_KEY"
    assert_file_contains "$HOME/.claude/.env" "GITHUB_PERSONAL_ACCESS_TOKEN"
}

@test "setup-env.sh sets secure permissions on .env" {
    run bash "$TEST_TMP_DIR/setup-env.sh"
    assert_success

    # Check permissions (600 = owner read/write only)
    local perms=$(stat -c "%a" "$HOME/.claude/.env" 2>/dev/null || stat -f "%Lp" "$HOME/.claude/.env" 2>/dev/null)
    [ "$perms" = "600" ]
}

# =============================================================================
# Existing .env Handling Tests
# =============================================================================

@test "setup-env.sh warns when .env already exists" {
    touch "$HOME/.claude/.env"
    run bash -c "echo '1' | bash '$TEST_TMP_DIR/setup-env.sh'"
    assert_output_contains "Warning"
    assert_output_contains "already exists"
}

@test "setup-env.sh offers options when .env exists" {
    touch "$HOME/.claude/.env"
    run bash -c "echo '3' | bash '$TEST_TMP_DIR/setup-env.sh'"
    assert_output_contains "Options:"
    assert_output_contains "Keep existing"
    assert_output_contains "Create new"
    assert_output_contains "Exit"
}

@test "setup-env.sh option 1 keeps existing .env" {
    echo "original_content" > "$HOME/.claude/.env"
    run bash -c "echo '1' | bash '$TEST_TMP_DIR/setup-env.sh'"
    assert_success
    assert_output_contains "Keeping existing"
    assert_file_contains "$HOME/.claude/.env" "original_content"
}

@test "setup-env.sh option 2 backs up existing .env" {
    echo "original_content" > "$HOME/.claude/.env"
    run bash -c "echo '2' | bash '$TEST_TMP_DIR/setup-env.sh'"
    assert_success
    assert_output_contains "Backed up"

    # Check backup exists
    local backup_count=$(ls "$HOME/.claude/.env.backup."* 2>/dev/null | wc -l)
    [ "$backup_count" -gt 0 ]
}

@test "setup-env.sh option 3 exits without changes" {
    touch "$HOME/.claude/.env"
    run bash -c "echo '3' | bash '$TEST_TMP_DIR/setup-env.sh'"
    assert_success
    assert_output_contains "Exiting"
}

@test "setup-env.sh handles invalid option" {
    touch "$HOME/.claude/.env"
    run bash -c "echo '9' | bash '$TEST_TMP_DIR/setup-env.sh'"
    assert_failure
    assert_output_contains "Invalid choice"
}

# =============================================================================
# Next Steps Output Tests
# =============================================================================

@test "setup-env.sh displays next steps" {
    run bash "$TEST_TMP_DIR/setup-env.sh"
    assert_success
    assert_output_contains "Next Steps"
    assert_output_contains "Edit"
    assert_output_contains "add your API keys"
}

@test "setup-env.sh lists required API keys" {
    run bash "$TEST_TMP_DIR/setup-env.sh"
    assert_success
    assert_output_contains "PERPLEXITY_API_KEY"
    assert_output_contains "TAVILY_API_KEY"
    assert_output_contains "GITHUB_PERSONAL_ACCESS_TOKEN"
}

@test "setup-env.sh lists infrastructure keys" {
    run bash "$TEST_TMP_DIR/setup-env.sh"
    assert_success
    assert_output_contains "UPSTASH_REDIS"
    assert_output_contains "SENTRY"
}

@test "setup-env.sh displays security notes" {
    run bash "$TEST_TMP_DIR/setup-env.sh"
    assert_success
    assert_output_contains "Security Notes"
    assert_output_contains "restricted permissions"
    assert_output_contains "ignored by Git"
}

# =============================================================================
# Editor Suggestions Tests
# =============================================================================

@test "setup-env.sh suggests editors for editing" {
    run bash "$TEST_TMP_DIR/setup-env.sh"
    assert_success
    assert_output_contains "nano"
    assert_output_contains "vim"
}

# =============================================================================
# Script Structure Tests
# =============================================================================

@test "setup-env.sh uses set -e" {
    head -20 "$TEST_TMP_DIR/setup-env.sh" | grep -q 'set -e'
    [ $? -eq 0 ]
}

@test "setup-env.sh defines CLAUDE_DIR variable" {
    grep -q 'CLAUDE_DIR=' "$TEST_TMP_DIR/setup-env.sh"
    [ $? -eq 0 ]
}

@test "setup-env.sh defines ENV_FILE variable" {
    grep -q 'ENV_FILE=' "$TEST_TMP_DIR/setup-env.sh"
    [ $? -eq 0 ]
}

@test "setup-env.sh defines ENV_EXAMPLE variable" {
    grep -q 'ENV_EXAMPLE=' "$TEST_TMP_DIR/setup-env.sh"
    [ $? -eq 0 ]
}

# =============================================================================
# Backup Timestamp Tests
# =============================================================================

@test "setup-env.sh backup includes timestamp" {
    echo "content" > "$HOME/.claude/.env"
    run bash -c "echo '2' | bash '$TEST_TMP_DIR/setup-env.sh'"
    assert_success

    # Check that backup file has timestamp pattern (YYYYMMDD_HHMMSS)
    local backup_files=$(ls "$HOME/.claude/.env.backup."* 2>/dev/null)
    [[ "$backup_files" =~ [0-9]{8}_[0-9]{6} ]]
}
