#!/bin/bash
# BATS Test Helper Functions
# Common utilities for all test files

# Get the path to the scripts directory
# BATS_TEST_DIRNAME is the directory containing the test file (e.g., /home/user/.claude/tests)
# Scripts are at /home/user/.claude/scripts
SCRIPTS_DIR="${BATS_TEST_DIRNAME}/../scripts"
FIXTURES_DIR="${BATS_TEST_DIRNAME}/fixtures"

# Create a temporary directory for tests
setup_test_environment() {
    export TEST_TMP_DIR="${BATS_TEST_TMPDIR:-$(mktemp -d)}"
    export CLAUDE_CONFIG_DIR="$TEST_TMP_DIR/.claude"
    export HOME="$TEST_TMP_DIR"
    mkdir -p "$CLAUDE_CONFIG_DIR"
    mkdir -p "$TEST_TMP_DIR/dev/zen-mcp-server/.zen_venv/bin"
    mkdir -p "$TEST_TMP_DIR/mocks"
    touch "$TEST_TMP_DIR/dev/zen-mcp-server/server.py"
    touch "$TEST_TMP_DIR/dev/zen-mcp-server/.zen_venv/bin/python"
    # Pre-create .env.mcp to avoid interactive prompt in install.sh
    touch "$CLAUDE_CONFIG_DIR/.env.mcp"
    # Add mocks to PATH
    export PATH="$TEST_TMP_DIR/mocks:$PATH"
}

# Clean up test environment
teardown_test_environment() {
    if [ -n "$TEST_TMP_DIR" ] && [ -d "$TEST_TMP_DIR" ]; then
        rm -rf "$TEST_TMP_DIR"
    fi
}

# Create a mock command
mock_command() {
    local cmd_name="$1"
    local exit_code="${2:-0}"
    local output="${3:-}"

    local mock_dir="$TEST_TMP_DIR/mocks"
    mkdir -p "$mock_dir"

    cat > "$mock_dir/$cmd_name" << EOF
#!/bin/bash
echo "$output"
exit $exit_code
EOF
    chmod +x "$mock_dir/$cmd_name"
    export PATH="$mock_dir:$PATH"
}

# Create a failing mock command
mock_command_fail() {
    local cmd_name="$1"
    local error_msg="${2:-Command failed}"
    mock_command "$cmd_name" 1 "$error_msg"
}

# Assert that a file exists
assert_file_exists() {
    local file="$1"
    [ -f "$file" ] || {
        echo "Expected file to exist: $file"
        return 1
    }
}

# Assert that a directory exists
assert_dir_exists() {
    local dir="$1"
    [ -d "$dir" ] || {
        echo "Expected directory to exist: $dir"
        return 1
    }
}

# Assert that a file contains a string
assert_file_contains() {
    local file="$1"
    local expected="$2"
    grep -q "$expected" "$file" || {
        echo "Expected file '$file' to contain: $expected"
        echo "Actual contents:"
        cat "$file"
        return 1
    }
}

# Assert that output contains a string
assert_output_contains() {
    local expected="$1"
    [[ "$output" == *"$expected"* ]] || {
        echo "Expected output to contain: $expected"
        echo "Actual output: $output"
        return 1
    }
}

# Assert that output does not contain a string
assert_output_not_contains() {
    local unexpected="$1"
    [[ "$output" != *"$unexpected"* ]] || {
        echo "Expected output NOT to contain: $unexpected"
        echo "Actual output: $output"
        return 1
    }
}

# Assert exit status
assert_success() {
    [ "$status" -eq 0 ] || {
        echo "Expected success (exit 0), got exit $status"
        echo "Output: $output"
        return 1
    }
}

assert_failure() {
    [ "$status" -ne 0 ] || {
        echo "Expected failure (exit non-zero), got exit 0"
        echo "Output: $output"
        return 1
    }
}

# Create a minimal .env.example file
create_env_example() {
    cat > "$CLAUDE_CONFIG_DIR/.env.example" << 'EOF'
# Test environment configuration
PERPLEXITY_API_KEY=test_key
TAVILY_API_KEY=test_key
GITHUB_PERSONAL_ACCESS_TOKEN=test_token
EOF
}

# Create a minimal settings.json file
create_settings_json() {
    cat > "$CLAUDE_CONFIG_DIR/settings.json" << 'EOF'
{
    "theme": "dark",
    "enableAllProjectMcpServers": true
}
EOF
}

# Create a minimal CLAUDE.md file
create_claude_md() {
    cat > "$CLAUDE_CONFIG_DIR/CLAUDE.md" << 'EOF'
# Test CLAUDE.md
Test configuration file.
EOF
}

# Initialize a git repo in a directory
init_git_repo() {
    local dir="${1:-$TEST_TMP_DIR}"
    cd "$dir" || return 1
    git init --quiet
    git config user.email "test@test.com"
    git config user.name "Test User"
    touch .gitkeep
    git add .gitkeep
    git commit -m "Initial commit" --quiet
    cd - > /dev/null || return 1
}

# Source a script's functions without running main
source_script_functions() {
    local script="$1"
    # Override the main function to prevent execution
    main() { :; }
    source "$script"
}
