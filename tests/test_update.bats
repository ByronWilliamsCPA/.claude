#!/usr/bin/env bats
# Tests for update.sh - Global Configuration Update Script

load 'helpers/test_helper'

setup() {
    setup_test_environment
    # Copy update.sh to test location
    cp "$SCRIPTS_DIR/update.sh" "$TEST_TMP_DIR/update.sh"
    chmod +x "$TEST_TMP_DIR/update.sh"

    # Create a proper git repo at ~/.claude
    mkdir -p "$HOME/.claude"
    init_git_repo "$HOME/.claude"

    # Add a remote to simulate origin
    cd "$HOME/.claude"
    git remote add origin "https://github.com/test/repo.git" 2>/dev/null || true

    # Create mock git command that handles various subcommands
    cat > "$TEST_TMP_DIR/mocks/git" << 'EOF'
#!/bin/bash
case "$1" in
    "rev-parse")
        if [ "$2" = "HEAD" ]; then
            echo "abc123"
        elif [ "$2" = "origin/main" ]; then
            echo "abc123"  # Same as HEAD = up to date
        elif [ "$2" = "--short" ]; then
            echo "abc123"
        elif [ "$2" = "--show-toplevel" ]; then
            echo "$HOME/.claude"
        else
            echo "$HOME/.claude"
        fi
        ;;
    "diff")
        if [ "$2" = "--quiet" ]; then
            exit 0  # No changes
        elif [ "$2" = "--name-only" ]; then
            echo ""
        fi
        ;;
    "fetch")
        echo "Fetching origin..."
        ;;
    "pull")
        echo "Already up to date."
        ;;
    "stash")
        echo "Stashed changes"
        ;;
    "log")
        echo "abc123 Latest commit message"
        ;;
    "remote")
        echo "origin"
        ;;
    *)
        echo "git $@"
        ;;
esac
exit 0
EOF
    chmod +x "$TEST_TMP_DIR/mocks/git"
}

teardown() {
    teardown_test_environment
}

# =============================================================================
# Header Tests
# =============================================================================

@test "update.sh displays update message" {
    run bash "$TEST_TMP_DIR/update.sh"
    assert_success
    assert_output_contains "Updating Global Claude Configuration"
}

# =============================================================================
# Directory Check Tests
# =============================================================================

@test "update.sh fails when ~/.claude directory missing" {
    rm -rf "$HOME/.claude"
    run bash "$TEST_TMP_DIR/update.sh"
    assert_failure
    assert_output_contains "Error"
    assert_output_contains "directory not found"
}

@test "update.sh fails when ~/.claude is not a git repository" {
    rm -rf "$HOME/.claude/.git"
    run bash "$TEST_TMP_DIR/update.sh"
    assert_failure
    assert_output_contains "Error"
    assert_output_contains "not a git repository"
}

# =============================================================================
# Local Modifications Tests
# =============================================================================

@test "update.sh detects local modifications" {
    # Create mock git that reports modifications
    cat > "$TEST_TMP_DIR/mocks/git" << 'EOF'
#!/bin/bash
case "$1" in
    "diff")
        if [ "$2" = "--quiet" ]; then
            exit 1  # Modifications detected
        elif [ "$2" = "--name-only" ]; then
            echo "modified_file.txt"
        fi
        ;;
    "stash")
        echo "Saved working directory"
        ;;
    "rev-parse")
        echo "abc123"
        ;;
    "fetch")
        echo "Fetching..."
        ;;
    "pull")
        echo "Already up to date."
        ;;
    "log")
        echo "abc123 commit"
        ;;
    *)
        echo "git $@"
        ;;
esac
exit 0
EOF
    chmod +x "$TEST_TMP_DIR/mocks/git"

    run bash "$TEST_TMP_DIR/update.sh"
    assert_success
    assert_output_contains "Local modifications detected" || assert_output_contains "stash"
}

@test "update.sh stashes local modifications before update" {
    cat > "$TEST_TMP_DIR/mocks/git" << 'EOF'
#!/bin/bash
case "$1" in
    "diff")
        if [ "$2" = "--quiet" ]; then
            exit 1
        elif [ "$2" = "--name-only" ]; then
            echo "file.txt"
        fi
        ;;
    "stash")
        echo "Saved working directory and index state"
        ;;
    "rev-parse")
        echo "abc123"
        ;;
    "fetch")
        echo "Fetching..."
        ;;
    "pull")
        echo "Already up to date."
        ;;
    "log")
        echo "abc123 commit"
        ;;
    *)
        echo "git $@"
        ;;
esac
exit 0
EOF
    chmod +x "$TEST_TMP_DIR/mocks/git"

    run bash "$TEST_TMP_DIR/update.sh"
    assert_success
    assert_output_contains "stash"
}

# =============================================================================
# Git Fetch Tests
# =============================================================================

@test "update.sh fetches latest changes" {
    run bash "$TEST_TMP_DIR/update.sh"
    assert_success
    assert_output_contains "Fetching latest changes"
}

# =============================================================================
# Up-to-Date Tests
# =============================================================================

@test "update.sh reports when already up to date" {
    run bash "$TEST_TMP_DIR/update.sh"
    assert_success
    assert_output_contains "Already up to date"
}

# =============================================================================
# Update Available Tests
# =============================================================================

@test "update.sh pulls when updates available" {
    cat > "$TEST_TMP_DIR/mocks/git" << 'EOF'
#!/bin/bash
case "$1" in
    "diff")
        exit 0
        ;;
    "rev-parse")
        if [ "$2" = "HEAD" ]; then
            echo "abc123"
        elif [ "$2" = "origin/main" ]; then
            echo "def456"  # Different = updates available
        elif [ "$2" = "--short" ]; then
            echo "def456"
        else
            echo "test"
        fi
        ;;
    "fetch")
        echo "Fetching..."
        ;;
    "pull")
        echo "Updating abc123..def456"
        echo "Fast-forward"
        ;;
    "log")
        if [[ "$2" == *".."* ]]; then
            echo "def456 New feature"
            echo "cde234 Bug fix"
        else
            echo "def456 Latest commit"
        fi
        ;;
    *)
        echo "git $@"
        ;;
esac
exit 0
EOF
    chmod +x "$TEST_TMP_DIR/mocks/git"

    run bash "$TEST_TMP_DIR/update.sh"
    assert_success
    assert_output_contains "Updates available"
}

@test "update.sh shows changes since last update" {
    cat > "$TEST_TMP_DIR/mocks/git" << 'EOF'
#!/bin/bash
case "$1" in
    "diff")
        exit 0
        ;;
    "rev-parse")
        if [ "$2" = "HEAD" ]; then
            echo "abc123"
        elif [ "$2" = "origin/main" ]; then
            echo "def456"
        elif [ "$2" = "--short" ]; then
            echo "def456"
        else
            echo "test"
        fi
        ;;
    "fetch")
        echo "Fetching..."
        ;;
    "pull")
        echo "Updated"
        ;;
    "log")
        echo "def456 New feature"
        ;;
    *)
        echo "git $@"
        ;;
esac
exit 0
EOF
    chmod +x "$TEST_TMP_DIR/mocks/git"

    run bash "$TEST_TMP_DIR/update.sh"
    assert_success
    assert_output_contains "Changes since last update"
}

# =============================================================================
# Completion Message Tests
# =============================================================================

@test "update.sh shows completion message" {
    run bash "$TEST_TMP_DIR/update.sh"
    assert_success
    assert_output_contains "up to date"
}

@test "update.sh displays available commands" {
    run bash "$TEST_TMP_DIR/update.sh"
    assert_success
    assert_output_contains "Available universal commands"
}

@test "update.sh mentions lint-check command" {
    run bash "$TEST_TMP_DIR/update.sh"
    assert_success
    assert_output_contains "lint-check"
}

@test "update.sh mentions security-validate command" {
    run bash "$TEST_TMP_DIR/update.sh"
    assert_success
    assert_output_contains "security-validate"
}

@test "update.sh mentions format-code command" {
    run bash "$TEST_TMP_DIR/update.sh"
    assert_success
    assert_output_contains "format-code"
}

@test "update.sh mentions git-workflow command" {
    run bash "$TEST_TMP_DIR/update.sh"
    assert_success
    assert_output_contains "git-workflow"
}

# =============================================================================
# Error Recovery Suggestions Tests
# =============================================================================

@test "update.sh provides setup instructions on directory missing" {
    rm -rf "$HOME/.claude"
    run bash "$TEST_TMP_DIR/update.sh"
    assert_failure
    assert_output_contains "git clone"
}

@test "update.sh provides recovery instructions on non-git directory" {
    rm -rf "$HOME/.claude/.git"
    run bash "$TEST_TMP_DIR/update.sh"
    assert_failure
    assert_output_contains "rm -rf"
    assert_output_contains "git clone"
}

# =============================================================================
# Script Structure Tests
# =============================================================================

@test "update.sh uses set -e" {
    head -20 "$TEST_TMP_DIR/update.sh" | grep -q 'set -e'
    [ $? -eq 0 ]
}

@test "update.sh defines CLAUDE_DIR variable" {
    grep -q 'CLAUDE_DIR=' "$TEST_TMP_DIR/update.sh"
    [ $? -eq 0 ]
}

# =============================================================================
# Git Operations Tests
# =============================================================================

@test "update.sh checks for git directory" {
    grep -q '\.git' "$TEST_TMP_DIR/update.sh"
    [ $? -eq 0 ]
}

@test "update.sh uses git fetch origin" {
    grep -q 'git fetch origin' "$TEST_TMP_DIR/update.sh"
    [ $? -eq 0 ]
}

@test "update.sh uses git pull origin main" {
    grep -q 'git pull origin main' "$TEST_TMP_DIR/update.sh"
    [ $? -eq 0 ]
}

@test "update.sh compares LOCAL and REMOTE commits" {
    grep -q 'LOCAL=' "$TEST_TMP_DIR/update.sh"
    [ $? -eq 0 ]
    grep -q 'REMOTE=' "$TEST_TMP_DIR/update.sh"
    [ $? -eq 0 ]
}
