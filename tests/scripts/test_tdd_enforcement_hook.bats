#!/usr/bin/env bats
# =============================================================================
# Encodes the TDD-enforcement opt-in contract for scripts/tdd-enforcement-hook.sh.
#
# Review finding: the current hook enforces TDD unconditionally for every
# recognized language extension, with no per-project opt-in, and blocks
# Go/Rust/PHP files outright because their TEST_FILES array is always empty
# (no branch in the hook's case/esac populates it, so the "no test found"
# path is unreachable to satisfy for those languages).
#
# This suite is written against the intended CONTRACT, not the current
# implementation:
#   - Without an opt-in marker (.claude/tdd-enforce in CLAUDE_PROJECT_DIR),
#     the hook must not block anything.
#   - With the marker present, Python (a language the hook can actually test
#     for) must block when no sibling test file exists, and must allow when
#     one does.
#   - With the marker present, a language the hook cannot verify (Go) must
#     warn, not block, since blocking on an unreachable test-detection path
#     is a false enforcement rather than a real gate.
#
# It intentionally FAILS against the current hook (no opt-in gate exists, and
# Go always blocks). The fix lands in a later task; this file exists to prove
# the defect and pin the target behavior.
#
# Mechanics note: the hook reads its JSON envelope from stdin. Piping stdin
# directly into bats' `run` does not work (`run` expects a single command,
# not the tail of a pipeline), and a bare pipeline that returns nonzero fails
# the test line under bats' errexit semantics before `run` can capture it.
# Instead, `run` wraps a `bash -c '...'` subshell that performs the pipe
# internally, so `run` captures the *subshell's* exit status, which is the
# hook's own exit status (the printf/pipe succeeds regardless of what the
# hook does with the piped input).
# =============================================================================

setup() {
    SCRIPT="$BATS_TEST_DIRNAME/../../scripts/tdd-enforcement-hook.sh"
    WORK="$(mktemp -d)"
    export CLAUDE_PROJECT_DIR="$WORK"
}

teardown() {
    rm -rf "$WORK"
}

# Runs the hook with a Write-tool JSON envelope for the given file path.
# Populates $status (bats-captured exit code) and $output. Arguments are
# passed positionally into the bash -c subshell (not string-interpolated
# into the script body) so paths never need manual shell-quoting.
run_hook() {
    local file_path="$1"
    run bash -c 'printf "%s" "$1" | bash "$2"' _ \
        "{\"tool_name\":\"Write\",\"tool_input\":{\"file_path\":\"${file_path}\"}}" \
        "$SCRIPT"
}

@test "go file without tests is NOT blocked when project has not opted in" {
    run_hook "$WORK/main.go"
    [ "$status" -eq 0 ]
}

@test "python file without tests is NOT blocked when project has not opted in" {
    run_hook "$WORK/app.py"
    [ "$status" -eq 0 ]
}

@test "python file without tests IS blocked when project opted in" {
    mkdir -p "$WORK/.claude"
    touch "$WORK/.claude/tdd-enforce"
    run_hook "$WORK/app.py"
    [ "$status" -eq 2 ]
}

@test "go file without tests warns but does not block even when opted in" {
    mkdir -p "$WORK/.claude"
    touch "$WORK/.claude/tdd-enforce"
    run_hook "$WORK/main.go"
    [ "$status" -eq 0 ]
}

@test "python file WITH sibling test passes when opted in" {
    mkdir -p "$WORK/.claude"
    touch "$WORK/.claude/tdd-enforce"
    printf 'def test_x():\n    pass\n' > "$WORK/test_app.py"
    run_hook "$WORK/app.py"
    [ "$status" -eq 0 ]
}
