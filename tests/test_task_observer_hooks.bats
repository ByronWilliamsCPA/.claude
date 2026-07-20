#!/usr/bin/env bats
# Tests for the task-observer hook pair added in commit 51e5354:
#   scripts/hooks/task-observer-reminder.sh (SessionStart)
#   scripts/hooks/task-observer-flush-check.py (Stop)
#
# The SessionStart hook records the observation-log line count as a
# per-session baseline. The Stop hook compares the live count against that
# baseline and blocks turn end (once) when a task-oriented session logged
# nothing. These tests sandbox HOME to a temp dir so nothing touches the
# real ~/.claude/skill-observations tree, and drive both scripts purely
# through their documented stdin-JSON contract.

load 'helpers/test_helper'

REMINDER_HOOK="${BATS_TEST_DIRNAME}/../scripts/hooks/task-observer-reminder.sh"
FLUSH_CHECK_HOOK="${BATS_TEST_DIRNAME}/../scripts/hooks/task-observer-flush-check.py"

setup() {
    export TEST_TMP_DIR="${BATS_TEST_TMPDIR:-$(mktemp -d)}"
    export HOME="$TEST_TMP_DIR"
    OBS_DIR="$HOME/.claude/skill-observations"
    STATE_DIR="$OBS_DIR/.state"
    LOG="$OBS_DIR/log.md"
}

teardown() {
    teardown_test_environment
}

# =============================================================================
# helpers
# =============================================================================

run_reminder() {
    # run_reminder <json-payload>
    printf '%s' "$1" | bash "$REMINDER_HOOK"
}

run_flush_check() {
    # run_flush_check <json-payload>
    printf '%s' "$1" | python3 "$FLUSH_CHECK_HOOK"
}

make_payload() {
    # make_payload <session_id> <transcript_path> <stop_hook_active: true|false>
    printf '{"session_id":"%s","transcript_path":"%s","stop_hook_active":%s}' \
        "$1" "$2" "$3"
}

write_baseline() {
    # write_baseline <session_id> <count>
    mkdir -p "$STATE_DIR"
    printf '%s\n' "$2" > "$STATE_DIR/$1.baseline"
}

write_log_with_observations() {
    # write_log_with_observations <n>
    local n="$1"
    mkdir -p "$OBS_DIR"
    : > "$LOG"
    local i
    for ((i = 1; i <= n; i++)); do
        printf '### Observation %d\nSome logged text.\n\n' "$i" >> "$LOG"
    done
}

write_transcript() {
    # write_transcript <path> <tool_use_count> <mutation_count>
    # Emits <tool_use_count> lines each matching the hook's tool_use regex;
    # the first <mutation_count> of them also carry an Edit name, matching
    # the hook's mutating-tool regex; the remainder carry a non-mutating
    # (Bash) name.
    local path="$1"
    local tool_uses="$2"
    local mutations="$3"
    : > "$path"
    local i
    for ((i = 1; i <= tool_uses; i++)); do
        if ((i <= mutations)); then
            printf '{"type":"tool_use","name":"Edit"}\n' >> "$path"
        else
            printf '{"type":"tool_use","name":"Bash"}\n' >> "$path"
        fi
    done
}

# =============================================================================
# SessionStart: task-observer-reminder.sh
# =============================================================================

@test "SessionStart hook writes baseline with correct count and prints reminder" {
    write_log_with_observations 3
    local session_id="sess-baseline-1"
    run run_reminder "{\"session_id\":\"$session_id\"}"
    assert_success
    assert_output_contains "TASK OBSERVATION (active this session):"
    assert_file_exists "$STATE_DIR/$session_id.baseline"
    [ "$(cat "$STATE_DIR/$session_id.baseline")" = "3" ]
}

@test "SessionStart hook with no log.md writes a baseline of 0" {
    local session_id="sess-baseline-2"
    run run_reminder "{\"session_id\":\"$session_id\"}"
    assert_success
    assert_file_exists "$STATE_DIR/$session_id.baseline"
    [ "$(cat "$STATE_DIR/$session_id.baseline")" = "0" ]
}

@test "SessionStart hook rejects a path-traversal session_id and writes no state file" {
    local session_id="../../etc/x"
    run run_reminder "{\"session_id\":\"$session_id\"}"
    assert_success
    # The allowlist blanks the id before any write happens, so the state dir
    # is never even created, and no file lands at the traversal target either.
    [ ! -d "$STATE_DIR" ]
    [ ! -f "$HOME/.claude/etc/x.baseline" ]
}

# =============================================================================
# Stop: task-observer-flush-check.py
# =============================================================================

@test "Stop hook stays silent when no baseline exists for the session" {
    local session_id="sess-nobaseline"
    local transcript="$TEST_TMP_DIR/transcript.jsonl"
    write_transcript "$transcript" 25 1
    local payload
    payload=$(make_payload "$session_id" "$transcript" "false")
    run run_flush_check "$payload"
    assert_success
    [ -z "$output" ]
}

@test "Stop hook stays silent for a low-activity transcript" {
    local session_id="sess-lowactivity"
    write_baseline "$session_id" 0
    local transcript="$TEST_TMP_DIR/transcript.jsonl"
    write_transcript "$transcript" 3 0
    local payload
    payload=$(make_payload "$session_id" "$transcript" "false")
    run run_flush_check "$payload"
    assert_success
    [ -z "$output" ]
}

@test "Stop hook stays silent for 25 tool_use with zero mutating tools" {
    local session_id="sess-nomutation"
    write_baseline "$session_id" 0
    local transcript="$TEST_TMP_DIR/transcript.jsonl"
    write_transcript "$transcript" 25 0
    local payload
    payload=$(make_payload "$session_id" "$transcript" "false")
    run run_flush_check "$payload"
    assert_success
    [ -z "$output" ]
}

@test "Stop hook blocks for 25 tool_use plus one Edit when nothing was logged" {
    local session_id="sess-block"
    write_baseline "$session_id" 0
    local transcript="$TEST_TMP_DIR/transcript.jsonl"
    write_transcript "$transcript" 25 1
    local payload
    payload=$(make_payload "$session_id" "$transcript" "false")
    run run_flush_check "$payload"
    assert_success
    local decision reason
    decision=$(jq -r '.decision' <<< "$output")
    reason=$(jq -r '.reason' <<< "$output")
    [ "$decision" = "block" ]
    [ -n "$reason" ]
}

@test "Stop hook stays silent on the following invocation due to the nudged marker" {
    local session_id="sess-nudge"
    write_baseline "$session_id" 0
    local transcript="$TEST_TMP_DIR/transcript.jsonl"
    write_transcript "$transcript" 25 1
    local payload
    payload=$(make_payload "$session_id" "$transcript" "false")

    run run_flush_check "$payload"
    assert_success
    local decision
    decision=$(jq -r '.decision' <<< "$output")
    [ "$decision" = "block" ]
    assert_file_exists "$STATE_DIR/$session_id.nudged"

    run run_flush_check "$payload"
    assert_success
    [ -z "$output" ]
    assert_file_exists "$STATE_DIR/$session_id.nudged"
}

@test "Stop hook stays silent when the observation count grew past baseline" {
    local session_id="sess-grown"
    write_baseline "$session_id" 0
    write_log_with_observations 1
    local transcript="$TEST_TMP_DIR/transcript.jsonl"
    write_transcript "$transcript" 25 1
    local payload
    payload=$(make_payload "$session_id" "$transcript" "false")
    run run_flush_check "$payload"
    assert_success
    [ -z "$output" ]
}

@test "Stop hook stays silent when stop_hook_active is true" {
    local session_id="sess-active"
    write_baseline "$session_id" 0
    local transcript="$TEST_TMP_DIR/transcript.jsonl"
    write_transcript "$transcript" 25 1
    local payload
    payload=$(make_payload "$session_id" "$transcript" "true")
    run run_flush_check "$payload"
    assert_success
    [ -z "$output" ]
}

@test "Stop hook exits 0 and prints nothing on malformed JSON stdin" {
    run bash -c "printf '%s' '{ not json' | python3 '$FLUSH_CHECK_HOOK'"
    assert_success
    [ -z "$output" ]
}

@test "Stop hook exits 0 and prints nothing on empty stdin" {
    run bash -c "printf '' | python3 '$FLUSH_CHECK_HOOK'"
    assert_success
    [ -z "$output" ]
}
